"""Offline response-contract validation and transparent fixture agreement summary."""

import json
import math
from pathlib import Path
import statistics


ROOT = Path(__file__).resolve().parents[2]
CORE_RESULTS = ROOT / "docs/jev-rnd/results.json"
QUESTIONS_RESULTS = ROOT / "docs/jev-rnd/questions-results.json"
SUMMARY = ROOT / "docs/jev-rnd/summary.json"
PROBABILITY_TOLERANCE = 0.03
COST_TOLERANCE = 1e-8
P95 = .95
LIMITATIONS = ("Hand-labelled simple synthetic fixtures; paired variants are not independent samples. "
               "No model quality, production calibration or total-workflow cost comparison.")


def number(value, low, high):
    assert isinstance(value, (int, float)) and not isinstance(value, bool)
    assert math.isfinite(value) and low <= value <= high


def check_answer(answer, question):
    assert answer["type"] == question["type"]
    if question["type"] == "noul":
        number(answer["noul"], 0, 1)
        return
    number(answer["confidence"], 0, 1)
    distribution = answer["probabilities"]
    for value in distribution.values():
        number(value, 0, 1)
    # Gateway rounds distributions. Missing score levels can represent zero mass.
    assert abs(sum(distribution.values()) - 1) <= PROBABILITY_TOLERANCE
    if question["type"] == "choice":
        assert answer["choice"] in question["criteria"]
        assert set(distribution) == set(question["criteria"])
    else:
        number(answer["score"], 0, len(question["criteria"]) - 1)
        assert all(str(key) in {str(i) for i in range(len(question["criteria"]))} for key in distribution)


def agreed(run, verdict):
    expected = run["expected"]
    if run["family"] == "primitives":
        return verdict["choice"] == "contradicted" and run["answers"]["failed"]["noul"] >= 0.9 and run["answers"]["severity"]["score"] >= 2
    if expected == "score>=3":
        return verdict["score"] >= 3
    if expected == "score<=1":
        return verdict["score"] <= 1
    # Question fixtures list every acceptable label.
    return verdict["choice"] in expected if isinstance(expected, list) else verdict["choice"] == expected


def latency_summary(runs):
    latencies = sorted(run["latency_ms"] for run in runs)
    return {"min": min(latencies), "median": statistics.median(latencies),
            "p95_nearest_rank": latencies[math.ceil(len(latencies) * P95) - 1], "max": max(latencies)}


def summarize(result):
    """Validate every saved answer against its request and summarize agreement per family."""
    runs = result["runs"]
    counts, by_case = {}, {}
    for run in runs:
        questions = run["request"]["questions"]
        assert set(run["answers"]) == set(questions)
        for name, answer in run["answers"].items():
            check_answer(answer, questions[name])
        verdict = run["answers"][next(iter(questions))]
        family = counts.setdefault(run["family"], {"calls": 0, "agreed": 0})
        family["calls"] += 1
        family["agreed"] += int(agreed(run, verdict))
        by_case.setdefault(run["case_id"], []).append(verdict)
    changed = [name for name, pair in by_case.items() if len(pair) == 2 and pair[0].get("choice") != pair[1].get("choice")]
    shifts = {name: round(abs(pair[0]["confidence"] - pair[1]["confidence"]), 3)
              for name, pair in by_case.items() if len(pair) == 2}
    cost = sum(run["cost_usd"] for run in runs)
    assert abs(cost - result["total_cost_usd"]) < COST_TOLERANCE
    return {"calls": len(runs), "unique_cases": len(by_case), "families": counts,
            "label_changed_by_option_order": changed, "max_confidence_shift": max(shifts.values(), default=0),
            "cost_usd": round(cost, 9), "input_tokens": sum(run["input_tokens"] or 0 for run in runs),
            "latency_ms": latency_summary(runs), "models": sorted({run["model"] for run in runs}),
            "limitations": LIMITATIONS}


def main():
    summary = summarize(json.loads(CORE_RESULTS.read_text()))
    # The questions suite is optional: verify passes before its paid run and validates it afterwards.
    if QUESTIONS_RESULTS.is_file():
        summary["questions"] = summarize(json.loads(QUESTIONS_RESULTS.read_text()))
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
