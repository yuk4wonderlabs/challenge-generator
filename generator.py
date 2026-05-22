"""
YUKA Challenge Generator
Generates deterministic proof-of-inference challenges using Claude.
Hard for weak models, solvable by strong ones, verifiable on-chain.
"""

import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import anthropic

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

CHALLENGES_DIR = Path(__file__).parent / "challenges"
CHALLENGES_DIR.mkdir(exist_ok=True)

# ── Challenge types ───────────────────────────────────────────────────────────

CHALLENGE_PROMPTS = {
    "math": """Generate a multi-step math reasoning challenge.

Rules:
- Must have exactly ONE correct numerical answer
- Requires 3-5 reasoning steps to solve
- Cannot be solved by pattern matching alone
- Should be hard for a small model (GPT-3.5 level) but solvable by a strong model

Return JSON only:
{
  "prompt": "the challenge question",
  "answer": "the exact correct answer (number only)",
  "solution": "step by step solution",
  "difficulty": 1-5
}""",

    "code": """Generate a code challenge where the agent must write a Python function.

Rules:
- Must have deterministic, testable output
- Requires actual reasoning, not just syntax knowledge
- Include 3 test cases the solution must pass
- Hard for weak models, solvable by strong ones

Return JSON only:
{
  "prompt": "write a python function that...",
  "function_name": "the function name",
  "test_cases": [{"input": ..., "expected": ...}, ...],
  "answer": "the complete correct python function",
  "difficulty": 1-5
}""",

    "logic": """Generate a logic/constraint satisfaction puzzle.

Rules:
- Must have exactly ONE valid solution
- Requires multi-step deductive reasoning
- Cannot be guessed, must be derived
- Hard for weak models, clear for strong ones

Return JSON only:
{
  "prompt": "the logic puzzle",
  "answer": "the exact correct answer",
  "solution": "the deductive reasoning steps",
  "difficulty": 1-5
}"""
}

# ── Generation ────────────────────────────────────────────────────────────────

def generate_challenge(challenge_type: str = "math") -> dict:
    if challenge_type not in CHALLENGE_PROMPTS:
        raise ValueError(f"unknown type: {challenge_type}. use: {list(CHALLENGE_PROMPTS.keys())}")

    print(f"[generating] {challenge_type} challenge...")

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[{
            "role": "user",
            "content": CHALLENGE_PROMPTS[challenge_type]
        }]
    )

    raw = response.content[0].text.strip()

    # strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    challenge_data = json.loads(raw.strip())

    # verify the answer field exists
    if "answer" not in challenge_data:
        raise ValueError("generated challenge missing answer field")

    return challenge_data

# ── Verification ──────────────────────────────────────────────────────────────

def verify_challenge(challenge_data: dict) -> bool:
    """Ask Claude to independently verify the answer is correct."""
    print("[verifying] cross-checking answer...")

    prompt = f"""Verify this challenge and its answer. Reply with JSON only.

CHALLENGE: {challenge_data['prompt']}
CLAIMED ANSWER: {challenge_data['answer']}

Is the answer correct? Work through it independently.

Return JSON only:
{{"correct": true/false, "verified_answer": "your answer", "notes": "any issues"}}"""

    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    result = json.loads(raw.strip())
    return result.get("correct", False)

# ── Packaging ─────────────────────────────────────────────────────────────────

def hash_answer(answer: str) -> str:
    return hashlib.sha256(answer.strip().lower().encode()).hexdigest()

def package_challenge(challenge_data: dict, challenge_type: str, epoch: int) -> dict:
    challenge_id = str(uuid.uuid4())[:8]
    answer = str(challenge_data["answer"])

    return {
        "id": challenge_id,
        "epoch": epoch,
        "type": challenge_type,
        "prompt": challenge_data["prompt"],
        "answer_hash": hash_answer(answer),        # public — for verification
        "answer": answer,                           # keep private until epoch ends
        "solution": challenge_data.get("solution", ""),
        "test_cases": challenge_data.get("test_cases", []),
        "difficulty": challenge_data.get("difficulty", 3),
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "status": "active",
    }

def save_challenge(packaged: dict) -> Path:
    fname = CHALLENGES_DIR / f"epoch-{packaged['epoch']:04d}-{packaged['id']}.json"

    # save public version (no answer)
    public = {k: v for k, v in packaged.items() if k not in ("answer", "solution")}
    public_path = CHALLENGES_DIR / f"public-{packaged['id']}.json"
    public_path.write_text(json.dumps(public, indent=2))

    # save full version (with answer — keep private)
    fname.write_text(json.dumps(packaged, indent=2))

    print(f"[saved] {fname}")
    return fname

# ── Main ──────────────────────────────────────────────────────────────────────

def issue_challenge(challenge_type: str = "math", epoch: int = 1) -> dict:
    data = generate_challenge(challenge_type)

    verified = verify_challenge(data)
    if not verified:
        print("[warning] answer failed verification — regenerating...")
        data = generate_challenge(challenge_type)
        verified = verify_challenge(data)
        if not verified:
            raise RuntimeError("could not generate a verified challenge after 2 attempts")

    packaged = package_challenge(data, challenge_type, epoch)
    save_challenge(packaged)

    print(f"\n[challenge issued]")
    print(f"  id:         {packaged['id']}")
    print(f"  type:       {packaged['type']}")
    print(f"  difficulty: {packaged['difficulty']}/5")
    print(f"  expires:    {packaged['expires_at']}")
    print(f"  answer_hash:{packaged['answer_hash'][:16]}...")
    print(f"\n  prompt: {packaged['prompt']}\n")

    return packaged


if __name__ == "__main__":
    import sys
    challenge_type = sys.argv[1] if len(sys.argv) > 1 else "math"
    epoch = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    issue_challenge(challenge_type, epoch)
