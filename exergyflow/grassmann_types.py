"""
Core data structures and configuration for Grassmann/Sankey-like diagrams.

See README.md for the full design/spec overview.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any

# Exceptions and data structures
class AutoRouteSpaceError(ValueError):
    """Raised when auto routing fails due to insufficient space for elbows."""

# -----------------------------
# Data structures
# -----------------------------


@dataclass
class Flow:
    name: str
    value: float
    direction: str  # 'in' or 'out'
    color: str = '#7fb3d5'
    # horizontal length for straight flow (default shared length)
    length: float = 2.2
    label: Optional[str] = None
    route: Optional[List["RouteSegment"]] = None  # optional custom path
    inlet_tri_height: float = 1.0  # multiplier of flow width for inlet triangle depth
    outlet_tri_height: float = 1.0  # multiplier of flow width for outlet triangle depth
    label_dx: float = 0.0
    label_dy: float = 0.0
    label_rotation: Optional[float] = None
    cycle_breaker: bool = False
    z: int = 3
    _x: float = 0.0
    _y: float = 0.0


@dataclass
class LinkFlow:
    name: str
    value: float
    color: str = '#7fb3d5'


@dataclass
class RouteSegment:
    kind: str  # 'rect' or 'elbow'
    length: float  # rect: section length, elbow: inner radius
    direction: Optional[str] = None  # for rect: 'right','left','up','down'
    # for elbow: 'rightup','rightdown','leftup','leftdown'
    turn: Optional[str] = None


@dataclass
class Process:
    name: str
    x: float
    y: float
    direction: str = 'right'  # direction of process and outlet first sections
    # left/right: 'top'/'bottom'; up/down: 'left'/'right'
    triangle_side: Optional[str] = None
    length: float = 1.8
    overlay: bool = False
    overlay_height: Optional[float] = None
    overlay_edgecolor: Optional[str] = None
    overlay_linewidth: Optional[float] = None
    overlay_linestyle: Optional[str] = None
    overlay_alpha: Optional[float] = None
    label_dx: float = 0.0
    label_dy: float = 0.0
    label_rotation: Optional[float] = None
    triangle_label: Optional[str] = None
    triangle_label_dx: float = 0.0
    triangle_label_dy: float = 0.0
    inflows: List[Flow] = field(default_factory=list)
    outflows: List[Flow] = field(default_factory=list)
    color: str = '#cfd8dc'
    edgecolor: str = 'black'
    z: int = 2


@dataclass
class ProcessSpec:
    """Declarative process definition for automatic layout."""

    name: str
    direction: str = 'right'
    length: float = 1.8
    color: str = '#cfd8dc'
    triangle_side: Optional[str] = None
    overlay: bool = False
    overlay_height: Optional[float] = None
    overlay_edgecolor: Optional[str] = None
    overlay_linewidth: Optional[float] = None
    overlay_linestyle: Optional[str] = None
    overlay_alpha: Optional[float] = None
    label_dx: float = 0.0
    label_dy: float = 0.0
    label_rotation: Optional[float] = None
    triangle_label: Optional[str] = None
    triangle_label_dx: float = 0.0
    triangle_label_dy: float = 0.0
    x: Optional[float] = None
    y: Optional[float] = None


@dataclass
class FlowDef:
    """Declarative flow definition for automatic layout."""

    name: str
    value: float
    label: Optional[str] = None
    source: Optional[str] = None  # process name or None/'source'
    target: Optional[str] = None  # process name or None/'sink'
    color: str = '#7fb3d5'
    length: float = 2.2
    inlet_tri_height: float = 0.3
    outlet_tri_height: float = 0.6
    route: Optional[List["RouteSegment"]] = None
    label_dx: float = 0.0
    label_dy: float = 0.0
    label_rotation: Optional[float] = None
    cycle_breaker: bool = False


@dataclass
class DiagramConfig:
    """Configuration for automatic layout + routing."""

    scale: float = 1.0
    auto_scale: bool = False
    auto_scale_target: float = 1.0
    # 'name_value_units', 'value_only', or 'value_units'
    flow_label_mode: str = 'name_value_units'
    # Flow value formatting for labels
    flow_value_format: Optional[str] = None  # e.g., ".3g" or ".2f"
    flow_value_unit: Optional[str] = None  # e.g., "kW"
    flow_value_unit_sep: str = " "
    render_min_flow_width: float = 0.0
    # Label styling (passed to matplotlib.text)
    flow_label_style: Dict[str, Any] = field(
        default_factory=lambda: {"fontsize": 8, "color": "black"})
    process_label_style: Dict[str, Any] = field(
        default_factory=lambda: {"fontsize": 9, "color": "black"})
    triangle_label_style: Dict[str, Any] = field(
        default_factory=lambda: {"fontsize": 8, "color": "black"})
    flow_gap: float = 0.0
    layer_gap: float = 2.0
    process_gap: float = 1.0
    elbow_inner_radius: float = 0.5
    layout_direction: str = 'right'
    min_straight: float = 0.2

