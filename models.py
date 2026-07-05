from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ProteinBase(BaseModel):
    protein_id: str
    protein_name: str
    sequence: Optional[str] = None
    domain: str
    domain_family: Optional[str] = None
    function: str
    organism: Optional[str] = None
    length: Optional[int] = None

class ProteinCreate(ProteinBase):
    pass

class ProteinResponse(ProteinBase):
    id: str   # MongoDB ObjectId as string

class AnalysisResult(BaseModel):
    amino_acid_composition: Dict[str, float]
    physicochemical_properties: Dict[str, float]
    motifs_found: Dict[str, List[int]]
    sequence_complexity: float
    domain_hints: Dict[str, Any]

class RulePrediction(BaseModel):
    domain: str
    confidence: float
    satisfied_conditions: List[str]
    description: str
    score: str

class PredictionRequest(BaseModel):
    query: str
    use_rule_based: bool = True
    analyze_sequence: bool = True

class PredictionResponse(BaseModel):
    match_type: str
    predictions: List[ProteinResponse]
    rule_based_predictions: Optional[List[RulePrediction]] = None
    analysis_results: Optional[AnalysisResult] = None
    confidence: Optional[float] = None
    warnings: List[str] = []