from google.cloud import bigquery
from dotenv import load_dotenv
import os

PROJECT_ID = os.getenv('PROJECT_ID')
DATASET_ID = os.getenv('DATASET_ID')
_client = bigquery.Client(project=PROJECT_ID)

async def call_procedure(proc_name: str,
                         params: list[bigquery.ScalarQueryParameter] = None):
    # Build fully qualified name using the env-sourced DATASET_ID
    fq_proc = f"{PROJECT_ID}.{DATASET_ID}.{proc_name}"

    if params:
        placeholders = ", ".join(f"@{p.name}" for p in params)
        sql = f"CALL `{fq_proc}`({placeholders})"
        job_config = bigquery.QueryJobConfig(query_parameters=params)
        job = _client.query(sql, job_config=job_config)
    else:
        sql = f"CALL `{fq_proc}`()"
        job = _client.query(sql)

    return [dict(row) for row in job.result()]