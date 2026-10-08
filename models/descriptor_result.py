"""
models/descriptor_result.py
Shared data contract for analysis results.
No Qt dependency — plain Python dataclasses only.
"""

from dataclasses import dataclass, field


@dataclass
class DescriptorResult:
    name: str                       # "MSD", "NGP", "Van Hove lag_1", etc.
    x_values: list                  # lag times or r values (x-axis)
    y_values: list                  # descriptor values (y-axis)
    y_errors: list = field(default_factory=list)   # CI or std (optional)
    x_label: str = "Lag time Δt (s)"
    y_label: str = "MSD (μm²)"
    units: str = ""
    fit_params: dict = field(default_factory=dict)  # e.g. {"alpha": 0.82, "r_squared": 0.997}
    metadata: dict = field(default_factory=dict)    # any extra info
