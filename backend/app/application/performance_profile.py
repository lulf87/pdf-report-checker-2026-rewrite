from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import time
from typing import Any, Callable, Iterator


Clock = Callable[[], float]


@dataclass
class PerfStage:
    name: str
    duration_seconds: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration_seconds": _round_seconds(self.duration_seconds),
            "metadata": _json_safe(self.metadata),
        }


class PerformanceProfile:
    """Small JSON-safe profiler for task and Codex audit runtime stages."""

    def __init__(self, *, clock: Clock | None = None) -> None:
        self._clock = clock or time.perf_counter
        self._stages: list[PerfStage] = []
        self._package_profiles: list[dict[str, Any]] = []

    @contextmanager
    def measure(self, name: str, **metadata: Any) -> Iterator[None]:
        started = self._clock()
        try:
            yield
        finally:
            self.record(name, self._clock() - started, metadata=metadata)

    def record(self, name: str, duration_seconds: float, *, metadata: dict[str, Any] | None = None) -> None:
        self._stages.append(
            PerfStage(
                name=name,
                duration_seconds=max(0.0, float(duration_seconds)),
                metadata=metadata or {},
            )
        )

    def add_package_profile(self, profile: dict[str, Any]) -> None:
        self._package_profiles.append(_json_safe(profile))

    def add_package_profiles(self, profiles: list[dict[str, Any]]) -> None:
        for profile in profiles:
            self.add_package_profile(profile)

    def to_dict(self) -> dict[str, Any]:
        stages = [stage.to_dict() for stage in self._stages]
        totals: dict[str, float] = {}
        for stage in stages:
            name = str(stage["name"])
            totals[name] = _round_seconds(totals.get(name, 0.0) + float(stage["duration_seconds"]))
        package_totals = _package_totals(self._package_profiles)
        return {
            "stages": stages,
            "totals": totals,
            "total_seconds": _round_seconds(sum(totals.values())),
            "packages": list(self._package_profiles),
            "package_totals": package_totals,
        }


def _package_totals(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    numeric_keys = [
        "target_count",
        "codex_exec_seconds",
        "image_count",
        "image_bytes",
        "prompt_size_bytes",
        "evidence_package_size_bytes",
    ]
    totals: dict[str, Any] = {"package_count": len(profiles)}
    for key in numeric_keys:
        value = sum(_number(profile.get(key)) for profile in profiles)
        totals[key] = _round_seconds(value) if key.endswith("_seconds") else int(value)
    return totals


def _number(value: Any) -> float:
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _round_seconds(value: float) -> float:
    return round(float(value), 6)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


__all__ = ["PerfStage", "PerformanceProfile"]
