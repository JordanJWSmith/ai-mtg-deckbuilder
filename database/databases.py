# databases.py
import asyncpg
import asyncio

class Database:
    """
    A minimal async database client using asyncpg.
    
    Usage:
        db = Database("postgresql://user:pass@host/dbname")
        await db.connect()
        result = await db.fetch_all("SELECT * FROM cards")
        await db.disconnect()
    """
    def __init__(self, url: str):
        self._url = url
        self._pool = None

    async def connect(self):
        """Establish a connection pool to the database."""
        self._pool = await asyncpg.create_pool(self._url)
    
    async def disconnect(self):
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()

    async def execute(self, query: str, *args):
        """
        Execute a query (INSERT, UPDATE, DELETE) and return the status.
        
        Args:
            query (str): SQL query string.
            *args: Query parameters.
            
        Returns:
            str: The status of the execution.
        """
        async with self._pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch_all(self, query: str, *args):
        """
        Fetch all results for a query.
        
        Args:
            query (str): SQL query string.
            *args: Query parameters.
            
        Returns:
            List[asyncpg.Record]: A list of records returned by the query.
        """
        async with self._pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetch_one(self, query: str, *args):
        """
        Fetch a single result for a query.
        
        Args:
            query (str): SQL query string.
            *args: Query parameters.
            
        Returns:
            asyncpg.Record or None: A single record or None if no record was found.
        """
        async with self._pool.acquire() as connection:
            return await connection.fetchrow(query, *args)
