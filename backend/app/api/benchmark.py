import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.pep_benchmark_service import pep_benchmark_service
from app.services.pep_dataset_service import pep_dataset_service
from app.schemas.benchmark import (
    BenchmarkSummaryResponse,
    PEPBenchmarkItemResponse,
    BenchmarkRunRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/benchmark", tags=["PEP Benchmark"])


@router.get("", response_model=BenchmarkSummaryResponse)
def get_benchmark_results(db: Session = Depends(get_db)):
    """
    Returns the aggregated PEP blind decision recovery benchmark summary and dataset.
    All data is derived from live python/peps documents and real discuss.python.org threads.
    """
    summary = pep_benchmark_service.get_summary(db)
    return summary


@router.get("/candidates")
def list_benchmark_candidates():
    """
    Lists the verified PEP candidates that have real discuss.python.org threads
    and official 'Rejected Ideas' sections.
    """
    candidates = pep_dataset_service.list_candidate_peps()
    return {
        "candidate_peps": candidates,
        "description": "Python Enhancement Proposals (PEPs) with ground-truth 'Rejected Ideas' and public discuss.python.org threads."
    }


@router.post("/run", response_model=BenchmarkSummaryResponse)
async def run_benchmark(
    payload: Optional[BenchmarkRunRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Executes the live blind decision recovery benchmark against Python PEPs.
    Fetches real PEP ground truth, ingests public Discourse discussions, runs
    DecisionTrail's extraction agent blindly, and computes explainable precision/recall.
    """
    targets = payload.pep_numbers if payload and payload.pep_numbers else None
    force_refresh = payload.force_refresh if payload else False

    await pep_benchmark_service.run_benchmark_suite(
        db=db,
        pep_numbers=targets,
        force_refresh=force_refresh
    )
    return pep_benchmark_service.get_summary(db)


@router.post("/run/{pep_number}", response_model=PEPBenchmarkItemResponse)
async def run_single_pep_benchmark(
    pep_number: int,
    force_refresh: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Evaluates a single PEP on demand.
    """
    record = await pep_benchmark_service.evaluate_pep(
        pep_number=pep_number,
        db=db,
        force_refresh=force_refresh
    )
    return record
