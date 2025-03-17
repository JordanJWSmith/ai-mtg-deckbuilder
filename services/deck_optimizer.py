# services/deck_optimizer.py
from typing import Dict, List, Any, Optional
import json
from collections import defaultdict

from rag.query_engine import DeckbuilderRAGQueryEngine

class DeckOptimizerService:
    """Service responsible for optimizing existing decks"""
    
    def __init__(self, openai_client, vector_db, card_db):
        self.openai = openai_client
        self.vector_db = vector_db
        self.card_db = card_db
        self.query_engine = DeckbuilderRAGQueryEngine(openai_client, vector_db)
    
    async def optimize_deck(self, decklist: Dict[str, int], format_name: str) -> Dict[str, Any]:
        """
        Optimize an existing deck
        
        Args:
            decklist: Dictionary mapping card names to quantities
            format_name: Format for the deck
            
        Returns:
            Dictionary with optimization suggestions and explanations
        """
        # Analyze the deck
        deck_analysis = await self._analyze_deck(decklist, format_name)
        
        # Get current meta trends
        meta_trends = await self._get_meta_trends(format_name)
        
        # Generate replacement suggestions
        suggestions = await self._generate_replacement_suggestions(
            decklist,
            deck_analysis,
            meta_trends,
            format_name
        )
        
        # Generate explanations for suggestions
        explanations = await self._generate_explanations(suggestions, deck_analysis)
        
        return {
            "suggestions": suggestions,
            "explanations": explanations
        }
    
    async def _analyze_deck(self, decklist: Dict[str, int], format_name: str) -> Dict[str, Any]:
        """Analyze the deck for strengths and weaknesses"""
        # Convert decklist to list of cards
        card_list = []
        for card_name, count in decklist.items():
            card_data = self.card_db.get_card_by_name(card_name)
            if card_data:
                card_list.append({
                    "name": card_name,
                    "count": count,
                    "data": card_data
                })
        
        # Create prompt for analysis
        card_info = "\n".join([f"{card['name']} (x{card['count']})" for card in card_list])
        
        prompt = f"""
        Analyze this Magic: The Gathering deck for {format_name} format:

        {card_info}

        Provide a detailed analysis including:
        1. Overall strategy identification
        2. Mana curve analysis
        3. Color distribution
        4. Key strengths
        5. Notable weaknesses
        6. Consistency assessment
        7. Potential improvement areas

        Format your response as a JSON object with these keys.
        """
        
        # Use OpenAI to analyze the deck
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a Magic: The Gathering deck analysis expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse response
        analysis = json.loads(response.choices[0].message.content)
        
        # Add calculated mana curve
        analysis["mana_curve"] = self._calculate_mana_curve(card_list)
        
        # Add color distribution
        analysis["color_distribution"] = self._calculate_color_distribution(card_list)
        
        return analysis
    
    def _calculate_mana_curve(self, card_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """Calculate the mana curve of the deck"""
        mana_curve = defaultdict(int)
        
        for card in card_list:
            # Skip lands
            if card["data"] and "Land" in card["data"].get("types", []):
                continue
            
            # Get mana value
            mana_value = card["data"].get("mana_value", card["data"].get("cmc", 0))
            
            # Group high mana values
            if mana_value >= 7:
                mana_curve["7+"] += card["count"]
            else:
                mana_curve[str(mana_value)] += card["count"]
        
        return dict(mana_curve)
    
    def _calculate_color_distribution(self, card_list: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate color distribution of the deck"""
        color_counts = defaultdict(int)
        total_pips = 0
        
        for card in card_list:
            if not card["data"]:
                continue
                
            # Get mana cost
            mana_cost = card["data"].get("mana_cost", "")
            
            # Count colored mana symbols
            for color in ["W", "U", "B", "R", "G"]:
                color_count = mana_cost.count(color)
                color_counts[color] += color_count * card["count"]
                total_pips += color_count * card["count"]
        
        # Calculate percentages
        color_distribution = {}
        if total_pips > 0:
            for color, count in color_counts.items():
                if count > 0:
                    color_distribution[color] = count / total_pips
        
        return color_distribution
    
    async def _get_meta_trends(self, format_name: str) -> Dict[str, Any]:
        """Get current meta trends for the format"""
        prompt = f"""
        Provide a summary of the current Magic: The Gathering meta for {format_name} format.
        Include:
        1. Top strategies/archetypes
        2. Key staple cards in each color
        3. Popular tech cards
        4. Cards that are gaining popularity
        5. Cards that are falling out of favor

        Format your response as a JSON object with these keys.
        """
        
        # Use OpenAI to get meta trends
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a Magic: The Gathering meta analyst."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse response
        return json.loads(response.choices[0].message.content)
    
    async def _generate_replacement_suggestions(self, 
                                             decklist: Dict[str, int],
                                             analysis: Dict[str, Any],
                                             meta_trends: Dict[str, Any],
                                             format_name: str) -> List[Dict[str, Any]]:
        """Generate suggestions for card replacements"""
        # Identify weak cards using analysis
        weak_cards = []
        for card_name, count in decklist.items():
            card_data = self.card_db.get_card_by_name(card_name)
            if not card_data:
                continue
                
            # Check if card is mentioned in weaknesses
            weaknesses = analysis.get("weaknesses", "").lower()
            improvement_areas = analysis.get("potential_improvement_areas", "").lower()
            
            if card_name.lower() in weaknesses or card_name.lower() in improvement_areas:
                weak_cards.append({
                    "name": card_name,
                    "count": count,
                    "data": card_data
                })
        
        # If no weak cards identified, use heuristics to find candidates
        if not weak_cards:
            weak_cards = self._identify_weak_cards_heuristic(decklist, analysis)
        
        # Get replacement suggestions from RAG
        suggestions = []
        strategy = analysis.get("strategy", "")
        
        # Extract key mechanics from strategy
        mechanics = self._extract_mechanics_from_strategy(strategy)
        
        # Create deck parameters for RAG query
        deck_params = {
            "primary_strategy": analysis.get("overall_strategy_identification", ""),
            "colors": list(analysis.get("color_distribution", {}).keys()),
            "mechanics": mechanics
        }
        
        # Get potential replacements
        for weak_card in weak_cards[:5]:  # Limit to top 5 weak cards
            card_pool = await self.query_engine.retrieve_card_pool(
                deck_params,
                format_name
            )
            
            # Filter card pool to exclude cards already in deck
            filtered_pool = [card for card in card_pool if card["name"] not in decklist]
            
            # Find best replacements
            replacements = await self._find_best_replacements(
                weak_card,
                filtered_pool,
                deck_params,
                meta_trends
            )
            
            # Add to suggestions
            suggestions.append({
                "card_to_replace": weak_card["name"],
                "quantity": weak_card["count"],
                "replacements": replacements
            })
        
        return suggestions
    
    def _identify_weak_cards_heuristic(self, decklist: Dict[str, int], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify weak cards using heuristics"""
        weak_cards = []
        
        # Convert decklist to list of cards with data
        card_list = []
        for card_name, count in decklist.items():
            card_data = self.card_db.get_card_by_name(card_name)
            if card_data:
                card_list.append({
                    "name": card_name,
                    "count": count,
                    "data": card_data
                })
        
        # Calculate average mana value
        total_mv = 0
        total_cards = 0
        for card in card_list:
            if "Land" not in card["data"].get("types", []):
                mv = card["data"].get("mana_value", card["data"].get("cmc", 0))
                total_mv += mv * card["count"]
                total_cards += card["count"]
        
        avg_mv = total_mv / total_cards if total_cards > 0 else 0
        
        # Find cards with mana value far from average
        for card in card_list:
            if "Land" in card["data"].get("types", []):
                continue
                
            mv = card["data"].get("mana_value", card["data"].get("cmc", 0))
            
            # High mana value cards in aggressive decks
            if "aggro" in analysis.get("overall_strategy_identification", "").lower() and mv > avg_mv + 2:
                weak_cards.append(card)
            
            # Low impact high mana cards
            if mv >= 5 and "Creature" in card["data"].get("types", []):
                power = card["data"].get("power", 0)
                toughness = card["data"].get("toughness", 0)
                if int(power) if power else 0 + int(toughness) if toughness else 0 < mv * 2:
                    weak_cards.append(card)
        
        # Sort by "weakness score"
        return sorted(weak_cards, key=lambda x: x["data"].get("mana_value", 0), reverse=True)
    
    def _extract_mechanics_from_strategy(self, strategy: str) -> List[str]:
        """Extract mechanics from strategy description"""
        common_mechanics = [
            "Flying", "Deathtouch", "Lifelink", "Trample", "Haste", "Vigilance",
            "Landfall", "Cascade", "Storm", "Affinity", "Devotion", "Proliferate",
            "Scry", "Surveil", "Explore", "Convoke", "Delve", "Prowess",
            "Threshold", "Kicker", "Cycling", "Flashback", "Escape", "Foretell"
        ]
        
        found_mechanics = []
        for mechanic in common_mechanics:
            if mechanic.lower() in strategy.lower():
                found_mechanics.append(mechanic)
        
        return found_mechanics
    
    async def _find_best_replacements(self, 
                                    weak_card: Dict[str, Any], 
                                    card_pool: List[Dict[str, Any]],
                                    deck_params: Dict[str, Any],
                                    meta_trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find the best replacements for a weak card"""
        # Filter card pool to cards of similar mana value and type
        card_mv = weak_card["data"].get("mana_value", weak_card["data"].get("cmc", 0))
        card_types = weak_card["data"].get("types", [])
        
        # Allow +/- 1 mana value
        min_mv = max(0, card_mv - 1)
        max_mv = card_mv + 1
        
        filtered_pool = []
        for card in card_pool:
            mv = card.get("mana_value", card.get("cmc", 0))
            types = card.get("types", [])
            
            # Check if card has similar mana value and at least one matching type
            if min_mv <= mv <= max_mv and any(t in types for t in card_types):
                filtered_pool.append(card)
        
        # If no matches, broaden search
        if not filtered_pool:
            filtered_pool = [card for card in card_pool if min_mv <= card.get("mana_value", card.get("cmc", 0)) <= max_mv]
        
        # Score replacements
        scored_replacements = []
        staple_cards = self._extract_staple_cards(meta_trends)
        
        for card in filtered_pool[:20]:  # Limit to 20 cards for scoring
            score = await self._score_replacement(card, weak_card, deck_params, staple_cards)
            scored_replacements.append({
                "name": card["name"],
                "score": score
            })
        
        # Sort by score and return top 3
        sorted_replacements = sorted(scored_replacements, key=lambda x: x["score"], reverse=True)
        return sorted_replacements[:3]
    
    def _extract_staple_cards(self, meta_trends: Dict[str, Any]) -> List[str]:
        """Extract staple cards from meta trends"""
        staple_cards = []
        
        # Extract staples from each color
        for color in ["white", "blue", "black", "red", "green"]:
            if f"{color}_staples" in meta_trends:
                staple_cards.extend(meta_trends[f"{color}_staples"])
        
        # Add popular tech cards
        if "popular_tech_cards" in meta_trends:
            staple_cards.extend(meta_trends["popular_tech_cards"])
        
        # Add cards gaining popularity
        if "cards_gaining_popularity" in meta_trends:
            staple_cards.extend(meta_trends["cards_gaining_popularity"])
        
        return staple_cards
    
    async def _score_replacement(self, 
                               replacement: Dict[str, Any], 
                               weak_card: Dict[str, Any],
                               deck_params: Dict[str, Any],
                               staple_cards: List[str]) -> float:
        """Score a replacement card"""
        prompt = f"""
            Score this replacement in a Magic: The Gathering deck:

            Original card: {weak_card['name']}
            Original card details: {weak_card['data'].get('text', 'No details available')}
            Replacement card: {replacement['name']}
            Replacement details: {replacement.get('text', 'No details available')}
            Deck strategy: {deck_params['primary_strategy']}
            Staple cards: {', '.join(staple_cards)}
            Evaluate how well the replacement card fits into the deck as a substitute for the original card. Consider factors such as mana cost, card type, synergy, and overall deck strategy. Provide a numeric score between 0 and 10, where 10 indicates an excellent replacement.
        """
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a Magic: The Gathering deck optimization expert."},
                {"role": "user", "content": prompt}
            ]
        )
        score_str = response.choices[0].message.content.strip()
        try:
            score = float(score_str)
        except ValueError:
            score = 0.0
        return score
    
    async def _generate_explanations(self, suggestions: List[Dict[str, Any]], analysis: Dict[str, Any]) -> Dict[str, str]:
        """Generate explanations for each optimization suggestion"""
        # For simplicity, we'll generate a basic explanation for each suggestion.
        explanations = {}
        for suggestion in suggestions:
            card_to_replace = suggestion["card_to_replace"]
            explanation_prompt = f"""
            Explain why {card_to_replace} might be a weak choice in this deck and how the suggested replacements could improve the deck's performance.
            Deck analysis: {json.dumps(analysis)}
            """
            response = await self.openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a Magic: The Gathering deck optimization expert."},
                    {"role": "user", "content": explanation_prompt}
                ]
            )
            explanations[card_to_replace] = response.choices[0].message.content.strip()
        return explanations