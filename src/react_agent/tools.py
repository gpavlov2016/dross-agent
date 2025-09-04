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
from react_agent.db import conn, get_db_connection

schemas = ["sp_api_thrive_2", "amazon_ads_thrive"]

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
    """Fetch the list of available views from the database.
    
    Returns:
        List[str]: A list of table names in the format {schema}.{table_name}.
    """
    try:
        # seller_id = get_seller_id(config) # TODO: uncomment this when we have a way to get the seller id
        # conn = await get_db_connection(seller_id) # TODO: uncomment this when we have a way to get the seller id

        conn = get_db_connection()
        cur = conn.cursor()
        schemas_str = ','.join(f"'{schema}'" for schema in schemas)
        cur.execute(f"""
            SELECT table_schema, table_name 
            FROM information_schema.views 
            WHERE table_schema IN ({schemas_str}) 
            ORDER BY table_schema, table_name;
        """)
        result = await asyncio.to_thread(cur.fetchall)
        # result contains tuples of (table_schema, table_name)

        included_tables = [
            "ad_group_level_report_view",
            "advertised_product_report_view",
            "campaign_level_report_view",
            "campaign_serving_status_detail_view",
            "profile_view",
            "product_ad_report_view",
            "purchased_product_keyword_report_view",
            "sb_ad_group_report_view",
            "sb_ad_report_view",
            "sb_campaign_report_view",
            "sb_keyword_report_view",
            "sb_purchased_product_view",
            "sb_search_term_report_view",
            "sb_target_report_view",
            "sd_ad_group_report_view",
            "sd_campaign_report_view",
            "sd_matched_target_report_view",
            "sd_product_ad_report_view",
            "sd_target_report_view",
            "search_term_ad_keyword_report_view",
            "search_term_targeting_report_view",
            "targeting_keyword_report_view",
            "targeting_report_view"
        ]
        # Filter to include:
        # 1. All tables from schemas other than amazon_ads_thrive
        # 2. Only specific tables from amazon_ads_thrive schema that are in our included list
        filtered_result = []
        for table in result:
            schema, table_name = table
            if schema == "amazon_ads_thrive":
                # Only include tables from amazon_ads_thrive if they're in our included list
                if table_name in included_tables:
                    filtered_result.append(table)
            else:
                # Include all tables from other schemas
                filtered_result.append(table)
        
        return [f"{table[0]}.{table[1]}" for table in filtered_result]

    except Exception as e:
        print(f"Error fetching views: {str(e)}")
        return []
    # seller_id = get_seller_id(config)
    # # conn = await get_db_connection(seller_id)
    # return [
    #     f"orders_view_{seller_id}",
    # ]

async def get_schema_tool(full_table_name: str, config: RunnableConfig) -> str:
    """Fetch column information for a specific table in Postgres.

    Args:
        full_table_name (str): The name of the table to get the schema for in the format {schema}.{table_name}.

    Returns:
        str: the column information for the table represented in the following format:
        Column: {row[0]}, Type: {row[1]}, Comment: {row[2]}
        or an error message if the operation fails.
    """
    try:
        # seller_id = get_seller_id(config)
        # conn = await get_db_connection(seller_id)

        table_schema, table_name = full_table_name.split(".")
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"""
            SELECT 
                c.column_name,
                c.data_type,
                col_description(pgc.oid, a.attnum) as column_comment
            FROM information_schema.columns c
            LEFT JOIN pg_class pgc ON pgc.relname = c.table_name
            LEFT JOIN pg_namespace n ON n.oid = pgc.relnamespace AND n.nspname = c.table_schema
            LEFT JOIN pg_attribute a ON a.attrelid = pgc.oid AND a.attname = c.column_name
            WHERE c.table_name = '{table_name}' 
            AND c.table_schema = '{table_schema}'
            ORDER BY c.ordinal_position;
        """)
        result = await asyncio.to_thread(cur.fetchall)
        # Format the schema information
        if not result or len(result) == 0:
            return f"No schema found for table {full_table_name}"
        
        schema_lines = []
        
        for row in result:
            column_name = row[0]
            data_type = row[1]
            column_comment = row[2]
            
            # Build column description
            line = f"Column: {column_name}, Type: {data_type}"
            
            # Add comment if available
            if column_comment:
                line += f", Comment: {column_comment}"
            
            schema_lines.append(line)
        
        schema_info = "\n".join(schema_lines)
        
        # print("schema_info: ", schema_info)
        return schema_info

    except Exception as e:
        return f"Error fetching schema for {full_table_name}: {str(e)}"


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
        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute(query)
            result = await asyncio.to_thread(cur.fetchall)
            # Get column names from cursor description
            columns = [desc[0] for desc in cur.description] if cur.description else []
            csv = pd.DataFrame(result, columns=columns).to_csv(index=False)
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
        # seller_id = get_seller_id(config)
        # conn = await get_db_connection(seller_id)
        conn = get_db_connection()

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
