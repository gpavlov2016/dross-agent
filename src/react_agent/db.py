import asyncio
from multiprocessing import connection
import psycopg2
from psycopg2.extensions import connection as pg_connection
from dotenv import load_dotenv
import os
from typing import Dict

load_dotenv()

# Cache for database connections - maps seller_id to connection
_connection_cache: Dict[str, pg_connection] = {}
# Maps email to seller_id
_sellers: Dict[str, str] = {}

async def sellers_init() -> None:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM sellers")
    sellers = cur.fetchall()
    for seller in sellers:
        _sellers[seller[0]] = seller[1]
    print("Sellers: ", _sellers)
    conn.close()
    return

async def get_db_connection(seller_id: str) -> pg_connection:
    """Get the database connection from cache or create a new one if not exists."""
    
    # Check if connection exists in cache
    if seller_id in _connection_cache:
        try:
            # Test if connection is still alive
            _connection_cache[seller_id].cursor().execute('SELECT 1')
            return _connection_cache[seller_id]
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            # If connection is dead, remove it from cache
            del _connection_cache[seller_id]
    
    print("Creating new connection for seller_id: ", seller_id)
    # Create new connection if not in cache or if previous connection was dead
    db_user = f"seller_role_{seller_id}.mrmlzpkjfosavipxrwct"
    db_password = os.getenv('DB_PASSWORD_SELLER_ROLE')
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST'),
            database=os.getenv('DB_NAME'),
            user=db_user,
            password=db_password,
            port=os.getenv('DB_PORT')
        )
    except Exception as e:
        print("Error creating connection: ", e)
        raise e
    print("Connection created for seller_id: ", seller_id)
    print("Connection: ", conn)
    # Store connection in cache
    _connection_cache[seller_id] = conn
    return conn

# async def supabase_init() -> Client:
#     """Initialize the Supabase client."""
#     configuration = Configuration.from_context()
#     supabase = create_client(
#         supabase_url=configuration.supabase_url,
#         supabase_key=configuration.supabase_key
#     )

#     return supabase


# conn = asyncio.run(sellers_init())

conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    database=os.getenv('DB_NAME'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    port=os.getenv('DB_PORT')
)

