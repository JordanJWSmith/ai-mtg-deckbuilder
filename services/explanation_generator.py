# services/explanation_generator.py
import json

class ExplanationGenerator:
    def __init__(self, openai_client):
        self.openai = openai_client

    async def generate_deck_explanation(self, deck, deck_params, deck_description, format):
        """
        Generate an explanation for the generated deck.

        Args:
            deck (dict): The generated deck list mapping card names to counts.
            deck_params (dict): Parameters extracted from the user's input.
            deck_description (str): The original natural language description.
            format (str): The MTG format (e.g., Standard, Modern).

        Returns:
            dict: A JSON object with keys:
                  - "strategy": Explanation of the overall deck strategy.
                  - "card_explanations": A dictionary mapping card names to their role explanations.
        """
        # Convert the deck into a formatted string for the prompt
        deck_list_str = "\n".join([f"{card} (x{count})" for card, count in deck.items()])

        prompt = f"""
You are a Magic: The Gathering deck strategy expert.
Given the deck description, parameters, and decklist below, generate a detailed explanation of the deck's overall strategy and provide brief explanations for the role of each card.

Deck Description: {deck_description}
Format: {format}
Deck Parameters: {json.dumps(deck_params)}
Decklist:
{deck_list_str}

Please respond with a JSON object containing two keys:
- "strategy": A string explaining the overall deck strategy, synergy, and balance.
- "card_explanations": An object where each key is a card name and each value is a brief explanation of that card's role in the deck.
"""
        # Request explanation from the OpenAI client
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a Magic: The Gathering deck strategy expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        try:
            explanation = json.loads(content)
        except json.JSONDecodeError:
            # Fallback in case the response isn't valid JSON.
            explanation = {"strategy": content, "card_explanations": {}}
        return explanation
