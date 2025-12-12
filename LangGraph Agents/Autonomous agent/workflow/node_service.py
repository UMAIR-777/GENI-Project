import json
import logging
import os
import re
from typing import List, Dict, Any, Tuple, Union
from dotenv import load_dotenv
from jsonschema import validate, ValidationError
from pydantic import BaseModel, ValidationError, validator
# from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES

from .ai_service import AIService
from .embedding_service import EmbeddingService
from .database_manager import DatabaseManager
from huggingface_hub import InferenceClient
from .template_renderer import TemplateRenderer
# from code_writer import Code_Agent_Node


embedding_service = EmbeddingService()
database_manager = DatabaseManager(embedding_service)

AVAILABLE_NODES = database_manager.fetch_nodes()

# Load environment variables
load_dotenv()

ai_service = AIService(model=os.getenv("MODEL_USED"))

# Initialize logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

NODE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "input": {"type": "array", "items": {"type": "string"}},
            "output": {"type": "array", "items": {"type": "string"}},
            "tags": {"type": "array", "items": {"type": "string"}},
            "description": {"type": "array", "items": {"type": "string"}},
            "spo": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "predicate": {"type": "string"},
                    "object": {"type": "string"}
                },
                "required": ["subject", "predicate", "object"]
            }
        },
        "required": ["id", "input", "output", "tags", "description", "spo"]
    }
}




# =============================================================================
# Common Components and Data Models
# =============================================================================

class spo(BaseModel):
    """Data model for Subject-Predicate-Object.
    
    @Feature: Node Semantic Embedding
    @Scenario: Validate spo structure for consistent embedding generation.
    
    Attributes:
        subject (str): The subject component.
        predicate (str): The predicate component.
        object (str): The object component.
    """
    subject: str
    predicate: str
    object: str

class BlueprintStep(BaseModel):
    """Data model for blueprint steps used in node filtering.
    
    @Feature: Blueprint Step Validation
    @Scenario: Validate blueprint step input with complete and correctly formatted data.
    
    Attributes:
        step (str): Unique identifier for the blueprint step.
        input (List[str]): List of input parameters.
        output (List[str]): List of expected outputs.
        tags (List[str]): Tags for categorization.
        description (List[str]): Detailed descriptions.
        spo (List[str]): Array for subject, predicate, object used in embeddings.
    """

    
    step: str
    input: List[str]
    output: List[str]
    tags: List[str]
    description: List[str]
    spo: List[str]

    @validator("input", "output", "tags", pre=True)
    def validate_lists(cls, v: Any) -> List[str]:
        if isinstance(v, list):
            return v
        logger.warning("Expected list type for attribute, got %s; defaulting to empty list.", type(v))
        return []

    @validator("spo", pre=True, always=True)
    def validate_spo(cls, v: Any) -> List[str]:
        if isinstance(v, dict):
            return [v.get("subject", ""), v.get("predicate", ""), v.get("object", "")]
        elif isinstance(v, list):
            return v
        logger.warning("spo attribute not in expected format; defaulting to empty list.")
        return []


class Node(BaseModel):
    """Data model for node instances used for filtering.
    
    @Feature: Node Data Integrity
    @Scenario: Validate node instance creation with proper formatting of spo.
    
    Attributes:
        id (str): Unique identifier for the node.
        input (List[str]): Input properties.
        output (List[str]): Output properties.
        tags (List[str]): Associated tags.
        description (List[str]): Node description.
        spo (List[str]): Subject, predicate, object for semantic processing.
    """
    id: str
    input: List[str]
    output: List[str]
    tags: List[str]
    description: List[str]
    spo: List[str]

class NodeService:
    """
    Manages node filtering, retrieval, and processing of missing nodes.
    """
    def __init__(self, embedding_service, database_manager, template_renderer, ai_service):
        self.embedding_service = embedding_service
        self.database_manager = database_manager
        self.template_renderer = template_renderer
        self.ai_service = ai_service


    

    # =============================================================================
    # Helper Functions for Data Conversion and Candidate Assembly
    # =============================================================================

    def convert_nodes_to_instances(self, nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Converts raw node dictionaries into validated Node instances.
        
        @Feature: Node Data Conversion
        @Scenario: Robust conversion with error checking and logging for invalid node data.
        
        Args:
            nodes (List[Dict[str, Any]]): List of raw node dictionaries.
        
        Returns:
            List[Dict[str, Any]]: List of validated node dictionaries.
        
        Raises:
            ValidationError: If node conversion fails.
        """
        validated_nodes = []
        for n in nodes:
            try:
                node_data = {
                    **n,
                    "spo": (
                        [n["spo"]["subject"], n["spo"]["predicate"], n["spo"]["object"]]
                        if isinstance(n.get("spo"), dict) else n.get("spo", [])
                    )
                }
                validated_node = Node(**node_data)
                validated_nodes.append(validated_node.dict())
            except ValidationError as ve:
                logger.error("Node validation error: %s", ve.json())
                raise
            except Exception as e:
                logger.error("Unexpected error during node conversion: %s", e, exc_info=True)
                raise
        return validated_nodes

    def convert_blueprint_steps_to_instances(self, blueprint_steps: List[Dict[str, Any]]) -> List[BlueprintStep]:
        """Converts raw blueprint step dictionaries into validated BlueprintStep instances.
        
        @Feature: Blueprint Step Conversion
        @Scenario: Robust conversion with detailed error logging for invalid blueprint step data.
        
        Args:
            blueprint_steps (List[Dict[str, Any]]): List of raw blueprint step dictionaries.
        
        Returns:
            List[BlueprintStep]: List of validated BlueprintStep instances.
        
        Raises:
            ValidationError: If blueprint step conversion fails.
        """
        validated_steps = []
        for step in blueprint_steps:
            try:
                step_data = {
                    **step,
                    "spo": (
                        [step["spo"]["subject"], step["spo"]["predicate"], step["spo"]["object"]]
                        if isinstance(step.get("spo"), dict) else step.get("spo", [])
                    )
                }
                validated_step = BlueprintStep(**step_data)
                validated_steps.append(validated_step)
            except ValidationError as ve:
                logger.error("BlueprintStep validation error: %s", ve.json())
                raise
            except Exception as e:
                logger.error("Unexpected error during blueprint step conversion: %s", e, exc_info=True)
                raise
        return validated_steps

    def build_candidate_list(self, filtered_nodes: List[Dict[str, Any]]) -> str:
        """Builds a formatted candidate list string from a list of node dictionaries.
        
        @Feature: Candidate List Assembly
        @Scenario: Assemble detailed candidate list for AI prompt generation.
        
        Args:
            filtered_nodes (List[Dict[str, Any]]): List of validated node dictionaries.
        
        Returns:
            str: Formatted candidate list string.
        """
        try:
            candidate_lines = []
            for node in filtered_nodes:
                line = (
                    f"node: {node['id']}: input={node['input']}, output={node['output']}, "
                    f"tags={node['tags']}, description={node['description']}, spo={node['spo']}"
                )
                candidate_lines.append(line)
            print(f"\n--- Candidate list --- :\n{candidate_lines}")
            return "\n".join(candidate_lines)
        except Exception as e:
            logger.error("Error building candidate list: %s", e, exc_info=True)
            raise

    # =============================================================================
    # Core Functions
    # =============================================================================

    def filter_ai_prompt(self, step: BlueprintStep, candidate_list: str) -> str:
        """Constructs the AI prompt for filtering candidate nodes based on a blueprint step.
        
        @Feature: Node Filtering - AI Verification for Node Selection
        @Scenario: Prompt Construction for Valid Input Processing
        
        Args:
            step (BlueprintStep): The blueprint step instance.
            candidate_list (str): Formatted string of candidate node details.
        
        Returns:
            str: Constructed prompt for the AI.
        
        Raises:
            Exception: If prompt construction fails.
        """
        try:
            spo_text = " ".join(step.spo) if isinstance(step.spo, list) else str(step.spo)
            prompt = self.template_renderer.render_prompt(
                "filter_nodes_prompt.jinja2",
                step=step,
                candidate_list=candidate_list,
                spo_text=spo_text
            )
            return prompt
        except Exception as e:
            logger.exception("Failed to construct AI prompt for blueprint step '%s'", step.step)
            raise Exception("AI prompt construction error") from e

    def parse_ai_response(self, ai_response: str, step_key: str) -> Union[List[str], str]:
        """Parses the AI response to extract selected node IDs.
        
        @Feature: AI Output Integrity - Parsing and Validation
        @Scenario: Robust AI Response Parsing with Error Recovery
        
        Args:
            ai_response (str): JSON string response from the AI.
            step_key (str): Identifier for the blueprint step.
        
        Returns:
            Union[List[str], str]: List of selected node IDs or "MISSING_NODE" if parsing fails.
        """
        try:
            parsed = json.loads(ai_response)
            if "SELECTED_NODE" in parsed:
                return parsed["SELECTED_NODE"]
            elif "MISSING_NODE" in parsed:
                return "MISSING_NODE"
            else:
                error_msg = f"Unexpected keys in AI response: {list(parsed.keys())}"
                logger.error("Step '%s': %s", step_key, error_msg)
                raise ValueError(error_msg)
        except Exception as e:
            logger.warning("Error parsing AI response for step '%s': %s", step_key, e)
            return "MISSING_NODE"

    def process_blueprint_step(
        self, step: BlueprintStep, similar_nodes: List[Tuple[Dict[str, Any], float]]
    ) -> Tuple[str, List[Dict[str, Any]], bool]:
        """Processes a single blueprint step: builds candidate list, generates AI prompt, 
        and filters candidate nodes based on AI response.
        
        @Feature: AI-Driven Node Matching
        @Scenario: End-to-End Processing of a Blueprint Step including handling of missing and partial candidates
        
        Args:
            step (BlueprintStep): Validated blueprint step.
            similar_nodes (List[Tuple[Dict[str, Any], float]]): List of candidate nodes with similarity scores.
        
        Returns:
            Tuple[str, List[Dict[str, Any]], bool]:
                - Step key (str)
                - Filtered list of candidate nodes (List[Dict[str, Any]])
                - Flag indicating if the step is missing candidates (True if missing, False otherwise)
        """
        step_key = step.step
        try:
            filtered_nodes = [node for node, *_ in similar_nodes]
            if not filtered_nodes:
                logger.warning("No candidates found for blueprint step '%s'", step_key)
                return step_key, [], True

            candidate_list = self.build_candidate_list(filtered_nodes)
            ai_prompt = self.filter_ai_prompt(step, candidate_list)
        except Exception as e:
            logger.error("Error processing blueprint step '%s': %s", step_key, e, exc_info=True)
            return step_key, [], True

        try:
            ai_response = ai_service.ask_ai(ai_prompt)
        except Exception as e:
            logger.error("AI call failed for blueprint step '%s': %s", step_key, e, exc_info=True)
            return step_key, [], True

        parsed_response = self.parse_ai_response(ai_response, step_key)
        if parsed_response == "MISSING_NODE":
            logger.info("AI indicates missing node for blueprint step '%s'", step_key)
            return step_key, [], True

        # Process selected node IDs (supports both dict and list responses)
        if isinstance(parsed_response, dict) and "SELECTED_NODE" in parsed_response:
            selected_ids = parsed_response["SELECTED_NODE"]
        elif isinstance(parsed_response, list):
            selected_ids = parsed_response
        else:
            logger.warning("Unexpected AI response structure for blueprint step '%s'", step_key)
            return step_key, [], True

        selected_nodes = [node for node in filtered_nodes if node.get("id") in selected_ids]
        if not selected_nodes:
            logger.warning("No matching nodes for selected IDs in blueprint step '%s'", step_key)
            return step_key, [], True
        try:
            # validated_nodes = self.validate_nodes(selected_nodes)
            validated_nodes = selected_nodes

        except Exception as e:
            logger.error("Validation failed for selected nodes in blueprint step '%s': %s", step_key, e, exc_info=True)
            return step_key, [], True

        return step_key, validated_nodes, False

    def filter_nodes_by_embedding_batch(
        self, state, blueprint_steps: List[Dict[str, Any]],
        nodes: List[Dict[str, Any]],
        top_k: int = 3
    ) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        """Filters nodes by batch processing blueprint steps using embedding similarity and AI verification.
        
        @Feature: Comprehensive Node Filtering with AI Verification
        @Scenario: End-to-End processing including valid input processing, missing node handling, partial candidate selection,
                and critical failure recovery with monitoring.
        
        Args:
            blueprint_steps (List[Dict[str, Any]]): List of raw blueprint step dictionaries.
            nodes (List[Dict[str, Any]]): List of raw node dictionaries.
            top_k (int, optional): Number of top similar nodes to retrieve per blueprint step. Defaults to 3.
        
        Returns:
            Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
                - Mapping from blueprint step keys to lists of validated candidate nodes.
                - List of blueprint steps (as dicts) for which no matching nodes were found.
        
        Raises:
            Exception: Propagates exceptions from conversion functions and retrieval errors.
        """
        try:
            validated_nodes = self.convert_nodes_to_instances(nodes)
        except Exception as e:
            logger.error("Node conversion failed: %s", e, exc_info=True)
            validated_nodes = []

        try:
            validated_steps = self.convert_blueprint_steps_to_instances(blueprint_steps)
            print(f"\n--- validated_steps (Blueprint steps) --- :\n{validated_steps}")
        except Exception as e:
            logger.error("Blueprint step conversion failed: %s", e, exc_info=True)
            validated_steps = []

        # Retrieve similar nodes for each blueprint step using embeddings
        try:
            # 'Note': 'retrieve_similar_nodes_batch' is assumed to be an existing, high-performance function.
            similar_nodes_by_query = self.retrieve_similar_nodes_batch(validated_steps, top_k)
            print(f"\n--- similar_nodes_by_query RETURNED--- :\n{similar_nodes_by_query}")
        except Exception as e:
            logger.error("Error retrieving similar nodes batch: %s", e, exc_info=True)
            raise

        filtered_nodes_map: Dict[str, List[Dict[str, Any]]] = {}
        missing_nodes_list: List[Dict[str, Any]] = []

        # Process each blueprint step individually.
        for step in validated_steps:
            candidates = similar_nodes_by_query.get(step.step, [])
            step_key, filtered_nodes, is_missing = self.process_blueprint_step(step, candidates)
            filtered_nodes_map[step_key] = filtered_nodes
            if is_missing:
                missing_nodes_list.append({
                    "subtask": step_key,
                    "Function_Inputs": step.input,
                    "Function_Output": step.output,
                    "Function_Tags": step.tags,
                    "Function_Description": step.description,
                    "Function_spo": step.spo,
                })


        logger.debug("Final missing nodes list: %s", json.dumps(missing_nodes_list, indent=2))
        logger.debug("Final filtered nodes map: %s", json.dumps(filtered_nodes_map, indent=2))
        if missing_nodes_list:
            state['missing_node_error']=True
            state['missing_nodes']=missing_nodes_list
        
            return "", missing_nodes_list
        else:
            return filtered_nodes_map, missing_nodes_list
        # return filtered_nodes_map, missing_nodes_list

    def validate_nodes(self, nodes: List[Dict]) -> List[Dict]:
        """Validates nodes against the defined schema."""
        try:
            validate(instance=nodes, schema=NODE_SCHEMA)
            return nodes
        except ValidationError as e:
            print(f"Validation error: {e}")
            # from DATA_FOLDER.save_available_nodes import AVAILABLE_NODES
            return AVAILABLE_NODES[:len(nodes)]
            
    # =============================================================================
    # Helper Functions for Embedding Extraction and Formatting
    # =============================================================================

    def extract_texts_from_step(self, step: BlueprintStep) -> Dict[str, str]:
        """Extracts and concatenates text attributes from a BlueprintStep instance.

        @Feature: Text Extraction for Embedding
        @Scenario: Concatenate input, output, tags, description, and spo for embedding generation.
        
        Args:
            step (BlueprintStep): A validated blueprint step instance.
        
        Returns:
            Dict[str, str]: Dictionary mapping attribute names to concatenated text.
        
        Raises:
            Exception: If text extraction fails.
        """
        try:
            # Match storage pattern: subject + " " + predicate + " " + object
            spo_text = " ".join(step.spo) if isinstance(step.spo, list) else ""
            print(f"\nspo (spo_text): {spo_text}\n")

            texts = {
                "input": ", ".join(step.input),
                "output": ", ".join(step.output),
                "tags": ", ".join(step.tags),
                "description": ", ".join(step.description),
                # "spo": " ".join(step.spo)
                "spo": spo_text
            }
            print(f"\n----Extracted texts from step '{step.step}': {texts}\n ----")
            
            # Add overall text matching storage pattern
            overall_text = (
                f"{step.step}: "
                f"input: {texts['input']}; "
                f"output: {texts['output']}; "
                f"tags: {texts['tags']}; "
                f"description: {texts['description']}; "
                f"spo: {texts['spo']}"
            )
            texts["overall"] = overall_text
            logger.debug("Processed blueprint step '%s': extracted texts %s", step.step, texts)
            print(f"\nOverall text (extract_texts_from_step): {overall_text}\n")
            return texts
        except Exception as e:
            logger.error("Error extracting texts from blueprint step '%s': %s", step.step, e, exc_info=True)
            raise

    def compute_normalized_embeddings(self, texts: Dict[str, str]) -> Dict[str, List[float]]:
        """Computes and normalizes embeddings for given text attributes.

        @Feature: Embedding Computation
        @Scenario: Generate embeddings using get_embeddings and normalize them via normalize_embedding.
        
        Args:
            texts (Dict[str, str]): Dictionary mapping attribute names to text.
        
        Returns:
            Dict[str, List[float]]: Dictionary mapping attribute names to normalized embedding vectors.
        
        Raises:
            Exception: If embedding computation or normalization fails.
        """
        try:
            embeddings = {}
            for key, text in texts.items():
                raw_embedding = self.embedding_service.embed_texts(texts=[text])
                norm_embedding = self.embedding_service.normalize_embedding(raw_embedding)
                embeddings[key] = norm_embedding[0]
            return embeddings
        except Exception as e:
            logger.error("Error computing normalized embeddings: %s", e, exc_info=True)
            raise

    def format_embeddings_for_sql(self, embeddings_list: List[List[float]]) -> List[str]:
        """Formats a list of embedding vectors into SQL-ready string representations.

        @Feature: Embedding Formatting for SQL
        @Scenario: Convert list of floats into a string format accepted by SQL vector arrays.
        
        Args:
            embeddings_list (List[List[float]]): List of embedding vectors.
        
        Returns:
            List[str]: List of string representations of embeddings.
        
        Raises:
            Exception: If formatting fails.
        """
        try:
            return [f'[{",".join(map(str, emb))}]' for emb in embeddings_list]
        except Exception as e:
            logger.error("Error formatting embeddings for SQL: %s", e, exc_info=True)
            raise

    # =============================================================================
    # Database Interaction Functions
    # =============================================================================

    def execute_similarity_query(
        self,
        formatted_input: List[str],
        formatted_output: List[str],
        formatted_tags: List[str],
        formatted_desc: List[str],
        formatted_spo: List[str],
        top_k: int
    ) -> List[Tuple]:
        """Executes the SQL query to retrieve similar nodes using two-stage filtering.

        @Feature: High-Performance SQL Query Execution
        @Scenario: Execute stored procedure retrieve_similar_nodes_twostep_batch with proper parameters.
        
        Args:
            formatted_input (List[str]): SQL-formatted embeddings for input.
            formatted_output (List[str]): SQL-formatted embeddings for output.
            formatted_tags (List[str]): SQL-formatted embeddings for tags.
            formatted_desc (List[str]): SQL-formatted embeddings for description.
            formatted_spo (List[str]): SQL-formatted embeddings for spo.
            top_k (int): Number of top similar nodes to retrieve.
        
        Returns:
            List[Tuple]: List of result rows from the SQL query.
        
        Raises:
            Exception: If SQL execution fails.
        """
        # conn = pool.getconn()
        # pool = get_db_pool()
        pool = self.database_manager.get_db_pool()
        if pool is None:
            # Initialize pool if not done
            from database_manager import DatabaseManager
            DatabaseManager.setup_database()
            pool = self.database_manager.get_db_pool()
            if pool is None:
                raise RuntimeError("Failed to initialize database connection pool")

        conn = pool.getconn()

        try:
            cur = conn.cursor()
            query = """
                SELECT * FROM retrieve_similar_nodes_twostep_batch(
                    %s::vector(1024)[],
                    %s::vector(1024)[],
                    %s::vector(1024)[],
                    %s::vector(1024)[],
                    %s::vector(1024)[],
                    %s::int
                )
            """
            params = (formatted_input, formatted_output, formatted_tags, formatted_desc, formatted_spo, top_k)
            cur.execute(query, params)
            results = cur.fetchall()
            logger.info("SQL query executed successfully; retrieved %d rows", len(results))
            return results
        except Exception as e:
            conn.rollback()
            logger.error("SQL query execution failed: %s", e, exc_info=True)
            raise
        finally:
            cur.close()
            pool.putconn(conn)

    def map_sql_results_to_steps(
        self, 
        results: List[Tuple],
        mapping_keys: List[str]
    ) -> Dict[str, List[Tuple]]:
        """Maps SQL query result rows to their corresponding BlueprintStep keys.

        @Feature: SQL Result Mapping
        @Scenario: Map 8-column SQL rows to blueprint step identifiers ensuring data integrity.
        
        Args:
            results (List[Tuple]): SQL result rows.
            mapping_keys (List[str]): List of blueprint step identifiers.
        
        Returns:
            Dict[str, List[Tuple]]: Mapping from blueprint step keys to lists of candidate node tuples.
        """
        similar_nodes_by_query = {key: [] for key in mapping_keys}
        # print(f"similar_nodes_by_query:___________________{similar_nodes_by_query}")
        for row in results:
            if len(row) != 8:
                logger.warning("Unexpected number of columns in result row: %s", row)
                continue
            query_idx, node_id, input_sim, output_sim, tags_sim, desc_sim, spo_sim, total_score = row
            # print(f"query_idx:_____________________{query_idx}")

            # print(f"node_id:_____________________{node_id}")
            if not isinstance(query_idx, int) or query_idx >= len(mapping_keys):
                logger.warning("Invalid query index %s in row: %s", query_idx, row)
                continue
            key = mapping_keys[query_idx]
            print(f"key:___________________{key}")

            # print(f"Available_nodes:______________________:{AVAILABLE_NODES}")

            # Locate node in AVAILABLE_NODES matching node_id
            node = next((n for n in AVAILABLE_NODES if n.get('id') == node_id), None)
            # print(f"node:___________________{node}")
            
            if node:
                candidate_tuple = (node, total_score, input_sim, output_sim, tags_sim, desc_sim, spo_sim)
                similar_nodes_by_query[key].append(candidate_tuple)
                logger.debug("Mapped node %s to step '%s' with score %s", node_id, key, total_score)
            else:
                logger.warning("Node with id %s not found in AVAILABLE_NODES", node_id)
        return similar_nodes_by_query

    # =============================================================================
    # Core Function: retrieve_similar_nodes_batch
    # =============================================================================

    def retrieve_similar_nodes_batch(self, blueprint_steps: List[BlueprintStep], top_k: int = 5) -> Dict[str, List[Tuple]]:
        """Retrieves similar nodes for a list of BlueprintStep instances using a two-stage filtering process.

        @Feature: High-Performance Workflow Node Matching
        @Scenario: Retrieve Similar Nodes with Two-Stage Filtering for valid blueprint steps and robust edge-case handling.
        
        Args:
            blueprint_steps (List[BlueprintStep]): List of validated blueprint step instances.
            top_k (int, optional): Number of top similar nodes to retrieve. Defaults to 5.
        
        Returns:
            Dict[str, List[Tuple]]: Mapping of blueprint step keys to lists of candidate node tuples.
        
        Raises:
            ValueError: If blueprint_steps is empty.
            Exception: For failures during embedding computation, SQL query execution, or result mapping.
        """
        if not blueprint_steps:
            logger.error("Blueprint steps list is empty.")
            raise ValueError("Blueprint steps list is empty")

        mapping_keys: List[str] = []
        input_embeddings: List[List[float]] = []
        output_embeddings: List[List[float]] = []
        tags_embeddings: List[List[float]] = []
        desc_embeddings: List[List[float]] = []
        spo_embeddings: List[List[float]] = []

        # Process each blueprint step and compute normalized embeddings.
        for step in blueprint_steps:
            mapping_keys.append(step.step)
            texts = self.extract_texts_from_step(step)
            embeddings = self.compute_normalized_embeddings(texts)
            input_embeddings.append(embeddings["input"])
            output_embeddings.append(embeddings["output"])
            tags_embeddings.append(embeddings["tags"])
            desc_embeddings.append(embeddings["description"])
            spo_embeddings.append(embeddings["spo"])
            logger.debug("Processed blueprint step '%s': extracted texts %s", step.step, texts)

        # Format all embeddings for SQL usage.
        formatted_input = self.format_embeddings_for_sql(input_embeddings)
        formatted_output = self.format_embeddings_for_sql(output_embeddings)
        formatted_tags = self.format_embeddings_for_sql(tags_embeddings)
        formatted_desc = self.format_embeddings_for_sql(desc_embeddings)
        formatted_spo = self.format_embeddings_for_sql(spo_embeddings)

        # Execute the similarity SQL query.
        results = self.execute_similarity_query(
            formatted_input, formatted_output, formatted_tags, formatted_desc, formatted_spo, top_k
        )
        logger.info("SQL Query Results: %s", results)

        # Map the SQL results to their respective blueprint steps.
        similar_nodes_by_query = self.map_sql_results_to_steps(results, mapping_keys)
        logger.debug("Final similar_nodes_by_query mapping: %s", similar_nodes_by_query)
        return similar_nodes_by_query


    def process_missing_nodes(self, missing_nodes: list) -> None:
        """Processes nodes that weren't found during filtering by generating new ones.
        
        Args:
            missing_nodes (list): List of dictionaries containing missing node details
        """
        for node in missing_nodes:
            logger.info(f"Processing missing node: {node['Function_Description']}")
            try:
                result = self.ai_service.generate_node(
                    description=node["Function_Description"],
                    inputs=node["Function_Inputs"],
                    outputs=node["Function_Output"]
                )
                logger.info(f"Generated node for {node['Function_Description']}: {result}")
                # Store the new node
                self.database_manager.store_node(result)
            except Exception as e:
                logger.error(f"Failed to process missing node {node['Function_Description']}: {e}")

