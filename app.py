from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import pyodbc
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# SQL Server connection configuration
SERVER = "localhost"
DATABASE = "Azurelib"
USERNAME = "sa"
PASSWORD = "abc*123"
DRIVER = "{ODBC Driver 17 for SQL Server}"

# Create connection string
CONNECTION_STRING = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}"

# Initialize Groq
llm = ChatGroq(
    temperature=0,
    groq_api_key="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",
    model_name="mixtral-8x7b-32768"  # You can also use "llama2-70b-4096"
)

# Get the database schema
def get_schema():
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
    # Query to get table and column information
    schema_query = """
    SELECT 
        t.name AS table_name,
        c.name AS column_name,
        ty.name AS data_type
    FROM sys.tables t
    INNER JOIN sys.columns c ON t.object_id = c.object_id
    INNER JOIN sys.types ty ON c.user_type_id = ty.user_type_id
    ORDER BY t.name, c.column_id
    """
    
    cursor.execute(schema_query)
    schema_info = cursor.fetchall()
    
    # Format schema information
    schema_text = "Database Schema:\n"
    current_table = ""
    
    for table, column, data_type in schema_info:
        if table != current_table:
            schema_text += f"\nTable: {table}\n"
            current_table = table
        schema_text += f"- {column} ({data_type})\n"
    
    cursor.close()
    conn.close()
    return schema_text

# Create prompt template
prompt = PromptTemplate.from_template("""
You are a SQL expert. Based on the following database schema and natural language query,
generate a SQL query that answers the question.

{schema}

Natural Language Query: {query}

Generate only the SQL query without any explanation or additional text.
The query should be compatible with Microsoft SQL Server.
""")

# Create the chain using the new syntax
chain = (
    {"schema": RunnablePassthrough(), "query": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# Function to execute SQL query
def execute_query(sql_query):
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        
        # Fetch column names
        columns = [column[0] for column in cursor.description]
        
        # Fetch results
        results = cursor.fetchall()
        
        # Convert results to list of dictionaries
        results_list = []
        for row in results:
            results_list.append(dict(zip(columns, row)))
        
        cursor.close()
        conn.close()
        return results_list
    
    except Exception as e:
        return f"Error executing query: {str(e)}"

# Main function to process natural language query
def process_natural_language_query(nl_query):
    try:
        # Get database schema
        schema = get_schema()
        
        # Generate SQL query using the new chain syntax
        sql_query = chain.invoke({
            "schema": schema,
            "query": nl_query
        })
        
        print("Generated SQL Query:")
        print(sql_query)
        
        # Execute the query
        results = execute_query(sql_query)
        
        return {
            "sql_query": sql_query,
            "results": results
        }
        
    except Exception as e:
        import traceback
        print(f"Full error traceback:\n{traceback.format_exc()}")
        return f"Error processing query: {str(e)}"

# Example usage
if __name__ == "__main__":
    # Example natural language query
    nl_query = "How many members are there?"
    
    # Process the query
    result = process_natural_language_query(nl_query)
    print("\nResults:")
    print(result)