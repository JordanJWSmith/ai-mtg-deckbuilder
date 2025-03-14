# main.py
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import logging

from dependencies import get_card_db, get_vector_db, get_openai_client
from services.rag_engine import DeckbuilderRAGQueryEngine
from services.deck_constructor import DeckConstructor
from services.deck_optimizer import DeckOptimizer
from services.explanation_generator import ExplanationGenerator

app = FastAPI(title="MTG AI Deckbuilder API")

# Models
class DeckRequest(BaseModel):
    description: str
    format: str
    specific_cards: Optional[List[str]] = None
    mechanics: Optional[List[str]] = None

class DeckOptimizationRequest(BaseModel):
    decklist: Dict[str, int]
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
        # Initialize RAG engine
        rag_engine = DeckbuilderRAGQueryEngine(openai_client, vector_db)
        
        # Process deck request
        card_pool = await rag_engine.process_deck_request(
            request.description,
            request.format,
            request.specific_cards
        )
        
        # Construct deck
        deck_constructor = DeckConstructor(openai_client, card_db)
        deck = await deck_constructor.construct_deck(
            card_pool,
            rag_engine.extracted_params,
            request.format,
            request.specific_cards
        )
        
        # Generate explanations
        explanation_generator = ExplanationGenerator(openai_client)
        explanations = await explanation_generator.generate_deck_explanation(
            deck,
            request.description,
            request.format
        )
        
        # Add to usage metrics in background
        background_tasks.add_task(
            log_deck_generation,
            request.format,
            rag_engine.extracted_params
        )
        
        return {
            "deck_list": deck,
            "strategy_explanation": explanations["strategy"],
            "card_explanations": explanations["card_explanations"],
            "mana_curve": calculate_mana_curve(deck)
        }
    except Exception as e:
        logging.error(f"Error generating deck: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize-deck", response_model=OptimizationResponse)
async def optimize_deck(
    request: DeckOptimizationRequest,
    openai_client=Depends(get_openai_client),
    vector_db=Depends(get_vector_db)
):
    try:
        # Initialize optimizer
        optimizer = DeckOptimizer(openai_client, vector_db)
        
        # Get optimization suggestions
        optimization_results = await optimizer.optimize_deck(
            request.decklist,
            request.format
        )
        
        return {
            "suggestions": optimization_results["recommendations"],
            "explanations": optimization_results["explanations"]
        }
    except Exception as e:
        logging.error(f"Error optimizing deck: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))