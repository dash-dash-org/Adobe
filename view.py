import streamlit as st
import os
import json
import time
import sys
import traceback

# Import your existing modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import single_pipeline
import RAG.embedding_creator as search_api
import test_schema_embedding

def load_table_schemas():
    """Load table schemas from JSON file."""
    try:
        with open("table_schemas.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        st.error("Table schemas file not found. Please generate table schemas first.")
        return []

def generate_embeddings():
    """Generate embeddings for the SQL schema."""
    try:
        test_schema_embedding.sql_to_json()
        st.success("Embeddings generated successfully!")
    except Exception as e:
        st.error(f"Error generating embeddings: {e}")

def process_query(nl_query, table_schemas):
    """
    Process the NL query through the entire pipeline.
    
    Args:
        nl_query (str): Natural language query
        table_schemas (list): List of available table schemas
    
    Returns:
        dict: Results of each pipeline stage
    """
    results = {
        "input_query": nl_query,
        "stages": {}
    }

    try:
        # Stage 1: Table Selection
        st.markdown("### 🔍 Stage 1: Table Selection")
        start_time = time.time()
        table_results, table_token_count = single_pipeline.table_agent(nl_query, ", ".join([ts.get('table_name', '') for ts in table_schemas]))
        results["stages"]["table_selection"] = {
            "selected_tables": table_results,
            "token_count": table_token_count,
            "time_taken": time.time() - start_time
        }
        st.write(f"**Selected Tables:** {table_results}")
        st.write(f"**Tokens Used:** {table_token_count}")

        # Stage 2: Column Pruning
        st.markdown("### 🧹 Stage 2: Column Pruning")
        start_time = time.time()
        column_results, column_token_count = single_pipeline.prune_agent(nl_query, table_results)
        results["stages"]["column_pruning"] = {
            # "selected_columns": column_results,
            "token_count": column_token_count,
            "time_taken": time.time() - start_time
        }
        # st.write(f"**Selected Columns:** {column_results}")
        st.write(f"**Tokens Used:** {column_token_count}")

        # Stage 3: SQL Query Generation
        st.markdown("### 💻 Stage 3: SQL Query Generation")
        start_time = time.time()
        sample_queries = search_api.search_similar_query(nl_query)
        sql_query, sql_token_count = single_pipeline.final_sql_query_generator(
            nl_query, column_results, sample_queries
        )
        results["stages"]["sql_generation"] = {
            "generated_query": sql_query,
            "token_count": sql_token_count,
            "time_taken": time.time() - start_time
        }
        st.code(sql_query, language="sql")
        st.write(f"**Tokens Used:** {sql_token_count}")

        # Total Performance Metrics
        total_tokens = table_token_count + column_token_count + sql_token_count
        total_time = sum(stage['time_taken'] for stage in results['stages'].values())
        results["total_metrics"] = {
            "total_tokens": total_tokens,
            "total_time": total_time
        }
        st.markdown("### 📊 Performance Metrics")
        st.write(f"**Total Tokens:** {total_tokens}")
        st.write(f"**Total Processing Time:** {total_time:.2f} seconds")

        return results

    except Exception as e:
        st.error(f"Error processing query: {e}")
        st.error(traceback.format_exc())
        return None

def main():
    st.set_page_config(
        page_title="SQL Query Generator",
        page_icon="🤖",
        layout="wide"
    )

    st.title("🤖 Natural Language to SQL Query Generator")

    # Sidebar for file uploads and actions
    with st.sidebar:
        st.header("📂 File Management")
        
        # SQL File Upload
        sql_file = st.file_uploader("Upload SQL Schema File", type=['sql'])
        if sql_file is not None:
            with open("files/data.sql", "wb") as f:
                f.write(sql_file.getbuffer())
            st.success("SQL file uploaded successfully!")

        # Generate Embeddings Button
        if st.button("Generate Schema Embeddings"):
            generate_embeddings()

    # Main Content Area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("🔤 Enter Natural Language Query")
        nl_query = st.text_area(
            "Type your query here", 
            placeholder="Example: Show me the top 5 most popular events",
            height=150
        )

    with col2:
        st.header("⚙️ Query Processing")
        if st.button("Generate SQL Query", type="primary"):
            if nl_query:
                # Load table schemas
                table_schemas = load_table_schemas()
                
                if table_schemas:
                    # Process the query
                    with st.spinner("Generating SQL Query..."):
                        results = process_query(nl_query, table_schemas)
                    
                    if results:
                        st.toast("Success! 🎉")
                        st.balloons()
                        # st.snow()
            else:
                st.warning("Please enter a natural language query.")

if __name__ == "__main__":
    main()