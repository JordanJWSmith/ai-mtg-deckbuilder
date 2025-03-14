class DeckConstructor:
    def __init__(self, openai_client):
        self.openai = openai_client
        
    async def construct_deck(self, card_pool, deck_params, format_name, specific_cards=None):
        # Group cards by function (lands, creatures, spells, etc.)
        categorized_cards = self._categorize_cards(card_pool)
        
        # Start with required cards if specified
        deck = []
        if specific_cards:
            deck = specific_cards
            
        # Determine appropriate land count based on format and strategy
        land_count = self._determine_land_count(format_name, deck_params['strategy'])
        
        # Build mana base
        mana_base = await self._build_mana_base(
            categorized_cards['lands'], 
            deck_params['colors'],
            land_count
        )
        deck.extend(mana_base)
        
        # Use LLM to select the rest of the deck
        remaining_cards = await self._select_nonland_cards(
            categorized_cards,
            deck_params,
            specific_cards,
            format_name,
            60 - len(deck)  # Adjust for other formats
        )
        deck.extend(remaining_cards)
        
        return deck