import asyncio
from multiprocessing import connection
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()


async def postgres_init() -> connection:
    # "postgresql://postgres:postgres@127.0.0.1:4322/postgres"
    # conn = psycopg2.connect(
    #     host='127.0.0.1',
    #     database='postgres',
    #     user='postgres',
    #     password='postgres',
    #     port=4322
    # )
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )
    return conn

conn = asyncio.run(postgres_init())
