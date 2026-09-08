from __future__ import annotations
from dataclasses import dataclass, asdict
import json, os, platform, time
from pathlib import Path

@dataclass
class FoundationResult:
    suite: str
    version: str
    passed: bool
    elapsed_ms: float
    logical_cpus: int
    architecture: str
    platform: str
    cpu_fallback: bool

    def to_dict(self):
        return asdict(self)

def run_foundation_smoke() -> FoundationResult:
    started = time.perf_counter()
    logical_cpus = os.cpu_count() or 1
    architecture = platform.machine() or "unknown"
    system = f"{platform.system()} {platform.release()}".strip()
    passed = logical_cpus >= 1 and bool(architecture)
    return FoundationResult(
        suite="foundation-smoke",
        version="0.1",
        passed=passed,
        elapsed_ms=round((time.perf_counter()-started)*1000, 3),
        logical_cpus=logical_cpus,
        architecture=architecture,
        platform=system,
        cpu_fallback=True,
    )

def save_result(path: str | Path, result: FoundationResult) -> None:
    Path(path).write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")
