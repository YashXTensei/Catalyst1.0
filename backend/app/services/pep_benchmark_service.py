import re
import asyncio
import logging
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.benchmark import PEPBenchmarkRecord
from app.services.pep_dataset_service import pep_dataset_service
from app.integrations.discourse_connector import discourse_connector
from app.agents.decision_extractor import decision_extractor
from app.utils.embeddings import generate_embedding, cosine_similarity

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "and", "or", "but", "if", "not", "no", "this", "that",
    "these", "those", "it", "its", "we", "they", "you", "use", "using", "why"
}


def extract_keywords(text: str) -> set:
    words = re.findall(r"\b[a-zA-Z0-9_\*\`\-]{2,}\b", text.lower())
    return set(w.strip("*`_") for w in words if w not in STOP_WORDS)


class PEPBenchmarkService:
    """
    Evaluates DecisionTrail's ability to recover rejected ideas blindly from real discussions.
    Calculates explainable precision, recall, and F1 scores against official PEP ground truth.
    """

    @staticmethod
    async def compare_ideas(
        ground_truth_ideas: List[Dict[str, str]],
        recovered_decisions: List[Dict[str, Any]],
        discussion_url: str,
    ) -> Tuple[List[Dict[str, Any]], int, int, int]:
        """
        Performs explainable, transparent comparison between Ground Truth rejected ideas
        and blindly extracted decisions/rejected alternatives.
        """
        comparisons: List[Dict[str, Any]] = []
        
        # Flatten recovered candidate ideas from extracted decisions
        recovered_candidates = []
        for d in recovered_decisions:
            decision_title = d.get("decision", "")
            reasoning = "; ".join(d.get("reasoning", []))
            evidence = "; ".join(d.get("evidence", []))
            
            # 1. Any explicitly listed rejected alternatives
            for alt in d.get("rejected_alternatives", []):
                recovered_candidates.append({
                    "idea": alt,
                    "reason": reasoning or decision_title,
                    "evidence": evidence,
                    "matched": False,
                })
            # 2. Decisions that were explicitly marked status == "rejected"
            if d.get("status") == "rejected" and decision_title:
                recovered_candidates.append({
                    "idea": decision_title,
                    "reason": reasoning,
                    "evidence": evidence,
                    "matched": False,
                })

        # Precompute embeddings once for candidate and ground-truth items
        gt_embeddings = {}
        for idx, gt in enumerate(ground_truth_ideas):
            try:
                gt_text = f"{gt.get('idea', '')}. {gt.get('reason', '')[:120]}"
                gt_embeddings[idx] = await generate_embedding(gt_text)
            except Exception:
                gt_embeddings[idx] = None

        cand_embeddings = {}
        for idx, cand in enumerate(recovered_candidates):
            try:
                cand_text = f"{cand['idea']}. {cand['reason'][:120]}"
                cand_embeddings[idx] = await generate_embedding(cand_text)
            except Exception:
                cand_embeddings[idx] = None

        true_positives = 0
        matched_gt_count = 0

        # Step 1: Evaluate each Ground Truth idea
        for g_idx, gt in enumerate(ground_truth_ideas):
            gt_idea = gt.get("idea", "")
            gt_reason = gt.get("reason", "")
            gt_words = extract_keywords(f"{gt_idea} {gt_reason[:200]}")
            v1 = gt_embeddings.get(g_idx)

            best_candidate = None
            best_score = 0.0
            best_explanation = ""

            for c_idx, cand in enumerate(recovered_candidates):
                if cand.get("matched"):
                    continue
                cand_idea = cand["idea"]
                cand_reason = cand["reason"]
                cand_words = extract_keywords(f"{cand_idea} {cand_reason}")
                v2 = cand_embeddings.get(c_idx)

                # Keyword overlap
                overlap = len(gt_words.intersection(cand_words))
                kw_score = overlap / max(1, min(len(gt_words), len(cand_words)))

                # Semantic similarity via precomputed vector embeddings
                sem_score = 0.0
                if v1 and v2:
                    try:
                        sem_score = max(0.0, cosine_similarity(v1, v2))
                    except Exception:
                        sem_score = kw_score
                else:
                    sem_score = kw_score

                # Blended explainable score
                combined_score = (0.5 * sem_score) + (0.5 * min(1.0, kw_score * 1.5))

                if combined_score > best_score:
                    best_score = combined_score
                    best_candidate = cand
                    best_explanation = f"Concept overlap: {overlap} matching keywords, semantic score: {sem_score:.2f}."

            # Classification thresholds
            if best_candidate and best_score >= 0.55:
                best_candidate["matched"] = True
                true_positives += 1
                matched_gt_count += 1
                comparisons.append({
                    "ground_truth_idea": gt_idea,
                    "ground_truth_reason": gt_reason[:500],
                    "recovered_idea": best_candidate["idea"],
                    "recovered_reason": best_candidate["reason"][:500],
                    "status": "matched",
                    "explanation": f"Recovered from discussion. {best_explanation}",
                    "confidence": round(best_score, 2),
                    "evidence_quote": best_candidate.get("evidence") or "Direct discussion excerpt.",
                    "discussion_url": discussion_url,
                })
            elif best_candidate and best_score >= 0.38:
                best_candidate["matched"] = True
                comparisons.append({
                    "ground_truth_idea": gt_idea,
                    "ground_truth_reason": gt_reason[:500],
                    "recovered_idea": best_candidate["idea"],
                    "recovered_reason": best_candidate["reason"][:500],
                    "status": "partial",
                    "explanation": f"Partial conceptual alignment ({best_score:.2f}). Reviewable match.",
                    "confidence": round(best_score, 2),
                    "evidence_quote": best_candidate.get("evidence") or "Discussion excerpt.",
                    "discussion_url": discussion_url,
                })
            else:
                comparisons.append({
                    "ground_truth_idea": gt_idea,
                    "ground_truth_reason": gt_reason[:500],
                    "recovered_idea": None,
                    "recovered_reason": None,
                    "status": "missed",
                    "explanation": "Discussed in final PEP document but not recovered from evaluated discussion thread.",
                    "confidence": 0.0,
                    "evidence_quote": None,
                    "discussion_url": discussion_url,
                })

        # Step 2: Identify recovered ideas that did not match any Ground Truth item (False Positives)
        false_positives = 0
        for cand in recovered_candidates:
            if not cand["matched"]:
                false_positives += 1
                comparisons.append({
                    "ground_truth_idea": None,
                    "ground_truth_reason": None,
                    "recovered_idea": cand["idea"],
                    "recovered_reason": cand["reason"][:500],
                    "status": "unmatched_recovery",
                    "explanation": "Extracted as rejected alternative from discussion thread, but absent in final PEP rejected section.",
                    "confidence": 0.70,
                    "evidence_quote": cand.get("evidence"),
                    "discussion_url": discussion_url,
                })

        false_negatives = len(ground_truth_ideas) - matched_gt_count

        return comparisons, true_positives, false_positives, false_negatives

    @classmethod
    async def evaluate_pep(
        cls,
        pep_number: int,
        db: Session,
        force_refresh: bool = False
    ) -> PEPBenchmarkRecord:
        """
        Evaluates a single PEP blindly, persists the record, and returns it.
        Resumable: will not re-run if already completed unless force_refresh=True.
        """
        existing = db.query(PEPBenchmarkRecord).filter(PEPBenchmarkRecord.pep_number == pep_number).first()
        if existing and not force_refresh and existing.status == "completed":
            logger.info(f"PEP {pep_number} benchmark result already exists in DB (resuming).")
            return existing

        # 1. Fetch Ground Truth (isolated)
        gt = await pep_dataset_service.get_pep_ground_truth(pep_number)
        if not gt:
            record = existing or PEPBenchmarkRecord(pep_number=pep_number, title=f"PEP {pep_number}", official_url="")
            record.status = "extraction_failure"
            record.error_message = "Could not fetch or parse official PEP document from python/peps repository."
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        title = gt.get("title", f"PEP {pep_number}")
        official_url = gt.get("official_url", f"https://peps.python.org/pep-{pep_number:04d}/")
        discussion_url = gt.get("primary_discussion_url")
        gt_rejected = gt.get("rejected_ideas", [])

        if not discussion_url:
            record = existing or PEPBenchmarkRecord(pep_number=pep_number, title=title, official_url=official_url)
            record.status = "unavailable_source"
            record.discussion_url = None
            record.total_ground_truth = len(gt_rejected)
            record.error_message = "No public discuss.python.org discussion link found in PEP metadata."
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        # 2. Fetch Discussion Thread
        topic = await discourse_connector.fetch_topic_by_url(discussion_url, max_posts=15)
        if not topic:
            record = existing or PEPBenchmarkRecord(pep_number=pep_number, title=title, official_url=official_url)
            record.status = "unavailable_source"
            record.discussion_url = discussion_url
            record.total_ground_truth = len(gt_rejected)
            record.error_message = f"Discourse topic at {discussion_url} could not be retrieved via Discourse API."
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        # 3. Blind Decision Extraction using existing decision_extractor (NEVER pass ground truth!)
        try:
            recovered_decisions = await decision_extractor.extract_from_discussion(
                title=topic.get("title", title),
                body=topic.get("body", ""),
                source_url=topic.get("url", discussion_url),
                comments=topic.get("comments", []),
                source_type="discourse",
            )
        except Exception as e:
            logger.error(f"Error during decision extraction for PEP {pep_number}: {e}")
            record = existing or PEPBenchmarkRecord(pep_number=pep_number, title=title, official_url=official_url)
            record.status = "extraction_failure"
            record.discussion_url = discussion_url
            record.total_ground_truth = len(gt_rejected)
            record.error_message = f"Decision extraction failed: {str(e)}"
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        # 4. Compare Ground Truth vs Blind Recoveries
        comparisons, tp, fp, fn = await cls.compare_ideas(gt_rejected, recovered_decisions, discussion_url)

        # 5. Compute Metrics
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # 6. Save or Update in DB
        record = existing or PEPBenchmarkRecord(pep_number=pep_number)
        record.title = title
        record.official_url = official_url
        record.discussion_url = discussion_url
        record.status = "completed"
        record.error_message = None
        record.total_ground_truth = len(gt_rejected)
        record.total_recovered = len(recovered_decisions)
        record.true_positives = tp
        record.false_positives = fp
        record.false_negatives = fn
        record.precision = round(precision, 3)
        record.recall = round(recall, 3)
        record.f1_score = round(f1, 3)
        record.comparisons = comparisons
        record.raw_recovered_decisions = recovered_decisions
        record.participants = topic.get("participants", [])

        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @classmethod
    async def run_benchmark_suite(
        cls,
        db: Session,
        pep_numbers: Optional[List[int]] = None,
        force_refresh: bool = False
    ) -> List[PEPBenchmarkRecord]:
        """Runs evaluation sequentially across candidate PEPs with rate-limit pacing."""
        targets = pep_numbers or pep_dataset_service.list_candidate_peps()
        results = []
        for idx, num in enumerate(targets):
            logger.info(f"Evaluating PEP {num} ({idx+1}/{len(targets)})...")
            res = await cls.evaluate_pep(num, db, force_refresh=force_refresh)
            results.append(res)
            # Polite pause between evaluations to respect Gemini 15 RPM quota
            if idx < len(targets) - 1:
                await asyncio.sleep(2.0)
        return results

    @classmethod
    def get_summary(cls, db: Session) -> Dict[str, Any]:
        """Aggregates all benchmark records into an executive summary."""
        records = db.query(PEPBenchmarkRecord).order_by(PEPBenchmarkRecord.pep_number.asc()).all()
        completed = [r for r in records if r.status == "completed"]
        failed = [r for r in records if r.status != "completed"]

        total_gt = sum(r.total_ground_truth for r in completed)
        total_rec = sum(r.total_recovered for r in completed)
        total_tp = sum(r.true_positives for r in completed)

        avg_prec = sum(r.precision for r in completed) / len(completed) if completed else 0.0
        avg_rec = sum(r.recall for r in completed) / len(completed) if completed else 0.0
        avg_f1 = sum(r.f1_score for r in completed) / len(completed) if completed else 0.0

        return {
            "total_peps_evaluated": len(records),
            "completed_evaluations": len(completed),
            "failed_evaluations": len(failed),
            "total_ground_truth_ideas": total_gt,
            "total_recovered_ideas": total_rec,
            "total_true_positives": total_tp,
            "average_precision": round(avg_prec * 100, 1),
            "average_recall": round(avg_rec * 100, 1),
            "average_f1_score": round(avg_f1 * 100, 1),
            "methodology": "Blind Decision Recovery Benchmark: Evaluates whether DecisionTrail's extraction agent recovers rejected architectural ideas from raw public discuss.python.org threads without access to official PEP documents. Reference answers are parsed from python/peps and compared using explainable semantic and keyword matching.",
            "dataset": records,
        }


pep_benchmark_service = PEPBenchmarkService()
