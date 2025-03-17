# rag/query_engine.py
from typing import Dict, List, Any, Optional
import json

class DeckbuilderRAGQueryEngine:
    """
    RAG Query Engine for Magic: The Gathering deck building
    Retrieves cards based on deck parameters using vector search and metadata filtering
    """
    
    def __init__(self, openai_client, vector_db):
        self.openai = openai_client
        self.vector_db = vector_db
    
    async def retrieve_card_pool(self, deck_params: Dict[str, Any], format_name: str) -> List[Dict[str, Any]]:
        """
        Retrieve relevant card pool based on deck parameters
        
        Args:
            deck_params: Extracted deck parameters from user request
            format_name: Format name (Standard, Modern, etc.)
            
        Returns:
            List of card objects that match the deck parameters
        """
        # Build filters for vector search
        filters = self._build_search_filters(deck_params, format_name)
        
        # Generate embeddings for different aspects of the deck concept
        strategy_embedding = await self._generate_concept_embedding(
            deck_params["primary_strategy"],
            deck_params.get("secondary_strategy", ""),
            deck_params["mechanics"]
        )
        
        # Query vector DB for cards matching the deck concept
        strategy_results = self.vector_db.query_cards(
            strategy_embedding, 
            filters=filters,
            top_k=200  # Get a large initial pool
        )
        
        # If win conditions specified, do a separate query for them
        win_condition_cards = []
        if "win_conditions" in deck_params and deck_params["win_conditions"]:
            win_condition_embedding = await self._generate_concept_embedding(
                deck_params["win_conditions"], "", []
            )
            win_condition_results = self.vector_db.query_cards(
                win_condition_embedding,
                filters=filters,
                top_k=50
            )
            win_condition_cards = [result["metadata"] for result in win_condition_results["matches"]]
        
        # Combine and deduplicate results
        all_cards = [result["metadata"] for result in strategy_results["matches"]]
        all_cards.extend(win_condition_cards)
        
        # Remove duplicates based on card name
        seen_names = set()
        unique_cards = []
        for card in all_cards:
            if card["name"] not in seen_names:
                seen_names.add(card["name"])
                unique_cards.append(card)
        
        return unique_cards
    
    def _build_search_filters(self, deck_params: Dict[str, Any], format_name: str) -> Dict[str, Any]:
        """Build vector database filters based on deck parameters"""
        # Get color filter
        colors = deck_params.get("colors", [])
        
        # Build format filter (for legality)
        format_filter = {"formats": format_name.lower()}
        
        # Build color filter (match cards within the color identity)
        color_filter = {}
        if colors:
            # Handle multicolor decks vs mono decks differently
            if len(colors) > 1:
                # For multicolor, allow cards that have any of the specified colors
                color_filter = {"colors": {"$in": colors}}
            else:
                # For mono, strictly match the single color
                color_filter = {"colors": colors[0]}
        
        # Combine filters
        return {
            "$and": [
                format_filter,
                color_filter
            ]
        }
    
    async def _generate_concept_embedding(self, 
                                         primary_strategy: str, 
                                         secondary_strategy: str = "", 
                                         mechanics: List[str] = None) -> List[float]:
        """Generate embedding for a deck concept"""
        # Create rich prompt to capture the deck concept
        concept_text = f"""
        Magic: The Gathering deck with these characteristics:
        Primary strategy: {primary_strategy}
        {"Secondary strategy: " + secondary_strategy if secondary_strategy else ""}
        {"Key mechanics: " + ', '.join(mechanics) if mechanics else ""}
        """
        
        # Generate embedding
        response = await self.openai.embeddings.create(
            input=concept_text,
            model="text-embedding-3-large"
        )
        
        return response.data[0].embedding