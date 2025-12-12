
-- Create vector extension if not exists
CREATE EXTENSION IF NOT EXISTS vector;

-- Create node_embeddings table with proper columns
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'node_embeddings') THEN
        CREATE TABLE node_embeddings (
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

-- Create HNSW index if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relname = 'idx_overall_embedding' AND n.nspname = current_schema()
    ) THEN
        CREATE INDEX idx_overall_embedding
        ON node_embeddings 
        USING hnsw (overall_embedding vector_cosine_ops);
    END IF;
END
$$;

-- Create workflows table
CREATE TABLE IF NOT EXISTS workflows (
    id SERIAL PRIMARY KEY,
    descriptions TEXT NOT NULL,
    workflow JSONB NOT NULL,
    embedding VECTOR(1024) NOT NULL
);

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
    phase1_threshold FLOAT := 0.7; -- Lowered threshold for initial check
    phase2_threshold FLOAT := 0.5; -- Lowered threshold for individual feature check
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
        FROM queries q, node_embeddings n
        WHERE (
            (1 - (n.input_embedding <=> q.input_emb) >= phase1_threshold) OR
            (1 - (n.output_embedding <=> q.output_emb) >= phase1_threshold) OR
            (1 - (n.tags_embedding <=> q.tags_emb) >= phase1_threshold) OR
            (1 - (n.description_embedding <=> q.desc_emb) >= phase1_threshold) OR
            (1 - (n.spo_embedding <=> q.spo_emb) >= phase1_threshold)
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
    SELECT p2.query_idx, p2.node_id, p2.input_sim, p2.output_sim, p2.tags_sim, p2.desc_sim, p2.spo_sim, p2.total_score
    FROM phase2 p2
    WHERE p2.rank <= top_k;
END;
$function$;