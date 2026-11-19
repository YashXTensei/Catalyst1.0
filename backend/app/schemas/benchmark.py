from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class RejectedIdeaComparisonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ground_truth_idea: Optional[str] = None
    ground_truth_reason: Optional[str] = None
    recovered_idea: Optional[str] = None
    recovered_reason: Optional[str] = None
    status: str  # "matched", "partial", "missed", "unmatched_recovery"
    explanation: str
    confidence: float
    evidence_quote: Optional[str] = None
    discussion_url: Optional[str] = None


class PEPBenchmarkItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pep_number: int
    title: str
    official_url: str
    discussion_url: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    total_ground_truth: int
    total_recovered: int
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: float
    recall: float
    f1_score: float
    participants: List[str] = []
    comparisons: List[RejectedIdeaComparisonSchema] = []


class BenchmarkSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_peps_evaluated: int
    completed_evaluations: int
    failed_evaluations: int
    total_ground_truth_ideas: int
    total_recovered_ideas: int
    total_true_positives: int
    average_precision: float
    average_recall: float
    average_f1_score: float
    methodology: str
    dataset: List[PEPBenchmarkItemResponse]


class BenchmarkRunRequest(BaseModel):
    pep_numbers: Optional[List[int]] = None
    force_refresh: bool = False
