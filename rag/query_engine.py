class DeckbuilderRAGQueryEngine:
    def __init__(self, openai_client, vector_db):
        self.openai = openai_client
        self.vector_db = vector_db
    
    async def process_deck_request(self, user_description, format_name, specific_cards=None):
        # Extract deck parameters from user description
        deck_params = await self._extract_deck_parameters(user_description)
        
        # Build format-specific filters
        format_filter = self._build_format_filter(format_name)
        
        # Get color identity filter
        color_filter = self._build_color_filter(deck_params['colors'])
        
        # Create combined filter
        combined_filter = {
            "$and": [
                format_filter,
                color_filter
            ]
        }
        
        # Create query embedding for the deck concept
        concept_embedding = await self._generate_concept_embedding(
            deck_params['strategy'],
            deck_params['mechanics']
        )
        
        # Query for cards matching the deck concept
        retrieval_results = self.vector_db.query_cards(
            concept_embedding, 
            filters=combined_filter,
            top_k=300  # Get a large initial pool
        )
        
        # Process the retrieved cards for deck construction
        return self._prepare_deck_construction_data(
            retrieval_results, 
            deck_params,
            specific_cards
        )
    
    async def _extract_deck_parameters(self, user_description):
        """Extract key parameters from user description using LLM"""
        response = await self.openai.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "Extract deck building parameters from the user's description."},
                {"role": "user", "content": f"Extract the following parameters from this deck description: colors, strategy, mechanics, and key card types. Description: {user_description}"}
            ],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)
    
    async def _generate_concept_embedding(self, strategy, mechanics):
        """Generate embedding for the deck concept"""
        concept_text = f"Magic the Gathering deck with strategy: {strategy}. Key mechanics: {', '.join(mechanics)}."
        response = await self.openai.embeddings.create(
            input=concept_text,
            model="text-embedding-3-large"
        )
        return response.data[0].embedding