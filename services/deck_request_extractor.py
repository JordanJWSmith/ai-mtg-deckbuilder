# services/deck_request_extractor.py
import json
from typing import Dict, List, Optional, Any

class DeckRequestExtractor:
    """Extracts structured deck parameters from user's natural language description"""
    
    def __init__(self, openai_client):
        self.openai = openai_client
    
    async def extract_deck_parameters(self, description: str, format_name: str, 
                                     user_mechanics: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Extract key deck building parameters from user description
        
        Args:
            description: Natural language description of the deck concept
            format_name: Format for the deck (Standard, Modern, etc.)
            user_mechanics: Optional list of mechanics specified by the user
            
        Returns:
            Dictionary of extracted parameters including colors, strategy, mechanics
        """
        # Create prompt for parameter extraction
        prompt = f"""
        Extract detailed deck building parameters from this Magic: The Gathering deck description:
        "{description}"
        
        Format: {format_name}
        
        Extract the following information:
        1. Colors (list of W, U, B, R, G)
        2. Primary strategy (aggro, midrange, control, combo, etc.)
        3. Secondary strategy (if any)
        4. Specific mechanics or keywords to focus on
        5. Key card types that are central to the strategy
        6. Mana curve preference (low, medium, high)
        7. Win conditions

        Format your response as a JSON object with these fields. Ensure all fields have values.
        """
        
        # Use OpenAI to extract parameters
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a Magic: The Gathering deck building expert."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        # Parse response
        extracted_params = json.loads(response.choices[0].message.content)
        
        # Merge user-specified mechanics if provided
        if user_mechanics:
            extracted_mechanics = extracted_params.get("mechanics", [])
            if isinstance(extracted_mechanics, list):
                extracted_params["mechanics"] = list(set(extracted_mechanics + user_mechanics))
            else:
                extracted_params["mechanics"] = user_mechanics
        
        return extracted_params