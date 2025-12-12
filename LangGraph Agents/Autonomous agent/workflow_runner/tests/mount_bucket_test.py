import os
import tempfile
import shutil
import os, tempfile, shutil
from typing import Any, Dict
from google.cloud import storage
from langgraph_handler import LanggraphHandler





# foor test in windows
NODE_MOUNT_POINT = r"D:\Office Work\workflow_branches\ai-workflow-research-py\project\app\WorkflowRunner\mount\node_bucket"
USER_MOUNT_POINT = r"D:\Office Work\workflow_branches\ai-workflow-research-py\project\app\WorkflowRunner\mount\user_bucket"

# for cloude-run or docker
# NODE_MOUNT_POINT = "/mount/node_bucket"
# USER_MOUNT_POINT = "/mount/user_bucket"


def fetch_bucket_to_dir(bucket_name: str, prefix: str, dest_dir: str) -> None:
    """
    Download every blob under `bucket_name` whose name starts with `prefix`
    into `dest_dir`, skipping any directory-placeholder blobs.
    (You can still call this directly if you ever need only a subfolder.)
    """
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=prefix)

    os.makedirs(dest_dir, exist_ok=True)
    for blob in blobs:
        # skip GCS-style "directories"
        if blob.name.endswith("/"):
            continue

        # strip the prefix to compute a relative path
        rel_path = blob.name[len(prefix):].lstrip("/")
        if not rel_path:
            continue  # skip the bare prefix object, if it exists

        local_path = os.path.join(dest_dir, rel_path)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        blob.download_to_filename(local_path)


def mount_bucket(bucket_name: str, dest_dir: str) -> None:
    """
    Download the **entire** GCS bucket `bucket_name` into a fixed local
    directory `dest_dir`, wiping out any old contents first.

    After this, your folder layout under `dest_dir` will exactly mirror
    the bucket's root structure:

        dest_dir/
          TenantNodes/
          TenantNodeWrapper/
          TenantRegistory/
          TenantState/
          …

    Or, for your `availabel_nodes` bucket:

        dest_dir/
          nodes/
            analyze_image.py
            …
    """
    # 1) Remove any previous contents so we start fresh
    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir)

    # 2) Recreate the mount directory
    os.makedirs(dest_dir, exist_ok=True)

    # 3) Download everything under the bucket's root ("") into dest_dir
    fetch_bucket_to_dir(bucket_name, prefix="", dest_dir=dest_dir)



def test_mount_and_cleanup():
    # Mount the shared nodes bucket
    mount_bucket("availabel_nodes", NODE_MOUNT_POINT)
    print("Shared nodes now at:", NODE_MOUNT_POINT)
    print("Contents:", os.listdir(NODE_MOUNT_POINT))

    # Mount the tenant's entire bucket
    mount_bucket("tenant002-workflow", USER_MOUNT_POINT)
    print("Tenant code now at:", USER_MOUNT_POINT)
    print("Contents:", os.listdir(USER_MOUNT_POINT))

    # Clean up
    shutil.rmtree(NODE_MOUNT_POINT)
    shutil.rmtree(USER_MOUNT_POINT)
    print("Cleaned both mount points.")

# if __name__ == "__main__":
#     test_mount_and_cleanup()
#     print("Done")
