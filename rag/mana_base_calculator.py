class ManaBaseCalculator:
    def __init__(self, card_db):
        self.card_db = card_db
        
    async def calculate_mana_base(self, deck_colors, format_name, spell_count, mana_requirements):
        """Calculate optimal mana base for a deck"""
        # Get format-legal lands
        legal_lands = await self.card_db.get_format_legal_lands(format_name)
        
        # Filter by color identity
        color_identity = "".join(sorted(deck_colors))
        matching_lands = [land for land in legal_lands if self._matches_color_identity(land, color_identity)]
        
        # Categorize lands
        land_categories = {
            "dual_lands": [],
            "fetch_lands": [],
            "shock_lands": [],
            "basic_lands": [],
            "utility_lands": [],
            "tri_lands": [],
            "pain_lands": []
        }
        
        for land in matching_lands:
            category = self._categorize_land(land)
            if category in land_categories:
                land_categories[category].append(land)
        
        # Calculate land count
        total_land_count = self._calculate_total_land_count(
            spell_count, 
            format_name, 
            mana_requirements
        )
        
        # Distribute lands by category
        land_distribution = self._distribute_lands(
            land_categories, 
            total_land_count, 
            deck_colors, 
            mana_requirements
        )
        
        return {
            "total_land_count": total_land_count,
            "land_distribution": land_distribution
        }
    
    def _matches_color_identity(self, land, color_identity):
        """Check if a land matches the deck's color identity"""
        # Implementation depends on card data structure
        land_colors = set(land.get("color_identity", []))
        return land_colors.issubset(set(color_identity))
    
    def _categorize_land(self, land):
        """Categorize a land by its type"""
        # Logic to categorize lands based on their characteristics
        text = land.get("oracle_text", "").lower()
        
        if "search your library for a" in text and "land" in text:
            return "fetch_lands"
        elif "enters the battlefield" in text and "pay 2 life" in text:
            return "shock_lands"
        elif "enters the battlefield tapped" in text and any(f"add {c}" in text for c in "WUBRG"):
            return "dual_lands"
        elif land.get("type_line", "").lower() == "basic land":
            return "basic_lands"
        # Add more categorization logic...
        
        return "utility_lands"
    
    def _calculate_total_land_count(self, spell_count, format_name, mana_requirements):
        """Calculate total land count based on spell count and format"""
        # Base land count by format
        format_base = {
            "standard": 24,
            "modern": 22,
            "commander": 38,
            "legacy": 20,
            "vintage": 18
        }
        
        base_count = format_base.get(format_name.lower(), 24)
        
        # Adjust based on average CMC
        avg_cmc = sum(mana_requirements.values()) / len(mana_requirements)
        cmc_adjustment = round((avg_cmc - 2.5) * 2)  # +/- 2 lands per +/- 1.0 average CMC
        
        return base_count + cmc_adjustment
    
    def _distribute_lands(self, land_categories, total_land_count, deck_colors, mana_requirements):
        """Distribute lands across categories"""
        # Calculate color proportions
        total_pips = sum(mana_requirements.values())
        color_proportions = {color: mana_requirements.get(color, 0) / total_pips for color in deck_colors}
        
        # Distribute lands
        distribution = {}
        
        # Prioritize fixing for multicolor decks
        if len(deck_colors) > 1:
            # Assign dual lands first
            dual_land_count = min(12, total_land_count // 3)
            for land in land_categories["dual_lands"][:dual_land_count]:
                distribution[land["name"]] = distribution.get(land["name"], 0) + 1
            
            # Assign fetch lands
            fetch_land_count = min(8, total_land_count // 4)
            for land in land_categories["fetch_lands"][:fetch_land_count]:
                distribution[land["name"]] = distribution.get(land["name"], 0) + 1
            
            # Fill remaining with basics proportional to color requirements
            remaining = total_land_count - sum(distribution.values())
            for color in deck_colors:
                basic_name = f"Basic {color}"
                count = round(remaining * color_proportions.get(color, 0))
                distribution[basic_name] = distribution.get(basic_name, 0) + count
        else:
            # Mono-color deck - mostly basics with some utility lands
            utility_count = min(4, total_land_count // 6)
            for land in land_categories["utility_lands"][:utility_count]:
                distribution[land["name"]] = distribution.get(land["name"], 0) + 1
                
            # Fill rest with basics
            remaining = total_land_count - sum(distribution.values())
            basic_name = f"Basic {deck_colors[0]}"
            distribution[basic_name] = distribution.get(basic_name, 0) + remaining
        
        return distribution