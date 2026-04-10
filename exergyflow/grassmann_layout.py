"""
Auto-layout and routing helpers for Grassmann/Sankey-like diagrams.

Contains stack helpers, anchor placement, DAG layout, and Manhattan routing.
See README.md for the full routing rules.
"""

from typing import Dict, List, Optional, Tuple, TYPE_CHECKING
from .grassmann_types import Flow, Process, ProcessSpec, FlowDef, DiagramConfig, RouteSegment, AutoRouteSpaceError
from .grassmann_geometry import (_dir_vec, _elbow_end, _turn_type_from_dirs,
                                 _is_horizontal, _is_vertical, _is_opposite, _route_displacement, _validate_route)

if TYPE_CHECKING:
    from .grassmann_diagram import Diagram

# Layout + routing helpers
# -----------------------------
# Layout helpers
# -----------------------------

# Overlap epsilon for stacked flows (eliminates hairline seams when gap=0)
EPS_FLOW_STACK = 5e-3


def _stack_flows_from_bottom(flows: List[Flow], y_bottom: float, scale: float, gap: float) -> List[Tuple[Flow, float]]:
    """Stack flows vertically from a bottom border."""
    eff_gap = gap if gap > 0 else -EPS_FLOW_STACK
    y_top = y_bottom + sum(f.value for f in flows) * \
        scale + max(len(flows) - 1, 0) * eff_gap
    stacked = []
    for f in flows:
        h = f.value * scale
        y_mid = y_top - h / 2.0
        stacked.append((f, y_mid))
        y_top -= h + eff_gap
    return stacked


def _stack_flows_from_left(flows: List[Flow], x_left: float, scale: float, gap: float) -> List[Tuple[Flow, float]]:
    """Stack flows horizontally from a left border."""
    eff_gap = gap if gap > 0 else -EPS_FLOW_STACK
    x_right = x_left + sum(f.value for f in flows) * \
        scale + max(len(flows) - 1, 0) * eff_gap
    stacked = []
    for f in flows:
        w = f.value * scale
        x_mid = x_right - w / 2.0
        stacked.append((f, x_mid))
        x_right -= w + eff_gap
    return stacked


def _stack_flows_from_bottom_edge(flows: List[Flow], y_bottom: float, scale: float, gap: float) -> List[Tuple[Flow, float]]:
    """Stack flows upward starting at a bottom edge (first flow at bottom)."""
    eff_gap = gap if gap > 0 else -EPS_FLOW_STACK
    stacked = []
    y = y_bottom
    for f in flows:
        h = f.value * scale
        y_mid = y + h / 2.0
        stacked.append((f, y_mid))
        y += h + eff_gap
    return stacked


def _stack_flows_from_top_edge(flows: List[Flow], y_top: float, scale: float, gap: float) -> List[Tuple[Flow, float]]:
    """Stack flows downward starting at a top edge (first flow at top)."""
    eff_gap = gap if gap > 0 else -EPS_FLOW_STACK
    stacked = []
    y = y_top
    for f in flows:
        h = f.value * scale
        y_mid = y - h / 2.0
        stacked.append((f, y_mid))
        y -= h + eff_gap
    return stacked


def _stack_flows_from_left_edge(flows: List[Flow], x_left: float, scale: float, gap: float) -> List[Tuple[Flow, float]]:
    """Stack flows rightward starting at a left edge (first flow at left)."""
    eff_gap = gap if gap > 0 else -EPS_FLOW_STACK
    stacked = []
    x = x_left
    for f in flows:
        w = f.value * scale
        x_mid = x + w / 2.0
        stacked.append((f, x_mid))
        x += w + eff_gap
    return stacked


def _stack_flows_from_right_edge(flows: List[Flow], x_right: float, scale: float, gap: float) -> List[Tuple[Flow, float]]:
    """Stack flows leftward starting at a right edge (first flow at right)."""
    eff_gap = gap if gap > 0 else -EPS_FLOW_STACK
    stacked = []
    x = x_right
    for f in flows:
        w = f.value * scale
        x_mid = x - w / 2.0
        stacked.append((f, x_mid))
        x -= w + eff_gap
    return stacked


def _flow_anchor_for_process(
    proc_spec: ProcessSpec,
    proc_pos: Tuple[float, float],
    rect_w: float,
    rect_h: float,
    flows: List[Flow],
    flow: Flow,
    scale: float,
    gap: float,
    is_outflow: bool,
) -> Tuple[float, float]:
    """Return the anchor point for a flow on a process border."""
    x, y = proc_pos
    x0 = x - rect_w / 2.0
    x1 = x + rect_w / 2.0
    y0 = y - rect_h / 2.0
    y1 = y + rect_h / 2.0
    if proc_spec.direction in ('right', 'left'):
        side = proc_spec.triangle_side or 'top'
        if side not in ('top', 'bottom'):
            side = 'top'
        if side == 'top':
            stack = _stack_flows_from_bottom_edge(flows, y0, scale, gap)
        else:
            stack = _stack_flows_from_top_edge(flows, y1, scale, gap)
        for f, y_mid in stack:
            if f.name == flow.name:
                if is_outflow:
                    return (x1, y_mid) if proc_spec.direction == 'right' else (x0, y_mid)
                return (x0, y_mid) if proc_spec.direction == 'right' else (x1, y_mid)
    else:
        side = proc_spec.triangle_side or 'left'
        if side not in ('left', 'right'):
            side = 'left'
        if side == 'left':
            stack = _stack_flows_from_right_edge(flows, x1, scale, gap)
        else:
            stack = _stack_flows_from_left_edge(flows, x0, scale, gap)
        for f, x_mid in stack:
            if f.name == flow.name:
                if is_outflow:
                    return (x_mid, y1) if proc_spec.direction == 'up' else (x_mid, y0)
                return (x_mid, y0) if proc_spec.direction == 'up' else (x_mid, y1)
    raise ValueError(
        f'Anchor for flow {flow.name} not found on process {proc_spec.name}')


def _flow_anchor_offset(
    proc_spec: ProcessSpec,
    rect_w: float,
    rect_h: float,
    flows: List[Flow],
    flow: Flow,
    scale: float,
    gap: float,
    is_outflow: bool,
) -> Tuple[float, float]:
    """Return anchor offset from process center for a given flow."""
    ax, ay = _flow_anchor_for_process(
        proc_spec,
        (0.0, 0.0),
        rect_w,
        rect_h,
        flows,
        flow,
        scale,
        gap,
        is_outflow,
    )
    return ax, ay


def _default_alignment_route(flow: Flow, start_dir: str, end_dir: str, elbow_inner: float) -> List[RouteSegment]:
    """Build a default route used for positioning when directions differ."""
    if start_dir == end_dir:
        return [RouteSegment(kind='rect', length=flow.length, direction=start_dir)]
    if _is_opposite(start_dir, end_dir):
        mid_dir = 'up' if _is_horizontal(start_dir) else 'right'
        return [
            RouteSegment(kind='rect', length=flow.length, direction=start_dir),
            RouteSegment(kind='elbow', length=elbow_inner,
                         turn=_turn_type_from_dirs(start_dir, mid_dir)),
            RouteSegment(kind='rect', length=flow.length, direction=mid_dir),
            RouteSegment(kind='elbow', length=elbow_inner,
                         turn=_turn_type_from_dirs(mid_dir, end_dir)),
            RouteSegment(kind='rect', length=flow.length, direction=end_dir),
        ]
    return [
        RouteSegment(kind='rect', length=flow.length, direction=start_dir),
        RouteSegment(kind='elbow', length=elbow_inner,
                     turn=_turn_type_from_dirs(start_dir, end_dir)),
        RouteSegment(kind='rect', length=flow.length, direction=end_dir),
    ]


def _place_process_from_inlet_end(end: Tuple[float, float], proc_spec: ProcessSpec, rect_w: float, rect_h: float) -> Tuple[float, float]:
    """Compute process center so its inlet border matches an inlet end point."""
    ex, ey = end
    if proc_spec.direction == 'right':
        return ex + rect_w / 2.0, ey
    if proc_spec.direction == 'left':
        return ex - rect_w / 2.0, ey
    if proc_spec.direction == 'up':
        return ex, ey + rect_h / 2.0
    if proc_spec.direction == 'down':
        return ex, ey - rect_h / 2.0
    raise ValueError(f'Unknown process direction: {proc_spec.direction}')


def _validate_diagram(diagram: "Diagram"):
    """Validate declarative diagram definitions with clear error messages."""
    if not diagram.processes:
        raise ValueError('Diagram must contain at least one process')
    layout_dir = diagram.config.layout_direction
    if layout_dir not in ('right', 'left', 'up', 'down'):
        raise ValueError(
            f'Invalid layout_direction "{layout_dir}". Use right/left/up/down.')
    if diagram.config.flow_label_mode not in ('name_value_units', 'value_only', 'value_units'):
        raise ValueError(
            f'Invalid flow_label_mode "{diagram.config.flow_label_mode}". Use '
            'name_value_units, value_only, or value_units.')
    for proc in diagram.processes.values():
        if proc.direction not in ('right', 'left', 'up', 'down'):
            raise ValueError(
                f'Process {proc.name} has invalid direction "{proc.direction}".')
        if proc.length <= 0:
            raise ValueError(
                f'Process {proc.name} must have length > 0')

    # Build process name set
    proc_names = set(diagram.processes.keys())
    # Validate flows and build edges
    edges = {p: set() for p in proc_names}
    indeg = {p: 0 for p in proc_names}
    for f in diagram.flows:
        src = f.source
        tgt = f.target
        if src == 'source':
            src = None
        if tgt == 'sink':
            tgt = None
        if f.cycle_breaker and (src is None or tgt is None):
            raise ValueError(
                f'Flow {f.name}: cycle_breaker only applies to process->process flows')
        if src is None and tgt is None:
            raise ValueError(
                f'Flow {f.name} must connect to a process or sink/source')
        if src is not None and src not in proc_names:
            raise ValueError(
                f'Flow {f.name} has unknown source process "{src}"')
        if tgt is not None and tgt not in proc_names:
            raise ValueError(
                f'Flow {f.name} has unknown target process "{tgt}"')
        if src is not None and tgt is not None and src == tgt:
            raise ValueError(
                f'Flow {f.name} cannot start and end at the same process "{src}"')
        if f.value < 0:
            raise ValueError(
                f'Flow {f.name} must have non-negative value')
        if f.length <= 0:
            raise ValueError(
                f'Flow {f.name} must have length > 0')
        if src is not None and tgt is not None and not f.cycle_breaker:
            if tgt not in edges[src]:
                edges[src].add(tgt)
                indeg[tgt] += 1

    # Cycle detection for auto layout
    queue = [p for p, d in indeg.items() if d == 0]
    visited = 0
    while queue:
        p = queue.pop(0)
        visited += 1
        for t in edges[p]:
            indeg[t] -= 1
            if indeg[t] == 0:
                queue.append(t)
    if visited != len(proc_names):
        raise ValueError(
            'Process graph has a cycle. Auto layout requires a DAG or explicit '
            'cycle_breaker flows. Break the cycle or mark a flow as cycle_breaker.')


def _compute_process_dims(proc: ProcessSpec, inflows: List[Flow], outflows: List[Flow], scale: float) -> Tuple[float, float, float, float]:
    """Return (rect_w, rect_h, sum_in, sum_out) for a process."""
    sum_in = sum(f.value for f in inflows)
    sum_out = sum(f.value for f in outflows)
    if not inflows and not outflows:
        raise ValueError(
            f'Process {proc.name} has no inflows or outflows')
    if proc.direction in ('left', 'right'):
        rect_w = proc.length
        rect_h = min(sum_in, sum_out) * scale
    else:
        rect_w = min(sum_in, sum_out) * scale
        rect_h = proc.length
    return rect_w, rect_h, sum_in, sum_out


def _topo_layers(proc_names: List[str], flows: List[FlowDef]) -> Dict[str, int]:
    """Assign each process a layer index using topological order."""
    edges = {p: set() for p in proc_names}
    indeg = {p: 0 for p in proc_names}
    for f in flows:
        if f.cycle_breaker:
            continue
        if f.source in proc_names and f.target in proc_names:
            if f.target not in edges[f.source]:
                edges[f.source].add(f.target)
                indeg[f.target] += 1
    queue = [p for p, d in indeg.items() if d == 0]
    order = []
    while queue:
        p = queue.pop(0)
        order.append(p)
        for t in edges[p]:
            indeg[t] -= 1
            if indeg[t] == 0:
                queue.append(t)
    if len(order) != len(proc_names):
        raise ValueError(
            'Process graph has a cycle. Auto layout requires a DAG.')
    layer = {p: 0 for p in proc_names}
    for p in order:
        for t in edges[p]:
            layer[t] = max(layer[t], layer[p] + 1)
    return layer


def _auto_route(start, start_dir, end, end_dir, elbow_inner, min_straight, width):
    """Create a Manhattan-style route from start to end, accounting for elbow radius."""
    sx, sy = start
    ex, ey = end
    eps = 1e-9
    route = []
    r_c = elbow_inner + width / 2.0

    def elbow_disp(d0, d1):
        return _elbow_end(0.0, 0.0, r_c, d0, d1)

    def split_total(total):
        if total < -eps:
            raise AutoRouteSpaceError(
                'Auto route failed: insufficient space for elbows')
        if total < 2 * min_straight:
            l1 = max(0.0, total / 2.0)
            l2 = total - l1
            return l1, l2
        l1 = max(min_straight, total / 2.0)
        l2 = total - l1
        if l2 < min_straight:
            l2 = min_straight
            l1 = total - l2
        return l1, l2

    def opposite_lengths(delta):
        # Solve L1 - L3 = delta with L1,L3 >= min_straight
        if delta >= 0:
            l3 = min_straight
            l1 = delta + l3
        else:
            l1 = min_straight
            l3 = l1 - delta
        return l1, l3

    if start_dir == end_dir:
        if _is_horizontal(start_dir):
            if abs(ey - sy) < eps:
                length = abs(ex - sx)
                if start_dir == 'right' and ex < sx - eps:
                    raise ValueError(
                        'Auto route failed: target is left of start for rightward flow')
                if start_dir == 'left' and ex > sx + eps:
                    raise ValueError(
                        'Auto route failed: target is right of start for leftward flow')
                route.append(RouteSegment(
                    kind='rect', length=length, direction=start_dir))
                return route
            if start_dir == 'right' and ex < sx - eps:
                raise ValueError(
                    'Auto route failed: target is left of start for rightward flow')
            if start_dir == 'left' and ex > sx + eps:
                raise ValueError(
                    'Auto route failed: target is right of start for leftward flow')
            vdir = 'up' if ey > sy else 'down'
            dx_e1, dy_e1 = elbow_disp(start_dir, vdir)
            dx_e2, dy_e2 = elbow_disp(vdir, end_dir)
            dx_rect = (ex - sx) - (dx_e1 + dx_e2)
            dy_rect = (ey - sy) - (dy_e1 + dy_e2)
            if (dy_rect > eps and vdir != 'up') or (dy_rect < -eps and vdir != 'down'):
                if abs(ey - sy) < abs(dy_e1 + dy_e2) - eps:
                    raise AutoRouteSpaceError(
                        'Auto route failed: insufficient space for elbows')
                raise ValueError(
                    'Auto route failed: target direction does not match geometry')
            if (dx_rect < -eps and start_dir == 'right') or (dx_rect > eps and start_dir == 'left'):
                raise AutoRouteSpaceError(
                    'Auto route failed: insufficient space for elbows')
            total_h = abs(dx_rect)
            total_v = abs(dy_rect)
            l1, l3 = split_total(total_h)
            l2 = total_v
            route.append(RouteSegment(
                kind='rect', length=l1, direction=start_dir))
            route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                      turn=_turn_type_from_dirs(start_dir, vdir)))
            route.append(RouteSegment(
                kind='rect', length=l2, direction=vdir))
            route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                      turn=_turn_type_from_dirs(vdir, end_dir)))
            route.append(RouteSegment(
                kind='rect', length=l3, direction=end_dir))
            return route
        else:
            if abs(ex - sx) < eps:
                length = abs(ey - sy)
                if start_dir == 'up' and ey < sy - eps:
                    raise ValueError(
                        'Auto route failed: target is below start for upward flow')
                if start_dir == 'down' and ey > sy + eps:
                    raise ValueError(
                        'Auto route failed: target is above start for downward flow')
                route.append(RouteSegment(
                    kind='rect', length=length, direction=start_dir))
                return route
            if start_dir == 'up' and ey < sy - eps:
                raise ValueError(
                    'Auto route failed: target is below start for upward flow')
            if start_dir == 'down' and ey > sy + eps:
                raise ValueError(
                    'Auto route failed: target is above start for downward flow')
            hdir = 'right' if ex > sx else 'left'
            dx_e1, dy_e1 = elbow_disp(start_dir, hdir)
            dx_e2, dy_e2 = elbow_disp(hdir, end_dir)
            dx_rect = (ex - sx) - (dx_e1 + dx_e2)
            dy_rect = (ey - sy) - (dy_e1 + dy_e2)
            if (dx_rect > eps and hdir != 'right') or (dx_rect < -eps and hdir != 'left'):
                if abs(ex - sx) < abs(dx_e1 + dx_e2) - eps:
                    raise AutoRouteSpaceError(
                        'Auto route failed: insufficient space for elbows')
                raise ValueError(
                    'Auto route failed: target direction does not match geometry')
            if (dy_rect < -eps and start_dir == 'up') or (dy_rect > eps and start_dir == 'down'):
                raise AutoRouteSpaceError(
                    'Auto route failed: insufficient space for elbows')
            total_v = abs(dy_rect)
            total_h = abs(dx_rect)
            l1, l3 = split_total(total_v)
            l2 = total_h
            route.append(RouteSegment(
                kind='rect', length=l1, direction=start_dir))
            route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                      turn=_turn_type_from_dirs(start_dir, hdir)))
            route.append(RouteSegment(
                kind='rect', length=l2, direction=hdir))
            route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                      turn=_turn_type_from_dirs(hdir, end_dir)))
            route.append(RouteSegment(
                kind='rect', length=l3, direction=end_dir))
            return route

    # Perpendicular directions
    if _is_horizontal(start_dir) and _is_vertical(end_dir):
        if start_dir == 'right' and ex < sx - eps:
            raise ValueError(
                'Auto route failed: target is left of start for rightward flow')
        if start_dir == 'left' and ex > sx + eps:
            raise ValueError(
                'Auto route failed: target is right of start for leftward flow')
        vdir = 'up' if ey > sy else 'down'
        if vdir != end_dir:
            raise ValueError(
                f'Auto route failed: target direction {end_dir} does not match geometry')
        dx_e, dy_e = elbow_disp(start_dir, vdir)
        dx_rect = (ex - sx) - dx_e
        dy_rect = (ey - sy) - dy_e
        if (dx_rect > eps and start_dir != 'right') or (dx_rect < -eps and start_dir != 'left'):
            raise ValueError(
                'Auto route failed: target direction does not match geometry')
        if (dx_rect < -eps and start_dir == 'right') or (dx_rect > eps and start_dir == 'left'):
            raise AutoRouteSpaceError(
                'Auto route failed: insufficient space for elbows')
        l1 = abs(dx_rect)
        l2 = abs(dy_rect)
        route.append(RouteSegment(
            kind='rect', length=l1, direction=start_dir))
        route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                  turn=_turn_type_from_dirs(start_dir, vdir)))
        route.append(RouteSegment(
            kind='rect', length=l2, direction=vdir))
        return route
    if _is_vertical(start_dir) and _is_horizontal(end_dir):
        if start_dir == 'up' and ey < sy - eps:
            raise ValueError(
                'Auto route failed: target is below start for upward flow')
        if start_dir == 'down' and ey > sy + eps:
            raise ValueError(
                'Auto route failed: target is above start for downward flow')
        hdir = 'right' if ex > sx else 'left'
        if hdir != end_dir:
            raise ValueError(
                f'Auto route failed: target direction {end_dir} does not match geometry')
        dx_e, dy_e = elbow_disp(start_dir, hdir)
        dx_rect = (ex - sx) - dx_e
        dy_rect = (ey - sy) - dy_e
        if (dy_rect > eps and start_dir != 'up') or (dy_rect < -eps and start_dir != 'down'):
            raise ValueError(
                'Auto route failed: target direction does not match geometry')
        if (dy_rect < -eps and start_dir == 'up') or (dy_rect > eps and start_dir == 'down'):
            raise AutoRouteSpaceError(
                'Auto route failed: insufficient space for elbows')
        l1 = abs(dy_rect)
        l2 = abs(dx_rect)
        route.append(RouteSegment(
            kind='rect', length=l1, direction=start_dir))
        route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                  turn=_turn_type_from_dirs(start_dir, hdir)))
        route.append(RouteSegment(
            kind='rect', length=l2, direction=hdir))
        return route

    # Opposite directions: use two elbows + three rects (a U-turn)
    if _is_opposite(start_dir, end_dir):
        if _is_horizontal(start_dir):
            vdir = 'up' if ey >= sy else 'down'
            dx_e1, dy_e1 = elbow_disp(start_dir, vdir)
            dx_e2, dy_e2 = elbow_disp(vdir, end_dir)
            dx_rect = (ex - sx) - (dx_e1 + dx_e2)
            dy_rect = (ey - sy) - (dy_e1 + dy_e2)
            if (dy_rect > eps and vdir != 'up') or (dy_rect < -eps and vdir != 'down'):
                if abs(ey - sy) < abs(dy_e1 + dy_e2) - eps:
                    raise AutoRouteSpaceError(
                        'Auto route failed: insufficient space for elbows')
                raise ValueError(
                    'Auto route failed: target direction does not match geometry')
            if (dx_rect < -eps and start_dir == 'right') or (dx_rect > eps and start_dir == 'left'):
                raise AutoRouteSpaceError(
                    'Auto route failed: insufficient space for elbows')
            l2 = abs(dy_rect)
            s = 1 if start_dir == 'right' else -1
            delta = dx_rect / s
            l1, l3 = opposite_lengths(delta)
            route.append(RouteSegment(
                kind='rect', length=l1, direction=start_dir))
            route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                      turn=_turn_type_from_dirs(start_dir, vdir)))
            route.append(RouteSegment(
                kind='rect', length=l2, direction=vdir))
            route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                      turn=_turn_type_from_dirs(vdir, end_dir)))
            route.append(RouteSegment(
                kind='rect', length=l3, direction=end_dir))
            return route
        else:
            hdir = 'right' if ex >= sx else 'left'
            dx_e1, dy_e1 = elbow_disp(start_dir, hdir)
            dx_e2, dy_e2 = elbow_disp(hdir, end_dir)
            dx_rect = (ex - sx) - (dx_e1 + dx_e2)
            dy_rect = (ey - sy) - (dy_e1 + dy_e2)
            if (dx_rect > eps and hdir != 'right') or (dx_rect < -eps and hdir != 'left'):
                if abs(ex - sx) < abs(dx_e1 + dx_e2) - eps:
                    raise AutoRouteSpaceError(
                        'Auto route failed: insufficient space for elbows')
                raise ValueError(
                    'Auto route failed: target direction does not match geometry')
            if (dy_rect < -eps and start_dir == 'up') or (dy_rect > eps and start_dir == 'down'):
                raise AutoRouteSpaceError(
                    'Auto route failed: insufficient space for elbows')
            l2 = abs(dx_rect)
            s = 1 if start_dir == 'up' else -1
            delta = dy_rect / s
            l1, l3 = opposite_lengths(delta)
            route.append(RouteSegment(
                kind='rect', length=l1, direction=start_dir))
            route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                      turn=_turn_type_from_dirs(start_dir, hdir)))
            route.append(RouteSegment(
                kind='rect', length=l2, direction=hdir))
            route.append(RouteSegment(kind='elbow', length=elbow_inner,
                                      turn=_turn_type_from_dirs(hdir, end_dir)))
            route.append(RouteSegment(
                kind='rect', length=l3, direction=end_dir))
            return route

    raise ValueError(
        f'Auto routing does not support direction change: {start_dir} -> {end_dir}')


def _build_auto_layout(diagram: Diagram):
    """Build process objects, place them, and compute flow anchors."""
    cfg = diagram.config
    proc_specs = diagram.processes
    proc_names = list(proc_specs.keys())

    # Create Flow objects
    flow_objs: Dict[str, Flow] = {}
    for f in diagram.flows:
        flow_objs[f.name] = Flow(
            name=f.name,
            value=f.value,
            direction='out',
            color=f.color,
            length=f.length,
            label=f.label if f.label is not None else f.name,
            inlet_tri_height=f.inlet_tri_height,
            outlet_tri_height=f.outlet_tri_height,
            label_dx=f.label_dx,
            label_dy=f.label_dy,
            label_rotation=f.label_rotation,
            cycle_breaker=f.cycle_breaker,
            route=f.route,
        )

    # Build inflow/outflow lists (preserve flow order)
    inflows: Dict[str, List[Flow]] = {p: [] for p in proc_names}
    outflows: Dict[str, List[Flow]] = {p: [] for p in proc_names}
    for f in diagram.flows:
        if f.target in proc_specs:
            inflows[f.target].append(flow_objs[f.name])
        if f.source in proc_specs:
            outflows[f.source].append(flow_objs[f.name])

    # Compute process sizes
    proc_dims: Dict[str, Tuple[float, float, float, float]] = {}
    for name, spec in proc_specs.items():
        rect_w, rect_h, sum_in, sum_out = _compute_process_dims(
            spec, inflows[name], outflows[name], cfg.scale)
        proc_dims[name] = (rect_w, rect_h, sum_in, sum_out)

    # Layering
    layers = _topo_layers(proc_names, diagram.flows)
    max_layer = max(layers.values()) if layers else 0
    layer_to_procs: Dict[int, List[str]] = {
        i: [] for i in range(max_layer + 1)}
    for p, l in layers.items():
        layer_to_procs[l].append(p)

    # Compute default layer positions
    positions: Dict[str, Tuple[float, float]] = {}
    current_axis = 0.0
    axis_dir = 1.0 if cfg.layout_direction in (
        'right', 'up') else -1.0
    horizontal_layout = cfg.layout_direction in ('right', 'left')
    for layer_idx in range(max_layer + 1):
        procs = layer_to_procs.get(layer_idx, [])
        if not procs:
            continue
        if horizontal_layout:
            layer_width = max(proc_dims[p][0] for p in procs)
            axis_center = axis_dir * (current_axis + layer_width / 2.0)
            cross_sizes = [proc_dims[p][1] for p in procs]
        else:
            layer_width = max(proc_dims[p][1] for p in procs)
            axis_center = axis_dir * (current_axis + layer_width / 2.0)
            cross_sizes = [proc_dims[p][0] for p in procs]
        total_cross = sum(cross_sizes) + \
            max(len(procs) - 1, 0) * cfg.process_gap
        cross_cursor = total_cross / 2.0
        for p, size in zip(procs, cross_sizes):
            cross_center = cross_cursor - size / 2.0
            if horizontal_layout:
                positions[p] = (axis_center, cross_center)
            else:
                positions[p] = (cross_center, axis_center)
            cross_cursor -= size + cfg.process_gap
        current_axis += layer_width + cfg.layer_gap

    # Determine positions based on the largest inlet flow source
    proc_in_from_proc = {p: [] for p in proc_names}
    for f in diagram.flows:
        if f.cycle_breaker:
            continue
        if f.target in proc_specs and f.source in proc_specs:
            proc_in_from_proc[f.target].append(f)

    roots = [p for p in proc_names if len(proc_in_from_proc[p]) == 0]
    # Topological order based on layers (stable by input order)
    order = sorted(proc_names, key=lambda p: (
        layers.get(p, 0), proc_names.index(p)))

    for p in order:
        if p in roots:
            continue
        inflows_from_proc = proc_in_from_proc.get(p, [])
        if not inflows_from_proc:
            continue
        max_flow_def = max(inflows_from_proc, key=lambda f: f.value)
        src = max_flow_def.source
        if src not in positions:
            continue
        src_spec = proc_specs[src]
        dst_spec = proc_specs[p]
        rect_w_src, rect_h_src, _, _ = proc_dims[src]
        rect_w_dst, rect_h_dst, _, _ = proc_dims[p]
        flow_obj = flow_objs[max_flow_def.name]
        start = _flow_anchor_for_process(
            src_spec,
            positions[src],
            rect_w_src,
            rect_h_src,
            outflows[src],
            flow_obj,
            cfg.scale,
            cfg.flow_gap,
            is_outflow=True,
        )
        if max_flow_def.route:
            _validate_route(max_flow_def.route)
            route = max_flow_def.route
        else:
            route = _default_alignment_route(
                flow_obj, src_spec.direction, dst_spec.direction, cfg.elbow_inner_radius)
        dx, dy = _route_displacement(
            route, flow_obj.value * cfg.scale)
        end = (start[0] + dx, start[1] + dy)
        dst_anchor_offset = _flow_anchor_offset(
            dst_spec,
            rect_w_dst,
            rect_h_dst,
            inflows[p],
            flow_obj,
            cfg.scale,
            cfg.flow_gap,
            is_outflow=False,
        )
        positions[p] = (end[0] - dst_anchor_offset[0],
                        end[1] - dst_anchor_offset[1])

    # Build Process objects with positions
    proc_objs: Dict[str, Process] = {}
    for name, spec in proc_specs.items():
        x, y = positions.get(name, (0.0, 0.0))
        if spec.x is not None:
            x = spec.x
        if spec.y is not None:
            y = spec.y
        proc_objs[name] = Process(
            name=name,
            x=x,
            y=y,
            direction=spec.direction,
            triangle_side=spec.triangle_side,
            length=spec.length,
            overlay=spec.overlay,
            overlay_height=spec.overlay_height,
            overlay_edgecolor=spec.overlay_edgecolor,
            overlay_linewidth=spec.overlay_linewidth,
            overlay_linestyle=spec.overlay_linestyle,
            overlay_alpha=spec.overlay_alpha,
            label_dx=spec.label_dx,
            label_dy=spec.label_dy,
            label_rotation=spec.label_rotation,
            triangle_label=spec.triangle_label,
            triangle_label_dx=spec.triangle_label_dx,
            triangle_label_dy=spec.triangle_label_dy,
            inflows=inflows[name],
            outflows=outflows[name],
            color=spec.color,
        )

    # Compute anchors for each flow
    anchors = {'start': {}, 'end': {}}
    for name, proc in proc_objs.items():
        rect_w, rect_h, _, _ = proc_dims[name]
        x0 = proc.x - rect_w / 2.0
        x1 = proc.x + rect_w / 2.0
        y0 = proc.y - rect_h / 2.0
        y1 = proc.y + rect_h / 2.0
        if proc.direction in ('right', 'left'):
            side = proc.triangle_side or 'top'
            if side not in ('top', 'bottom'):
                side = 'top'
            if side == 'top':
                inflow_stack = _stack_flows_from_bottom_edge(
                    proc.inflows, y0, cfg.scale, cfg.flow_gap)
                outflow_stack = _stack_flows_from_bottom_edge(
                    proc.outflows, y0, cfg.scale, cfg.flow_gap)
            else:
                inflow_stack = _stack_flows_from_top_edge(
                    proc.inflows, y1, cfg.scale, cfg.flow_gap)
                outflow_stack = _stack_flows_from_top_edge(
                    proc.outflows, y1, cfg.scale, cfg.flow_gap)
            for flow, y_mid in inflow_stack:
                anchors['end'][flow.name] = (
                    x0, y_mid) if proc.direction == 'right' else (x1, y_mid)
            for flow, y_mid in outflow_stack:
                anchors['start'][flow.name] = (
                    x1, y_mid) if proc.direction == 'right' else (x0, y_mid)
        else:
            side = proc.triangle_side or 'left'
            if side not in ('left', 'right'):
                side = 'left'
            if side == 'left':
                inflow_stack = _stack_flows_from_right_edge(
                    proc.inflows, x1, cfg.scale, cfg.flow_gap)
                outflow_stack = _stack_flows_from_right_edge(
                    proc.outflows, x1, cfg.scale, cfg.flow_gap)
            else:
                inflow_stack = _stack_flows_from_left_edge(
                    proc.inflows, x0, cfg.scale, cfg.flow_gap)
                outflow_stack = _stack_flows_from_left_edge(
                    proc.outflows, x0, cfg.scale, cfg.flow_gap)
            for flow, x_mid in inflow_stack:
                anchors['end'][flow.name] = (
                    x_mid, y0) if proc.direction == 'up' else (x_mid, y1)
            for flow, x_mid in outflow_stack:
                anchors['start'][flow.name] = (
                    x_mid, y1) if proc.direction == 'up' else (x_mid, y0)

    return proc_objs, flow_objs, anchors
