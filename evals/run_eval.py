"""
Evaluation benchmark runner for POST /triage.
Tests 8 hand-labeled cases against the endpoint and computes accuracy.
Usage: python evals/run_eval.py [--endpoint http://localhost:8000/triage]
"""

import sys
import os
import json
import requests
import argparse
from datetime import datetime, timezone

EVAL_CASES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases.json")


def run_eval(endpoint_url: str = "http://localhost:8000/triage"):
    print("=" * 65)
    print("  LLM Triage Evaluation Benchmark (8 Labeled Cases)")
    print(f"  Target Endpoint: {endpoint_url}")
    print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 65)

    with open(EVAL_CASES_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total = len(cases)
    category_matches = 0
    urgency_matches = 0
    failures = []

    for c in cases:
        case_id = c["id"]
        input_text = c["input"]
        exp_cat = c["expected_category"]
        exp_urg = c["expected_urgency"]

        try:
            res = requests.post(endpoint_url, json={"text": input_text}, timeout=35)
            if res.status_code != 200:
                print(f"  [FAIL] {case_id}: HTTP {res.status_code} - {res.text[:100]}")
                failures.append({"case_id": case_id, "error": f"HTTP {res.status_code}"})
                continue

            data = res.json()
            got_cat = data.get("category")
            got_urg = data.get("urgency")

            cat_ok = (got_cat == exp_cat)
            urg_ok = (got_urg == exp_urg)

            if cat_ok:
                category_matches += 1
            if urg_ok:
                urgency_matches += 1

            status = "PASS" if (cat_ok and urg_ok) else "PARTIAL" if (cat_ok or urg_ok) else "FAIL"
            print(f"  [{status}] {case_id} -> Category: {got_cat} (expected {exp_cat}) | Urgency: {got_urg} (expected {exp_urg})")

            if not (cat_ok and urg_ok):
                failures.append({
                    "case_id": case_id,
                    "expected": {"category": exp_cat, "urgency": exp_urg},
                    "got": {"category": got_cat, "urgency": got_urg},
                    "reason": data.get("reason")
                })

        except Exception as e:
            print(f"  [ERROR] {case_id}: {str(e)}")
            failures.append({"case_id": case_id, "error": str(e)})

    cat_acc = (category_matches / total) * 100
    urg_acc = (urgency_matches / total) * 100
    full_acc = ((total - len(failures)) / total) * 100

    print("\n" + "=" * 65)
    print("  Evaluation Results Summary:")
    print(f"  Category Accuracy : {category_matches}/{total} ({cat_acc:.1f}%)")
    print(f"  Urgency Accuracy  : {urgency_matches}/{total} ({urg_acc:.1f}%)")
    print(f"  Full Match Score  : {total - len(failures)}/{total} ({full_acc:.1f}%)")
    print("=" * 65)

    return total - len(failures), total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LLM Eval benchmark")
    parser.add_argument("--endpoint", default="http://localhost:8000/triage", help="Endpoint URL")
    args = parser.parse_args()
    run_eval(args.endpoint)
