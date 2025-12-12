# File Name: graph_states.py
# Purpose: Define StateGraph classes for different workflows.

# may be we donot use this file !!!!!!!!!!!!!!!!!!!!!!!

# we will add all functions in functionragistory file

# ______________________________________

import operator
from operator import add
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from langgraph.graph import MessagesState,StateGraph
from typing import List, Optional, Annotated, Sequence


class GraphState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    write_post_system_prompt : str
    postTopic : str
    targetAudience : str
    post: str
    summarize_system_prompt : str
    input_summary_text: str
    #Inputs:
    youtube_url: str
    input_text: str
    content: str
    audience: str
    tone: str
    length: str
    website_url: str
    prompt: str
    context: str
    #Outputs:
    transcript: str
    blog: str
    summary : str
    website_scraped_content: str
    ai_response: str



class q1_state(TypedDict):
    question : str
    ans_1 : str

class output_q1_state(TypedDict):
    ans_1 : str

class q2_state(TypedDict):
    question : str
    ans_2 : str

class output_q2_state(TypedDict):
    ans_2 : str

class finalState(TypedDict):
    # question : Annotated[str, operator.add]
    question : str
    ans_1 : str
    ans_2: str
    final_ans: str


