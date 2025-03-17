# rag/mana_base_calculator.py
from typing import Dict, List, Any
from collections import defaultdict

class ManaBaseCalculator:
    """
    Calculates the appropriate mana base for a deck
    Considers color distribution, mana curve, and format requirements
    """
    
    def __init__(self, card_db):
        self.card_db = card_db
    
    def calculate_mana_base(self, 
                           deck: Dict[str, int], 
                           colors: List[str],
                           format_name: str) -> Dict[str, int]:
        """
        Calculate the mana base for a deck
        
        Args:
            deck: Dictionary of non-land cards in the deck
            colors: List of colors in the deck
            format_name: Format for the deck
            
        Returns:
            Dictionary of land cards to add to the deck
        """
        # Calculate color requirements
        color_requirements = self._calculate_color_requirements(deck)
        
        # Determine total land count
        total_land_count = self._determine_land_count(deck, format_name)
        
        # Calculate color distribution
        color_distribution = self._calculate_color_distribution(color_requirements)
        
        # Build mana base
        mana_base = {}
        
        # Add basic lands based on color distribution
        basic_lands = {
            "W": "Plains",
            "U": "Island",
            "B": "Swamp",
            "R": "Mountain",
            "G": "Forest"
        }
        
        # Calculate how many lands of each color to add
        remaining_lands = total_land_count
        for color, percentage in color_distribution.items():
            if color in basic_lands:
                count = int(total_land_count * percentage)
                mana_base[basic_lands[color]] = count
                remaining_lands -= count
        
        # Distribute any remaining lands
        if remaining_lands > 0:
            # Add remaining lands to the colors with highest requirements
            sorted_colors = sorted(color_distribution.items(), key=lambda x: x[1], reverse=True)
            for color, _ in sorted_colors:
                if remaining_lands <= 0:
                    break
                if color in basic_lands:
                    mana_base[basic_lands[color]] = mana_base.get(basic_lands[color], 0) + 1
                    remaining_lands -= 1
        
        return mana_base
    
    def _calculate_color_requirements(self, deck: Dict[str, int]) -> Dict[str, int]:
        """Calculate color requirements based on mana costs"""
        color_requirements = defaultdict(int)
        
        for card_name, count in deck.items():
            card_data = self.card_db.get_card_by_name(card_name)
            if card_data:
                # Skip lands
                if "Land" in card_data.get("types", []):
                    continue
                
                # Get mana cost
                mana_cost = card_data.get("mana_cost", "")
                
                # Count colored mana symbols
                for color in ["W", "U", "B", "R", "G"]:
                    color_count = mana_cost.count(color)
                    color_requirements[color] += color_count * count
        
        return dict(color_requirements)
    
    def _determine_land_count(self, deck: Dict[str, int], format_name: str) -> int:
        """Determine the appropriate land count for the deck"""
        # Count non-land cards
        non_land_count = 0
        for card_name, count in deck.items():
            card_data = self.card_db.get_card_by_name(card_name)
            if card_data and "Land" not in card_data.get("types", []):
                non_land_count += count
        
        # Calculate average mana value
        total_mana_value = 0
        total_cards = 0
        
        for card_name, count in deck.items():
            card_data = self.card_db.get_card_by_name(card_name)
            if card_data and "Land" not in card_data.get("types", []):
                mana_value = card_data.get("mana_value", card_data.get("cmc", 0))
                total_mana_value += mana_value * count
                total_cards += count
        
        avg_mana_value = total_mana_value / total_cards if total_cards > 0 else 0
        
        # Base land count on average mana value
        if format_name.lower() == "commander":
            return 38  # Commander decks typically run more lands
        elif avg_mana_value >= 4.0:
            return 26  # High curve decks need more lands
        elif avg_mana_value >= 3.0:
            return 24  # Medium curve decks
        else:
            return 22  # Low curve decks
    
    def _calculate_color_distribution(self, color_requirements: Dict[str, int]) -> Dict[str, float]:
        """Calculate color distribution for lands"""
        total_requirements = sum(color_requirements.values())
        
        if total_requirements == 0:
            # If no color requirements, distribute evenly
            num_colors = len(color_requirements)
            if num_colors == 0:
                return {}
            return {color: 1.0 / num_colors for color in color_requirements}
        
        # Calculate percentage for each color
        return {color: count / total_requirements for color, count in color_requirements.items()}