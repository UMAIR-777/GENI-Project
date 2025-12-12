-- -- Create vector extension if not exists
-- CREATE EXTENSION IF NOT EXISTS vector;

-- -- Create nodes_embeddings table with proper columns
-- DO $$
-- BEGIN
--     IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'nodes_embeddings') THEN
--         CREATE TABLE nodes_embeddings (
--             node_id TEXT PRIMARY KEY,
--             input_embedding VECTOR(1024),
--             output_embedding VECTOR(1024),
--             tags_embedding VECTOR(1024),
--             description_embedding VECTOR(1024),
--             spo_embedding VECTOR(1024),
--             overall_embedding VECTOR(1024)
--         );
--     END IF;
-- END
-- $$;

-- -- Create HNSW index if not exists
-- DO $$
-- BEGIN
--     IF NOT EXISTS (
--         SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
--         WHERE c.relname = 'idx_overall_embedding' AND n.nspname = current_schema()
--     ) THEN
--         CREATE INDEX idx_overall_embedding
--         ON nodes_embeddings 
--         USING ivfflat  (overall_embedding vector_cosine_ops);
--     END IF;
-- END
-- $$;


-- Create vector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Create nodes_embeddings table with proper columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'nodes_embeddings') THEN
        CREATE TABLE nodes_embeddings (
            node_id TEXT PRIMARY KEY,
            input_embedding VECTOR(1024),
            output_embedding VECTOR(1024),
            tags_embedding VECTOR(1024),
            description_embedding VECTOR(1024),
            spo_embedding VECTOR(1024),
            overall_embedding VECTOR(1024)
        );
    END IF;
END
$$;


-- Create index with fallback to ivfflat  if ivfflat  not available
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_overall_embedding' AND n.nspname = current_schema()
    ) THEN
        BEGIN
            -- Try to create HNSW index first
            CREATE INDEX  idx_overall_embedding
            ON nodes_embeddings 
            USING ivfflat  (overall_embedding vector_cosine_ops);
        EXCEPTION WHEN undefined_object THEN
            -- Fall back to ivfflat  if ivfflat  not available
            CREATE INDEX  idx_overall_embedding
            ON nodes_embeddings 
            USING ivfflat  (overall_embedding vector_cosine_ops);
            -- WITH (lists = 100);
        END;
    END IF;
END
$$;


-- in your database_queries.sql (or run manually)

-- drop old if you’re in dev
-- DROP TABLE IF EXISTS workflows;

-- create with the new columns from your SQLAlchemy model
-- CREATE TABLE IF NOT EXISTS workflows (
--     id TEXT PRIMARY KEY,                        -- now a text PK
--     name TEXT NOT NULL,                         -- renamed/added
--     tenant_id TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
--     user_id   TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
--     group_id  TEXT     REFERENCES groups(id) ON DELETE CASCADE,
--     descriptions TEXT NOT NULL,                 -- descriptions (note order)
--     workflow     JSONB NOT NULL,
--     embedding    VECTOR(1024) NOT NULL,
--     is_public    BOOLEAN DEFAULT FALSE,
--     version      TEXT   NOT NULL DEFAULT '1',
--     created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
--     updated_at   TIMESTAMPTZ         DEFAULT now()
-- );

-- if you need an index on embedding
-- DO $$
-- BEGIN
--   IF NOT EXISTS (
--     SELECT 1
--       FROM pg_class c
--       JOIN pg_namespace n ON n.oid = c.relnamespace
--      WHERE c.relname = 'idx_workflow_embedding'
--        AND n.nspname = current_schema()
--   ) THEN
--     CREATE INDEX idx_workflow_embedding
--       ON workflows
--       USING ivfflat  (embedding vector_cosine_ops);
--   END IF;
-- END$$;


-- Create ivfflat  index for pgvector 0.4.0
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE c.relname = 'idx_workflow_embedding'
       AND n.nspname = current_schema()
  ) THEN
    -- Using ivfflat  instead of ivfflat  for v0.4.0 compatibility
    CREATE INDEX  idx_workflow_embedding
      ON workflows
      USING ivfflat  (embedding vector_cosine_ops);
    --   WITH (lists = 100);  -- Adjust lists parameter based on your data size
  END IF;
END$$;



-- Create or replace the two-stage similarity retrieval function
CREATE OR REPLACE FUNCTION retrieve_similar_nodes_twostep_batch(
    query_inputs VECTOR(1024)[],
    query_outputs VECTOR(1024)[],
    query_tags VECTOR(1024)[],
    query_descriptions VECTOR(1024)[],
    query_spos VECTOR(1024)[],
    top_k INT
) RETURNS TABLE (
    query_idx INT,
    node_id TEXT,
    input_sim FLOAT,
    output_sim FLOAT,
    tags_sim FLOAT,
    desc_sim FLOAT,
    spo_sim FLOAT,
    total_score FLOAT
) LANGUAGE plpgsql AS $function$
DECLARE
    phase1_threshold FLOAT := 0.6; -- Average similarity threshold for Phase 1
    phase2_threshold FLOAT := 0.5; -- Strict individual feature threshold for Phase 2
BEGIN
    RETURN QUERY
    WITH queries AS (
        SELECT (ordinality - 1)::INT AS query_idx, input_emb, output_emb, tags_emb, desc_emb, spo_emb
        FROM unnest(
            query_inputs, query_outputs, query_tags, query_descriptions, query_spos
        ) WITH ORDINALITY AS t(input_emb, output_emb, tags_emb, desc_emb, spo_emb, ordinality)
    ),
    phase1 AS (
        SELECT q.query_idx, n.node_id,
            1 - (n.input_embedding <=> q.input_emb) AS input_sim,
            1 - (n.output_embedding <=> q.output_emb) AS output_sim,
            1 - (n.tags_embedding <=> q.tags_emb) AS tags_sim,
            1 - (n.description_embedding <=> q.desc_emb) AS desc_sim,
            1 - (n.spo_embedding <=> q.spo_emb) AS spo_sim
        FROM queries q, nodes_embeddings n
        WHERE (
            ((
                (1 - (n.input_embedding <=> q.input_emb)) +
                (1 - (n.output_embedding <=> q.output_emb)) +
                (1 - (n.tags_embedding <=> q.tags_emb)) +
                (1 - (n.description_embedding <=> q.desc_emb)) +
                (1 - (n.spo_embedding <=> q.spo_emb))
            ) / 5) >= phase1_threshold  -- Average similarity >= phase1_threshold
        )
    ),
    phase2 AS (
        SELECT p.*,
            (p.input_sim + p.output_sim + p.tags_sim + p.desc_sim + p.spo_sim) * 0.2 AS total_score,
            ROW_NUMBER() OVER (
                PARTITION BY p.query_idx
                ORDER BY (p.input_sim + p.output_sim + p.tags_sim + p.desc_sim + p.spo_sim) DESC
            ) AS rank
        FROM phase1 p
        WHERE (
            p.input_sim >= phase2_threshold AND
            p.output_sim >= phase2_threshold AND
            p.tags_sim >= phase2_threshold AND
            p.desc_sim >= phase2_threshold AND
            p.spo_sim >= phase2_threshold
        )
    )
    SELECT p2.query_idx, p2.node_id::text AS node_id, p2.input_sim, p2.output_sim, p2.tags_sim, p2.desc_sim, p2.spo_sim, p2.total_score
    FROM phase2 p2
    WHERE p2.rank <= top_k;
END;
$function$;