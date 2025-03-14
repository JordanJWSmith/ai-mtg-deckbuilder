import json

class ArchetypeDataGenerator:
    def __init__(self, openai_client, card_db):
        self.openai = openai_client
        self.card_db = card_db
    
    async def generate_archetype_examples(self, archetype_name, format_name, count=10):
        """Generate synthetic decklists for a specific archetype"""
        
        # Get archetype description
        archetype_desc = await self._get_archetype_description(archetype_name, format_name)
        
        # Generate decklists
        decklists = []
        for i in range(count):
            decklist = await self._generate_decklist(archetype_desc, format_name)
            decklists.append(decklist)
        
        return decklists
    
    async def _get_archetype_description(self, archetype_name, format_name):
        """Get detailed description of an archetype"""
        prompt = f"Describe the '{archetype_name}' archetype in the {format_name} format of Magic: The Gathering. Include key cards, strategy, and common patterns."
        
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a Magic: The Gathering expert."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return response.choices[0].message.content
    
    async def _generate_decklist(self, archetype_desc, format_name):
        """Generate a single decklist based on archetype description"""
        legal_cards = await self.card_db.get_format_legal_cards(format_name)
        
        prompt = f"""
        Create a realistic Magic: The Gathering decklist for the following archetype in {format_name} format:
        
        {archetype_desc}
        
        Generate a 60-card decklist (including lands) that follows typical construction patterns for this archetype.
        Format the response as a JSON object with card names as keys and quantities as values.
        """
        
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a Magic: The Gathering deck building expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)