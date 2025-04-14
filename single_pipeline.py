import os
import json
import requests
# import test_schema_embedding
from dotenv import load_dotenv
import time
import RAG.embedding_creator as search_api

load_dotenv()

# Get the Groq API key
GROQ_API_KEY_1 = os.getenv("GROQ_API_KEY_RAG")
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_RAG_2")
GROQ_API_KEY_3 = os.getenv("GROQ_API_KEY_SHIVAM")
GROQ_API_KEY = GROQ_API_KEY_1
MODEL="qwen-2.5-32b"

api_key_list = [GROQ_API_KEY_1, GROQ_API_KEY_2, GROQ_API_KEY_3]
current_index = 0
# MODEL = 'llama-3.1-8b-instant'

total_tokens = 0

def call_groq_api(api_key, model, messages, temperature=0.2, max_tokens=8000, n=1):
    """
    Call the Groq API to get a response from the language model.
    
    Args:
        api_key (str): API key for authentication
        model (str): Model name to use
        messages (list): List of message dictionaries containing role and content
        temperature (float, optional): Temperature for controlling randomness. Defaults to 0.2
        max_tokens (int, optional): Maximum number of tokens to generate. Defaults to 8100
        n (int, optional): Number of responses to generate. Defaults to 1
    
    Returns:
        tuple: (completion_text, call_token_count)
            - completion_text (str): The generated response from the model
            - call_token_count (int): Number of tokens used in this API call
    """
    global current_index
    current_index = (current_index + 1) % len(api_key_list)
    api_key = api_key_list[current_index]
    # print("Using API Key:", api_key)

    global total_tokens
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    data = {
        "model": model,
        "messages": messages,
        'temperature': temperature,
        'max_tokens': max_tokens,
        'n': n
    }

    try:
        response = requests.post(url, headers=headers, json=data)
    except Exception as e:
        print("Error in API call:", e)
        # print(json.dumps(response_json, indent=4))    

    response_json = response.json()
    total_tokens += response_json.get('usage', {}).get('total_tokens', 0)
    call_token_count = response_json.get('usage', {}).get('total_tokens', 0)
    # print(json.dumps(response_json, indent=4))
    completion_text = response_json['choices'][0]['message']['content']

    return completion_text, call_token_count

def table_agent(raw_user_query, possible_tables):
    """
    Identifies necessary tables from the database schema based on the user query.
    
    Args:
        raw_user_query (str): The original user query in natural language
    
    Returns:
        tuple: (required_tables, table_agent_token)
            - required_tables (str): Comma-separated list of required table names
            - table_agent_token (int): Number of tokens used in this operation
    """
    
    print("Table Agent Started...")

    prompt = f"""You are a database expert tasked with identifying the necessary tables for SQL query generation.

            CONTEXT:
            - User query: '{raw_user_query}'
            - Possible Tables: {possible_tables} (organized by priority based on vector similarity)

            INSTRUCTIONS:
            1. Analyze the user query and determine ALL tables required to generate a complete SQL response
            2. Only select tables that actually exist in the provided schema
            3. Do not omit any table that might be needed for joins or data extraction
            4. Do not invent or suggest tables not present in the schema

            OUTPUT FORMAT:
            - Return only a comma-separated list of table names (e.g., "table1,table2,table3")
            - Ensure each table name exactly matches the name in the schema
            - Do not include any explanations, quotes, brackets, note, or additional text

            Your task is critical as subsequent processing will rely on your table selection.
            """

    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    response, table_agent_token = call_groq_api(GROQ_API_KEY ,MODEL,messages,temperature=0.06)

    print("Table agent completed.")

    return response, table_agent_token

def prune_agent(raw_user_query, required_tables):
    """
    Identifies necessary columns from the required tables for SQL query generation.
    
    Args:
        raw_user_query (str): The original user query in natural language
        required_tables (str): Comma-separated list of required table names
    
    Returns:
        tuple: (required_table_details, pruning_token_count)
            - required_table_details (list): List of table details with required columns
            - pruning_token_count (int): Number of tokens used in this operation
    """
    required_tables=required_tables.split(",")
   
    pruning_token_count = 0
    required_table_details = ""
    # print(required_tables)
    for table_name in list(required_tables):
        time.sleep(1)
        try:
            
            # print("Pruning Started for Table:", table_name)
            table_schema = _get_table_schema(table_name)
            
            prompt = f"""You are a database expert identifying necessary columns for SQL generation.

                CONTEXT:
                - User query: '{raw_user_query}'
                - Table schema: {table_schema}

                INSTRUCTIONS:
                1. Select only columns from this table needed to answer the user's query
                2. Consider columns needed for selection, filtering, joins, grouping, or calculations

                OUTPUT FORMAT:
                Return a compact JSON object:
                {{
                "{table_name}": {{
                    "column1": "type:varchar | description:Primary key, used for joins",
                    "column2": "type:int | description:Filtering condition in query"
                }}
                }}

                Combine data type and important relationship details in the description.
                Only include columns necessary for this specific query.
                """
            # TODO: Improvise the table_schema structure for further processing by the prompt
            messages = [
                {
                    "role": "user",
                    
                    "content": prompt
                }
            ]

            table_attributes_required, token_count = call_groq_api(GROQ_API_KEY,MODEL,messages)
            # print(table_attributes_required)
            pruning_token_count += token_count
            # required_table_details += table_attributes_required
            # print("Table Pruning Completed for Table", table_name)
        except Exception as e:
            # print(":("*20)
            print(e)
            
    return table_attributes_required, pruning_token_count

def final_sql_query_generator(raw_user_query, required_table_details, sample_query_response= "None"):
    """
    Generates the final SQL query based on the user query and required table details.
    
    Args:
        raw_user_query (str): The original user query in natural language
        required_table_details (list): List of table details with their required columns
        sample_query_response (str, optional): Example query response format. Defaults to "None"
    
    Returns:
        tuple: (sql_statement, final_call_token_count)
            - sql_statement (str): The generated SQL query
            - final_call_token_count (int): Number of tokens used in this operation
    """
    print("Final Query Generation started...")
    prompt = f"""You are an advanced SQL query generator with expertise in database schema interpretation.

TASK: Generate a precise SQL query that answers the user's question using only the provided table schemas.

INPUT:
- User question: "{raw_user_query}"
- Available table schemas: {required_table_details}
- Expected output format reference: {sample_query_response}

INSTRUCTIONS:
1. Analyze the table schemas carefully - use ONLY tables and columns provided in the schema
2. Create a SQL query that directly addresses the user's question
3. Include proper JOINs when relationships exist between tables
4. Use appropriate conditions, grouping, aggregations, and sorting as required
5. Maintain original column names exactly as provided in the schema
6. Return complex objects properly (JSON arrays, nested data)
7. Handle edge cases:
   - For partial text matching, use appropriate operators (LIKE, REGEXP)
   - For date/time queries, use proper date functions
   - For numerical comparisons, choose suitable operators
   - For missing or NULL values, handle with IS NULL/IS NOT NULL
   - For aggregations, include GROUP BY for all non-aggregated columns
   - For sorting, specify ASC/DESC explicitly
8. Optimize the query to be efficient and not overly complex

OUTPUT FORMAT:
Return ONLY valid SQL query text - no explanations, comments, additional text, not even \n and```sql ...``` .
You may include ; in the end if required.
"""
    messages = [
            {
                "role": "user",
                
                "content": prompt
            }
        ]
    
    sql_statement, final_call_token_count = call_groq_api(GROQ_API_KEY,MODEL,messages)

    print("Final SQL query Generated.")
    dummy_reponse = str(sql_statement)
    sql_statement = dummy_reponse.replace("\n", " ")
    # print(sql_statement)

    return sql_statement, final_call_token_count



def _get_database_schema(query):
    """
    Fetches the relevant database schema for a given query using similarity search.
    
    Args:
        query (str): The user query to find relevant schema for
    
    Returns:
        str: JSON string containing the relevant database schema
    # """
    # isinstance_search_db = test_schema_embedding.wrapper()
    # results = isinstance_search_db.similarity_search( query, k=1)

    # return results[0].page_content
    pass

def _get_table_schema(table_name):
    """
    Fetches the schema of a specific table from the table_schemas.json file.
    
    Args:
        table_name (str): Name of the table to get schema for
    
    Returns:
        dict: Table schema containing column definitions and their types
    """
    with open("./table_schemas.json", "r", encoding="utf-8") as file:
        data=json.load(file)

    for objs_json in data:
        # print(objs_json)
        if table_name not in dict(objs_json)["table_name"]:
            pass
        else:
            # print("$$$"*43)
            return objs_json
        

    return "Table Not Found"
       

if __name__ == "__main__":
    # print(_get_table_schema('events'))
    _get_table_schema('events')