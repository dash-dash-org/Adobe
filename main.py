# PATH_TO_SQL_QUERY_TESTING_FILE = "/Users/shivammishra/Desktop/test/queryEnhancerDataset/other/train_generate_task.json"
PATH_TO_SQL_QUERY_TESTING_FILE = "/Users/shivammishra/Desktop/Adobe/other/test.json"
# PATH_TO_SQL_QUERY_TESTING_FILE = "/Users/shivammishra/Desktop/Adobe/train_generate_task.json"
import os
import json
import time
import threading
import single_pipeline
import RAG.embedding_creator as search_api

def start_single_pipeline(nl_query):
    """
    Dummy function to process the NL query.
    Should return the corresponding SQL query as a string.
    """
    print(f"Processing query: {nl_query}")

    start_time = time.time()

    # Getting Relevant Tables [RAG]
    relevant_tables = search_api.search_tables(nl_query)
    # Getting Relevant Tables [LLM]
    relevant_tables, table_agent_token_count = single_pipeline.table_agent(nl_query, relevant_tables)
    # Getting Relevant Columns [LLM]
    relevant_schema, column_agent_token_count = single_pipeline.prune_agent(nl_query, relevant_tables)
    # Getting Relevant Sample Queries [RAG]
    relevant_sample_queries = search_api.search_similar_query(nl_query)
    # Getting SQL Query [LLM]
    sql_query, sql_agent_token_count = single_pipeline.final_sql_query_generator(nl_query, relevant_schema, relevant_sample_queries)

    print("-----------")
    print("Table Creation Token Count:", table_agent_token_count)
    print("Column Pruning Token Count:", column_agent_token_count)
    print("SQL Generation Token Count:", sql_agent_token_count)
    print("-----------")

    file_path = "result.json"

    # Read existing data
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []

    # Append new entry
    data.append({"NL": nl_query, "Query": sql_query})

    # Write back to file
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

    end_time = time.time()
    print("-----------Performance Metrics-----------")
    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"Total Tokens: {table_agent_token_count + column_agent_token_count + sql_agent_token_count}")
    print(f"SQL Query: {sql_query}")
    print("----------------------------")
    exit()
    return sql_query  # Replace this with actual query generation logic

def normalize_string(s):
    """Convert to lowercase and strip extra spaces."""
    return s.lower().strip()

def check_query_match(expected_query, generated_query):
    """Compare normalized queries."""
    return normalize_string(expected_query) == normalize_string(generated_query)

def process_single_json_object(json_obj):
    """Process a single JSON object and return whether it matches."""
    nl_query = json_obj.get("NL")
    expected_query = json_obj.get("Query")
    generated_query = start_single_pipeline(nl_query)
    print("-"*30)
    print(f"Expected: {expected_query}")
    print(f"Generated: {generated_query}")
    print("-"*30)
    return check_query_match(expected_query, generated_query)

def process_json_objects(file_path):
    """Read JSON file and return the list of objects."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return json.load(file)  

def create_filtered_tables_dataset(input_file_path, output_file_path="filtered_tables_dataset.json"):
    """
    Create a dataset with user queries and filtered tables.
    Resume processing if the output file already exists.
    
    Args:
        input_file_path: Path to the training data file
        output_file_path: Path to save the resulting JSON file
    """
    # Read the training data
    try:
        training_data = process_json_objects(input_file_path)
        print(f"Loaded {len(training_data)} queries from training data.")
    except Exception as e:
        print(f"Error loading training data: {str(e)}")
        return []
    
    # Check if output file exists and load previous results
    existing_results = []
    processed_queries = set()
    if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
        try:
            with open(output_file_path, 'r', encoding='utf-8') as f:
                existing_results = json.load(f)
                processed_queries = {entry.get("user_raw_query") for entry in existing_results}
                print(f"Loaded {len(existing_results)} existing entries from {output_file_path}")
                print(f"Resuming from item {len(existing_results) + 1}")
        except Exception as e:
            print(f"Warning: Could not load existing results: {str(e)}")
            print("Starting from the beginning...")
    
    results = existing_results.copy()  # Start with existing results
    
    print(f"Processing {len(training_data)} queries for filtered tables dataset...")
    print(f"Already processed: {len(processed_queries)}")
    
    # Create a log file to track progress
    log_file = f"{os.path.splitext(output_file_path)[0]}_progress.log"
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(f"\n{'-'*50}\n")
        log.write(f"Resume processing at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Already processed {len(processed_queries)} queries.\n")
    
    try:
        for idx, item in enumerate(training_data):
            query = item.get("NL")
            if not query or query in processed_queries:
                continue
            
            print(f"[{len(results)+1}/{len(training_data)}] Processing: {query[:50]}...")
            
            try:
                # Get filtered tables from RAG
                raw_rag_filtered_tables = search_api.search_tables(query)
                
                # Convert RAG filtered tables to dictionary format
                rag_filtered_tables = {}
                for table_data in raw_rag_filtered_tables:
                    table_name = table_data[0]
                    table_schema = table_data[1]
                    table_score = table_data[2]
                    rag_filtered_tables[table_name] = {
                        "schema": table_schema,
                        "score": table_score
                    }
                    
                time.sleep(20)  # Optional: Sleep to avoid rate limits
                # Get filtered tables from LLM
                llm_filtered_tables, token_count = single_pipeline.table_agent(query, raw_rag_filtered_tables)
                print(f"LLM Token Count: {token_count}")
                
                if "\n\n"  in llm_filtered_tables:
                    llm_filtered_tables = llm_filtered_tables.split("\n\n")[0]
                # Add to results
                results.append({
                    "user_raw_query": query,
                    "rag_filtered_tables": rag_filtered_tables,
                    "llm_filtered_tables": llm_filtered_tables
                })
                
                # Add to processed queries
                processed_queries.add(query)
                
                # Log successful processing
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"{time.strftime('%H:%M:%S')}: Processed query #{len(results)}: {query[:50]}...\n")
                
                # Save intermediate results periodically
                if len(results) % 10 == 0:
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        json.dump(results, f, indent=4)
                    print(f"Saved {len(results)} results to {output_file_path}")
                    
            except Exception as e:
                error_msg = f"Error processing query '{query[:50]}...': {str(e)}"
                print(f"ERROR: {error_msg}")
                # Log the error
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"ERROR {time.strftime('%H:%M:%S')}: {error_msg}\n")
                # Continue with next query
                continue
        
        # Save final results
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
        
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"Completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Successfully processed {len(results)} entries.\n")
        
        print(f"Dataset created with {len(results)} entries and saved to {output_file_path}")
        return results
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Saving current progress...")
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=4)
        
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"INTERRUPTED at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Saved {len(results)} entries. Can resume later.\n")
            
        print(f"Saved {len(results)} results to {output_file_path}")
        print("You can resume by running the same command again.")
        return results
    
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        print("Attempting to save current progress...")
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4)
            
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"ERROR at {time.strftime('%Y-%m-%d %H:%M:%S')}: {str(e)}\n")
                log.write(f"Saved {len(results)} entries. Can resume later.\n")
                
            print(f"Saved {len(results)} results to {output_file_path}")
            print("You can resume by running the same command again.")
        except:
            print("Failed to save results. Data may be lost.")
        return results

def validate_and_regenerate_entries(input_file_path, output_file_path=None, max_retries=1):
    """
    Check if LLM filtered tables are present in RAG filtered tables.
    If not, regenerate data for those queries.
    
    Args:
        input_file_path: Path to the filtered tables dataset
        output_file_path: Path to save the validated dataset (default: input_file_path + "_validated.json")
        max_retries: Maximum number of retries for regenerating data
        
    Returns:
        Updated dataset with valid entries
    """
    if output_file_path is None:
        output_file_path = os.path.splitext(input_file_path)[0] + "_validated.json"
    
    # Check if output file exists and load previous results
    validated_dataset = []
    processed_queries = set()
    
    if os.path.exists(output_file_path) and os.path.getsize(output_file_path) > 0:
        try:
            with open(output_file_path, 'r', encoding='utf-8') as f:
                validated_dataset = json.load(f)
                processed_queries = {entry.get("user_raw_query") for entry in validated_dataset}
                print(f"Loaded {len(validated_dataset)} existing validated entries")
                print(f"Resuming validation from item {len(validated_dataset) + 1}")
        except Exception as e:
            print(f"Warning: Could not load existing validated results: {str(e)}")
            print("Starting validation from the beginning...")
    
    # Try to load input dataset
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error: Could not load dataset from {input_file_path}: {str(e)}")
        return validated_dataset
    
    # Create log file for tracking progress
    log_file = f"{os.path.splitext(output_file_path)[0]}_validation.log"
    with open(log_file, 'a', encoding='utf-8') as log:
        log.write(f"\n{'-'*50}\n")
        log.write(f"Resume validation at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.write(f"Already validated {len(processed_queries)} queries.\n")
    
    regenerated_count = 0
    skipped_count = 0
    already_valid_count = 0
    
    print(f"Validating {len(dataset)} entries...")
    
    try:
        for idx, entry in enumerate(dataset):
            query = entry.get("user_raw_query", "")
            
            # Skip already processed queries
            if query in processed_queries:
                continue
            
            rag_tables = entry.get("rag_filtered_tables", {})
            llm_tables_str = entry.get("llm_filtered_tables", "")
            
            print(f"\n[{len(validated_dataset)+1}/{len(dataset)}] Checking: {query[:50]}...")
            
            # Parse LLM tables string into a list
            llm_tables = parse_llm_tables(llm_tables_str)
            
            # Check if all LLM tables exist in RAG tables
            missing_tables = [table for table in llm_tables if table not in rag_tables]
            
            if not missing_tables:
                # All tables are valid, add to validated dataset
                validated_dataset.append(entry)
                processed_queries.add(query)
                already_valid_count += 1
                
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"{time.strftime('%H:%M:%S')}: Valid query #{len(validated_dataset)}: {query[:50]}...\n")
                
                # Save every 10 entries
                if len(validated_dataset) % 10 == 0:
                    with open(output_file_path, 'w', encoding='utf-8') as f:
                        json.dump(validated_dataset, f, indent=4)
                    print(f"Saved {len(validated_dataset)} validated entries")
                
                continue
                
            print(f"Found missing tables for query: {query[:50]}...")
            print(f"Missing tables: {missing_tables}")
            
            # Try to regenerate data for this query
            retry_successful = False
            try:
                for retry in range(max_retries):
                    print(f"Regeneration attempt {retry+1}/{max_retries}...")
                    
                    # Get filtered tables from RAG again
                    raw_rag_filtered_tables = search_api.search_tables(query)
                    
                    # Convert RAG filtered tables to dictionary format
                    rag_filtered_tables = {}
                    for table_data in raw_rag_filtered_tables:
                        table_name = table_data[0]
                        table_schema = table_data[1]
                        table_score = table_data[2]
                        rag_filtered_tables[table_name] = {
                            "schema": table_schema,
                            "score": table_score
                        }
                    
                    # Get filtered tables from LLM again
                    new_llm_filtered_tables, _ = single_pipeline.table_agent(query, raw_rag_filtered_tables)
                    
                    # Parse new LLM tables
                    new_llm_tables = parse_llm_tables(new_llm_filtered_tables)
                    
                    # Check if all new LLM tables exist in new RAG tables
                    new_missing_tables = [table for table in new_llm_tables if table not in rag_filtered_tables]
                    
                    if not new_missing_tables:
                        # Successfully regenerated without missing tables
                        new_entry = {
                            "user_raw_query": query,
                            "rag_filtered_tables": rag_filtered_tables,
                            "llm_filtered_tables": new_llm_filtered_tables
                        }
                        validated_dataset.append(new_entry)
                        processed_queries.add(query)
                        retry_successful = True
                        regenerated_count += 1
                        
                        with open(log_file, 'a', encoding='utf-8') as log:
                            log.write(f"{time.strftime('%H:%M:%S')}: Regenerated #{len(validated_dataset)}: {query[:50]}...\n")
                        
                        print(f"Successfully regenerated entry for query: {query[:50]}")
                        break
            except Exception as e:
                error_msg = f"Error regenerating query '{query[:50]}...': {str(e)}"
                print(f"ERROR: {error_msg}")
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"ERROR {time.strftime('%H:%M:%S')}: {error_msg}\n")
            
            if not retry_successful:
                print(f"Skip after {max_retries} failed attempts for query: {query[:50]}")
                skipped_count += 1
                with open(log_file, 'a', encoding='utf-8') as log:
                    log.write(f"{time.strftime('%H:%M:%S')}: SKIPPED {query[:50]}...\n")
            
            # Save every 10 entries
            if len(validated_dataset) % 10 == 0:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(validated_dataset, f, indent=4)
                print(f"Saved {len(validated_dataset)} validated entries")
        
        # Save final validated dataset
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(validated_dataset, f, indent=4)
        
        print(f"\nValidation complete:")
        print(f"- Original entries: {len(dataset)}")
        print(f"- Valid entries: {len(validated_dataset)}")
        print(f"- Already valid: {already_valid_count}")
        print(f"- Regenerated successfully: {regenerated_count}")
        print(f"- Skipped/invalid: {skipped_count}")
        print(f"- Validated dataset saved to {output_file_path}")
        
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"Completed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Original entries: {len(dataset)}\n")
            log.write(f"Valid entries: {len(validated_dataset)}\n")
            log.write(f"Already valid: {already_valid_count}\n")
            log.write(f"Regenerated successfully: {regenerated_count}\n")
            log.write(f"Skipped/invalid: {skipped_count}\n")
        
        return validated_dataset
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Saving current progress...")
        with open(output_file_path, 'w', encoding='utf-8') as f:
            json.dump(validated_dataset, f, indent=4)
        
        with open(log_file, 'a', encoding='utf-8') as log:
            log.write(f"INTERRUPTED at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            log.write(f"Saved {len(validated_dataset)} validated entries. Can resume later.\n")
            
        print(f"Saved {len(validated_dataset)} validated entries to {output_file_path}")
        print("You can resume by running the same command again.")
        return validated_dataset
    
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        print("Attempting to save current progress...")
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(validated_dataset, f, indent=4)
            
            with open(log_file, 'a', encoding='utf-8') as log:
                log.write(f"ERROR at {time.strftime('%Y-%m-%d %H:%M:%S')}: {str(e)}\n")
                log.write(f"Saved {len(validated_dataset)} entries. Can resume later.\n")
                
            print(f"Saved {len(validated_dataset)} validated entries to {output_file_path}")
            print("You can resume by running the same command again.")
        except:
            print("Failed to save results. Data may be lost.")
        return validated_dataset

def parse_llm_tables(llm_tables_str):
    """
    Parse the LLM filtered tables string into a list of table names.
    
    Args:
        llm_tables_str: String containing comma-separated table names
        
    Returns:
        List of table names
    """
    if not llm_tables_str:
        return []
    
    # Split by comma and strip whitespace
    tables = [table.strip() for table in llm_tables_str.split(',')]
    return [table for table in tables if table]  # Remove empty strings

def process_queries_multithreaded(file_path, max_threads=16):
    """Process queries using multithreading."""
    json_objects = process_json_objects(file_path)
    
    threads = []
    successful_matches = 0
    unsuccessful_matches = 0
    lock = threading.Lock()
    
    def worker(json_obj):
        nonlocal successful_matches, unsuccessful_matches
        if process_single_json_object(json_obj):
            with lock:
                successful_matches += 1
        else:
            with lock:
                unsuccessful_matches += 1
    
    for json_obj in json_objects:
        thread = threading.Thread(target=worker, args=(json_obj,))
        threads.append(thread)
        thread.start()
        
        if len(threads) >= max_threads:
            for t in threads:
                t.join()
            threads = []
    
    for t in threads:
        t.join()
    
    print("\n=== Multithreaded Processing ===")
    print(f"Successful Matches: {successful_matches}")
    print(f"Unsuccessful Matches: {unsuccessful_matches}")

def process_queries_linear(file_path):
    """Process queries one by one in a normal linear way."""
    json_objects = process_json_objects(file_path)
    
    successful_matches = 0
    unsuccessful_matches = 0
    
    for json_obj in json_objects:
        if process_single_json_object(json_obj):
            successful_matches += 1
        else:
            unsuccessful_matches += 1
        
        # Print live updates
        print(f"Processed: {successful_matches + unsuccessful_matches}, "
              f"Successful: {successful_matches}, Unsuccessful: {unsuccessful_matches}")
    
    print("\n=== Linear Processing ===")
    print(f"Successful Matches: {successful_matches}")
    print(f"Unsuccessful Matches: {unsuccessful_matches}")

if __name__ == "__main__":
    sql_file_path = 'other/sample_submission_generate_task.json'
    
    # Create filtered tables dataset with resume capability
    create_filtered_tables_dataset(PATH_TO_SQL_QUERY_TESTING_FILE, "filtered_tables_dataset.json")
    
    # Validate and regenerate entries with resume capability
    validate_and_regenerate_entries("filtered_tables_dataset.json", max_retries=2)
    
    # print("\nRunning Multithreaded Processing...")
    # process_queries_multithreaded(sql_file_path)

    # print("\nRunning Linear Processing...")
    # process_queries_linear(sql_file_path)