"""
YUKA Challenge Generator
Gemini 2.0 Flash (free) generates challenges.
Claude Sonnet verifies answers before publishing.
Hard for weak models, solvable by strong ones, verifiable on-chain.
"""

import os
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import google.generativeai as genai

# Gemini free tier — generation + verification
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
gemini = genai.GenerativeModel("gemini-2.0-flash")

CHALLENGES_DIR = Path(__file__).parent / "challenges"
CHALLENGES_DIR.mkdir(exist_ok=True)

# ── Challenge prompts ─────────────────────────────────────────────────────────

CHALLENGE_PROMPTS = {
    "math": """Generate a multi-step math reasoning challenge.

Rules:
- Must have exactly ONE correct numerical answer
- Requires 3-5 reasoning steps to solve
- Cannot be solved by pattern matching alone
- Hard for a weak model (GPT-3.5 level), solvable by a strong one

Return JSON only, no markdown:
{
  "prompt": "the challenge question",
  "answer": "the exact correct answer (number only)",
  "solution": "step by step solution",
  "difficulty": 3
}""",

    "code": """Generate a Python coding challenge.

Rules:
- Agent must write a Python function
- Must have deterministic, testable output
- Include exactly 3 test cases
- Hard for weak models, solvable by strong ones

Return JSON only, no markdown:
{
  "prompt": "write a python function that...",
  "function_name": "solve",
  "test_cases": [{"input": "value", "expected": "value"}],
  "answer": "def solve(...):\\n    ...",
  "difficulty": 3
}""",

    "logic": """Generate a logic puzzle with one unique solution.

Rules:
- Must have exactly ONE valid answer
- Requires multi-step deductive reasoning
- Cannot be guessed, must be derived
- Hard for weak models, clear for strong ones

Return JSON only, no markdown:
{
  "prompt": "the logic puzzle",
  "answer": "the exact correct answer",
  "solution": "the deductive reasoning steps",
  "difficulty": 3
}"""
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())

def hash_answer(answer: str) -> str:
    return hashlib.sha256(answer.strip().lower().encode()).hexdigest()

# ── Generation (Gemini — free) ────────────────────────────────────────────────

def generate_challenge(challenge_type: str = "math") -> dict:
    if challenge_type not in CHALLENGE_PROMPTS:
        raise ValueError(f"unknown type: {challenge_type}. use: {list(CHALLENGE_PROMPTS.keys())}")

    print(f"[gemini] generating {challenge_type} challenge...")

    response = gemini.generate_content(CHALLENGE_PROMPTS[challenge_type])
    data = parse_json(response.text)

    if "answer" not in data or "prompt" not in data:
        raise ValueError("generated challenge missing required fields")

    return data

# ── Verification (Claude Sonnet — cheap) ──────────────────────────────────────

def verify_challenge(challenge_data: dict) -> bool:
    print("[gemini] verifying answer...")

    prompt = f"""Verify this challenge and answer. Work through it independently. Reply with JSON only.

CHALLENGE: {challenge_data['prompt']}
CLAIMED ANSWER: {challenge_data['answer']}

Return JSON only, no markdown:
{{"correct": true, "verified_answer": "your answer", "notes": "any issues"}}"""

    response = gemini.generate_content(prompt)
    result = parse_json(response.text)
    verified = result.get("correct", False)

    if not verified:
        print(f"  [fail] got: {result.get('verified_answer')} — notes: {result.get('notes')}")
    else:
        print(f"  [pass] answer confirmed")

    return verified

# ── Packaging ─────────────────────────────────────────────────────────────────

def package_challenge(data: dict, challenge_type: str, epoch: int) -> dict:
    challenge_id = str(uuid.uuid4())[:8]
    answer = str(data["answer"])

    return {
        "id": challenge_id,
        "epoch": epoch,
        "type": challenge_type,
        "prompt": data["prompt"],
        "answer_hash": hash_answer(answer),
        "answer": answer,                      # private — never publish this
        "solution": data.get("solution", ""),
        "test_cases": data.get("test_cases", []),
        "difficulty": data.get("difficulty", 3),
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        "status": "active",
        "generated_by": "gemini-2.0-flash",
        "verified_by": "claude-sonnet-4-6",
    }

def save_challenge(packaged: dict) -> dict:
    # private (full — keep secret)
    private_path = CHALLENGES_DIR / f"epoch-{packaged['epoch']:04d}-{packaged['id']}.json"
    private_path.write_text(json.dumps(packaged, indent=2))

    # public (no answer/solution)
    public = {k: v for k, v in packaged.items() if k not in ("answer", "solution")}
    public_path = CHALLENGES_DIR / f"public-{packaged['id']}.json"
    public_path.write_text(json.dumps(public, indent=2))

    print(f"[saved] {private_path.name}")
    return public

# ── Main ──────────────────────────────────────────────────────────────────────

def issue_challenge(challenge_type: str = "math", epoch: int = 1) -> dict:
    data = generate_challenge(challenge_type)

    verified = verify_challenge(data)
    if not verified:
        print("[retry] regenerating...")
        data = generate_challenge(challenge_type)
        verified = verify_challenge(data)
        if not verified:
            raise RuntimeError("failed to generate verified challenge after 2 attempts")

    packaged = package_challenge(data, challenge_type, epoch)
    public = save_challenge(packaged)

    print(f"""
[challenge issued]
  id:          {packaged['id']}
  epoch:       {packaged['epoch']}
  type:        {packaged['type']}
  difficulty:  {packaged['difficulty']}/5
  expires:     {packaged['expires_at']}
  answer_hash: {packaged['answer_hash'][:16]}...
  generated:   {packaged['generated_by']}
  verified:    {packaged['verified_by']}

  prompt: {packaged['prompt']}
""")

    return public


if __name__ == "__main__":
    import sys
    challenge_type = sys.argv[1] if len(sys.argv) > 1 else "math"
    epoch = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    issue_challenge(challenge_type, epoch)
