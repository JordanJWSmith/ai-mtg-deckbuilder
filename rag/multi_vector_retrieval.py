async def multi_vector_retrieval(user_description, vector_db, openai_client):
    """Perform multi-vector retrieval to get different card aspects"""
    
    # Extract key concepts from user description
    concepts = await extract_mtg_concepts(user_description, openai_client)
    
    # Generate embeddings for each concept separately
    embeddings = {}
    for concept_type, concept_value in concepts.items():
        response = await openai_client.embeddings.create(
            input=concept_value,
            model="text-embedding-3-large"
        )
        embeddings[concept_type] = response.data[0].embedding
    
    # Query vector DB for each concept type
    results = {}
    for concept_type, embedding in embeddings.items():
        results[concept_type] = vector_db.query_cards(
            embedding,
            top_k=50,
            filters={"concept_type": concept_type}
        )
    
    # Rerank and combine results
    final_results = rerank_and_combine(results, concepts)
    return final_results