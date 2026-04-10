"""
Sankey and Grassmann diagrams for energy and exergy analysis.

Public re-exports for the main API.
"""

from .grassmann_diagram import Diagram
from .grassmann_types import DiagramConfig, RouteSegment

__all__ = ["Diagram", "DiagramConfig", "RouteSegment"]

try:  # pragma: no cover - best effort when installed
    from importlib.metadata import version as _pkg_version
    __version__ = _pkg_version("exergyflow")
except Exception:  # pragma: no cover - fallback for editable/dev usage
    __version__ = "0.1.0"
