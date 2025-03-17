# process_mtgjson.py

##########################################
### DOWNLOAD SOURCE FILES ###
# Download the most comprehensive file (AllPrintings)
# curl -o AllPrintings.json https://mtgjson.com/api/v5/AllPrintings.json

# OR download the atomic cards file for a smaller file with unique cards
# curl -o AtomicCards.json https://mtgjson.com/api/v5/AtomicCards.json

# Download format legality information
# curl -o Legalities.json https://mtgjson.com/api/v5/Legalities.json
##########################################

import json
import os
import psycopg2
from psycopg2.extras import execute_values
import openai

# Configure database connection
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "mtg_deckbuilder")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS", "postgres")

# Configure OpenAI connection for embeddings
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_tables(conn):
    """Create the necessary database tables"""
    with conn.cursor() as cur:
        # Cards table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            mana_cost VARCHAR(255),
            cmc FLOAT,
            colors TEXT[],
            color_identity TEXT[],
            type_line TEXT,
            oracle_text TEXT,
            power VARCHAR(10),
            toughness VARCHAR(10),
            keywords TEXT[],
            set_code VARCHAR(10)
        );
        """)
        
        # Format legality table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS legalities (
            card_id VARCHAR(255) REFERENCES cards(id),
            format VARCHAR(50),
            legal BOOLEAN,
            PRIMARY KEY (card_id, format)
        );
        """)
        
        # Card embeddings table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS card_embeddings (
            card_id VARCHAR(255) PRIMARY KEY REFERENCES cards(id),
            embedding VECTOR(1536)
        );
        """)
        
        # Card mechanics table for more efficient querying
        cur.execute("""
        CREATE TABLE IF NOT EXISTS card_mechanics (
            card_id VARCHAR(255) REFERENCES cards(id),
            mechanic VARCHAR(255),
            PRIMARY KEY (card_id, mechanic)
        );
        """)
        
        # Synergy pairs table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS card_synergies (
            card1_id VARCHAR(255) REFERENCES cards(id),
            card2_id VARCHAR(255) REFERENCES cards(id),
            synergy_score FLOAT,
            synergy_type VARCHAR(50),
            description TEXT,
            PRIMARY KEY (card1_id, card2_id)
        );
        """)
        
        conn.commit()

def process_cards(mtgjson_file, conn):
    """Process cards from MTGJSON and insert into database"""
    print(f"Loading data from {mtgjson_file}...")
    with open(mtgjson_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # For AtomicCards.json format
    if 'data' in data:
        cards_data = data['data']
        cards = []
        for card_name, card_versions in cards_data.items():
            # Use the first version of each card
            card = card_versions[0]
            cards.append(card)
    # For AllPrintings.json format
    else:
        cards = []
        for set_code, set_data in data['data'].items():
            for card in set_data['cards']:
                # Add set code to card
                card['setCode'] = set_code
                cards.append(card)
    
    # Insert cards
    with conn.cursor() as cur:
        card_values = []
        for card in cards:
            # Skip non-English cards, tokens, and other special cards
            if card.get('language') and card['language'] != 'English':
                continue
            if card.get('isToken', False) or card.get('isPromo', False):
                continue
                
            # Create card tuple
            card_tuple = (
                card.get('uuid', card.get('id')),
                card.get('name', ''),
                card.get('manaCost', ''),
                card.get('convertedManaCost', card.get('cmc', 0)),
                card.get('colors', []),
                card.get('colorIdentity', []),
                card.get('type', card.get('typeLine', '')),
                card.get('text', card.get('oracleText', '')),
                card.get('power', ''),
                card.get('toughness', ''),
                card.get('keywords', []),
                card.get('setCode', '')
            )
            card_values.append(card_tuple)
            
            # Batch insert every 1000 cards
            if len(card_values) >= 1000:
                execute_values(
                    cur,
                    """
                    INSERT INTO cards 
                    (id, name, mana_cost, cmc, colors, color_identity, type_line, oracle_text, power, toughness, keywords, set_code)
                    VALUES %s
                    ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        mana_cost = EXCLUDED.mana_cost,
                        cmc = EXCLUDED.cmc,
                        colors = EXCLUDED.colors,
                        color_identity = EXCLUDED.color_identity,
                        type_line = EXCLUDED.type_line,
                        oracle_text = EXCLUDED.oracle_text,
                        power = EXCLUDED.power,
                        toughness = EXCLUDED.toughness,
                        keywords = EXCLUDED.keywords,
                        set_code = EXCLUDED.set_code
                    """,
                    card_values
                )
                card_values = []
                conn.commit()
                
        # Insert any remaining cards
        if card_values:
            execute_values(
                cur,
                """
                INSERT INTO cards 
                (id, name, mana_cost, cmc, colors, color_identity, type_line, oracle_text, power, toughness, keywords, set_code)
                VALUES %s
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    mana_cost = EXCLUDED.mana_cost,
                    cmc = EXCLUDED.cmc,
                    colors = EXCLUDED.colors,
                    color_identity = EXCLUDED.color_identity,
                    type_line = EXCLUDED.type_line,
                    oracle_text = EXCLUDED.oracle_text,
                    power = EXCLUDED.power,
                    toughness = EXCLUDED.toughness,
                    keywords = EXCLUDED.keywords,
                    set_code = EXCLUDED.set_code
                """,
                card_values
            )
            conn.commit()
    
    print(f"Processed {len(cards)} cards")

def process_legalities(legalities_file, conn):
    """Process format legalities from MTGJSON"""
    print(f"Loading legalities from {legalities_file}...")
    with open(legalities_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    legalities_data = data['data']
    
    # Insert legalities
    with conn.cursor() as cur:
        legality_values = []
        for card_id, formats in legalities_data.items():
            for format_name, legality in formats.items():
                legality_values.append((
                    card_id,
                    format_name,
                    legality == 'Legal'
                ))
                
                # Batch insert
                if len(legality_values) >= 5000:
                    execute_values(
                        cur,
                        """
                        INSERT INTO legalities (card_id, format, legal)
                        VALUES %s
                        ON CONFLICT (card_id, format) DO UPDATE SET
                            legal = EXCLUDED.legal
                        """,
                        legality_values
                    )
                    legality_values = []
                    conn.commit()
                    
        # Insert remaining legalities
        if legality_values:
            execute_values(
                cur,
                """
                INSERT INTO legalities (card_id, format, legal)
                VALUES %s
                ON CONFLICT (card_id, format) DO UPDATE SET
                    legal = EXCLUDED.legal
                """,
                legality_values
            )
            conn.commit()
    
    print("Processed legalities")

def extract_mechanics(conn):
    """Extract mechanics from card text for more efficient searching"""
    print("Extracting mechanics from cards...")
    with conn.cursor() as cur:
        # Get all cards
        cur.execute("SELECT id, oracle_text, keywords FROM cards")
        cards = cur.fetchall()
        
        # Common MTG mechanics to look for
        known_mechanics = [
            "Flying", "First strike", "Double strike", "Deathtouch", "Haste",
            "Hexproof", "Indestructible", "Lifelink", "Menace", "Reach",
            "Trample", "Vigilance", "Flash", "Defender", "Equip",
            "Ward", "Protection", "Landfall", "Cascade", "Cycling",
            "Delve", "Miracle", "Surveil", "Dredge", "Convoke",
            "Prowess", "Affinity", "Devotion", "Exploit", "Explore",
            "Extort", "Flashback", "Goaded", "Hellbent", "Infect",
            "Kicker", "Madness", "Myriad", "Overload", "Persist",
            "Proliferate", "Prowl", "Regenerate", "Replicate", "Scry",
            "Threshold", "Transform", "Unearth", "Unleash", "Bloodthirst",
            "Boast", "Cipher", "Conspire", "Cumulative upkeep", "Dash",
            "Emerge", "Encore", "Escalate", "Exalted", "Evoke",
            "Fabricate", "Fading", "Fuse", "Graft", "Gravestorm",
            "Imprint", "Jump-start", "Modular", "Morph", "Mutate",
            "Ninjutsu", "Outlast", "Offering", "Populate", "Forecast",
            "Retrace", "Riot", "Skulk", "Soulshift", "Split second",
            "Storm", "Sunburst", "Suspend", "Totem armor", "Tribute",
            "Undying", "Vanishing", "Wither", "Devoid", "Intimidate"
        ]
        
        # Pattern match and insert
        mechanic_values = []
        for card_id, oracle_text, keywords in cards:
            # Add explicit keywords
            if keywords:
                for keyword in keywords:
                    mechanic_values.append((card_id, keyword))
            
            # Look for mechanics in oracle text
            if oracle_text:
                for mechanic in known_mechanics:
                    if mechanic.lower() in oracle_text.lower():
                        mechanic_values.append((card_id, mechanic))
        
        # Deduplicate
        mechanic_values = list(set(mechanic_values))
        
        # Insert mechanics
        execute_values(
            cur,
            """
            INSERT INTO card_mechanics (card_id, mechanic)
            VALUES %s
            ON CONFLICT (card_id, mechanic) DO NOTHING
            """,
            mechanic_values
        )
        conn.commit()
    
    print(f"Extracted {len(mechanic_values)} mechanics")

def generate_card_embeddings(conn):
    """Generate and store embeddings for cards"""
    print("Generating card embeddings...")
    with conn.cursor() as cur:
        # Get cards that don't have embeddings yet
        cur.execute("""
            SELECT c.id, c.name, c.oracle_text, c.type_line, c.mana_cost, string_agg(cm.mechanic, ', ') as mechanics
            FROM cards c
            LEFT JOIN card_embeddings ce ON c.id = ce.card_id
            LEFT JOIN card_mechanics cm ON c.id = cm.card_id
            WHERE ce.card_id IS NULL
            GROUP BY c.id, c.name, c.oracle_text, c.type_line, c.mana_cost
            LIMIT 1000
        """)
        cards = cur.fetchall()
        
        if not cards:
            print("No new cards to embed")
            return
            
        print(f"Generating embeddings for {len(cards)} cards...")
        
        for i in range(0, len(cards), 100):  # Process in batches of 100
            batch = cards[i:i+100]
            
            # Create text representations
            texts = []
            for card_id, name, oracle_text, type_line, mana_cost, mechanics in batch:
                card_text = f"""
                Name: {name}
                Mana Cost: {mana_cost or ''}
                Type: {type_line or ''}
                Oracle Text: {oracle_text or ''}
                Mechanics: {mechanics or ''}
                """
                texts.append(card_text)
            
            # Generate embeddings
            response = openai_client.embeddings.create(
                input=texts,
                model="text-embedding-3-large"
            )
            
            # Insert embeddings
            embedding_values = []
            for j, embedding_data in enumerate(response.data):
                card_id = batch[j][0]
                embedding = embedding_data.embedding
                embedding_values.append((card_id, embedding))
            
            execute_values(
                cur,
                """
                INSERT INTO card_embeddings (card_id, embedding)
                VALUES %s
                ON CONFLICT (card_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding
                """,
                embedding_values
            )
            conn.commit()
            print(f"Processed {i + len(batch)}/{len(cards)} embeddings")

def main():
    # Connect to database
    conn = psycopg2.connect(
        host=DB_HOST,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )
    
    try:
        # Create tables
        create_tables(conn)
        
        # Process MTGJSON files
        process_cards("AllPrintings.json", conn)
        process_legalities("Legalities.json", conn)
        
        # Extract mechanics
        extract_mechanics(conn)
        
        # Generate embeddings (this can be run separately as it's time-consuming)
        generate_card_embeddings(conn)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()