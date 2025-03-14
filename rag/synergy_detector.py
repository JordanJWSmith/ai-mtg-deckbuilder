## Specific RAG Techniques for Magic: The Gathering
import itertools
from sklearn.metrics.pairwise import cosine_similarity


### 1. Card Synergy Detection

class SynergyDetector:
    def __init__(self, openai_client, vector_db):
        self.openai = openai_client
        self.vector_db = vector_db
        
    async def detect_synergies(self, card_list):
        """Detect synergies between cards in a list"""
        # Group cards by potential synergy categories
        synergy_groups = await self._group_by_synergy_potential(card_list)
        
        # Analyze each group for specific synergies
        synergy_pairs = []
        for group_name, cards in synergy_groups.items():
            if len(cards) < 2:
                continue
                
            # Generate combinations of cards
            combinations = itertools.combinations(cards, 2)
            
            for card1, card2 in combinations:
                synergy_score = await self._calculate_synergy_score(card1, card2)
                if synergy_score > 0.6:  # Threshold for meaningful synergy
                    synergy_pairs.append({
                        "card1": card1["name"],
                        "card2": card2["name"],
                        "score": synergy_score,
                        "type": group_name,
                        "description": await self._describe_synergy(card1, card2)
                    })
        
        return synergy_pairs
    
    async def _group_by_synergy_potential(self, card_list):
        """Group cards by potential synergy categories"""
        # Common synergy categories in MTG
        synergy_categories = {
            "tribal": [],
            "graveyard": [],
            "artifacts": [],
            "spells_matter": [],
            "counters": [],
            "tokens": [],
            "lifegain": [],
            "sacrifice": [],
            "etb_effects": [],
            "mana_ramp": []
        }
        
        # Simple keyword matching for initial grouping
        for card in card_list:
            text = card["oracle_text"].lower()
            
            if "creature type" in text or any(tribe in text for tribe in ["elf", "goblin", "zombie", "human", "merfolk"]):
                synergy_categories["tribal"].append(card)
                
            if "graveyard" in text or "dies" in text or "exile" in text:
                synergy_categories["graveyard"].append(card)
                
            # Add more category detection logic...
        
        # Use LLM for more complex categorization
        for card in card_list:
            categories = await self._categorize_card_synergies(card)
            for category in categories:
                if category in synergy_categories:
                    synergy_categories[category].append(card)
        
        return synergy_categories
    
    async def _calculate_synergy_score(self, card1, card2):
        """Calculate synergy score between two cards using embeddings"""
        # Get embeddings for both cards
        card1_embedding = await self._get_card_embedding(card1)
        card2_embedding = await self._get_card_embedding(card2)
        
        # Calculate cosine similarity as base score
        base_score = cosine_similarity(card1_embedding, card2_embedding)
        
        # Adjust score based on explicit synergy rules
        adjusted_score = await self._adjust_synergy_score(base_score, card1, card2)
        
        return adjusted_score
    
    async def _describe_synergy(self, card1, card2):
        """Generate a description of how two cards synergize"""
        prompt = f"""
        Describe the synergy between these two Magic: The Gathering cards:
        
        Card 1: {card1['name']}
        Text: {card1['oracle_text']}
        
        Card 2: {card2['name']}
        Text: {card2['oracle_text']}
        
        Explain specifically how these cards work together and why they are stronger together than individually.
        Keep the explanation concise and focus on the mechanical interaction.
        """
        
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a Magic: The Gathering synergy expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        
        return response.choices[0].message.content.strip()