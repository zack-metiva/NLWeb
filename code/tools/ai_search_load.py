import os
import sys
import argparse

# Add project root to sys.path to allow imports from other directories
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    VectorSearchAlgorithmKind
)
from db_create_utils import documentsFromCSVLine
from config.config import CONFIG

# This file contains the code to create the AI Search vector databases
# and load them with the schema json and associated embeddings
# This is not part of the runtime, but is used for uploading the data

def get_index_client():
    """Get a search client for the index"""
    credential = AzureKeyCredential(API_KEY)
    return SearchClient(endpoint=ENDPOINT, index_name=INDEX_NAME, credential=credential)

def get_index_admin_client():
    """Get a SearchIndexClient for managing indexes"""
    credential = AzureKeyCredential(API_KEY)
    return SearchIndexClient(endpoint=ENDPOINT, credential=credential)

def create_vector_search_config(algorithm_name="hnsw_config", profile_name="vector_config"):
    """Create and return a vector search configuration"""
    return VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=algorithm_name,
                kind=VectorSearchAlgorithmKind.HNSW,
                parameters={
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500,
                    "metric": "cosine"
                }
            )
        ],
        profiles=[
            VectorSearchProfile(
                name=profile_name,
                algorithm_configuration_name=algorithm_name,
            )
        ]
    )

def drop_index():
    """
    Drop the index from Azure Search service.
    Returns:
        bool: True if the index was dropped, False otherwise.
    """
    index_client = get_index_admin_client()
    try:
        index_client.delete_index(INDEX_NAME)
        print(f"Index '{INDEX_NAME}' dropped successfully.")
        return True
    except Exception as e:
        error_message = str(e)
        if "ResourceNotFound" in error_message:
            print(f"Index '{INDEX_NAME}' does not exist, skipping.")
        else:
            print(f"Error dropping index '{INDEX_NAME}': {error_message}")
        return False

def create_index_definition(profile_name="vector_config"):
    """Create and return an index definition with specified embedding size"""
    # TODO: Detect embedding size from the data
    embedding_size = 1536
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
        SimpleField(name="url", type=SearchFieldDataType.String,  filterable=True),
        SimpleField(name="name", type=SearchFieldDataType.String, filterable=True, sortable=True),
        SimpleField(name="site", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="schema_json", type=SearchFieldDataType.String, filterable=False),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            vector_search_dimensions=embedding_size,
            vector_search_profile_name=profile_name
        )
    ]
    vector_search = create_vector_search_config(profile_name=profile_name)
    return SearchIndex(name=INDEX_NAME, fields=fields, vector_search=vector_search)

def create_search_index():
    """Create the search index with the specified name and embedding size"""
    index_client = get_index_admin_client()
    index = create_index_definition()
    index_client.create_or_update_index(index)
    print(f"Index '{INDEX_NAME}' created or updated successfully.")

def get_documents_from_csv(csv_file_path, site):
    """Read CSV file and return documents for a specific index"""
    documents = []
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        for line in file:
            if line.strip():  # Skip empty lines
                try:
                    docs = documentsFromCSVLine(line, site)
                    for document in docs:
                        documents.append(document)
                except ValueError as e:
                    print(f"Skipping row due to error: {str(e)}")
    
    return documents

def upload_documents(documents, site):
    """Upload documents to the index in batches"""
    index_client = get_index_client()
    # TODO: Should this be configurable based on embedding size?
    batch_size = 1000
    total_batches = (len(documents) + batch_size - 1) // batch_size
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]
        current_batch = i // batch_size + 1
        index_client.upload_documents(batch)
        print(f"Uploaded batch {current_batch} of {total_batches} ({len(batch)} documents) to {INDEX_NAME} from {site}")

def upload_data_from_csv(csv_file_path, site):
    """Process CSV file and upload documents to the index"""
    documents = get_documents_from_csv(csv_file_path, site)
    print(f"Found {len(documents)} documents from {site}")
    upload_documents(documents, site)
    return len(documents)

def main():
    parser = argparse.ArgumentParser(
        description="Load embeddings into Azure AI Search. Optionally reload the index and/or specify the endpoint."
    )
    parser.add_argument(
        "input_file_or_directory", type=str,
        help="Source file or directory containing embedding .txt files to upload."
    )
    parser.add_argument(
        "--reload", action="store_true",
        help="Drop and recreate the index before uploading data."
    )
    parser.add_argument(
        "--endpoint", type=str, default=None,
        help="Override the endpoint name (default: preferred endpoint from config)."
    )
    args = parser.parse_args()

    # Select endpoint: default to preferred but allow override
    global INDEX_NAME, API_KEY, ENDPOINT
    endpoint_name = args.endpoint or CONFIG.preferred_retrieval_endpoint
    azure_config = CONFIG.retrieval_endpoints[endpoint_name]
    # Check db_type matches for this loader
    if getattr(azure_config, 'db_type', None) != 'azure_ai_search':
        print(f"Error: This loader only supports Azure AI search. The selected endpoint ('{endpoint_name}') has db_type '{getattr(azure_config, 'db_type', None)}'.")
        exit(1)
    INDEX_NAME = azure_config.index_name
    API_KEY = azure_config.api_key
    ENDPOINT = azure_config.api_endpoint

    print(f"Using Azure endpoint: {ENDPOINT}")

    if args.reload:
        drop_index()
        create_search_index()
    else:
        # Check if index exists
        try:
            get_index_admin_client().get_index(INDEX_NAME)
            print(f"Using existing index '{INDEX_NAME}'")
        except Exception as e:
            print(f"Error: Index '{INDEX_NAME}' does not exist. Please run with the --reload argument to create it.")
            exit(1)
            
    source_path = args.input_file_or_directory
    if os.path.isdir(source_path):
        csv_files = [f.replace('.txt', '') for f in os.listdir(source_path) if f.endswith('.txt')]
        print(csv_files)
        total_documents = 0
        for csv_file in csv_files:
            print(f"\nProcessing file: {csv_file}")
            csv_file_path = os.path.join(source_path, f"{csv_file}.txt")
            try:
                documents_added = upload_data_from_csv(csv_file_path, csv_file)
                total_documents += documents_added
            except Exception as e:
                print(f"Error processing file {csv_file}: {e}")
        print(f"\nData processing completed successfully. {total_documents} total documents added.")
    elif os.path.isfile(source_path):
        base_name = os.path.splitext(os.path.basename(source_path))[0]
        print(f"\nProcessing file: {base_name}")
        try:
            documents_added = upload_data_from_csv(source_path, base_name)
            print(f"\nData processing completed successfully. {documents_added} total documents added.")
        except Exception as e:
            print(f"Error processing file {base_name}: {e}")
    else:
        print(f"Error: {source_path} is not a valid file or directory.")

if __name__ == "__main__":
    main()
