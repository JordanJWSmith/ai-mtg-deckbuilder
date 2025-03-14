from pinecone import Pinecone

class MTGVectorDatabase:
    def __init__(self, api_key, index_name="mtg-cards"):
        self.pc = Pinecone(api_key=api_key)
        self.index = self.pc.Index(index_name)
    
    def upsert_card(self, card_id, embedding, metadata):
        """Insert or update a card in the vector database"""
        self.index.upsert(
            vectors=[{
                'id': card_id,
                'values': embedding,
                'metadata': {
                    'name': metadata['name'],
                    'colors': metadata['colors'],
                    'cmc': metadata['cmc'],
                    'types': metadata['types'],
                    'formats': metadata['formats'],
                    'keywords': metadata['keywords'],
                    'rarity': metadata['rarity'],
                    'set': metadata['set']
                }
            }]
        )
    
    def query_cards(self, query_embedding, filters=None, top_k=100):
        """Query cards from vector database with optional filters"""
        query_params = {
            'vector': query_embedding,
            'top_k': top_k,
            'include_metadata': True
        }
        
        if filters:
            query_params['filter'] = filters
            
        return self.index.query(**query_params)