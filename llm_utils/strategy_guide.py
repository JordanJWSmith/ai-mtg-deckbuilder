async def generate_strategy_guide(deck, format_name, openai_client):
    """Generate a detailed strategy guide with scenario-based examples"""
    
    # Analyze the deck
    deck_analysis = analyze_deck(deck)
    
    # Generate common matchups
    common_matchups = await get_common_matchups(format_name)
    
    # Create prompt for strategy guide
    prompt = f"""
    # MTG Strategy Guide Task
    
    ## Deck Analysis
    {format_deck_analysis(deck_analysis)}
    
    ## Common Matchups in {format_name}
    {format_matchups(common_matchups)}
    
    ## Instructions
    Create a comprehensive strategy guide for this deck, including:
    
    1. General strategy overview
    2. Key card interactions and combos
    3. Mulligan guidelines
    4. Specific play patterns against each common matchup
    5. Sideboarding recommendations if applicable
    6. Examples of how to handle difficult game situations
    
    For each matchup, include at least one scenario-based example that illustrates the correct play pattern.
    """
    
    # Get strategy guide
    response = await openai_client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "You are a professional Magic: The Gathering player and strategy guide author."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return {
        "strategy_guide": response.choices[0].message.content,
        "deck_analysis": deck_analysis
    }