async def construct_deck_with_cot(card_pool, deck_params, format_name, openai_client):
    """Construct a deck using chain-of-thought reasoning"""
    
    # Prepare context with limited card pool
    context = prepare_llm_context(card_pool, deck_params)
    
    # Create prompt for chain-of-thought reasoning
    prompt = f"""
    # MTG Deck Construction Task
    
    ## Requirements
    - Format: {format_name}
    - Colors: {', '.join(deck_params['colors'])}
    - Strategy: {deck_params['strategy']}
    - Key mechanics: {', '.join(deck_params['mechanics'])}
    
    ## Available Cards
    {format_cards_for_context(context['card_pool'])}
    
    ## Step-by-Step Instructions
    1. First, think about the mana base requirements for this deck.
    2. Then, determine the key card types needed (creatures, spells, etc.).
    3. Next, identify the core cards that best fulfill the strategy.
    4. Add supporting cards that enhance the core strategy.
    5. Finally, balance the deck to ensure a proper mana curve.
    
    Think through each step and explain your reasoning. Then provide the final decklist.
    """
    
    # Use OpenAI API with chain-of-thought prompting
    response = await openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a Magic: The Gathering deck building expert."},
            {"role": "user", "content": prompt}
        ]
    )
    
    # Parse the response to extract the decklist and reasoning
    full_response = response.choices[0].message.content
    
    # Extract decklist and reasoning (implementation would depend on response format)
    decklist, reasoning = extract_decklist_and_reasoning(full_response)
    
    return {
        "decklist": decklist,
        "reasoning": reasoning
    }