class MTGHybridSearch:
    def __init__(self, vector_db, sql_db):
        self.vector_db = vector_db
        self.sql_db = sql_db
    
    async def hybrid_search(self, query, filters):
        """Combine vector search with metadata filtering"""
        
        # First, apply exact filters through SQL
        sql_results = await self.sql_db.query_cards_by_criteria(
            colors=filters.get('colors'),
            format=filters.get('format'),
            card_types=filters.get('card_types'),
            keywords=filters.get('keywords')
        )
        
        if not sql_results:
            return []
        
        # Extract IDs for vector filtering
        sql_ids = [card['id'] for card in sql_results]
        
        # Create vector filter to only consider these IDs
        vector_filter = {"id": {"$in": sql_ids}}
        
        # Generate embedding for the query
        query_embedding = await generate_embedding(query)
        
        # Perform vector search with ID filter
        vector_results = self.vector_db.query_cards(
            query_embedding,
            filters=vector_filter,
            top_k=len(sql_ids)  # Allow all SQL results to be ranked
        )
        
        return vector_results