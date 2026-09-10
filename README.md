<div align="center">

# OYYO Benchmark

### Independent evaluation for portable, private and business-ready AI systems

**Reasoning · Business Execution · Coding · Agents · MCP · Artifacts · Language · Memory · Multimodal · Security · Hardware Efficiency**

[OYYO](https://oyyo.one) · [SDK](https://github.com/vpicciuolo/oyyo-sdk) · [Models](https://github.com/vpicciuolo/oyyo-models) · [Benchmark Spec](./docs/SPEC.md) · [Founder](https://github.com/vpicciuolo) · [Investors](https://oyyo.one/investors)

**Version:** `0.1.0-foundation` · **Made in UAE 🇦🇪 · Dubai-IT**

</div>

> [!IMPORTANT]
> **OYYO is proprietary technology and is not open source.** This repository is public to document and reproduce selected benchmark methodology and results. Public visibility does not grant rights to OYYO's private runtime, orchestration engine, models, intellectual property or other proprietary components.

## What is OYYO Benchmark?

OYYO Benchmark is the public evaluation framework used to measure whether AI models, runtimes and execution backends are suitable for the OYYO ecosystem.

Instead of selecting technology from marketing claims or a single leaderboard score, OYYO evaluates the things that matter in real work: **task completion, reasoning quality, coding, tool use, business execution, language intelligence, artifact creation, multimodal capability, reliability, portability and hardware efficiency**.

The goal is simple: **measure before selecting, publish the evidence that can be published, and keep component metrics visible.**

## Why it exists

AI systems are increasingly judged by headline benchmark numbers. Those numbers can be useful, but they rarely answer the full operational question:

> Can this model or runtime reliably complete real business work on the hardware, latency, memory and security constraints where OYYO needs to run?

OYYO Benchmark is designed around that question.

A candidate does not become an OYYO component because it is popular, widely downloaded or highly ranked by its vendor. It must pass OYYO's independent qualification pipeline.

## Evaluation families

| Family | What OYYO evaluates |
| --- | --- |
| General reasoning | Multi-step reasoning, instruction following, consistency and task completion |
| Business execution | Analysis, planning, operations, research and practical business workflows |
| Coding & terminal | Code generation, debugging, repository work, command execution and engineering tasks |
| Tools, agents & MCP | Function calling, tool selection, orchestration, agent behavior and Model Context Protocol workflows |
| Documents & artifacts | Documents, spreadsheets, presentations and structured business outputs |
| Language intelligence | Semantic translation, intent, tone, terminology, multilingual and cross-lingual quality |
| Memory & temporal knowledge | Retrieval, continuity, context use, provenance and time-sensitive reasoning |
| Multimodal | Image, audio and video understanding where supported |
| Growth & marketing | Research, positioning, content, campaign and growth-oriented execution |
| Security & reliability | Malformed inputs, failure handling, repeatability, fallbacks and operational robustness |
| Hardware efficiency | CPU/GPU/NPU behavior, RAM, VRAM, load time, TTFT, throughput and energy where measurable |

## OYYO qualification pipeline

```text
License & provenance
        ↓
Compatibility
        ↓
Quality
        ↓
Business execution
        ↓
Tools & agents
        ↓
Language
        ↓
Multimodal
        ↓
Hardware efficiency
        ↓
Reliability & security
        ↓
Human acceptance review
```

No single benchmark score bypasses this gate.

## Metrics remain visible

OYYO avoids hiding materially different behaviors inside one attractive composite number.

Results can include:

- task success rate
- quality score
- repeatability
- time to first token (TTFT)
- tokens per second
- end-to-end latency
- RAM and VRAM usage
- model load time
- supported context
- CPU fallback behavior
- crash and recovery behavior
- hardware utilization
- energy consumption where measurable

A composite efficiency index may be calculated, but its underlying components remain separately inspectable.

## Reproducibility contract

A benchmark result should capture enough information to reproduce the run, including:

- exact model identity and revision
- artifact checksum
- quantization or conversion details
- runtime/backend and version
- benchmark version
- command and configuration
- operating system
- CPU, GPU or NPU
- RAM and VRAM
- timestamp

See the [OYYO Benchmark Specification](./docs/SPEC.md) for the current foundation specification.

## Quick start

Requires Python 3.11+.

```bash
git clone https://github.com/vpicciuolo/oyyo-benchmark.git
cd oyyo-benchmark
python -m pip install -e .
oyyo-benchmark smoke
```

Or run the module directly:

```bash
python -m oyyo_benchmark.cli smoke
```

Save a result:

```bash
oyyo-benchmark smoke --output result.json
```

## Repository map

```text
oyyo-benchmark/
├── docs/        Benchmark specification
├── schemas/     Machine-readable result schemas
├── src/         Public benchmark runner and CLI
├── suites/      Benchmark suites and fixtures
└── VERSION      Framework version
```

## OYYO public engineering ecosystem

The public OYYO repositories have different responsibilities and are intentionally linked:

| Repository | Purpose |
| --- | --- |
| **[oyyo-benchmark](https://github.com/vpicciuolo/oyyo-benchmark)** | Independent evaluation, qualification methodology and reproducible metrics |
| **[oyyo-models](https://github.com/vpicciuolo/oyyo-models)** | Model manifests, compatibility metadata, model cards, provenance and release-gate records |
| **[oyyo-sdk](https://github.com/vpicciuolo/oyyo-sdk)** | Python and TypeScript integration surface for OYYO-compatible and OYYO-native APIs |

The OYYO core runtime and orchestration engine are proprietary and are not published as open-source software.

## Built for the OYYO architecture

OYYO is being built as a **proprietary AI orchestration system for modern business**, coordinating models, memory, tools, agents, multimodal capabilities and structured work through a portable runtime architecture.

The project is designed around practical execution rather than dependence on one model vendor or one benchmark leaderboard.

Learn more at **[oyyo.one](https://oyyo.one)**.

## Status

This repository is currently at the **foundation stage (`0.1.0`)**. The framework, schemas and qualification philosophy are public while OYYO's core technology remains proprietary.

## Ownership and rights

**Copyright © 2026 OYYO · HRN INNOVATION TECHNOLOGIES LTD. All rights reserved.**

OYYO is proprietary technology. Unless an individual file or artifact explicitly states otherwise, no license to use, copy, modify, distribute, sublicense or create derivative works is granted merely because material is visible in this public repository.

---

<div align="center">

**OYYO · AI orchestration for real work · Made in UAE 🇦🇪 · Dubai-IT**

[Website](https://oyyo.one) · [SDK](https://github.com/vpicciuolo/oyyo-sdk) · [Models](https://github.com/vpicciuolo/oyyo-models) · [Founder](https://github.com/vpicciuolo)

</div>
