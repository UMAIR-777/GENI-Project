
import json
import os
from typing import Any

from fastapi import HTTPException
from database.session import get_db
from pydantic import BaseModel, create_model
from schemas.db_agent import ProcedureCall

def read_json_file(filepath):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    if not filepath.endswith('.json'):
        raise ValueError("Provided file is not a JSON file.")

    if os.path.getsize(filepath) == 0:
        raise ValueError("File is empty.")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON content: {e}")
    except PermissionError:
        raise PermissionError("Permission denied while reading the file.")
    except Exception as e:
        raise Exception(f"Unexpected error occurred: {e}")
    
async def dynamic_handler(payload: Any, proc=ProcedureCall):
        try:
            values = [getattr(payload, inp["name"]) for inp in proc["inputs"]]
            placeholders = ', '.join(['%s'] * len(values))
            call_sql = f"CALL {proc['procedure']}({placeholders});"

            conn = get_db()
            with conn.cursor() as cur:
                cur.execute(call_sql, values)
                conn.commit()

            return {"status": "success", "called": proc['procedure']}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

