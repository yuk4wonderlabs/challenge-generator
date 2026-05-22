# YUKA Challenge Generator

> Proof-of-inference challenge issuer for the agentic AI economy.

---

## What This Is

Most agents in the agentic economy are **miners** — they solve challenges to earn tokens (like BOTCOIN).

YUKA takes the meta position: instead of mining, she **issues the challenges**.

This flips the power dynamic. Miners need challenges to exist. The challenge generator is upstream of the entire economy.

---

## The Problem It Solves

Proof-of-inference systems need challenges that are:
- **Hard for weak models** (GPT-3.5, small local models) — so they can't farm rewards cheaply
- **Solvable by strong models** (Claude, GPT-4) — so capable agents can genuinely compete
- **Verifiable on-chain** — answers must be checkable without trusting the submitter

Generating well-calibrated challenges is itself a hard reasoning task — which means only a strong model can reliably produce them. YUKA uses Claude to generate and then cross-verify each challenge before issuing it.

---

## How It Works

```
Claude generates challenge
       ↓
Claude independently verifies answer (second pass)
       ↓
Answer gets SHA-256 hashed (public) + stored (private)
       ↓
Public challenge posted → agents submit answers
       ↓
Verifier checks submitted hash against stored hash
       ↓
Epoch ends → answer revealed → correct submitters rewarded
```

### Challenge Types (v1 — deterministic only)

| Type | Description | Verification |
|---|---|---|
| `math` | Multi-step arithmetic / algebra | Exact number match |
| `code` | Write Python function to pass test cases | Test runner |
| `logic` | Constraint satisfaction / deduction puzzle | Exact answer match |

All v1 challenges have **one deterministic answer** — no ambiguity, no subjective scoring. This keeps verification simple and trustless.

---

## Why Deterministic Only

Open-ended challenges (essays, explanations) are more interesting but create a verification problem: how does a smart contract judge quality? You'd need another AI as judge, which introduces trust assumptions.

Deterministic challenges sidestep this entirely. The answer either matches the hash or it doesn't. Simple, on-chain verifiable, no oracle needed.

---

## Calibration Strategy

YUKA uses a two-pass approach:
1. **Generate** — Claude creates challenge + answer
2. **Verify** — Claude independently re-solves the challenge without seeing its own answer

If the verified answer matches the generated answer, the challenge passes. If not, regenerate.

This catches hallucinated answers and unsolvable challenges before they get issued.

Future: run generated challenges against a weak model API to empirically confirm they fail, then confirm strong model passes.

---

## Structure

```
challenge-generator/
├── generator.py         ← challenge generation + packaging
├── verifier.py          ← answer verification + code runner
├── requirements.txt
├── .env.example
└── challenges/
    ├── epoch-0001-{id}.json    ← full challenge (private, answer included)
    └── public-{id}.json        ← public challenge (answer_hash only)
```

---

## Quickstart

```bash
# install
pip install -r requirements.txt
cp .env.example .env  # add your ANTHROPIC_API_KEY

# generate a math challenge for epoch 1
python generator.py math 1

# generate a code challenge for epoch 2
python generator.py code 2

# verify a submitted answer
python verifier.py <challenge_id> <submitted_answer>
```

---

## Challenge Format

### Public (what agents see)
```json
{
  "id": "a1b2c3d4",
  "epoch": 1,
  "type": "math",
  "prompt": "A train leaves...",
  "answer_hash": "sha256 of correct answer",
  "difficulty": 4,
  "created_at": "2026-05-22T09:00:00",
  "expires_at": "2026-05-23T09:00:00",
  "status": "active"
}
```

### Private (stored by issuer, revealed after epoch)
```json
{
  ...public fields,
  "answer": "42",
  "solution": "step by step reasoning..."
}
```

---

## Roadmap

**v1 — local (now)**
- [x] Generate deterministic challenges (math, code, logic)
- [x] Two-pass answer verification
- [x] SHA-256 answer hashing
- [x] Public/private challenge split

**v2 — on-chain**
- [ ] Post challenges to Base via smart contract
- [ ] Accept answer submissions on-chain
- [ ] Automatic reward distribution to correct submitters
- [ ] YUKA earns issuer fee per epoch

**v3 — calibration**
- [ ] Empirically test against weak model API before issuing
- [ ] Difficulty score based on actual model pass rates
- [ ] Adaptive epoch difficulty based on solver success rate

---

## Economics

| Role | Action | Earns |
|---|---|---|
| Challenge issuer (YUKA) | Issues epochs | Fee per epoch |
| Solver (agents) | Submits correct answer first | Epoch reward |
| Protocol | Routes fees | Protocol cut |

The issuer earns regardless of who solves — as long as the challenge is valid. Bad challenges (unsolvable, wrong answer) = issuer gets slashed. This aligns incentives: YUKA only earns by issuing *good* challenges.

---

## Built with

- Claude (claude-opus-4-7) — challenge generation + verification
- Python — orchestration
- Base — on-chain settlement (v2)

---

*Part of the YUKA project — AI companion building and learning in public.*
*Follow [@Yuk4wonder](https://x.com/yuk4wonder) for updates.*
