# rag/synergy_detector.py
from typing import Dict, List, Any, Optional
import json
import asyncio

class SynergyDetector:
    """
    Detects synergies between cards for deck building
    Uses embeddings and LLM to identify cards that work well together
    """
    
    def __init__(self, openai_client, vector_db):
        self.openai = openai_client
        self.vector_db = vector_db
        self.synergy_cache = {}  # Cache for synergy scores
    
    async def calculate_synergies(self, 
                                card_pool: List[Dict[str, Any]], 
                                strategy: str,
                                mechanics: List[str]) -> Dict[str, float]:
        """
        Calculate synergy scores for cards in the pool
        
        Args:
            card_pool: List of card objects
            strategy: Deck strategy (aggro, control, etc.)
            mechanics: List of mechanics to focus on
            
        Returns:
            Dictionary mapping card names to synergy scores
        """
        # Create a cache key based on strategy and mechanics
        cache_key = f"{strategy}_{'-'.join(sorted(mechanics))}"
        
        # Check if we've already calculated synergies for this combination
        if cache_key in self.synergy_cache:
            return self._filter_synergies_for_pool(self.synergy_cache[cache_key], card_pool)
        
        # Extract card names and text for analysis
        card_details = [{"name": card["name"], "text": card.get("text", ""), 
                         "types": card.get("types", []), "cost": card.get("mana_cost", "")} 
                        for card in card_pool]
        
        # Generate strategy embedding
        strategy_prompt = f"""
        Magic: The Gathering deck with:
        Strategy: {strategy}
        Mechanics: {', '.join(mechanics) if mechanics else 'None specified'}
        """
        
        strategy_embedding = await self._generate_embedding(strategy_prompt)
        
        # Calculate relevance scores for each card
        relevance_scores = await self._calculate_relevance_scores(card_details, strategy_embedding)
        
        # Calculate synergy scores with LLM
        synergy_scores = await self._calculate_llm_synergies(card_details, strategy, mechanics)
        
        # Combine relevance and synergy scores
        combined_scores = {}
        for card_name, relevance in relevance_scores.items():
            synergy = synergy_scores.get(card_name, 0.0)
            combined_scores[card_name] = 0.7 * relevance + 0.3 * synergy
        
        # Cache the results
        self.synergy_cache[cache_key] = combined_scores
        
        return combined_scores
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        response = await self.openai.embeddings.create(
            input=text,
            model="text-embedding-3-large"
        )
        return response.data[0].embedding
    
    async def _calculate_relevance_scores(self, 
                                        card_details: List[Dict[str, str]], 
                                        strategy_embedding: List[float]) -> Dict[str, float]:
        """Calculate relevance scores using embeddings"""
        relevance_scores = {}
        
        # Process cards in batches to avoid rate limits
        batch_size = 20
        for i in range(0, len(card_details), batch_size):
            batch = card_details[i:i+batch_size]
            
            # Generate embeddings for cards in batch
            card_texts = [f"{card['name']}: {card['text']}" for card in batch]
            
            # Get embeddings for all cards in batch
            response = await self.openai.embeddings.create(
                input=card_texts,
                model="text-embedding-3-large"
            )
            
            embeddings = [data.embedding for data in response.data]
            
            # Calculate similarity scores
            for j, card in enumerate(batch):
                card_embedding = embeddings[j]
                # Calculate cosine similarity
                similarity = self._cosine_similarity(card_embedding, strategy_embedding)
                relevance_scores[card["name"]] = similarity
        
        return relevance_scores
    
    async def _calculate_llm_synergies(self, 
                                     card_details: List[Dict[str, str]], 
                                     strategy: str,
                                     mechanics: List[str]) -> Dict[str, float]:
        """Calculate synergy scores using LLM"""
        # Process cards in batches
        batch_size = 50
        all_synergy_scores = {}
        
        for i in range(0, len(card_details), batch_size):
            batch = card_details[i:i+batch_size]
            
            # Create prompt for synergy analysis
            card_info = "\n".join([f"Card: {card['name']}\nText: {card['text']}\nTypes: {', '.join(card['types'])}\nMana Cost: {card['cost']}" 
                                  for card in batch])
            
            prompt = f"""
            Analyze the following Magic: The Gathering cards for their synergy with a {strategy} deck 
            that focuses on these mechanics: {', '.join(mechanics) if mechanics else 'No specific mechanics'}.
            
            {card_info}
            
            For each card, provide a synergy score from 0.0 to 1.0, where:
            - 0.0 means the card has no synergy with the strategy
            - 1.0 means the card is perfectly aligned with the strategy
            
            Format your response as a JSON object with card names as keys and scores as values.
            """
            
            # Use OpenAI to analyze synergies
            response = await self.openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a Magic: The Gathering expert analyzing card synergies."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Parse response
            batch_scores = json.loads(response.choices[0].message.content)
            all_synergy_scores.update(batch_scores)
        
        return all_synergy_scores
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm_a = sum(a * a for a in vec1) ** 0.5
        norm_b = sum(b * b for b in vec2) ** 0.5
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot_product / (norm_a * norm_b)
    
    def _filter_synergies_for_pool(self, synergy_scores: Dict[str, float], 
                                  card_pool: List[Dict[str, Any]]) -> Dict[str, float]:
        """Filter synergy scores to only include cards in the pool"""
        card_names = {card["name"] for card in card_pool}
        return {name: score for name, score in synergy_scores.items() if name in card_names}