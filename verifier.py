"""
YUKA Challenge Verifier
Checks submitted answers against the challenge answer hash.
For code challenges, runs test cases.
"""

import json
import hashlib
import subprocess
import tempfile
from pathlib import Path

CHALLENGES_DIR = Path(__file__).parent / "challenges"

# ── Answer checking ───────────────────────────────────────────────────────────

def hash_answer(answer: str) -> str:
    return hashlib.sha256(answer.strip().lower().encode()).hexdigest()

def check_answer(challenge_id: str, submitted_answer: str) -> dict:
    # find the public challenge file
    matches = list(CHALLENGES_DIR.glob(f"public-{challenge_id}.json"))
    if not matches:
        return {"correct": False, "reason": "challenge not found"}

    challenge = json.loads(matches[0].read_text())

    if challenge["status"] != "active":
        return {"correct": False, "reason": f"challenge is {challenge['status']}"}

    submitted_hash = hash_answer(submitted_answer)
    correct = submitted_hash == challenge["answer_hash"]

    return {
        "correct": correct,
        "challenge_id": challenge_id,
        "submitted_hash": submitted_hash[:16] + "...",
        "reason": "correct answer" if correct else "wrong answer",
    }

# ── Code challenge runner ─────────────────────────────────────────────────────

def run_code_challenge(challenge_id: str, submitted_code: str) -> dict:
    matches = list(CHALLENGES_DIR.glob(f"public-{challenge_id}.json"))
    if not matches:
        return {"passed": False, "reason": "challenge not found"}

    challenge = json.loads(matches[0].read_text())
    test_cases = challenge.get("test_cases", [])

    if not test_cases:
        return {"passed": False, "reason": "no test cases found"}

    results = []
    for i, tc in enumerate(test_cases):
        test_script = f"""
{submitted_code}

result = {challenge.get('function_name', 'solution')}({tc['input']!r})
print(repr(result))
"""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(test_script)
            tmp_path = f.name

        try:
            proc = subprocess.run(
                ["python3", tmp_path],
                capture_output=True, text=True, timeout=5
            )
            output = proc.stdout.strip().strip("'\"")
            expected = str(tc["expected"])
            passed = output == expected
            results.append({
                "test": i + 1,
                "passed": passed,
                "expected": expected,
                "got": output,
            })
        except subprocess.TimeoutExpired:
            results.append({"test": i + 1, "passed": False, "reason": "timeout"})
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    all_passed = all(r["passed"] for r in results)
    return {
        "passed": all_passed,
        "results": results,
        "score": f"{sum(r['passed'] for r in results)}/{len(results)}",
    }

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("usage: python verifier.py <challenge_id> <answer>")
        sys.exit(1)

    challenge_id = sys.argv[1]
    answer = sys.argv[2]

    result = check_answer(challenge_id, answer)
    print(json.dumps(result, indent=2))
