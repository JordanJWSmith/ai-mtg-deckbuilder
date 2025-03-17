# services/deck_constructor.py
from typing import Dict, List, Any, Optional
import json
from collections import defaultdict

from rag.synergy_detector import SynergyDetector
from rag.mana_base_calculator import ManaBaseCalculator

class DeckConstructorService:
    """Service responsible for constructing a coherent deck from a card pool"""
    
    def __init__(self, openai_client, card_db, vector_db):
        self.openai = openai_client
        self.card_db = card_db
        self.synergy_detector = SynergyDetector(openai_client, vector_db)
        self.mana_base_calculator = ManaBaseCalculator(card_db)
    
    async def construct_deck(self, 
                           card_pool: List[Dict[str, Any]], 
                           deck_params: Dict[str, Any],
                           format_name: str,
                           specific_cards: Optional[List[str]] = None) -> Dict[str, int]:
        """
        Construct a complete MTG deck based on the provided card pool and parameters
        
        Args:
            card_pool: List of card objects from the RAG engine
            deck_params: Extracted deck parameters
            format_name: Format for deck construction (Standard, Modern, etc.)
            specific_cards: List of specific cards to include in the deck
            
        Returns:
            Dictionary mapping card names to quantities
        """
        # Initialize deck
        deck = {}
        
        # Add specific cards if provided
        if specific_cards:
            for card_name in specific_cards:
                card_data = self.card_db.get_card_by_name(card_name)
                if card_data and self._is_card_legal(card_data, format_name):
                    deck[card_name] = 1  # Start with one copy, will adjust later
        
        # Calculate synergy scores for cards in the pool
        synergy_scores = await self.synergy_detector.calculate_synergies(
            card_pool, 
            deck_params["primary_strategy"],
            deck_params.get("mechanics", [])
        )
        
        # Group cards by type for better deck construction
        card_groups = self._group_cards_by_type(card_pool)
        
        # Determine deck composition based on strategy
        composition = self._determine_deck_composition(
            deck_params["primary_strategy"],
            deck_params.get("secondary_strategy", ""),
            format_name
        )
        
        # Select cards based on composition and synergy scores
        deck = self._select_cards(
            deck if deck else {},
            card_groups,
            synergy_scores,
            composition,
            format_name
        )
        
        # Calculate mana base
        mana_base = self.mana_base_calculator.calculate_mana_base(
            deck, 
            deck_params["colors"],
            format_name
        )
        
        # Combine non-land cards with mana base
        deck.update(mana_base)
        
        # Adjust quantities to meet format requirements
        deck = self._adjust_quantities(deck, format_name)
        
        # Ensure deck meets format rules
        deck = self._validate_deck(deck, format_name)
        
        return deck
    
    def _group_cards_by_type(self, card_pool: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group cards by their primary type"""
        card_groups = defaultdict(list)
        
        for card in card_pool:
            card_type = self._get_primary_type(card)
            card_groups[card_type].append(card)
        
        return card_groups
    
    def _get_primary_type(self, card: Dict[str, Any]) -> str:
        """Get the primary type of a card"""
        types = card.get("types", [])
        
        # Common primary types in order of precedence
        primary_types = ["Creature", "Planeswalker", "Instant", "Sorcery", "Artifact", "Enchantment", "Land"]
        
        for ptype in primary_types:
            if ptype in types:
                return ptype
        
        return "Other"
    
    def _determine_deck_composition(self, primary_strategy: str, secondary_strategy: str, format_name: str) -> Dict[str, int]:
        """Determine deck composition based on strategy"""
        composition = {
            "Creature": 0,
            "Planeswalker": 0,
            "Instant": 0,
            "Sorcery": 0,
            "Artifact": 0,
            "Enchantment": 0,
            "Land": 0
        }
        
        # Calculate non-land card count based on format
        non_land_count = 36 if format_name.lower() == "commander" else 36
        land_count = 24 if format_name.lower() == "commander" else 24
        
        # Adjust composition based on primary strategy
        if primary_strategy.lower() == "aggro":
            composition["Creature"] = int(non_land_count * 0.6)
            composition["Instant"] = int(non_land_count * 0.15)
            composition["Sorcery"] = int(non_land_count * 0.1)
            composition["Artifact"] = int(non_land_count * 0.05)
            composition["Enchantment"] = int(non_land_count * 0.05)
            composition["Planeswalker"] = int(non_land_count * 0.05)
        elif primary_strategy.lower() == "control":
            composition["Creature"] = int(non_land_count * 0.25)
            composition["Instant"] = int(non_land_count * 0.3)
            composition["Sorcery"] = int(non_land_count * 0.2)
            composition["Artifact"] = int(non_land_count * 0.05)
            composition["Enchantment"] = int(non_land_count * 0.1)
            composition["Planeswalker"] = int(non_land_count * 0.1)
        elif primary_strategy.lower() == "midrange":
            composition["Creature"] = int(non_land_count * 0.45)
            composition["Instant"] = int(non_land_count * 0.2)
            composition["Sorcery"] = int(non_land_count * 0.15)
            composition["Artifact"] = int(non_land_count * 0.05)
            composition["Enchantment"] = int(non_land_count * 0.05)
            composition["Planeswalker"] = int(non_land_count * 0.1)
        elif primary_strategy.lower() == "combo":
            composition["Creature"] = int(non_land_count * 0.3)
            composition["Instant"] = int(non_land_count * 0.25)
            composition["Sorcery"] = int(non_land_count * 0.2)
            composition["Artifact"] = int(non_land_count * 0.1)
            composition["Enchantment"] = int(non_land_count * 0.1)
            composition["Planeswalker"] = int(non_land_count * 0.05)
        else:
            # Default balanced composition
            composition["Creature"] = int(non_land_count * 0.4)
            composition["Instant"] = int(non_land_count * 0.2)
            composition["Sorcery"] = int(non_land_count * 0.15)
            composition["Artifact"] = int(non_land_count * 0.1)
            composition["Enchantment"] = int(non_land_count * 0.1)
            composition["Planeswalker"] = int(non_land_count * 0.05)
        
        # Adjust for secondary strategy if provided
        if secondary_strategy:
            # Implement secondary strategy adjustments here
            pass
        
        # Ensure land count is appropriate
        composition["Land"] = land_count
        
        return composition
    
    def _select_cards(self, 
                     existing_deck: Dict[str, int],
                     card_groups: Dict[str, List[Dict[str, Any]]],
                     synergy_scores: Dict[str, float],
                     composition: Dict[str, int],
                     format_name: str) -> Dict[str, int]:
        """Select cards based on composition and synergy scores"""
        deck = existing_deck.copy()
        
        # Set max copies per card based on format
        max_copies = 1 if format_name.lower() == "commander" else 4
        
        # Track how many cards we've added of each type
        added_counts = {card_type: 0 for card_type in composition}
        
        # Account for cards already in the deck (specific cards)
        for card_name in deck:
            card_data = self.card_db.get_card_by_name(card_name)
            if card_data:
                card_type = self._get_primary_type(card_data)
                added_counts[card_type] += deck[card_name]
        
        # Sort cards by synergy score within each type
        for card_type, cards in card_groups.items():
            # Skip lands, they're handled separately
            if card_type == "Land":
                continue
                
            # Sort cards by synergy score in descending order
            sorted_cards = sorted(
                cards, 
                key=lambda x: synergy_scores.get(x["name"], 0),
                reverse=True
            )
            
            # Add cards until we meet the composition target
            for card in sorted_cards:
                if added_counts[card_type] >= composition[card_type]:
                    break
                    
                # Skip if card is already in deck
                if card["name"] in deck:
                    continue
                
                # Add card to deck
                deck[card["name"]] = 1
                added_counts[card_type] += 1
                
                # If card is very high synergy, consider adding more copies
                if synergy_scores.get(card["name"], 0) > 0.8:
                    # Add more copies up to max_copies
                    additional_copies = min(max_copies - 1, composition[card_type] - added_counts[card_type])
                    deck[card["name"]] += additional_copies
                    added_counts[card_type] += additional_copies
        
        return deck
    
    def _adjust_quantities(self, deck: Dict[str, int], format_name: str) -> Dict[str, int]:
        """Adjust card quantities to meet format requirements"""
        # Get format-specific rules
        min_cards = 100 if format_name.lower() == "commander" else 60
        max_copies = 1 if format_name.lower() == "commander" else 4
        
        # Count current deck size
        current_size = sum(deck.values())
        
        # If deck is too small, add more copies of high-synergy cards
        if current_size < min_cards:
            # Sort cards by synergy (would need to pass synergy scores)
            # For now, just add more copies of existing cards
            for card_name in list(deck.keys()):
                if current_size >= min_cards:
                    break
                    
                # Skip basic lands
                card_data = self.card_db.get_card_by_name(card_name)
                if card_data and "Basic" in card_data.get("supertypes", []):
                    continue
                
                # Add more copies up to max_copies
                while deck[card_name] < max_copies and current_size < min_cards:
                    deck[card_name] += 1
                    current_size += 1
        
        # If deck is still too small, add more basic lands
        if current_size < min_cards:
            # Find basic lands in the deck
            basic_lands = [name for name in deck if self._is_basic_land(name)]
            
            # If no basic lands, add some
            if not basic_lands:
                # Add some basic lands based on deck colors
                # This is a placeholder - real implementation would be more sophisticated
                deck["Plains"] = 0
                deck["Island"] = 0
                deck["Swamp"] = 0
                deck["Mountain"] = 0
                deck["Forest"] = 0
                basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
            
            # Add more copies of basic lands
            land_index = 0
            while current_size < min_cards:
                land_name = basic_lands[land_index % len(basic_lands)]
                deck[land_name] = deck.get(land_name, 0) + 1
                current_size += 1
                land_index += 1
        
        return deck
    
    def _validate_deck(self, deck: Dict[str, int], format_name: str) -> Dict[str, int]:
        """Ensure deck meets format rules"""
        # Check format-specific rules
        # For now, just return the deck as is
        return deck
    
    def _is_card_legal(self, card: Dict[str, Any], format_name: str) -> bool:
        """Check if a card is legal in the given format"""
        # Check card legality in the format
        if "legality" in card:
            return card["legality"].get(format_name.lower(), "not_legal") != "not_legal"
        return True
    
    def _is_basic_land(self, card_name: str) -> bool:
        """Check if a card is a basic land"""
        basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
        return card_name in basic_lands
    
    def calculate_mana_curve(self, deck: Dict[str, int]) -> Dict[str, int]:
        """Calculate the mana curve of the deck"""
        mana_curve = defaultdict(int)
        
        for card_name, count in deck.items():
            card_data = self.card_db.get_card_by_name(card_name)
            if card_data:
                # Skip lands
                if "Land" in card_data.get("types", []):
                    continue
                
                # Get mana value
                mana_value = card_data.get("mana_value", card_data.get("cmc", 0))
                
                # Group high mana values
                if mana_value >= 7:
                    mana_curve["7+"] += count
                else:
                    mana_curve[str(mana_value)] += count
        
        return dict(mana_curve)