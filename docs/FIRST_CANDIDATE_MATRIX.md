# OYYO Mini / Nano First-Candidate Matrix 0.1

The first OYYO-native model is selected by **hard engineering gates plus measured quality/efficiency**, not parameter count or public leaderboard position.

Machine-readable source: `suites/native-first-candidate-0.1.json`.

## Selection order

1. OYYO Mini is the first executable engineering vehicle.
2. OYYO Nano follows as the constrained/edge optimization line.
3. A candidate that fails any hard gate is not rankable.
4. Eligible candidates are compared only on the same declared hardware profile.
5. Every required family metric must be present before a score is produced.

## Hard gates

The matrix requires positive evidence for provenance, commercial rights, intended adaptation rights, reproducible revision, artifact integrity, OYYO runtime loading, policy handoff, declared structured/tool contract behavior, contamination review, and the OYYO independence test.

These are binary gates. A high quality score cannot compensate for a failed rights, integrity, policy or independence gate.

## Mini scoring

Mini emphasizes the balanced laptop/desktop target:

- overall quality: 25%
- tool + structured-output reliability: 20%
- multilingual semantic quality: 15%
- peak RAM: 15%
- first-token latency: 15%
- coding: 10%

## Nano scoring

Nano puts more weight on constrained execution:

- peak RAM: 30%
- overall quality: 20%
- first-token latency: 20%
- multilingual semantic quality: 10%
- tool + structured-output reliability: 10%
- package size: 10%

Normalization bands in the 0.1 matrix are engineering comparison bands, not product performance promises. They may only change under a new matrix revision when changing them would alter candidate ranking.

## CLI

Evaluate one candidate:

```bash
oyyo-benchmark candidate-evaluate \
  --matrix suites/native-first-candidate-0.1.json \
  --candidate examples/native-mini-candidate.example.json
```

Compare several candidates by repeating `--candidate`. Results are emitted in ranking order. The command returns a non-zero exit status when no supplied candidate is eligible.

## Evidence discipline

A candidate evidence file is an evaluation input, not proof by itself. Each `true` hard gate should ultimately be traceable to the corresponding provenance review, package integrity record, runtime test, policy test or independence-test result.

**Copyright © 2026 OYYO · HRN INNOVATION TECHNOLOGIES LTD. All rights reserved.**
