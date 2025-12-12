from pydantic import BaseModel
from typing import Any, List, Dict

class PromptRequest(BaseModel):
    prompt: str

class PromptResponse(BaseModel):
    prompt: str
    bdd_feature: str

class ToplevelResponse(BaseModel):
    Prompt: str
    Founder_Goal: str
    Client_Type: str
    Revenue_Model: str

class ProjectMetadata(BaseModel):
    project_name: str
    requirements: List[str]

class AnalysisData(BaseModel):
    market_needs: List[str]
    value_propositions: List[str]
    kpis: List[str]

class CompetitorAnalysis(BaseModel):
    competitors: List[Dict[str, str]]

class SegmentationData(BaseModel):
    personas: List[str]
    pain_points: List[str]

class MarketFitData(BaseModel):
    problem_solution_fit: str
    market_size: str

class CUJData(BaseModel):
    journeys: List[Dict[str, str]]

class FeatureFile(BaseModel):
    content: str

class StrategyInput(BaseModel):
    Prompt: str
    Founder_Goal: str
    Client_Type: str
    # in your code you pass strategy_input_data.Revenue_Model,
    # so I’m naming it to match that import:
    Revenue_Model: List[str]

class JsonResponse(BaseModel):
    # used as response_model for all your GET endpoints where you return
    # {"root": <loaded JSON>}, so:
    root: Any

