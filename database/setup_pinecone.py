# setup_pinecone.py
import os
import psycopg2
import pinecone

# Configure PostgreSQL connection
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "mtg_deckbuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

def setup_pinecone_index():
    """
    Initialize Pinecone and create the index if it does not exist.
    Uses a 1536-dimension vector space (as defined by our embedding model).
    """
    # Get Pinecone configuration from environment variables
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENVIRONMENT = os.getenv("PINECONE_ENVIRONMENT")
    INDEX_NAME = os.getenv("PINECONE_INDEX", "mtg-cards")
    VECTOR_DIM = 1536

    # Initialize Pinecone client
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)
    
    # Check if the index already exists; if not, create it
    if INDEX_NAME not in pinecone.list_indexes():
        pinecone.create_index(name=INDEX_NAME, dimension=VECTOR_DIM, metric="cosine")
        print(f"Created Pinecone index: {INDEX_NAME}")
    else:
        print(f"Pinecone index '{INDEX_NAME}' already exists")
    
    return INDEX_NAME

def populate_pinecone_index(index_name):
    """
    Connect to the PostgreSQL database and fetch card embeddings
    from the 'card_embeddings' table, then upsert them into the Pinecone index.
    Assumes each embedding is stored as a list of floats.
    """
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    with conn.cursor() as cur:
        cur.execute("SELECT card_id, embedding FROM card_embeddings")
        rows = cur.fetchall()
        vectors = []
        for card_id, embedding in rows:
            # The embedding is expected to be a list of floats.
            vectors.append((card_id, embedding))
            # Upsert in batches of 100 to avoid exceeding request limits
            if len(vectors) >= 100:
                pinecone.Index(index_name).upsert(vectors=vectors)
                vectors = []
        # Upsert any remaining vectors
        if vectors:
            pinecone.Index(index_name).upsert(vectors=vectors)
    conn.close()
    print("Populated Pinecone index with card embeddings.")

def main():
    index_name = setup_pinecone_index()
    # Uncomment the following line if you wish to populate the index immediately.
    populate_pinecone_index(index_name)

if __name__ == "__main__":
    main()
