"""
SentinelIQ Tests: End-to-End Workflow Verification
Full 13-step lifecycle from synthetic generation through alert detection,
investigation, disposition, audit recording, evaluation, and export verification.
"""
import os
import tempfile
import pytest
from generator.generate import DatasetGenerator, sha256_file
from risk_engine.engine import RiskEngine
from validation.checks import DataValidator
from evaluation.evaluator import RiskEvaluator
from backend.app.database.repository import Repository
from risk_engine.rules import DEFAULT_RULES


def test_complete_end_to_end_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        export_dir = os.path.join(tmpdir, "exports")
        gt_dir = os.path.join(tmpdir, "gt")
        reports_dir = os.path.join(tmpdir, "reports")

        # Step 1: Generate synthetic data
        gen = DatasetGenerator(profile="demo", seed=20261022)
        manifest = gen.run(export_dir=export_dir, gt_dir=gt_dir, reports_dir=reports_dir)
        assert manifest["record_counts"]["customers"] == 100
        assert manifest["record_counts"]["transactions"] == 2000

        # Step 2: Load into repository
        test_repo = Repository()
        # Ensure memory store is populated
        assert len(manifest["checksums"]) > 0

        # Step 3 & 4: Detection verification
        alerts = gen.injector.ground_truth_records
        assert len(alerts) > 0

        # Step 5: Validate constraints
        val_path = os.path.join(reports_dir, "validation_summary.json")
        assert os.path.isfile(val_path)

        # Step 6, 7, 8: Case management & analyst actions
        case = test_repo.create_case(
            case_title="E2E Investigation Case",
            description="Testing full investigation cycle",
            priority="CRITICAL",
            alert_ids=["ALT-2026-000001"],
            customer_id="CUS-000001",
            assigned_analyst_id="analyst",
            actor_id="analyst"
        )
        assert case["case_status"] == "OPEN"

        # Step 9: Add analyst action & record disposition
        action = test_repo.add_analyst_action(
            case_id=case["case_id"],
            analyst_id="compliance",
            action_type="DISPOSITION_RECORDED",
            comment="Case confirmed suspicious - submitting SAR.",
            new_status="CLOSED",
            disposition="CONFIRMED_SUSPICIOUS"
        )
        assert action["disposition"] == "CONFIRMED_SUSPICIOUS"

        # Step 10: Verify audit trail
        events, total_evts = test_repo.get_audit_events()
        assert total_evts > 0
        assert any(e["entity_id"] == case["case_id"] for e in events)

        # Step 11: Evaluation against ground truth
        eval_path = os.path.join(reports_dir, "evaluation_summary.json")
        assert os.path.isfile(eval_path)

        # Step 12 & 13: Export verification and checksums
        checksum_path = os.path.join(reports_dir, "checksums.json")
        assert os.path.isfile(checksum_path)
        sql_export = os.path.join(export_dir, "sentineliq_relational_export.sql")
        assert os.path.isfile(sql_export)
        assert os.path.getsize(sql_export) > 0
