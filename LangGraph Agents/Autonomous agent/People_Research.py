#!/usr/bin/env python3
"""
People Researcher Agent – a fully operational agent modeled on the
[people-researcher repo](https://github.com/langchain-ai/people-researcher).

This agent does the following:
  1. Generates search queries based on a person’s details and a desired extraction schema.
  2. Uses Tavily’s asynchronous search API to perform concurrent web searches.
  3. Deduplicates and formats the search results and uses an Anthropic LLM to generate “research notes.”
  4. Extracts structured information from the research notes.
  5. Reflects on the extraction to decide whether the results are satisfactory or if more search is needed.

Before running:
  • Install dependencies:
      pip install tavily-python langchain-community langgraph langchain-anthropic
  • Set your Tavily API key in your environment, for example:
      export TAVILY_API_KEY="tvly-YourApiKeyHere"
  • (Optionally) set other keys as needed.
"""

import os, json, asyncio
from typing import Any, Dict, List, Literal, Optional, cast
from dataclasses import dataclass, fields

from pydantic import BaseModel, Field

# === External SDKs ===
from tavily import AsyncTavilyClient  # Tavily search/extract client (async)
from langchain_anthropic import ChatAnthropic  # For extraction & reflection LLM calls
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.runnables import RunnableConfig

# === LangGraph imports ===
from langgraph.graph import START, END, StateGraph

# ========= Configuration =========

@dataclass(kw_only=True)
class Configuration:
    max_search_queries: int = 3      # Number of search queries to generate
    max_search_results: int = 3      # Maximum search results per query
    max_reflection_steps: int = 1    # Maximum reflection iterations allowed

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> "Configuration":
        configurable = config["configurable"] if config and "configurable" in config else {}
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls) if f.init
        }
        # Only use those values that are not None
        return cls(**{k: v for k, v in values.items() if v is not None})

# ========= State Models =========

# Default extraction schema (as used in the repo)
DEFAULT_EXTRACTION_SCHEMA = {
    "title": "Person",
    "description": "Person information",
    "type": "object",
    "required": ["years_experience", "current_company", "role", "prior_companies"],
    "properties": {
        "role": {
            "type": "string",
            "description": "Current role of the person."
        },
        "years_experience": {
            "type": "number",
            "description": "Years of full-time work experience (excluding internships)."
        },
        "current_company": {
            "type": "string",
            "description": "Name of the current company."
        },
        "prior_companies": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of previous companies."
        }
    }
}

# Input state: what the user provides.
class InputState(BaseModel):
    person: Dict[str, Any]
    extraction_schema: Dict[str, Any] = Field(default_factory=lambda: DEFAULT_EXTRACTION_SCHEMA)
    user_notes: str = ""

# Output state: what is produced during execution.
class OutputState(BaseModel):
    info: Dict[str, Any] = {}
    completed_notes: List[str] = []
    search_queries: List[str] = []
    reflection_steps_taken: int = 0
    is_satisfactory: bool = False

# Overall state is the union of input and output.
class OverallState(InputState, OutputState):
    pass

# ========= Prompt Constants =========

QUERY_WRITER_PROMPT = (
    "Given the following person details: {person}, extraction schema: {info}, and user notes: {user_notes}, "
    "generate up to {max_search_queries} targeted search queries that will help gather information to populate the schema."
)

INFO_PROMPT = (
    "Generate structured research notes based on the following web sources:\n{content}\n"
    "Using the extraction schema below:\n{info}\n"
    "and considering the person details:\n{people}\nUser notes: {user_notes}\n"
)

EXTRACTION_PROMPT = (
    "Using the following research notes:\n{notes}\n"
    "and the extraction schema:\n{info}\n"
    "Extract the relevant information and output valid JSON."
)

REFLECTION_PROMPT = (
    "Review the extracted information below against the extraction schema:\n"
    "Extraction Schema: {schema}\n"
    "Extracted Info: {info}\n"
    "Determine if the extracted information is satisfactory. "
    "If not, list the missing fields and generate 1-3 additional search queries to gather the missing information. "
    "Return your answer as JSON with keys: 'is_satisfactory' (bool), 'missing_fields' (list of strings), "
    "'search_queries' (list of strings), and 'reasoning' (string)."
)

# ========= Utility Functions =========

def deduplicate_and_format_sources(search_docs: List[Dict[str, Any]], max_tokens_per_source: int = 1000, include_raw_content: bool = True) -> str:
    """Deduplicate and join content from search results."""
    seen = set()
    parts = []
    for doc in search_docs:
        results = doc.get("results", [])
        for res in results:
            url = res.get("url")
            if url and url not in seen:
                seen.add(url)
                content = res.get("content", "")
                if len(content) > max_tokens_per_source:
                    content = content[:max_tokens_per_source]
                parts.append(f"Title: {res.get('title', '')}\nURL: {url}\nContent: {content}\n")
    return "\n".join(parts)

def format_all_notes(notes: List[str]) -> str:
    """Concatenate all research notes."""
    return "\n".join(notes)

# ========= Initialize External Clients =========

# Rate limiter for Anthropic calls
from langchain_core.rate_limiters import InMemoryRateLimiter
rate_limiter = InMemoryRateLimiter(requests_per_second=4, check_every_n_seconds=0.1, max_bucket_size=10)

claude_llm = ChatAnthropic(model="claude-3-5-sonnet-latest", temperature=0, rate_limiter=rate_limiter)
tavily_async_client = AsyncTavilyClient()

# ========= Node Functions =========

# 1. Generate search queries based on person details and extraction schema.
def generate_queries(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    configurable = Configuration.from_runnable_config(config)
    max_search_queries = configurable.max_search_queries
    # Build a simple string from person details
    person_str = f"Email: {state.person.get('email', '')}"
    if "name" in state.person:
        person_str += f", Name: {state.person['name']}"
    if "linkedin" in state.person:
        person_str += f", LinkedIn: {state.person['linkedin']}"
    if "role" in state.person:
        person_str += f", Role: {state.person['role']}"
    if "company" in state.person:
        person_str += f", Company: {state.person['company']}"
    query_instructions = QUERY_WRITER_PROMPT.format(
        person=person_str,
        info=json.dumps(state.extraction_schema, indent=2),
        user_notes=state.user_notes,
        max_search_queries=max_search_queries,
    )
    # Define a simple structured output model
    class Queries(BaseModel):
        queries: List[str]
    structured_llm = claude_llm.with_structured_output(Queries)
    results = structured_llm.invoke([
        {"role": "system", "content": query_instructions},
        {"role": "user", "content": "Generate a list of search queries."}
    ])
    state.search_queries = results.queries
    return {"search_queries": results.queries}

# 2. Perform asynchronous web searches using Tavily for each query.
async def research_person(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    configurable = Configuration.from_runnable_config(config)
    max_search_results = configurable.max_search_results
    search_tasks = []
    for query in state.search_queries:
        task = tavily_async_client.search(
            query,
            days=360,
            max_results=max_search_results,
            include_raw_content=True,
            topic="general",
        )
        search_tasks.append(task)
    search_docs = await asyncio.gather(*search_tasks)
    source_str = deduplicate_and_format_sources(search_docs, max_tokens_per_source=1000, include_raw_content=True)
    p = INFO_PROMPT.format(
        info=json.dumps(state.extraction_schema, indent=2),
        content=source_str,
        people=json.dumps(state.person, indent=2),
        user_notes=state.user_notes,
    )
    result = await claude_llm.ainvoke(p)
    state.completed_notes = [str(result.content)]
    return {"completed_notes": state.completed_notes}

# 3. Gather notes and extract structured information.
def gather_notes_extract_schema(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    notes = format_all_notes(state.completed_notes)
    system_prompt = EXTRACTION_PROMPT.format(
        info=json.dumps(state.extraction_schema, indent=2),
        notes=notes
    )
    # For simplicity, call the LLM and try to parse JSON output.
    result = claude_llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Extract the information as valid JSON."}
    ])
    try:
        extracted_info = json.loads(result.content)
    except Exception as e:
        extracted_info = {}
    state.info = extracted_info
    return {"info": extracted_info}

# 4. Reflect on the extraction and decide whether more research is needed.
class ReflectionOutput(BaseModel):
    is_satisfactory: bool
    missing_fields: List[str]
    search_queries: List[str]
    reasoning: str

def reflection(state: OverallState, config: RunnableConfig) -> Dict[str, Any]:
    structured_llm = claude_llm.with_structured_output(ReflectionOutput)
    system_prompt = REFLECTION_PROMPT.format(
        schema=json.dumps(state.extraction_schema, indent=2),
        info=json.dumps(state.info, indent=2)
    )
    result = structured_llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Provide a reflection output as JSON."}
    ])
    reflection_output = result  # This is an instance of ReflectionOutput.
    if reflection_output.is_satisfactory:
        state.is_satisfactory = True
        return {"is_satisfactory": True}
    else:
        state.reflection_steps_taken += 1
        state.search_queries = reflection_output.search_queries
        return {
            "is_satisfactory": False,
            "search_queries": reflection_output.search_queries,
            "reflection_steps_taken": state.reflection_steps_taken,
        }

# 5. Route from reflection: if extraction is satisfactory then end; otherwise, if we haven’t exceeded max steps, go back to research.
def route_from_reflection(state: OverallState, config: RunnableConfig) -> Literal[END, "research_person"]:
    configurable = Configuration.from_runnable_config(config)
    if state.is_satisfactory:
        return END
    if state.reflection_steps_taken < configurable.max_reflection_steps:
        return "research_person"
    return END

# ========= Build the Graph =========

builder = StateGraph(
    OverallState,
    input=InputState,
    output=OutputState,
    config_schema=Configuration,
)

builder.add_node("generate_queries", generate_queries)
builder.add_node("research_person", research_person)  # async node
builder.add_node("gather_notes_extract_schema", gather_notes_extract_schema)
builder.add_node("reflection", reflection)

builder.add_edge(START, "generate_queries")
builder.add_edge("generate_queries", "research_person")
builder.add_edge("research_person", "gather_notes_extract_schema")
builder.add_edge("gather_notes_extract_schema", "reflection")
builder.add_conditional_edges("reflection", route_from_reflection)

graph = builder.compile()

# ========= Main Execution =========

if __name__ == "__main__":
    # Example input state: a person to research and associated parameters.
    initial_state = OverallState(
        person={
            "email": "jane.doe@example.com",
            "name": "Jane Doe",
            "linkedin": "https://www.linkedin.com/in/janedoe",
            "role": "Software Engineer",
            "company": "ExampleCorp"
        },
        extraction_schema=DEFAULT_EXTRACTION_SCHEMA,
        user_notes="Focus on work experience and prior companies.",
        completed_notes=[],
        search_queries=[],
        reflection_steps_taken=0,
        is_satisfactory=False,
        info={}
    )
    # Run the graph (note: since one node is asynchronous, use asyncio.run)
    final_state = asyncio.run(graph.invoke(initial_state))
    
    # Print the final extracted information and the complete state.
    print("Final Extracted Info:")
    print(json.dumps(final_state.get("info", {}), indent=2))
    print("\nComplete State:")
    print(final_state.json(indent=2))
