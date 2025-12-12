# File Name: run_workflow.py
# Purpose: Execute the compiled workflow with input data. 
# Here i will use the main graphBuilder funtion from jsonToLangGraph file.

# ___________________________________________
import os, tempfile, shutil
from typing import Any, Dict
from google.cloud import storage
from .langgraph_handler import LanggraphHandler
from dotenv import load_dotenv
from typing import Dict, List, Optional

#Load environment variables from .env
load_dotenv()  

# Bucket Mounting paths get from env
NODE_MOUNT_POINT = os.getenv("NODE_MOUNT_POINT")
USER_MOUNT_POINT = os.getenv("USER_MOUNT_POINT")

# download bucket to given paths
def fetch_bucket_to_dir(bucket_name: str, prefix: str, dest_dir: str) -> None:
    """
    Download every object under `bucket_name` whose name starts with `prefix`
    into the local directory `dest_dir`, skipping any "directory placeholder"
    blobs (names ending in '/'). Creates any subdirectories needed.

    Args:
        bucket_name: GCS bucket name.
        prefix:      GCS key prefix (e.g. 'nodes/' or '' for the whole bucket).
        dest_dir:    Local filesystem directory where files will be placed.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)

    os.makedirs(dest_dir, exist_ok=True)

    for blob in blobs:
        # Skip folder‐only entries
        if blob.name.endswith("/"):
            continue

        # Compute the path relative to the prefix
        rel_path = blob.name[len(prefix):].lstrip("/")
        if not rel_path:
            # e.g. prefix was '' and blob.name was '', skip
            continue

        local_path = os.path.join(dest_dir, rel_path)
        # Ensure folder exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        # Download the file
        blob.download_to_filename(local_path)

# preparing to mounte bucket
def mount_bucket(bucket_name: str, dest_dir: str) -> None:
    """
    Wipe & recreate `dest_dir`, then download the ENTIRE GCS bucket `bucket_name`
    into it (preserving all top-level folders).
    """
    # 1) Remove any old files
    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir)

    # 2) Recreate the mount point directory
    os.makedirs(dest_dir, exist_ok=True)

    # 3) Download all objects from the bucket root into dest_dir
    fetch_bucket_to_dir(bucket_name, prefix="", dest_dir=dest_dir)


#  Upload all updated files to gcp bucket 
def push_dir_to_bucket(bucket_name: str, source_dir: str, prefix: str = "") -> None:
    """
    Upload all files under `source_dir` into GCS bucket `bucket_name`
    under the given `prefix`. Creates blobs for new files and
    overwrites existing ones.
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    for root, dirs, files in os.walk(source_dir):
        for filename in files:
            local_path = os.path.join(root, filename)
            # Compute path in bucket: <prefix>/<relative path from source_dir>
            rel_path = os.path.relpath(local_path, source_dir)
            blob_name = os.path.join(prefix, rel_path).replace(os.sep, "/")
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            print(f"Uploaded {local_path} → gs://{bucket_name}/{blob_name}")


# main function to run workflow and defined path to connect files
def run_Workflow(
    user_input: List[Dict[str, Any]] ,
    input_json: Dict[str, Any],
    bucket_name: str,
) -> Any:
    """
    1) Download shared 'availabel_nodes' bucket into NODE_MOUNT_POINT
    2) Download the entire tenant bucket into USER_MOUNT_POINT
    3) Generate wrapper, state, and registry under USER_MOUNT_POINT
    4) Build & invoke the LangGraph workflow
    """
    try:
        # ── 1) Mount the avilabel nodes bucket
        os.makedirs(NODE_MOUNT_POINT, exist_ok=True)
        mount_bucket("availabel_nodes", NODE_MOUNT_POINT)

        # ── 2) Mount the tenant's bucket
        os.makedirs(USER_MOUNT_POINT, exist_ok=True)
        mount_bucket(bucket_name, USER_MOUNT_POINT)

        # ── 3) Define where to write our wraper and generated code
        avilabel_nodes_path = os.path.join(NODE_MOUNT_POINT, "nodes")
        user_nodes_path = os.path.join(USER_MOUNT_POINT, "TenantNodes")
        wrapper_path  = os.path.join(USER_MOUNT_POINT, "TenantNodeWrapper", "all_nodes_wraper.py")
        state_path    = os.path.join(USER_MOUNT_POINT, "TenantState",       "state.py")
        registry_path = os.path.join(USER_MOUNT_POINT, "TenantRegistory",   "registry.py")


        for p in (wrapper_path, state_path, registry_path):
            os.makedirs(os.path.dirname(p), exist_ok=True)

        # ── 4) Generate wrapper, state, and registry via our langgraph handler
        handler = LanggraphHandler()
        handler.generate_wrapper_functions_dynamic(
            folder_paths=[avilabel_nodes_path, user_nodes_path],
            output_file_path=wrapper_path,
            config_json=input_json
        )
        handler.generate_graph_state_file(
            json_data=input_json,
            output_file_path=state_path
        )
        handler.generate_registry_from_file_paths(
            function_file_path=wrapper_path,
            class_file_path=state_path,
            output_file_path=registry_path
        )

        # ── 5) Build & run the graph
        from jsonToLangGraph import graph_builder
        app_instance, input_dict, node_list = graph_builder(input_json)
        # print("\n\nWorkflow Results :")
        # print("*"*20)
        # print(app_instance.invoke(input_dict))
        # print("*"*20)

        # ── 6) Push local changes back to the tenant bucket
        # (so any new files/folders you created under USER_MOUNT_POINT end up in GCS)
        push_dir_to_bucket(bucket_name=bucket_name,
                           source_dir=USER_MOUNT_POINT,
                           prefix="")  # or a sub‐prefix if you only want parts
        
        print(f"Bucket-> {bucket_name} is updated successfuly.")
        
        results=[]
        for input in user_input:
            result = app_instance.invoke(input)
            results.append(result)

        return results
        # return (app_instance)

    finally:
        # CLEANUP: remove both mount directories
        shutil.rmtree(NODE_MOUNT_POINT, ignore_errors=True)
        shutil.rmtree(USER_MOUNT_POINT, ignore_errors=True)
        print(f"successfuly un-mounted the bucket {bucket_name}")

# if __name__ == "__main__":
#     # Hardcoded bucket name
#     bucket_name = "tenant002-workflow"
#     # which workflow of bucket to execute
#     workflow_id="workflow1nodes"
#     # run workflow required (input_json,bucket_name,workflow_id)
#     workflow_result=run_Workflow(input_json=json_youtube_transcript_to_summarize,bucket_name=bucket_name,workflow_id=workflow_id)
#     print(workflow_result.keys())
#     print(workflow_result)

# json_youtube_transcript_to_summarize = {
# 'main':{
# 'state':{'mainstate' : 'GraphState', 'inputstate' : None, 'outputstate' : None},
# 'nodes': [
 
#   {'id': 'get_youtube_transcript',
#           'type': 'runnable',
#           'data': {'id': ['langgraph','utils','runnable','RunnableCallable'],'name': 'get_youtube_transcript'},
#           'inputs': {'youtube_url': "https://www.youtube.com/watch?v=qAF1NjEVHhY"},
#           'output': {'transcript': ''}},
  
#   {'id': 'ask_ai',
#           'type': 'runnable',
#           'data': {'id': ['langgraph', 'utils', 'runnable', 'RunnableCallable'], 'name': 'ask_ai'},
#           "inputs": {"prompt": "You are helpfull Assistant You have to Summarize the given Text in few lines.",
#                       "context": ""},
#           'output': {'ai_response': ''}},
  
#   {'id': '__start__', 'type': 'schema', 'data': '__start__'},

#   {'id': '__end__', 'type': 'schema', 'data': '__end__'}],

#  'edges': [{'source': '__start__', 'target': 'get_youtube_transcript'},
#   {'source': 'get_youtube_transcript', 'target': 'ask_ai', 'mapping' : {'context':'transcript'}},
#   {'source': 'ask_ai', 'target': '__end__'}]}
# }