"""This module provides example tools for web scraping and search functionality.

It includes a basic Tavily search function (as an example) and database interaction tools.

These tools are intended as free examples to get started. For production use,
consider implementing more robust and specialized tools tailored to your needs.
"""

from typing import Any, Callable, List, Optional, Dict, cast
import pandas as pd
import asyncio
from react_agent.db import get_db_connection, _sellers
from langchain_core.runnables import RunnableConfig
from langchain_tavily import TavilySearch  # type: ignore[import-not-found]

from react_agent.configuration import Configuration
from react_agent.db import conn

pg_schema = "sp_api_thrive_2"

async def search(query: str) -> Optional[dict[str, Any]]:
    """Search for general web results.

    This function performs a search using the Tavily search engine, which is designed
    to provide comprehensive, accurate, and trusted results. It's particularly useful
    for answering questions about current events.
    """
    configuration = Configuration.from_context()
    wrapped = TavilySearch(max_results=configuration.max_search_results)
    return cast(dict[str, Any], await wrapped.ainvoke({"query": query}))




def get_seller_id(config: RunnableConfig) -> str:
    return "admin"
    # print("config: ", config)
    langgraph_auth_user = (
        config["configurable"].get("langgraph_auth_user")
        if config and "configurable" in config
        else None
    )
    print("get_seller_id: langgraph_auth_user: ", langgraph_auth_user)
    
    # Handle both dot notation and dict access for email
    email = getattr(langgraph_auth_user, 'email', None) or langgraph_auth_user.get('email')
    if not email:
        raise ValueError("No email found in langgraph_auth_user")
        
    if email not in _sellers:
        raise ValueError(f"No seller found for email: {email}")

    return _sellers[email]


async def list_tables_tool(config: RunnableConfig) -> List[str]:
    """Fetch the list of available tables from the database."""
    try:
        # seller_id = get_seller_id(config) # TODO: uncomment this when we have a way to get the seller id
        # conn = await get_db_connection(seller_id) # TODO: uncomment this when we have a way to get the seller id

        cur = conn.cursor()
        cur.execute(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{pg_schema}' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        result = await asyncio.to_thread(cur.fetchall)
        # result contains tuples of (table_name, )
        return [table[0] for table in result]

    except Exception as e:
        print(f"Error fetching tables: {str(e)}")
        return []
    # seller_id = get_seller_id(config)
    # # conn = await get_db_connection(seller_id)
    # return [
    #     f"orders_view_{seller_id}",
    # ]


async def get_schema_tool(table_name: str, config: RunnableConfig) -> str:
    """Fetch the schema for a specific table in Postgres.

    Args:
        table_name (str): The name of the table to get the schema for.

    Returns:
        str: the schema for the table represented in the following format:
        Column: {row[0]}, Type: {row[1]}, Max Length: {row[2]}, Default: {row[3]}, Nullable: {row[4]}
        or an error message if the operation fails.
    """
    try:
        # seller_id = get_seller_id(config)
        # conn = await get_db_connection(seller_id)

        cur = conn.cursor()
        cur.execute(f"""
            SELECT column_name, data_type, character_maximum_length, column_default, is_nullable
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE table_name = '{table_name}' AND table_schema = '{pg_schema}';
        """)
        result = await asyncio.to_thread(cur.fetchall)
        # Format the schema information into CREATE TABLE statement format
        if not result:
            return f"No schema found for table {table_name}"
        
        create_statement = f"CREATE TABLE {table_name} (\n"
        column_definitions = []
        
        for row in result:
            column_name = row[0]
            data_type = row[1]
            max_length = row[2]
            default_value = row[3]
            is_nullable = row[4]
            
            # Build column definition
            column_def = f"    {column_name} {data_type}"
            
            # Add length constraint if applicable
            if max_length and data_type in ['character varying', 'varchar', 'char']:
                column_def += f"({max_length})"
            
            # Add NOT NULL constraint if applicable
            if is_nullable == 'NO':
                column_def += " NOT NULL"
            
            # Add default value if applicable
            if default_value:
                column_def += f" DEFAULT {default_value}"
            
            column_definitions.append(column_def)
        
        create_statement += ",\n".join(column_definitions)
        create_statement += "\n);"
        
        print("create_statement: ", create_statement)
        return create_statement

    except Exception as e:
        return f"Error fetching schema for {table_name}: {str(e)}"


async def db_query_tool(query: str, config: RunnableConfig) -> Dict[str, Any]:
    """Execute a SQL query and return the results or error message.

    Args:
        query (str): The SQL query to execute.

    Returns:
        Dict[str, Any]: A dictionary containing either:
            - 'success': True/False
            - 'data': DataFrame with results (if successful)
            - 'error': Error message (if failed)
    """
    try:
        # seller_id = get_seller_id(config)
        # conn = await get_db_connection(seller_id)
        query = f"SET search_path TO {pg_schema};\n" + query
        cur = conn.cursor()
        try:
            cur.execute(query)
            result = await asyncio.to_thread(cur.fetchall)
            csv = pd.DataFrame(result).to_csv(index=False)
            return {
                "success": True,
                "query": query,
                "data": csv,
            }
        except Exception as e:
            conn.rollback()
            raise e

    except Exception as e:
        return {"success": False, "error": str(e)}


async def db_write_tool(query: str, config: RunnableConfig) -> dict[str, Any]:
    """Execute a write SQL query (INSERT, UPDATE, DELETE) and return the result or error message.

    Args:
        query (str): The SQL write query to execute.

    Returns:
        dict[str, Any]: A dictionary containing:
            - 'success': True/False
            - 'rows_affected': Number of rows affected (if successful)
            - 'message': Success or error message
            - 'error': Error message (if failed)
    """
    try:
        seller_id = get_seller_id(config)
        conn = await get_db_connection(seller_id)

        def blocking_db_write():
            cur = conn.cursor()
            try:
                cur.execute(query)
                rows_affected = cur.rowcount
                conn.commit()
                return {
                    "success": True,
                    "rows_affected": rows_affected,
                    "message": "Write query executed successfully",
                }
            except Exception as e:
                conn.rollback()
                raise e

        return await asyncio.to_thread(blocking_db_write)
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Write query execution failed",
        }


TOOLS: List[Callable[..., Any]] = [
    list_tables_tool,
    get_schema_tool,
    db_query_tool,
]
