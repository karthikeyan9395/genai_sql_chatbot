import streamlit as st
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
import pyodbc
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="SQL Query Assistant",
    page_icon="🤖",
    layout="wide"
)

# SQL Server connection configuration
SERVER = "localhost"
DATABASE = "Azurelib"
USERNAME = "sa"
PASSWORD = "abc*123"
DRIVER = "{ODBC Driver 17 for SQL Server}"

# Create connection string
CONNECTION_STRING = f"DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}"

# Initialize session state for chat history
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Initialize Groq
@st.cache_resource
def init_llm():
    return ChatGroq(
        temperature=0,
        groq_api_key="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",
        model_name="mixtral-8x7b-32768"
    )

llm = init_llm()

# Get the database schema
@st.cache_data
def get_schema():
    conn = pyodbc.connect(CONNECTION_STRING)
    cursor = conn.cursor()
    
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
        
        columns = [column[0] for column in cursor.description]
        results = cursor.fetchall()
        
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
        schema = get_schema()
        sql_query = chain.invoke({
            "schema": schema,
            "query": nl_query
        })
        
        results = execute_query(sql_query)
        
        return {
            "sql_query": sql_query,
            "results": results
        }
        
    except Exception as e:
        import traceback
        return f"Error processing query: {str(e)}"

# Streamlit UI
st.title("🤖 Natural Language to SQL Assistant")

# Sidebar with schema information
with st.sidebar:
    st.header("Database Schema")
    st.text(get_schema())

# Main chat interface
st.markdown("### Chat with your Database")
st.markdown("Ask questions about your data in natural language!")

# Chat input
if query := st.chat_input("Ask a question about your data..."):
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": query})
    
    # Process query
    with st.spinner("Generating response..."):
        result = process_natural_language_query(query)
        
        # Add assistant's response to chat history
        if isinstance(result, dict):
            sql_query = result["sql_query"]
            query_results = result["results"]
            
            response = {
                "sql": sql_query,
                "results": query_results
            }
        else:
            response = {"error": str(result)}
        
        st.session_state.chat_history.append({"role": "assistant", "content": response})

# Display chat history
for message in st.session_state.chat_history:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(message["content"])
    else:
        with st.chat_message("assistant"):
            content = message["content"]
            if isinstance(content, dict):
                if "error" in content:
                    st.error(content["error"])
                else:
                    st.code(content["sql"], language="sql")
                    if content["results"]:
                        st.json(content["results"])
                    else:
                        st.info("No results found for this query.")

# Clear chat button
if st.sidebar.button("Clear Chat History"):
    st.session_state.chat_history = []
    st.rerun()