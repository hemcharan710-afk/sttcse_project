"""
models/validation_report.py
Shared data contract for validation results.
No Qt dependency — plain Python dataclasses only.
"""

from dataclasses import dataclass, field


@dataclass
class ValidationCheck:
    name: str               # e.g. "Missing particle IDs"
    status: str             # "passed" | "warning" | "error"
    detail: str = ""        # shown when row is expanded
    correctable: bool = False  # True → shows "Apply corrections" button


@dataclass
class ValidationReport:
    filename: str
    n_particles: int
    n_observations: int
    frame_range: tuple          # (min_frame, max_frame)
    checks: list = field(default_factory=list)   # list[ValidationCheck]

    @property
    def passed_count(self):
        return sum(1 for c in self.checks if c.status == "passed")

    @property
    def warning_count(self):
        return sum(1 for c in self.checks if c.status == "warning")

    @property
    def error_count(self):
        return sum(1 for c in self.checks if c.status == "error")
