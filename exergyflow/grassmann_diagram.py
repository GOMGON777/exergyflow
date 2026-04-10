"""
Public API for building and drawing Grassmann/Sankey-like diagrams.

See README.md for the overall design and usage rules.
"""

from typing import Dict, List, Optional, Tuple
import matplotlib.pyplot as plt
from .grassmann_types import DiagramConfig, ProcessSpec, FlowDef, Flow, Process, RouteSegment, AutoRouteSpaceError
from .grassmann_layout import _build_auto_layout, _validate_diagram, _auto_route
from .grassmann_geometry import _route_displacement, _validate_route, _dir_vec
from .grassmann_render import _draw_flow, draw_process

# Diagram class
class Diagram:
    """Declarative diagram: processes + flows, with automatic layout and routing."""

    def __init__(self, config: Optional[DiagramConfig] = None):
        self.config = config or DiagramConfig()
        self.processes: Dict[str, ProcessSpec] = {}
        self.flows: List[FlowDef] = []

    def _format_flow_value(self, value: float, include_units: bool = True) -> str:
        """Format a flow value for labels, optionally including units."""
        fmt = self.config.flow_value_format
        if fmt:
            try:
                text = format(value, fmt)
            except Exception:
                text = f"{value}"
        else:
            text = f"{value}"
        unit = self.config.flow_value_unit if include_units else None
        if unit:
            sep = self.config.flow_value_unit_sep or " "
            text = f"{text}{sep}{unit}"
        return text

    def add_process(
        self,
        name: str,
        direction: Optional[str] = None,
        length: Optional[float] = None,
        color: Optional[str] = None,
        triangle_side: Optional[str] = None,
        overlay: Optional[bool] = None,
        overlay_height: Optional[float] = None,
        overlay_edgecolor: Optional[str] = None,
        overlay_linewidth: Optional[float] = None,
        overlay_linestyle: Optional[str] = None,
        overlay_alpha: Optional[float] = None,
        label_dx: float = 0.0,
        label_dy: float = 0.0,
        label_rotation: Optional[float] = None,
        triangle_label: Optional[str] = None,
        triangle_label_dx: float = 0.0,
        triangle_label_dy: float = 0.0,
        x: Optional[float] = None,
        y: Optional[float] = None,
    ):
        """Register a process for auto-layout (or fixed x/y if provided)."""
        if name in self.processes:
            raise ValueError(f'Duplicate process name: {name}')
        spec = ProcessSpec(
            name=name,
            direction=direction or self.config.layout_direction,
            length=length if length is not None else 1.8,
            color=color or '#cfd8dc',
            triangle_side=triangle_side,
            overlay=bool(overlay) if overlay is not None else False,
            overlay_height=overlay_height,
            overlay_edgecolor=overlay_edgecolor,
            overlay_linewidth=overlay_linewidth,
            overlay_linestyle=overlay_linestyle,
            overlay_alpha=overlay_alpha,
            label_dx=label_dx,
            label_dy=label_dy,
            label_rotation=label_rotation,
            triangle_label=triangle_label,
            triangle_label_dx=triangle_label_dx,
            triangle_label_dy=triangle_label_dy,
            x=x,
            y=y,
        )
        self.processes[name] = spec
        return spec

    def add_flow(
        self,
        name: str,
        value: float,
        source: Optional[str] = None,
        target: Optional[str] = None,
        color: Optional[str] = None,
        length: Optional[float] = None,
        inlet_tri_height: Optional[float] = None,
        outlet_tri_height: Optional[float] = None,
        label_dx: float = 0.0,
        label_dy: float = 0.0,
        label_rotation: Optional[float] = None,
        cycle_breaker: bool = False,
        route: Optional[List["RouteSegment"]] = None,
        label: Optional[str] = None,
    ):
        """Register a flow between processes (or source/sink) for auto-layout."""
        if any(f.name == name for f in self.flows):
            raise ValueError(f'Duplicate flow name: {name}')
        flow = FlowDef(
            name=name,
            value=value,
            label=label,
            source=source,
            target=target,
            color=color or '#7fb3d5',
            length=length if length is not None else 2.2,
            inlet_tri_height=0.3 if inlet_tri_height is None else inlet_tri_height,
            outlet_tri_height=0.6 if outlet_tri_height is None else outlet_tri_height,
            label_dx=label_dx,
            label_dy=label_dy,
            label_rotation=label_rotation,
            cycle_breaker=cycle_breaker,
            route=route,
        )
        self.flows.append(flow)
        return flow

    def draw(self, ax=None):
        """Validate, layout, route, and draw the diagram. Returns (fig, ax)."""
        _validate_diagram(self)
        fig = None
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 4))

        # Auto-scale if requested: map max flow magnitude to auto_scale_target
        prev_scale = self.config.scale
        try:
            if self.config.auto_scale:
                max_flow = max((f.value for f in self.flows), default=0.0)
                if max_flow > 0 and self.config.auto_scale_target > 0:
                    self.config.scale = self.config.auto_scale_target / max_flow
            proc_objs, flow_objs, anchors = _build_auto_layout(self)
            # Process rectangles for label avoidance
            label_avoid_rects = []
            for proc in proc_objs.values():
                sum_in = sum(f.value for f in proc.inflows)
                sum_out = sum(f.value for f in proc.outflows)
                proc_flow = min(sum_in, sum_out) * self.config.scale
                if proc.direction in ('right', 'left'):
                    rect_w = proc.length
                    rect_h = proc_flow
                else:
                    rect_w = proc_flow
                    rect_h = proc.length
                x0 = proc.x - rect_w / 2.0
                x1 = proc.x + rect_w / 2.0
                y0 = proc.y - rect_h / 2.0
                y1 = proc.y + rect_h / 2.0
                label_avoid_rects.append((x0, y0, x1, y1))

            label_mode = self.config.flow_label_mode
            # Draw flows first, then processes on top
            for fdef in self.flows:
                flow = flow_objs[fdef.name]
                start = anchors['start'].get(fdef.name)
                end = anchors['end'].get(fdef.name)
                source_is_proc = fdef.source in proc_objs
                target_is_proc = fdef.target in proc_objs
                if label_mode == 'value_only':
                    value_text = self._format_flow_value(flow.value, include_units=False)
                    label_text = value_text
                elif label_mode == 'value_units':
                    value_text = self._format_flow_value(flow.value, include_units=True)
                    label_text = value_text
                else:
                    value_text = self._format_flow_value(flow.value, include_units=True)
                    label_text = f"{flow.label or flow.name} = {value_text}"

                if source_is_proc and target_is_proc:
                    # internal flow: auto route or validate manual route
                    if start is None or end is None or fdef.source is None or fdef.target is None:
                        raise ValueError(
                            f'Flow {fdef.name} missing source or target anchor')
                    if fdef.route:
                        flow.route = fdef.route
                        _validate_route(flow.route)
                        start_dir = flow.route[0].direction
                        end_dir = flow.route[-1].direction
                        if start_dir != proc_objs[fdef.source].direction:
                            raise ValueError(
                                f'Flow {fdef.name} route must start in direction "{proc_objs[fdef.source].direction}"')
                        if end_dir != proc_objs[fdef.target].direction:
                            raise ValueError(
                                f'Flow {fdef.name} route must end in direction "{proc_objs[fdef.target].direction}"')
                        dx, dy = _route_displacement(
                            flow.route, flow.value * self.config.scale)
                        flow._x, flow._y = start
                        end_x = flow._x + dx
                        end_y = flow._y + dy
                        if end is not None:
                            if abs(end_x - end[0]) > 1e-6 or abs(end_y - end[1]) > 1e-6:
                                raise ValueError(
                                    f'Flow {fdef.name} route does not end at target anchor')
                    else:
                        try:
                            flow.route = _auto_route(
                                start,
                                proc_objs[fdef.source].direction,
                                end,
                                proc_objs[fdef.target].direction,
                                self.config.elbow_inner_radius,
                                self.config.min_straight,
                                flow.value * self.config.scale,
                            )
                        except AutoRouteSpaceError:
                            radii = [
                                self.config.elbow_inner_radius,
                                0.4,
                                0.3,
                                0.2,
                                0.1,
                                0.0,
                            ]
                            # dedupe while preserving order, clamp to non-negative
                            seen = set()
                            candidates = []
                            for r in radii:
                                r = max(0.0, r)
                                if r not in seen:
                                    candidates.append(r)
                                    seen.add(r)
                            success = False
                            last_exc = None
                            for r in candidates[1:]:
                                try:
                                    flow.route = _auto_route(
                                        start,
                                        proc_objs[fdef.source].direction,
                                        end,
                                        proc_objs[fdef.target].direction,
                                        r,
                                        self.config.min_straight,
                                        flow.value * self.config.scale,
                                    )
                                    success = True
                                    break
                                except AutoRouteSpaceError as exc2:
                                    last_exc = exc2
                                    continue
                                except ValueError as exc2:
                                    raise ValueError(
                                        f'Flow {fdef.name}: {exc2}') from exc2
                            if not success:
                                raise ValueError(
                                    f'Flow {fdef.name}: space to fit flow is too small') from last_exc
                        except ValueError as exc:
                            raise ValueError(f'Flow {fdef.name}: {exc}') from exc
                        flow._x, flow._y = start
                    _draw_flow(ax, flow, width=flow.value * self.config.scale,
                               inlet_triangle=False, outlet_triangle=False,
                               label_avoid_rects=label_avoid_rects, label_text=label_text,
                               label_offset=(flow.label_dx, flow.label_dy),
                               flow_label_style=self.config.flow_label_style,
                               render_width=max(flow.value * self.config.scale,
                                                self.config.render_min_flow_width))
                elif target_is_proc:
                    # initial flow (source is None/'source')
                    if fdef.target is None:
                        raise ValueError(
                            f'Flow {fdef.name} missing target process')
                    if end is None:
                        raise ValueError(
                            f'Flow {fdef.name} missing target anchor')
                    flow.direction = 'in'
                    if fdef.route:
                        flow.route = fdef.route
                        _validate_route(flow.route)
                        end_dir = flow.route[-1].direction
                        if end_dir != proc_objs[fdef.target].direction:
                            raise ValueError(
                                f'Flow {fdef.name} route must end in direction "{proc_objs[fdef.target].direction}"')
                        dx, dy = _route_displacement(
                            flow.route, flow.value * self.config.scale)
                        flow._x = end[0] - dx
                        flow._y = end[1] - dy
                    else:
                        proc_dir = proc_objs[fdef.target].direction
                        vx, vy = _dir_vec(proc_dir, flow.length)
                        flow._x = end[0] - vx
                        flow._y = end[1] - vy
                    _draw_flow(ax, flow, width=flow.value * self.config.scale,
                               inlet_triangle=True, outlet_triangle=False,
                               override_direction=proc_objs[fdef.target].direction,
                               label_avoid_rects=label_avoid_rects, label_text=label_text,
                               label_offset=(flow.label_dx, flow.label_dy),
                               flow_label_style=self.config.flow_label_style,
                               render_width=max(flow.value * self.config.scale,
                                                self.config.render_min_flow_width))
                elif source_is_proc:
                    # final flow (target is None/'sink')
                    if fdef.source is None:
                        raise ValueError(
                            f'Flow {fdef.name} missing source process')
                    if start is None:
                        raise ValueError(
                            f'Flow {fdef.name} missing source anchor')
                    flow.direction = 'out'
                    if fdef.route:
                        flow.route = fdef.route
                        _validate_route(flow.route)
                        start_dir = flow.route[0].direction
                        if start_dir != proc_objs[fdef.source].direction:
                            raise ValueError(
                                f'Flow {fdef.name} route must start in direction "{proc_objs[fdef.source].direction}"')
                        flow._x, flow._y = start
                    else:
                        flow._x, flow._y = start
                    _draw_flow(ax, flow, width=flow.value * self.config.scale,
                               inlet_triangle=False, outlet_triangle=True,
                               override_direction=proc_objs[fdef.source].direction,
                               label_avoid_rects=label_avoid_rects, label_text=label_text,
                               label_offset=(flow.label_dx, flow.label_dy),
                               flow_label_style=self.config.flow_label_style,
                               render_width=max(flow.value * self.config.scale,
                                                self.config.render_min_flow_width))
                else:
                    raise ValueError(
                        f'Flow {fdef.name} must connect to at least one process')

            for proc in proc_objs.values():
                draw_process(ax, proc, scale=self.config.scale, gap=self.config.flow_gap,
                             triangle_side='auto', draw_inflows=False, draw_outflows=False,
                             process_label_style=self.config.process_label_style,
                             triangle_label_style=self.config.triangle_label_style)

            ax.set_aspect('equal', adjustable='datalim')
            ax.axis('off')
            ax.relim()
            ax.autoscale_view()
            if fig is None:
                fig = ax.figure
            tight_layout = getattr(fig, "tight_layout", None)
            if callable(tight_layout):
                tight_layout()
            return fig, ax
        finally:
            self.config.scale = prev_scale
