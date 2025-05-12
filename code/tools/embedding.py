import time
import asyncio
import sys
import os
import glob
import argparse

# Add project root to sys.path to allow imports from other directories in the codebase
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT_DIR)

from config.config import CONFIG
from llm.llm import get_bulk_embeddings as llm_get_bulk_embeddings

def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content
    except Exception as e:
        print(f"Error reading file {file_path}: {str(e)}")
        return None
    
def clean_utf8(text):
    return text.encode('utf-8', errors='ignore').decode('utf-8')

def process_files(schema_file_path, base_name, num_to_process=10000000, provider=None, batch_size=100, output_dir="/tmp"):
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, base_name + ".txt")
    input_path = schema_file_path
    num_done = 0
    try:
        with open(input_path, 'r') as input_file, \
             open(output_path, 'w', encoding='utf-8') as output_file:
            
            batch = []
            batch_urls = []
            batch_jsons = []
            
            for line in input_file:
                # Skip empty lines
                if not line.strip():
                    continue
                
                line = clean_utf8(line)
                try:
                    # Split line by tab
                    url, json_str = line.strip().split('\t')
                    
                    batch_urls.append(url)
                    batch_jsons.append(json_str)
                    batch.append(json_str[0:6000])
                    num_done += 1
                    # Process batch when it reaches the specified batch size
                    if len(batch) == batch_size or (num_done > num_to_process):
                        embeddings = asyncio.run(llm_get_bulk_embeddings(batch, provider=provider))
                        for i in range(len(batch)):
                            output_file.write(f"{batch_urls[i]}\t{batch_jsons[i]}\t{embeddings[i]}\n")
                        print(f"Processed {num_done} lines")
                        # Clear the batches
                        batch = []
                        batch_urls = []
                        batch_jsons = []
                        time.sleep(5)
                except Exception as e:
                    print(f"Error processing line: {str(e)}")
                    continue
                if num_done > num_to_process:
                    break
            # Process any remaining items in the final batch
            if batch:
                embeddings = asyncio.run(llm_get_bulk_embeddings(batch, provider=provider))
                for i in range(len(batch)):
                    output_file.write(f"{batch_urls[i]}\t{batch_jsons[i]}\t{embeddings[i]}\n")
    except Exception as e:
        print(f"Error processing files: {str(e)}")

def process_schema_file(schema_file, output_dir, provider, batch_size, force=False):
    base_name = os.path.basename(schema_file)
    if base_name.endswith("_schemas.txt"):
        base_name = base_name[:-12]
    embedding_file = os.path.join(output_dir, base_name + ".txt")
    if force or not os.path.exists(embedding_file):
        print(f"Processing {base_name}")
        process_files(schema_file, base_name, provider=provider, batch_size=batch_size, output_dir=output_dir)
    else:
        print(f"Skipping {base_name} - embedding file already exists")

def main():
    parser = argparse.ArgumentParser(
        description="Generate and save embeddings for a file or all files in a directory."
    )
    parser.add_argument(
        "input_file_or_directory", type=str,
        help="The input file or directory to process. If a directory, all *_schemas.txt files will be processed."
    )
    parser.add_argument(
        "--provider", type=str, default=None,
        help="The embedding provider to use (default: preferred provider)."
    )
    parser.add_argument(
        "--batch-size", type=int, default=100,
        help="Batch size for embedding requests (default: 100)."
    )
    parser.add_argument(
        "--output-dir", type=str, default="/tmp",
        help="Directory to save embedding files (default: /tmp)."
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Overwrite embedding files even if they already exist."
    )
    args = parser.parse_args()

    input_path = args.input_file_or_directory
    output_dir = args.output_dir
    force = args.force

    if os.path.isdir(input_path):
        # Process all *_schemas.txt files in the directory
        schema_files = glob.glob(os.path.join(input_path, "*_schemas.txt"))
        if not schema_files:
            print(f"No *_schemas.txt files found in directory: {input_path}")
        for schema_file in schema_files:
            process_schema_file(schema_file, output_dir, args.provider, args.batch_size, force=force)
    elif os.path.isfile(input_path):
        process_schema_file(input_path, output_dir, args.provider, args.batch_size, force=force)
    else:
        print(f"Error: {input_path} is not a valid file or directory.")

if __name__ == "__main__":
    main()

