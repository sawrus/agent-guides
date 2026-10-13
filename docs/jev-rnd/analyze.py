"""Offline response-contract validation and transparent fixture agreement summary."""

import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[2]


def number(value, low, high):
    assert isinstance(value, (int, float)) and not isinstance(value, bool)
    assert math.isfinite(value) and low <= value <= high


def main():
    result = json.loads((ROOT / "docs/jev-rnd/results.json").read_text())
    runs = result["runs"]
    counts = {}
    by_case = {}
    for run in runs:
        questions = run["request"]["questions"]
        assert set(run["answers"]) == set(questions)
        for name, answer in run["answers"].items():
            question = questions[name]
            assert answer["type"] == question["type"]
            if question["type"] == "noul":
                number(answer["noul"], 0, 1)
                continue
            number(answer["confidence"], 0, 1)
            distribution = answer["probabilities"]
            for value in distribution.values():
                number(value, 0, 1)
            # Gateway rounds distributions. Missing score levels can represent zero mass.
            assert abs(sum(distribution.values()) - 1) <= 0.03
            if question["type"] == "choice":
                assert answer["choice"] in question["criteria"]
                assert set(distribution) == set(question["criteria"])
            else:
                number(answer["score"], 0, len(question["criteria"]) - 1)
                assert all(str(key) in {str(i) for i in range(len(question["criteria"]))} for key in distribution)
        verdict = run["answers"]["verdict"]
        expected = run["expected"]
        if run["family"] == "primitives":
            agreed = verdict["choice"] == "contradicted" and run["answers"]["failed"]["noul"] >= 0.9 and run["answers"]["severity"]["score"] >= 2
        elif expected == "score>=3":
            agreed = verdict["score"] >= 3
        elif expected == "score<=1":
            agreed = verdict["score"] <= 1
        else:
            agreed = verdict["choice"] == expected
        family = counts.setdefault(run["family"], {"calls": 0, "agreed": 0})
        family["calls"] += 1
        family["agreed"] += int(agreed)
        by_case.setdefault(run["case_id"], []).append(verdict)
    changed = [name for name, pair in by_case.items() if len(pair) == 2 and pair[0].get("choice") != pair[1].get("choice")]
    shifts = {name: round(abs(pair[0]["confidence"] - pair[1]["confidence"]), 3)
              for name, pair in by_case.items() if len(pair) == 2}
    latencies = sorted(run["latency_ms"] for run in runs)
    cost = sum(run["cost_usd"] for run in runs)
    assert abs(cost - result["total_cost_usd"]) < 1e-8
    summary = {"calls": len(runs), "unique_cases": len(by_case), "families": counts,
               "label_changed_by_option_order": changed, "max_confidence_shift": max(shifts.values()),
               "cost_usd": round(cost, 9), "input_tokens": sum(run["input_tokens"] for run in runs),
               "latency_ms": {"min": min(latencies), "median": statistics.median(latencies),
                              "p95_nearest_rank": latencies[math.ceil(len(latencies) * .95) - 1], "max": max(latencies)},
               "models": sorted({run["model"] for run in runs}),
               "limitations": "Hand-labelled simple synthetic fixtures; paired variants are not independent samples. No model quality, production calibration or total-workflow cost comparison."}
    (ROOT / "docs/jev-rnd/summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
