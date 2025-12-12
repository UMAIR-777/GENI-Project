# File Name: workflow_functions.py
# Purpose: Define all the functions used in the workflows (e.g., retrieve, grade_documents, generate, etc.).
# ________________________________________________________

# node file

from chatTemplates import *
from llmConfig import *

def write_post(state):
      system_prompt=state['write_post_system_prompt']
      postTopic=state['postTopic']
      targetAudience=state['targetAudience']
      input_template = write_post_template(system_prompt,postTopic,targetAudience)
      output = llm.invoke(input_template).content
      return {'post' : output}

def summarize(state):
  system_prompt=state['summarize_system_prompt']
  input_summary_text=state['input_summary_text']
  input_template = summarize_template(system_prompt,input_summary_text)
  output = llm.invoke(input_template).content
  return {'summary' : output}

def response_1(state):
    question = state["question"]
    if 'Who' in question:
        return {'ans_1' : 'He is a Graduated in Bs Computer Science'}
    
def response_2(state):
    question = state["question"]
    if 'Who' in question:
        return {'ans_2' : 'Currently he is working as an Ai Engineer'}
    
def call_model(state):
    context_1 = state["ans_1"]
    context_2 = state["ans_2"]
    question = state["question"]
    msg = f"context :\n {context_1} \n {context_2} \n Main question: {question} \n please provide the answer of question according to given context and donot tell naything extra which you donot know , and make sure to answer like a humen"
    reply = llm.invoke(msg)
    return {"final_ans" : reply.content}