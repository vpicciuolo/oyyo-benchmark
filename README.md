# OYYO Benchmark

Public, reproducible evaluation framework for OYYO model, runtime, hardware, business, language, multimodal, agent, artifact, security and efficiency benchmarking.

**Project:** https://oyyo.one  
**Version:** `0.1.0-foundation`

OYYO deliberately benchmarks before selecting or training its first model family. Vendor scores are evidence, not a selection decision.

## Benchmark families

- General reasoning
- Business execution
- Coding and terminal work
- Tool/function calling and agents
- Documents, spreadsheets and presentations
- Language and semantic translation
- Memory and temporal knowledge
- Image, audio and video understanding
- Growth/marketing execution
- Security and reliability
- Hardware efficiency

## Promotion gate

License → compatibility → quality → business → tools → language → multimodal → hardware → reliability → human review.

## Metrics

Publish component metrics rather than hiding everything in a single score: task success, quality, repeatability, latency, TTFT, tokens/sec, RAM, VRAM, load time, context, crash/fallback behavior and energy where measurable.

## Quick start

```bash
python -m oyyo_benchmark.cli smoke
```

Candidate model registries will only be committed after source/license verification.
