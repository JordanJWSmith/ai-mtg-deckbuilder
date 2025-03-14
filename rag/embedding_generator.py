import openai
from pinecone import Pinecone

class CardEmbeddingGenerator:
    def __init__(self, openai_api_key, embedding_model="text-embedding-3-large"):
        self.client = openai.OpenAI(api_key=openai_api_key)
        self.embedding_model = embedding_model
    
    def generate_card_embedding(self, card_data):
        # Create a rich representation of the card
        card_text = f"""
        Name: {card_data['name']}
        Mana Cost: {card_data['mana_cost']}
        Types: {card_data['type_line']}
        Oracle Text: {card_data['oracle_text']}
        Keywords: {', '.join(card_data.get('keywords', []))}
        Power/Toughness: {card_data.get('power', '')}/{card_data.get('toughness', '')}
        """
        
        # Generate embedding
        response = self.client.embeddings.create(
            input=card_text,
            model=self.embedding_model
        )
        
        return response.data[0].embedding