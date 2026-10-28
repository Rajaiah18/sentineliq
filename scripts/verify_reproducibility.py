"""
SentinelIQ Reproducibility & Checksum Verification Script
Generates datasets twice with identical seed, verifies bitwise checksum equality,
and validates that altering the random seed alters the output data.
"""
import os
import shutil
import tempfile
import sys
import json
import argparse
from generator.generate import DatasetGenerator, sha256_file


DETERMINISTIC_FILES = [
    "customers.csv",
    "accounts.csv",
    "merchants.csv",
    "devices.csv",
    "transactions.csv",
    "transfer_links.csv",
    "risk_rules.csv",
    "alerts.csv",
    "cases.csv",
    "analyst_actions.csv",
    "audit_events.csv",
    "sentineliq_relational_export.sql"
]


def verify_reproducibility(profile: str = "demo", seed: int = 20261022) -> bool:
    print("=" * 80)
    print(f"SentinelIQ Reproducibility Verification Suite (Profile: {profile}, Seed: {seed})")
    print("=" * 80)

    temp_dir_1 = tempfile.mkdtemp(prefix="sentineliq_run1_")
    temp_dir_2 = tempfile.mkdtemp(prefix="sentineliq_run2_")
    temp_dir_diff = tempfile.mkdtemp(prefix="sentineliq_diff_seed_")

    try:
        # Run 1: Same seed
        print(f"\n[1/3] Generating Run 1 (Seed: {seed}) into {temp_dir_1}...")
        gen1 = DatasetGenerator(profile=profile, seed=seed)
        manifest1 = gen1.run(export_dir=temp_dir_1, gt_dir=os.path.join(temp_dir_1, "gt"), reports_dir=os.path.join(temp_dir_1, "rep"))

        # Run 2: Same seed
        print(f"\n[2/3] Generating Run 2 (Seed: {seed}) into {temp_dir_2}...")
        gen2 = DatasetGenerator(profile=profile, seed=seed)
        manifest2 = gen2.run(export_dir=temp_dir_2, gt_dir=os.path.join(temp_dir_2, "gt"), reports_dir=os.path.join(temp_dir_2, "rep"))

        # Run 3: Different seed
        diff_seed = seed + 999
        print(f"\n[3/3] Generating Run 3 with Different Seed ({diff_seed}) into {temp_dir_diff}...")
        gen_diff = DatasetGenerator(profile=profile, seed=diff_seed)
        manifest_diff = gen_diff.run(export_dir=temp_dir_diff, gt_dir=os.path.join(temp_dir_diff, "gt"), reports_dir=os.path.join(temp_dir_diff, "rep"))

        print("\n" + "-" * 80)
        print("Comparing SHA-256 Checksums for Identical Seed Runs:")
        print("-" * 80)

        all_identical = True
        for filename in DETERMINISTIC_FILES:
            file1 = os.path.join(temp_dir_1, filename)
            file2 = os.path.join(temp_dir_2, filename)

            if not os.path.exists(file1) or not os.path.exists(file2):
                print(f"[-] Missing output file: {filename}")
                all_identical = False
                continue

            h1 = sha256_file(file1)
            h2 = sha256_file(file2)

            if h1 == h2:
                print(f"[MATCH] {filename:<32} {h1[:16]}... == {h2[:16]}...")
            else:
                print(f"[MISMATCH] {filename:<32} {h1} != {h2}")
                all_identical = False

        print("\n" + "-" * 80)
        print(f"Verifying Output Divergence with Altered Seed ({diff_seed}):")
        print("-" * 80)

        seed_alters_data = False
        txn_file_1 = os.path.join(temp_dir_1, "transactions.csv")
        txn_file_diff = os.path.join(temp_dir_diff, "transactions.csv")

        h_orig = sha256_file(txn_file_1)
        h_diff = sha256_file(txn_file_diff)

        if h_orig != h_diff:
            seed_alters_data = True
            print(f"[PASS] Divergence confirmed: transactions.csv hash changed with seed {diff_seed}.")
            print(f"       Original Seed ({seed}):      {h_orig}")
            print(f"       Altered Seed  ({diff_seed}): {h_diff}")
        else:
            print("[FAIL] Output was unexpectedly identical with different seed!")

        print("\n" + "=" * 80)
        if all_identical and seed_alters_data:
            print("REPRODUCIBILITY VERIFICATION PASSED: 100% Deterministic & Seed-Sensitive.")
            print("=" * 80)
            return True
        else:
            print("REPRODUCIBILITY VERIFICATION FAILED.")
            print("=" * 80)
            return False

    finally:
        shutil.rmtree(temp_dir_1, ignore_errors=True)
        shutil.rmtree(temp_dir_2, ignore_errors=True)
        shutil.rmtree(temp_dir_diff, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelIQ Reproducibility Verification")
    parser.add_argument("--profile", type=str, default="demo", choices=["demo", "full"])
    parser.add_argument("--seed", type=int, default=20261022)
    args = parser.parse_args()

    success = verify_reproducibility(profile=args.profile, seed=args.seed)
    if not success:
        sys.exit(1)
    sys.exit(0)
