# dependencies.py
from functools import lru_cache
import os
import redis
from openai import AsyncOpenAI
from pinecone import Pinecone
from fastapi import Depends

from database.databases import Database

@lru_cache()
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    return AsyncOpenAI(api_key=api_key)

@lru_cache()
def get_vector_db():
    api_key = os.getenv("PINECONE_API_KEY")
    environment = os.getenv("PINECONE_ENVIRONMENT")
    index_name = os.getenv("PINECONE_INDEX_NAME", "mtg-cards")
    
    pc = Pinecone(api_key=api_key)
    return pc.Index(index_name)

@lru_cache()
def get_card_db():
    """Initialize and return the card database connection"""
    database_url = os.getenv("DATABASE_URL")
    return Database(database_url)

@lru_cache()
def get_redis_client():
    """Initialize and return Redis client for caching"""
    redis_url = os.getenv("REDIS_URL")
    return redis.from_url(redis_url)

def get_rag_engine(
    openai_client=Depends(get_openai_client),
    vector_db=Depends(get_vector_db)
    ):
    return DeckbuilderRAGQueryEngine(openai_client, vector_db)