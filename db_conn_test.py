import asyncio
from multiprocessing import connection

import psycopg2


async def postgres_init() -> connection:
    # "postgresql://postgres:postgres@127.0.0.1:4322/postgres"
    conn = psycopg2.connect(
        host='127.0.0.1',
        database='postgres',
        user='postgres',
        password='postgres',
        port=4322
    )
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders LIMIT 10;")
    cur.execute("""
        SELECT column_name, data_type, character_maximum_length, column_default, is_nullable
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE table_name = 'orders';
    """)
    schema_rows = cur.fetchall()
    print("\nTable Schema:")
    for row in schema_rows:
        print(f"Column: {row[0]}, Type: {row[1]}, Max Length: {row[2]}, Default: {row[3]}, Nullable: {row[4]}")
    
    # Execute the original query after schema check
    cur.execute("SELECT * FROM orders LIMIT 10;")
    rows = cur.fetchall()
    print(rows)

    return conn

if __name__ == "__main__":
    asyncio.run(postgres_init())
