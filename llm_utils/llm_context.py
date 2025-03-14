def prepare_llm_context(card_pool, deck_params, max_tokens=12000):
    """Prepare optimal context for LLM within token limits"""
    
    # Estimate token counts
    system_prompt_tokens = 1000  # Reserve for system prompt
    user_query_tokens = 500      # Reserve for user's query
    response_tokens = 1500       # Reserve for response generation
    
    # Calculate remaining tokens for card context
    remaining_tokens = max_tokens - (system_prompt_tokens + user_query_tokens + response_tokens)
    
    # Estimate tokens per card
    tokens_per_card = 150  # Average tokens for card details
    
    # Calculate how many cards we can include
    max_cards = remaining_tokens // tokens_per_card
    
    # Prioritize cards based on relevance
    prioritized_cards = prioritize_cards(card_pool, deck_params)
    
    # Select top cards that fit within token limit
    selected_cards = prioritized_cards[:max_cards]
    
    # Format card details for context
    card_context = format_cards_for_context(selected_cards)
    
    return {
        "deck_params": deck_params,
        "card_pool": card_context,
        "total_cards": len(card_pool),
        "selected_cards": len(selected_cards)
    }

def prioritize_cards(card_pool, deck_params):
    """Prioritize cards based on relevance to deck parameters"""
    scored_cards = []
    
    for card in card_pool:
        score = 0
        
        # Score based on color match
        if set(card['colors']).issubset(set(deck_params['colors'])):
            score += 10
        
        # Score based on mechanic match
        for mechanic in deck_params['mechanics']:
            if mechanic.lower() in card['oracle_text'].lower():
                score += 5
        
        # Score based on strategy match
        strategy_keywords = extract_strategy_keywords(deck_params['strategy'])
        for keyword in strategy_keywords:
            if keyword.lower() in card['oracle_text'].lower():
                score += 3
        
        scored_cards.append((card, score))
    
    # Sort by score descending
    scored_cards.sort(key=lambda x: x[1], reverse=True)
    
    # Return just the cards
    return [card for card, _ in scored_cards]