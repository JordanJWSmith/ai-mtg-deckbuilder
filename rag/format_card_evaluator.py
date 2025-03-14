import json

class FormatCardEvaluator:
    def __init__(self, openai_client, card_db):
        self.openai = openai_client
        self.card_db = card_db
        
    async def evaluate_for_format(self, card_name, format_name):
        """Evaluate a card's strength in a specific format"""
        # Get card data
        card = await self.card_db.get_card_by_name(card_name)
        
        # Get format meta information
        format_meta = await self.card_db.get_format_meta(format_name)
        
        # Generate evaluation
        prompt = f"""
        Evaluate the card '{card_name}' for the {format_name} format in Magic: The Gathering.
        
        Card Details:
        {json.dumps(card, indent=2)}
        
        Current {format_name} Meta Information:
        Top Decks: {', '.join(format_meta['top_decks'])}
        Common Strategies: {', '.join(format_meta['common_strategies'])}
        Format Speed: {format_meta['format_speed']}
        
        Provide an evaluation that includes:
        1. Overall power level (1-10)
        2. Which decks/archetypes would want this card
        3. Potential synergies in the format
        4. Weaknesses in the current meta
        """
        
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": f"You are an expert on the {format_name} format in Magic: The Gathering."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)