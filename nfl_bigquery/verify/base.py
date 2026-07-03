from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationResult:
    name: str
    passed: bool
    detail: str
