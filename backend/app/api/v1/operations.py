"""
SentinelIQ Operations API Router
Handles Data Generation, Data Validation, Quality Evaluation, Export Downloads, and Audit Log.
"""
import os
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from backend.app.config import settings
from backend.app.database.repository import repo
from backend.app.security.permissions import RequireAdmin, RequireCompliance
from generator.generate import DatasetGenerator
from validation.checks import DataValidator
from evaluation.evaluator import RiskEvaluator
from risk_engine.rules import DEFAULT_RULES

router = APIRouter(tags=["Operations & Audits"])


class GenerationRunRequest(BaseModel):
    profile: str = Field("demo", description="'demo' or 'full'")
    seed: int = Field(20261022, description="Deterministic random seed")


# In-memory tracking of operational jobs
_generation_history = []
_validation_history = []
_evaluation_history = []


# =============================================================================
# Generation Runs
# =============================================================================
@router.post("/generation-runs")
def trigger_generation_run(payload: GenerationRunRequest, user: Dict[str, Any] = RequireAdmin):
    run_id = f"GEN-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    gen = DatasetGenerator(profile=payload.profile, seed=payload.seed)
    manifest = gen.run(
        export_dir=settings.DATASET_EXPORT_DIR,
        gt_dir=settings.GROUND_TRUTH_DIR,
        reports_dir=settings.REPORTS_DIR
    )

    # Re-seed repository in-memory store with generated files
    repo._try_load_exports_into_memory()

    run_record = {
        "run_id": run_id,
        "profile": payload.profile,
        "seed": payload.seed,
        "status": "COMPLETED",
        "triggered_by": user.get("username", "ADMIN"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "record_counts": manifest.get("record_counts", {})
    }
    _generation_history.insert(0, run_record)

    repo.insert_audit_event(
        event_type="DATA_GENERATION_RUN",
        actor_id=user.get("username", "ADMIN"),
        entity_type="SYSTEM",
        entity_id=run_id,
        action_summary=f"Synthetic dataset generated (Profile: {payload.profile}, Seed: {payload.seed})",
        new_value=run_record
    )

    return run_record


@router.get("/generation-runs")
def list_generation_runs():
    return {"runs": _generation_history}


# =============================================================================
# Validation Runs
# =============================================================================
@router.post("/validation-runs")
def trigger_validation_run(user: Dict[str, Any] = RequireCompliance):
    run_id = f"VAL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # Read current state from repository / export files
    validator = DataValidator()
    customers, _ = repo.get_customers(page_size=100)
    accounts, _ = repo.get_accounts(page_size=100)
    transactions, _ = repo.get_transactions(page_size=100)
    alerts, _ = repo.get_alerts(page_size=100)
    cases, _ = repo.get_cases(page_size=100)
    actions = list(repo._memory_store["analyst_actions"].values())
    merchants = list(repo._memory_store["merchants"].values())
    devices = list(repo._memory_store["devices"].values())
    transfers = list(repo._memory_store["transfer_links"].values())

    report = validator.run_all_checks(
        customers=customers,
        accounts=accounts,
        merchants=merchants,
        devices=devices,
        transactions=transactions,
        transfer_links=transfers,
        alerts=alerts,
        cases=cases,
        analyst_actions=actions,
        rules=DEFAULT_RULES
    )

    # Save to reports
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    with open(os.path.join(settings.REPORTS_DIR, "validation_summary.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    val_record = {
        "run_id": run_id,
        "status": "COMPLETED",
        "passed": report["passed"],
        "error_count": report["error_count"],
        "warning_count": report["warning_count"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    _validation_history.insert(0, val_record)

    repo.insert_audit_event(
        event_type="VALIDATION_RUN",
        actor_id=user.get("username", "COMPLIANCE"),
        entity_type="SYSTEM",
        entity_id=run_id,
        action_summary=f"Validation executed. Errors: {report['error_count']}, Warnings: {report['warning_count']}",
        new_value=val_record
    )

    return report


@router.get("/validation-runs")
def list_validation_runs():
    return {"runs": _validation_history}


# =============================================================================
# Evaluation Runs
# =============================================================================
@router.post("/evaluation-runs")
def trigger_evaluation_run(user: Dict[str, Any] = RequireCompliance):
    run_id = f"EVAL-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    # Load ground truth from ground truth directory
    gt_file = os.path.join(settings.GROUND_TRUTH_DIR, "ground_truth.json")
    if not os.path.isfile(gt_file):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ground truth file not found. Please run generator first to establish benchmark."
        )

    with open(gt_file, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    alerts, _ = repo.get_alerts(page_size=100)
    _, total_txns = repo.get_transactions(page_size=1)

    evaluator = RiskEvaluator()
    eval_report = evaluator.evaluate(
        alerts=alerts,
        ground_truth_records=ground_truth,
        total_transactions_count=total_txns
    )

    with open(os.path.join(settings.REPORTS_DIR, "evaluation_summary.json"), "w", encoding="utf-8") as f:
        json.dump(eval_report, f, indent=2)

    eval_record = {
        "run_id": run_id,
        "status": "COMPLETED",
        "precision": eval_report["metrics"]["precision"],
        "recall": eval_report["metrics"]["recall"],
        "f1_score": eval_report["metrics"]["f1_score"],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    _evaluation_history.insert(0, eval_record)

    repo.insert_audit_event(
        event_type="EVALUATION_RUN",
        actor_id=user.get("username", "COMPLIANCE"),
        entity_type="SYSTEM",
        entity_id=run_id,
        action_summary=f"Evaluation completed. Precision: {eval_record['precision']}, Recall: {eval_record['recall']}",
        new_value=eval_record
    )

    return eval_report


@router.get("/evaluation-runs")
def list_evaluation_runs():
    return {"runs": _evaluation_history}


# =============================================================================
# Exports Download
# =============================================================================
@router.get("/exports")
def list_available_exports():
    export_dir = settings.DATASET_EXPORT_DIR
    files = []
    if os.path.isdir(export_dir):
        for f in os.listdir(export_dir):
            if f.endswith((".csv", ".json", ".sql")):
                full_path = os.path.join(export_dir, f)
                files.append({
                    "filename": f,
                    "size_bytes": os.path.getsize(full_path),
                    "download_url": f"/api/v1/exports/{f}"
                })
    return {"exports": files}


@router.get("/exports/{export_type}")
def download_export_file(export_type: str):
    # Sanitize filename
    safe_filename = os.path.basename(export_type)
    file_path = os.path.join(settings.DATASET_EXPORT_DIR, safe_filename)

    # Check reports dir if not in export
    if not os.path.isfile(file_path):
        alt_path = os.path.join(settings.REPORTS_DIR, safe_filename)
        if os.path.isfile(alt_path):
            file_path = alt_path

    if not os.path.isfile(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Export file '{safe_filename}' not found. Please trigger dataset generation."
        )

    media_type = "text/csv" if safe_filename.endswith(".csv") else ("application/json" if safe_filename.endswith(".json") else "application/sql")
    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type=media_type
    )


# =============================================================================
# Audit Log
# =============================================================================
@router.get("/audit")
def list_audit_log(page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=100), entity_type: Optional[str] = None):
    items, total = repo.get_audit_events(page=page, page_size=page_size, entity_type=entity_type)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }
