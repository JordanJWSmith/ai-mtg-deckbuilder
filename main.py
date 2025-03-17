# main.py
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import logging

from dependencies import get_card_db, get_vector_db, get_openai_client
from services.deck_request_extractor import DeckRequestExtractor
from services.deck_constructor import DeckConstructorService
from services.deck_optimizer import DeckOptimizerService
from services.explanation_generator import ExplanationGenerator
from rag.query_engine import DeckbuilderRAGQueryEngine

app = FastAPI(title="MTG AI Deckbuilder API")

# Models
class DeckRequest(BaseModel):
    description: str
    format: str
    specific_cards: Optional[List[str]] = None
    mechanics: Optional[List[str]] = None

class DeckOptimizationRequest(BaseModel):
    decklist: Dict[str, int]  # Card name to count mapping
    format: str

class DeckResponse(BaseModel):
    deck_list: Dict[str, int]
    strategy_explanation: str
    card_explanations: Dict[str, str]
    mana_curve: Dict[str, int]

class OptimizationResponse(BaseModel):
    suggestions: List[Dict[str, Any]]
    explanations: Dict[str, str]

# Routes
@app.post("/generate-deck", response_model=DeckResponse)
async def generate_deck(
    request: DeckRequest,
    background_tasks: BackgroundTasks,
    card_db=Depends(get_card_db),
    vector_db=Depends(get_vector_db),
    openai_client=Depends(get_openai_client)
):
    try:
        # Initialize components
        rag_engine = DeckbuilderRAGQueryEngine(openai_client, vector_db)
        extractor = DeckRequestExtractor(openai_client)
        constructor = DeckConstructorService(openai_client, card_db, vector_db)
        explanation_gen = ExplanationGenerator(openai_client)
        
        # Extract deck parameters from description
        deck_params = await extractor.extract_deck_parameters(
            request.description,
            request.format,
            request.mechanics
        )
        
        # Process deck request
        card_pool = await rag_engine.retrieve_card_pool(
            deck_params,
            request.format
        )
        
        # Construct deck
        deck = await constructor.construct_deck(
            card_pool,
            deck_params,
            request.format,
            request.specific_cards
        )
        
        # Generate explanations
        explanations = await explanation_gen.generate_deck_explanation(
            deck,
            deck_params,
            request.description,
            request.format
        )
        
        # Calculate mana curve
        mana_curve = constructor.calculate_mana_curve(deck)
        
        # Add to usage metrics in background
        background_tasks.add_task(
            log_deck_generation,
            request.format,
            deck_params
        )
        
        return {
            "deck_list": deck,
            "strategy_explanation": explanations["strategy"],
            "card_explanations": explanations["card_explanations"],
            "mana_curve": mana_curve
        }
    except Exception as e:
        logging.error(f"Error generating deck: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize-deck", response_model=OptimizationResponse)
async def optimize_deck(
    request: DeckOptimizationRequest,
    openai_client=Depends(get_openai_client),
    vector_db=Depends(get_vector_db),
    card_db=Depends(get_card_db)
):
    try:
        # Initialize optimizer
        optimizer = DeckOptimizerService(openai_client, vector_db, card_db)
        
        # Get optimization suggestions
        optimization_results = await optimizer.optimize_deck(
            request.decklist,
            request.format
        )
        
        return {
            "suggestions": optimization_results["suggestions"],
            "explanations": optimization_results["explanations"]
        }
    except Exception as e:
        logging.error(f"Error optimizing deck: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def log_deck_generation(format_name, deck_params):
    """Log deck generation metrics for analytics"""
    # Implementation to store metrics about generated decks
    logging.info(f"Generated {format_name} deck with strategy: {deck_params['strategy']}")