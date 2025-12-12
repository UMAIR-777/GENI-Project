import json
import psycopg2
from typing import List, Dict
from itertools import zip_longest

from sqlalchemy import DateTime

from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES

class DatabaseManager:
    def __init__(self, **db_config):
        self.conn = psycopg2.connect(**db_config)

    def create_nodes_table(self) -> None:
        """
        Create 'nodes' table with metadata and timestamps.
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE EXTENSION IF NOT EXISTS vector;
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    input TEXT[] NOT NULL,
                    output TEXT[] NOT NULL,
                    tags TEXT[] NOT NULL,
                    description TEXT[] NOT NULL,
                    spo JSONB NOT NULL,
                    node_metadata JSONB NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """
            )
        self.conn.commit()

    def insert_nodes(self, nodes: List[Dict]) -> None:
        """
        Insert or update nodes with metadata and timestamps.
        """
        with self.conn.cursor() as cur:
            for node in nodes:
                metadata = node.get('node_metadata', {})
                cur.execute(
                    """
                    INSERT INTO nodes (
                        id, input, output, tags, description, spo,
                        node_metadata, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, now(), now())
                    ON CONFLICT (id) DO UPDATE SET
                        input = EXCLUDED.input,
                        output = EXCLUDED.output,
                        tags = EXCLUDED.tags,
                        description = EXCLUDED.description,
                        spo = EXCLUDED.spo,
                        node_metadata = EXCLUDED.node_metadata,
                        updated_at = now();
                    """,
                    (
                        node['id'],
                        node['input'],
                        node['output'],
                        node['tags'],
                        node['description'],
                        json.dumps(node['spo']),
                        json.dumps(metadata)
                    )
                )
        self.conn.commit()

    def fetch_nodes(self) -> List[Dict]:
        """
        Retrieve all nodes, including metadata and timestamps.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, input, output, tags, description, spo, node_metadata, created_at, updated_at FROM nodes;"
            )
            rows = cur.fetchall()

        nodes = []
        for node_id, inp, outp, tags, desc, spo_json, meta_json, c_at, u_at in rows:
            spo = spo_json if isinstance(spo_json, dict) else json.loads(spo_json)
            metadata = meta_json if isinstance(meta_json, dict) else json.loads(meta_json)
            nodes.append({
                'id': node_id,
                'input': inp,
                'output': outp,
                'tags': tags,
                'description': desc,
                'spo': spo,
                'node_metadata': metadata,
                'created_at': c_at.isoformat(),
                'updated_at': u_at.isoformat()
            })
        return nodes

if __name__ == "__main__":
    # Print original
    print("original_available_nodes:", json.dumps(AVAILABLE_NODES, indent=2))

    # Initialize DB manager
    db = DatabaseManager(
        dbname="refactor",
        user="postgres",
        password="ali",
        host="localhost",
        port="5432"
    )
    db.create_nodes_table()
    db.insert_nodes(AVAILABLE_NODES)

    # Fetch from DB
    fetched = db.fetch_nodes()
    print("fetched_available_nodes:", json.dumps(fetched, indent=2))

    # Compare
    # def compare_nodes(orig: List[Dict], new: List[Dict]) -> None:
    #     orig_serial = [json.dumps(n, sort_keys=True) for n in orig]
    #     new_serial  = [json.dumps(n, sort_keys=True) for n in new]
    #     if orig_serial == new_serial:
    #         print(" original and fetched AVAILABLE_NODES match exactly.")
    #     else:
    #         print(" Differences found between original and fetched AVAILABLE_NODES:")
    #         for idx, (o, n) in enumerate(zip_longest(orig_serial, new_serial, fillvalue=None)):
    #             if o != n:
    #                 print(f"-- Index {idx}:")
    #                 print("   original:", o)
    #                 print("   fetched :", n)

    # compare_nodes(AVAILABLE_NODES, fetched)

    