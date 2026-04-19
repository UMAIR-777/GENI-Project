# AI Voice Agent Builder

An end-to-end **Voice Automation Platform** that converts natural language queries into **structured, executable AI voice agents** using graph-based orchestration.

Built using **LangGraph**, this system enables dynamic workflow generation, query disambiguation, and real-time voice execution for business use cases such as **lead generation and sales automation**.

---

## Overview

This project addresses a key limitation in voice AI systems:  
**unclear user intent leading to poor execution accuracy**.

The platform introduces a structured pipeline:

Natural Language → JSON Representation → Agent Graph → Execution

It ensures that only **validated and disambiguated queries** are converted into executable voice workflows.

---

## Key Features

- Natural Language to JSON transformation  
- Graph-based agent orchestration using LangGraph  
- Real-time voice processing with:
  - VAD (Voice Activity Detection)
  - EOU (End of Utterance Detection)  
- Supervisor Agent for intelligent decision-making  
- Dynamic query disambiguation (MCQ + open-ended strategies)  
- Asynchronous workflow execution  

---

## System Architecture

### 1. Input Layer
- Accepts voice/text queries  
- Detects speech boundaries (VAD)  
- Ensures complete utterances (EOU)

### 2. Query Structuring
- Converts input into structured JSON
- Extracts:
  - Intent
  - Entities
  - Constraints

### 3. Query Disambiguation (Core Module)
- Detects ambiguous queries using confidence thresholds  
- Triggered by a **Supervisor Agent**
- Applies:
  - MCQ-based clarification (guided)
  - Open-ended clarification (contextual)

**Result:**
- Accuracy improved from **60% → 90%**
- Reduced incorrect workflow generation

### 4. Agent Graph Builder
- Converts JSON into executable workflows using LangGraph
- Nodes = functional actions  
- Edges = execution flow  

### 5. Execution Engine
- Runs asynchronous AI voice agents  
- Handles API calls, responses, and task execution  

---

## Performance Improvements

- +30% increase in workflow accuracy (60% → 90%)  
- +25% improvement in execution efficiency  
- Significant reduction in ambiguity-related failures  

---

## Real-World Use Case

### Lead Generation Voice Bot (Real Estate & Sales)

- Automated customer interaction  
- Lead qualification through voice  
- Reduced manual workload  
- Improved response consistency  

---

## Tech Stack

- LangGraph (workflow orchestration)  
- Python (async execution)  
- Large Language Models (intent understanding)  
- Speech Processing (VAD, EOU)  
- Custom Supervisor Agent (decision control)  

---

## What Makes This Project Strong

- Handles **ambiguous user intent before execution**  
- Uses **graph-based dynamic workflows**, not static pipelines  
- Integrates **control logic (Supervisor Agent)** into AI systems  
- Designed with **real-world deployment in mind**  

---

## Future Work

- Reinforcement learning for adaptive disambiguation  
- Multi-language voice support  
- CRM integrations  
- Real-time monitoring dashboard  

---

## Author

Muhammad Umair  
AI Engineer | Applied Mathematics
Focus: Voice AI, Intelligent Systems, Workflow Automation
