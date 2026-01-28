# File Name: llm_config.py
# Purpose: Configure and initialize different LLMs (e.g., Groq, GPT, Llama).

# _______________________________
# geting key from .env

import os
from dotenv import load_dotenv

# Load variables from the .env file into the environment
load_dotenv()
# os.environ['LANGCHAIN_TRACING_V2'] = 'true'
# os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
# os.environ['LANGCHAIN_PROJECT'] = 'Sub-Workflows'
# os.environ['LANGCHAIN_API_KEY'] = os.getenv("LANGCHAIN_API_KEY")
os.environ['GROQ_API_KEY'] = os.getenv("GROQQ_API_KEY")


# ___________________________________
from langchain_groq import ChatGroq

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

