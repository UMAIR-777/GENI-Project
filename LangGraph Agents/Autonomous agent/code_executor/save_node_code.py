from google.cloud import storage
import datetime, hashlib

def save_node_code(code: str, description: str, inputs: list, output: str) -> (str, dict): # type: ignore
    """
    Saves the generated node code to Google Cloud Storage and returns the file URI and metadata.
    The metadata includes:
      - char_length: number of characters in the code
      - line_count: number of lines in the code
      - hash, timestamp, filename, function_description, function_inputs, function_output
    """
    # Set your bucket name
    bucket_name = "nodes_bucket"
    
    # Generate filename based on current UTC timestamp and code hash
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    code_hash = hashlib.sha256(code.encode('utf-8')).hexdigest()[:8]
    filename = f"node_{timestamp}_{code_hash}.py"
    
    # Initialize the Cloud Storage client with your project
    storage_client = storage.Client(project="codet-dev-d5157")
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(filename)
    
    # Upload the code as a string
    blob.upload_from_string(code, content_type="text/x-python")
    
    # Construct the GCS URI
    file_uri = f"gs://{bucket_name}/{filename}"
    
    # Build metadata as before
    base_metadata = {
        "char_length": len(code),
        "line_count": code.count("\n") + 1,
        "hash": code_hash,
        "timestamp": timestamp,
        "filename": filename,
        "function_description": description,
        "function_inputs": inputs,
        "function_output": output
    }
    
    node_metadata = base_metadata
    
    # Print the URI and metadata for testing
    print("Saved Node Code to GCS:")
    print(f"URI: {file_uri}")
    print(f"Metadata: {node_metadata}")
    
    return file_uri, node_metadata

# def save_node_code(code: str,description: str, inputs: list, output: str) -> (str, dict):
#     """
#     Saves the generated node code to a file and returns the file URI and metadata.
#     The metadata now includes:
#       - char_length: the number of characters in the code
#       - line_count: the number of lines in the code
#       - hash, timestamp, filename (base metadata)
#       - Additional details: function name, description, inputs, output, and class name (if any)
#     """
#     # Define storage directory
#     storage_dir = "nodes_storage"
#     os.makedirs(storage_dir, exist_ok=True)
    
#     # Generate filename based on current UTC timestamp and code hash
#     timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
#     code_hash = hashlib.sha256(code.encode('utf-8')).hexdigest()[:8]
#     filename = f"node_{timestamp}_{code_hash}.py"
#     file_path = os.path.join(storage_dir, filename)
    
#     # Save the code to the file
#     with open(file_path, "w", encoding="utf-8") as f:
#         f.write(code)
    
    
#     # Base metadata: character length, line count, hash, timestamp, and filename
#     base_metadata = {
#         "char_length": len(code),
#         "line_count": code.count("\n") + 1,
#         "hash": code_hash,
#         "timestamp": timestamp,
#         "filename": filename,
#         "function_description": description,
#         "function_inputs": inputs,
#         "function_output": output
#     }
    
    
    
#     # Combine base metadata with extra details
#     node_metadata = base_metadata
    
#     # Print the URI and metadata for testing
#     print("Saved Node Code:")
#     print(f"URI: {file_path}")
#     print(f"Metadata: {node_metadata}")
    
#     return file_path, node_metadata



# import os
# from google.cloud import storage

# def upload_file(bucket_name, source_file_path, destination_blob_name):
#     """Uploads a file to the specified Google Cloud Storage bucket."""
#     # Initialize the Cloud Storage client
#     storage_client = storage.Client(project="codet-dev-d5157")
    
#     # Get the bucket and create a blob object
#     bucket = storage_client.bucket(bucket_name)
#     blob = bucket.blob(destination_blob_name)
    
#     # Upload the file from the local file system to the bucket
#     blob.upload_from_filename(source_file_path)
#     print(f"File {source_file_path} uploaded to {destination_blob_name} in bucket {bucket_name}.")

# if __name__ == "__main__":
#     bucket_name = "nodes_bucket"
    
#     # Replace this with the local path of your function file
#     source_file_path = "path/to/local/sample_functions.py"
    
#     # This will be the name of the file once it's in the bucket
#     destination_blob_name = "sample_functions.py"
    
#     upload_file(bucket_name, source_file_path, destination_blob_name)