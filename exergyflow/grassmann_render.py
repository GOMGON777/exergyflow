"""
Rendering utilities for Grassmann/Sankey-like diagrams (Matplotlib).

Draws flows, elbows, process blocks, imbalance triangles, and labels.
See README.md for rendering conventions.
"""

from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from matplotlib.patches import Polygon
from matplotlib.lines import Line2D
from .grassmann_types import Flow, Process, LinkFlow
from .grassmann_geometry import rect_poly, elbow_wedge_from_type, _validate_route, _dir_vec, _route_displacement
from .grassmann_layout import (_stack_flows_from_bottom_edge, _stack_flows_from_top_edge,
                               _stack_flows_from_left_edge, _stack_flows_from_right_edge)

# Overlap epsilons (to avoid hairline gaps)
EPS_FLOW_INLET_TRI = -5e-3   # Inlet triangle base nudged into its flow rectangle
EPS_FLOW_OUTLET_TRI = 5e-3  # Outlet triangle base nudged into its flow rectangle
EPS_FLOW_RECT_ELBOW = 5e-3  # Rectangles overlap adjacent elbows
# Rectangles overlap process border (inlet/outlet join)
EPS_FLOW_RECT_PROCESS = 5e-3
EPS_PROCESS_TRI = 5e-3  # Imbalance triangle overlaps process rectangle edge

# Text style helper


def _text_kwargs(style: Optional[Dict[str, Any]], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Merge text style dict with defaults, skipping None values."""
    merged = dict(defaults)
    if style:
        for k, v in style.items():
            if v is not None:
                merged[k] = v
    return merged

# Drawing engine
# -----------------------------
# Drawing engine
# -----------------------------


def _draw_flow(
    ax,
    flow: Flow,
    width: float,
    inlet_triangle: bool = False,
    outlet_triangle: bool = False,
    override_direction: Optional[str] = None,
    label_avoid_rects: Optional[List[Tuple[float,
                                           float, float, float]]] = None,
    label_text: Optional[str] = None,
    label_offset: Optional[Tuple[float, float]] = None,
    render_width: Optional[float] = None,
    flow_label_style: Optional[Dict[str, Any]] = None,
):
    """Draw a flow (rectangles + elbows) and optional inlet/outlet triangles."""
    x, y = flow._x, flow._y
    start_x, start_y = x, y
    last_rect_mid = (x, y)
    flow_dir = override_direction
    last_dir = override_direction
    rect_segments = []
    draw_w = render_width if render_width is not None else width
    if flow.route:
        _validate_route(flow.route)
        flow_dir = flow.route[0].direction
        current_dir = None
        for idx, seg in enumerate(flow.route):
            if seg.kind == 'rect':
                if seg.direction is None:
                    raise ValueError('rect segment requires direction')
                x_start, y_start = x, y
                # If adjacent to elbows or process borders, extend/shift slightly to avoid hairline gaps.
                prev_is_elbow = (
                    idx - 1 >= 0 and flow.route[idx - 1].kind == 'elbow')
                next_is_elbow = (idx + 1 < len(flow.route)
                                 and flow.route[idx + 1].kind == 'elbow')
                is_first = (idx == 0)
                is_last = (idx == len(flow.route) - 1)
                back_overlap = (EPS_FLOW_RECT_ELBOW if prev_is_elbow else 0.0) + \
                    (EPS_FLOW_RECT_PROCESS if is_first else 0.0)
                fwd_overlap = (EPS_FLOW_RECT_ELBOW if next_is_elbow else 0.0) + \
                    (EPS_FLOW_RECT_PROCESS if is_last else 0.0)
                draw_len = seg.length + back_overlap + fwd_overlap
                if back_overlap > 0.0:
                    vx_eps, vy_eps = _dir_vec(seg.direction, back_overlap)
                    draw_start_x = x - vx_eps
                    draw_start_y = y - vy_eps
                else:
                    draw_start_x = x
                    draw_start_y = y
                pts, (x_draw, y_draw) = rect_poly(
                    draw_start_x, draw_start_y, draw_len, draw_w, seg.direction)
                ax.add_patch(Polygon(pts, closed=True, facecolor=flow.color,
                             edgecolor='none', linewidth=0.0, zorder=flow.z))
                current_dir = seg.direction
                # Advance along the true (non-extended) length for routing
                vx, vy = _dir_vec(seg.direction, seg.length)
                x, y = x_start + vx, y_start + vy
                last_rect_mid = ((x_start + x) / 2.0, (y_start + y) / 2.0)
                rect_segments.append(
                    (seg.length, current_dir, last_rect_mid))
            elif seg.kind == 'elbow':
                if seg.turn is None or current_dir is None:
                    raise ValueError(
                        'elbow segment requires turn and a previous direction')
                wedge, (x, y), current_dir, center, ang0, ang1 = elbow_wedge_from_type(
                    x, y, seg.length, draw_w, seg.turn, current_dir)
                wedge.set_facecolor(flow.color)
                wedge.set_edgecolor('none')
                wedge.set_linewidth(0.0)
                wedge.set_zorder(flow.z)
                ax.add_patch(wedge)
            else:
                raise ValueError(f'Unknown segment kind: {seg.kind}')
        last_dir = current_dir
    else:
        direction = flow_dir
        if direction is None:
            direction = 'left' if flow.direction == 'in' else 'right'
            flow_dir = direction
        last_dir = direction
        # Extend single-section flows slightly into the process border
        back_overlap = EPS_FLOW_RECT_PROCESS if flow.direction == 'out' else 0.0
        fwd_overlap = EPS_FLOW_RECT_PROCESS if flow.direction == 'in' else 0.0
        draw_len = flow.length + back_overlap + fwd_overlap
        if back_overlap > 0.0:
            vx_eps, vy_eps = _dir_vec(direction, back_overlap)
            draw_start_x = x - vx_eps
            draw_start_y = y - vy_eps
        else:
            draw_start_x = x
            draw_start_y = y
        pts, _ = rect_poly(draw_start_x, draw_start_y,
                           draw_len, draw_w, direction)

        ax.add_patch(Polygon(pts, closed=True, facecolor=flow.color,
                     edgecolor='none', linewidth=0.0, zorder=flow.z))
        # advance to end of single-section flow
        vx, vy = _dir_vec(direction, flow.length)
        x, y = x + vx, y + vy
        rect_segments.append(
            (flow.length, direction, (start_x + vx / 2.0, start_y + vy / 2.0)))

    if flow.direction == 'in' and inlet_triangle:
        # Triangle at flow start (opposite shared side), base parallel to opposite side
        dir_for_tri = flow_dir or 'left'
        base_len = draw_w
        tri_len = draw_w * getattr(flow, 'inlet_tri_height', 1.0)
        base_x, base_y = start_x, start_y
        # Nudge base slightly into the rectangle to avoid hairline gaps
        if dir_for_tri == 'right':
            base_x += EPS_FLOW_INLET_TRI
        elif dir_for_tri == 'left':
            base_x -= EPS_FLOW_INLET_TRI
        elif dir_for_tri == 'up':
            base_y += EPS_FLOW_INLET_TRI
        elif dir_for_tri == 'down':
            base_y -= EPS_FLOW_INLET_TRI
        if dir_for_tri in ('right', 'left'):
            half_base = base_len / 2.0
            apex = _dir_vec(dir_for_tri, tri_len)
            tri_pts = [
                (base_x, base_y - half_base),
                (base_x, base_y + half_base),
                (base_x + apex[0], base_y + apex[1]),
            ]
        else:
            half_base = base_len / 2.0
            apex = _dir_vec(dir_for_tri, tri_len)
            tri_pts = [
                (base_x - half_base, base_y),
                (base_x + half_base, base_y),
                (base_x + apex[0], base_y + apex[1]),
            ]
        ax.add_patch(Polygon(tri_pts, closed=True, facecolor='white',
                     edgecolor='none', linewidth=0.0, zorder=flow.z + 2))

    if flow.direction == 'out' and outlet_triangle:
        # Triangle at flow end (opposite shared side), base parallel to opposite side
        dir_for_tri = last_dir or 'right'
        base_len = 1.2 * draw_w
        tri_len = draw_w * getattr(flow, 'outlet_tri_height', 1.0)
        base_x, base_y = x, y
        # Nudge base slightly into the rectangle to avoid hairline gaps
        if dir_for_tri == 'right':
            base_x -= EPS_FLOW_OUTLET_TRI
        elif dir_for_tri == 'left':
            base_x += EPS_FLOW_OUTLET_TRI
        elif dir_for_tri == 'up':
            base_y -= EPS_FLOW_OUTLET_TRI
        elif dir_for_tri == 'down':
            base_y += EPS_FLOW_OUTLET_TRI
        if dir_for_tri in ('right', 'left'):
            half_base = base_len / 2.0
            apex = _dir_vec(dir_for_tri, tri_len)
            tri_pts = [
                (base_x, base_y - half_base),
                (base_x, base_y + half_base),
                (base_x + apex[0], base_y + apex[1]),
            ]
        else:
            half_base = base_len / 2.0
            apex = _dir_vec(dir_for_tri, tri_len)
            tri_pts = [
                (base_x - half_base, base_y),
                (base_x + half_base, base_y),
                (base_x + apex[0], base_y + apex[1]),
            ]
        ax.add_patch(Polygon(tri_pts, closed=True, facecolor=flow.color,
                     edgecolor='none', linewidth=0.0, zorder=flow.z + 2))

    if label_text is None:
        label_text = f"{flow.label or flow.name} = {flow.value}"
    _draw_flow_label(ax, label_text, rect_segments, width, flow.z + 1,
                     avoid_rects=label_avoid_rects, label_offset=label_offset,
                     label_rotation=flow.label_rotation,
                     flow_label_style=flow_label_style)


def _draw_flow_label(ax, label_text, rect_segments, width, z, font_size=8, pad=0.12,
                     avoid_rects: Optional[List[Tuple[float,
                                                      float, float, float]]] = None,
                     label_offset: Optional[Tuple[float, float]] = None,
                     label_rotation: Optional[float] = None,
                     flow_label_style: Optional[Dict[str, Any]] = None):
    """Place label on longest rect segment; if it doesn't fit, place outside with leader."""
    if not rect_segments:
        return
    # Pick longest segment
    length, direction, (x_mid, y_mid) = max(rect_segments, key=lambda t: t[0])
    dx, dy = label_offset or (0.0, 0.0)
    base_x = x_mid + dx
    base_y = y_mid + dy
    rotation = label_rotation if label_rotation is not None else (
        90 if direction in ('up', 'down') else 0
    )

    # Try placing on segment, measure in data units
    text_kwargs = _text_kwargs(
        flow_label_style, {"fontsize": font_size, "color": "black"})
    txt = ax.text(
        base_x,
        base_y,
        label_text,
        ha=text_kwargs.get("ha", "center"),
        va=text_kwargs.get("va", "center"),
        rotation=rotation,
        rotation_mode=text_kwargs.get("rotation_mode", "anchor"),
        zorder=z,
        alpha=0.0,
        **{k: v for k, v in text_kwargs.items()
           if k not in ("ha", "va", "rotation_mode", "alpha")},
    )
    text_w = None
    text_h = None
    try:
        fig = ax.figure
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bbox = txt.get_window_extent(renderer=renderer)
        (x0, y0) = ax.transData.inverted().transform((bbox.x0, bbox.y0))
        (x1, y1) = ax.transData.inverted().transform((bbox.x1, bbox.y1))
        text_w = abs(x1 - x0)
        text_h = abs(y1 - y0)
        needed = text_w if direction in ('left', 'right') else text_h
        fits = needed <= max(length, 1e-9)
        if avoid_rects:
            pad = 0.02
            bx0, bx1 = min(x0, x1), max(x0, x1)
            by0, by1 = min(y0, y1), max(y0, y1)
            bx0 -= pad
            bx1 += pad
            by0 -= pad
            by1 += pad
            for rx0, ry0, rx1, ry1 in avoid_rects:
                if not (bx1 < rx0 or bx0 > rx1 or by1 < ry0 or by0 > ry1):
                    fits = False
                    break
    except Exception:
        fits = True
    if fits:
        txt.set_alpha(text_kwargs.get("alpha", 1.0))
        return
    # Move outside with leader line, prefer a side that avoids process rectangles
    txt.remove()
    offset = width / 2.0 + pad
    if direction in ('left', 'right'):
        candidates = [(x_mid, y_mid + offset), (x_mid, y_mid - offset)]
    else:
        candidates = [(x_mid + offset, y_mid), (x_mid - offset, y_mid)]

    def intersects_any(px, py):
        if not avoid_rects:
            return False
        if text_w is None or text_h is None:
            for rx0, ry0, rx1, ry1 in avoid_rects:
                if rx0 <= px <= rx1 and ry0 <= py <= ry1:
                    return True
            return False
        bx0 = px - text_w / 2.0
        bx1 = px + text_w / 2.0
        by0 = py - text_h / 2.0
        by1 = py + text_h / 2.0
        for rx0, ry0, rx1, ry1 in avoid_rects:
            if not (bx1 < rx0 or bx0 > rx1 or by1 < ry0 or by0 > ry1):
                return True
        return False

    out_x, out_y = candidates[0]
    if avoid_rects:
        valid = [p for p in candidates if not intersects_any(
            p[0] + dx, p[1] + dy)]
        if valid:
            out_x, out_y = valid[0]
        else:
            # pick the candidate with fewer overlaps (ties go to first)
            def overlap_count(p):
                return sum(1 for rx0, ry0, rx1, ry1 in avoid_rects
                           if rx0 <= (p[0] + dx) <= rx1 and ry0 <= (p[1] + dy) <= ry1)
            out_x, out_y = min(candidates, key=overlap_count)
    out_x += dx
    out_y += dy
    ax.add_line(Line2D([x_mid, out_x], [y_mid, out_y],
                       color='black', linewidth=0.4, zorder=z))
    ax.text(
        out_x,
        out_y,
        label_text,
        ha=text_kwargs.get("ha", "center"),
        va=text_kwargs.get("va", "center"),
        rotation=rotation,
        rotation_mode=text_kwargs.get("rotation_mode", "anchor"),
        zorder=z,
        alpha=text_kwargs.get("alpha", 1.0),
        **{k: v for k, v in text_kwargs.items()
           if k not in ("ha", "va", "rotation_mode", "alpha")},
    )


def _draw_link(ax, x_left: float, x_right: float, y_bottom: float, flows: List[LinkFlow], scale: float, gap: float):
    """Draw shared link flows between two process sides."""
    # Draw shared flows between two process sides
    length = x_right - x_left
    y_top = y_bottom + sum(f.value for f in flows) * \
        scale + max(len(flows) - 1, 0) * gap
    for f in flows:
        h = f.value * scale
        y_mid = y_top - h / 2.0
        pts, _ = rect_poly(x_left, y_mid, length, h, 'right')
        ax.add_patch(Polygon(pts, closed=True, facecolor=f.color,
                     edgecolor='none', linewidth=0.0, zorder=3))
        ax.text(x_left + length / 2.0, y_mid,
                f"{f.name} = {f.value}", fontsize=8, ha='center', va='center', zorder=4)
        y_top -= h + gap


def draw_process(
    ax,
    process: Process,
    scale: float = 1.0,
    gap: float = 0.0,
    triangle_side: str = 'auto',
    draw_inflows: bool = True,
    draw_outflows: bool = True,
    inlet_triangles: bool = False,
    outlet_triangles: bool = False,
    inflow_filter: Optional[set] = None,
    outflow_filter: Optional[set] = None,
    no_triangle_names: Optional[set] = None,
    process_label_style: Optional[Dict[str, Any]] = None,
    triangle_label_style: Optional[Dict[str, Any]] = None,
):
    """Draw a process, its flows, and its imbalance triangle."""
    # Summations
    sum_in = sum(f.value for f in process.inflows)
    sum_out = sum(f.value for f in process.outflows)
    proc_flow = min(sum_in, sum_out) * scale

    # Process rectangle bounds (dimension depends on direction)
    if process.direction in ('right', 'left'):
        rect_w = process.length
        rect_h = proc_flow
    else:
        rect_w = proc_flow
        rect_h = process.length

    x0 = process.x - rect_w / 2.0
    x1 = process.x + rect_w / 2.0
    y0 = process.y - rect_h / 2.0
    y1 = process.y + rect_h / 2.0

    # Place flows (stacked from the edge opposite the imbalance triangle)

    proc_dir = process.direction

    if draw_inflows:
        if proc_dir in ('right', 'left'):
            side = process.triangle_side or (
                'top' if triangle_side == 'auto' else triangle_side)
            if side not in ('top', 'bottom'):
                side = 'top'
            if side == 'top':
                inflow_stack = _stack_flows_from_bottom_edge(
                    process.inflows, y0, scale, gap)
            else:
                inflow_stack = _stack_flows_from_top_edge(
                    process.inflows, y1, scale, gap)
            for flow, y_mid in inflow_stack:
                if inflow_filter is None or flow.name in inflow_filter:
                    width = flow.value * scale
                    end_x, end_y = (
                        x0, y_mid) if proc_dir == 'right' else (x1, y_mid)
                    if flow.route:
                        _validate_route(flow.route)
                        last_rect_dir = flow.route[-1].direction
                        if last_rect_dir != proc_dir:
                            raise ValueError(
                                'inlet last section direction must match process direction')
                        dx, dy = _route_displacement(flow.route, width)
                        flow._x = end_x - dx
                        flow._y = end_y - dy
                    else:
                        vx, vy = _dir_vec(proc_dir, flow.length)
                        flow._x = end_x - vx
                        flow._y = end_y - vy

                    use_in_tri = inlet_triangles and (
                        no_triangle_names is None or flow.name not in no_triangle_names)
                    use_out_tri = outlet_triangles and (
                        no_triangle_names is None or flow.name not in no_triangle_names)
                    _draw_flow(ax, flow, width=width, inlet_triangle=use_in_tri,
                               outlet_triangle=use_out_tri, override_direction=proc_dir)
        else:
            side = process.triangle_side or (
                'left' if triangle_side == 'auto' else triangle_side)
            if side not in ('left', 'right'):
                side = 'left'
            if side == 'left':
                inflow_stack = _stack_flows_from_right_edge(
                    process.inflows, x1, scale, gap)
            else:
                inflow_stack = _stack_flows_from_left_edge(
                    process.inflows, x0, scale, gap)
            for flow, x_mid in inflow_stack:
                width = flow.value * scale
                if inflow_filter is None or flow.name in inflow_filter:
                    end_x, end_y = (
                        x_mid, y0) if proc_dir == 'up' else (x_mid, y1)
                    if flow.route:
                        _validate_route(flow.route)
                        last_rect_dir = flow.route[-1].direction
                        if last_rect_dir != proc_dir:
                            raise ValueError(
                                'inlet last section direction must match process direction')
                        dx, dy = _route_displacement(flow.route, width)
                        flow._x = end_x - dx
                        flow._y = end_y - dy
                    else:
                        vx, vy = _dir_vec(proc_dir, flow.length)
                        flow._x = end_x - vx
                        flow._y = end_y - vy

                    use_in_tri = inlet_triangles and (
                        no_triangle_names is None or flow.name not in no_triangle_names)
                    use_out_tri = outlet_triangles and (
                        no_triangle_names is None or flow.name not in no_triangle_names)
                    _draw_flow(ax, flow, width=width, inlet_triangle=use_in_tri,
                               outlet_triangle=use_out_tri, override_direction=proc_dir)

    if draw_outflows:
        if proc_dir in ('right', 'left'):
            side = process.triangle_side or (
                'top' if triangle_side == 'auto' else triangle_side)
            if side not in ('top', 'bottom'):
                side = 'top'
            if side == 'top':
                outflow_stack = _stack_flows_from_bottom_edge(
                    process.outflows, y0, scale, gap)
            else:
                outflow_stack = _stack_flows_from_top_edge(
                    process.outflows, y1, scale, gap)
            for flow, y_mid in outflow_stack:
                if outflow_filter is None or flow.name in outflow_filter:
                    width = flow.value * scale
                    flow._x, flow._y = (
                        x1, y_mid) if proc_dir == 'right' else (x0, y_mid)
                    if flow.route:
                        _validate_route(flow.route)
                        first_rect_dir = flow.route[0].direction
                        if first_rect_dir != proc_dir:
                            raise ValueError(
                                'outlet first section direction must match process direction')
                    use_in_tri = inlet_triangles and (
                        no_triangle_names is None or flow.name not in no_triangle_names)
                    use_out_tri = outlet_triangles and (
                        no_triangle_names is None or flow.name not in no_triangle_names)
                    _draw_flow(ax, flow, width=width, inlet_triangle=use_in_tri,
                               outlet_triangle=use_out_tri, override_direction=proc_dir)
        else:
            # Ensure top/bottom border alignment by snapping flow outer edge to the border
            side = process.triangle_side or (
                'left' if triangle_side == 'auto' else triangle_side)
            if side not in ('left', 'right'):
                side = 'left'
            if side == 'left':
                outflow_stack = _stack_flows_from_right_edge(
                    process.outflows, x1, scale, gap)
            else:
                outflow_stack = _stack_flows_from_left_edge(
                    process.outflows, x0, scale, gap)
            for flow, x_mid in outflow_stack:
                width = flow.value * scale
                if outflow_filter is None or flow.name in outflow_filter:
                    if proc_dir == 'up':
                        end_x, end_y = x_mid, y1
                    else:
                        end_x, end_y = x_mid, y0
                    if flow.route:
                        _validate_route(flow.route)
                        first_rect_dir = flow.route[0].direction
                        if first_rect_dir != proc_dir:
                            raise ValueError(
                                'outlet first section direction must match process direction')
                        flow._x, flow._y = end_x, end_y
                    else:
                        flow._x, flow._y = end_x, end_y
                    use_in_tri = inlet_triangles and (
                        no_triangle_names is None or flow.name not in no_triangle_names)
                    use_out_tri = outlet_triangles and (
                        no_triangle_names is None or flow.name not in no_triangle_names)
                    _draw_flow(ax, flow, width=width, inlet_triangle=use_in_tri,
                               outlet_triangle=use_out_tri, override_direction=proc_dir)

    # Draw process on top so the shared side is visually unified
    rect_pts = [(x0, y0), (x0, y1), (x1, y1), (x1, y0)]
    ax.add_patch(Polygon(rect_pts, closed=True, facecolor=process.color,
                 edgecolor='none', linewidth=0.0, zorder=process.z))

    # Imbalance triangle (right triangle; side depends on direction)
    raw_diff = (sum_out - sum_in)
    diff = raw_diff * scale
    tri_height = abs(diff)
    if abs(diff) > 1e-9:
        eps_overlap = EPS_PROCESS_TRI
        if process.direction in ('left', 'right'):
            side = process.triangle_side or (
                'top' if triangle_side == 'auto' else triangle_side)
            if side not in ('top', 'bottom'):
                side = 'top'
            # Choose the apex corner in a horizontal process.
            # For right-facing processes, excess outflow (diff > 0) should use the right corner.
            # For left-facing processes, excess inflow (diff < 0) should use the right corner.
            use_right_corner = diff > 0 if process.direction == 'right' else diff < 0
            if side == 'top':
                if use_right_corner:
                    tri_pts = [(x0, y1 - eps_overlap), (x1, y1 -
                                                        eps_overlap), (x1, y1 + tri_height)]
                    A = (x1, y1)
                else:
                    tri_pts = [(x0, y1 - eps_overlap), (x1, y1 -
                                                        eps_overlap), (x0, y1 + tri_height)]
                    A = (x0, y1)
            else:
                if use_right_corner:
                    tri_pts = [(x0, y0 + eps_overlap), (x1, y0 +
                                                        eps_overlap), (x1, y0 - tri_height)]
                    A = (x1, y0)
                else:
                    tri_pts = [(x0, y0 + eps_overlap), (x1, y0 +
                                                        eps_overlap), (x0, y0 - tri_height)]
                    A = (x0, y0)
        else:
            side = process.triangle_side or (
                'left' if triangle_side == 'auto' else triangle_side)
            if side not in ('left', 'right'):
                side = 'left'
            flip = diff > 0
            # For up-direction: diff>0 uses top corner; for down-direction: diff>0 uses bottom corner
            use_top = (flip and process.direction == 'up') or (
                (not flip) and process.direction == 'down')
            if side == 'left':
                if use_top:
                    tri_pts = [(x0 + eps_overlap, y0),
                               (x0 + eps_overlap, y1), (x0 - tri_height, y1)]
                    A = (x0, y1)
                else:
                    tri_pts = [(x0 + eps_overlap, y0),
                               (x0 + eps_overlap, y1), (x0 - tri_height, y0)]
                    A = (x0, y0)
            else:
                if use_top:
                    tri_pts = [(x1 - eps_overlap, y0),
                               (x1 - eps_overlap, y1), (x1 + tri_height, y1)]
                    A = (x1, y1)
                else:
                    tri_pts = [(x1 - eps_overlap, y0),
                               (x1 - eps_overlap, y1), (x1 + tri_height, y0)]
                    A = (x1, y0)
        ax.add_patch(Polygon(tri_pts, closed=True, facecolor=process.color,
                     edgecolor='none', linewidth=0.0, zorder=process.z))
        # Second triangle shares the hypotenuse with the first, non-overlapping
        # Detect the right-angle vertex A from tri_pts
        eps = 1e-9
        A = None
        B = None
        C = None
        for i in range(3):
            a = tri_pts[i]
            b = tri_pts[(i + 1) % 3]
            c = tri_pts[(i + 2) % 3]
            v1 = (b[0] - a[0], b[1] - a[1])
            v2 = (c[0] - a[0], c[1] - a[1])
            if abs(v1[0] * v2[0] + v1[1] * v2[1]) < eps:
                A, B, C = a, b, c
                break
        if A is None:
            A, B, C = tri_pts[0], tri_pts[1], tri_pts[2]
        if A is None or B is None or C is None:
            # Defensive: should never happen, but avoids Optional warnings
            return None
        D = (B[0] + C[0] - A[0], B[1] + C[1] - A[1])
        tri_pts_2 = [B, C, D]
        ax.add_patch(Polygon(tri_pts_2, closed=True, facecolor=process.color,
                     edgecolor='none', linewidth=0.0, zorder=process.z, alpha=0.35))

    proc_text_kwargs = _text_kwargs(
        process_label_style, {"fontsize": 9, "color": "black"})
    label_rotation = process.label_rotation
    if label_rotation is None:
        label_rotation = proc_text_kwargs.get("rotation")
    text_args = {}
    if label_rotation is not None:
        text_args["rotation"] = label_rotation
    ax.text(
        process.x + process.label_dx,
        process.y + process.label_dy,
        process.name,
        ha=proc_text_kwargs.get("ha", "center"),
        va=proc_text_kwargs.get("va", "center"),
        zorder=process.z + 1,
        **text_args,
        **{k: v for k, v in proc_text_kwargs.items() if k not in ("ha", "va", "rotation")},
    )

    # Optional overlay rectangle (no fill, border only)
    if process.overlay:
        overlay_mag = process.overlay_height
        if overlay_mag is None:
            overlay_mag = 2.0 * (proc_flow + tri_height)
        if overlay_mag > 0:
            # Center overlay on rectangle + imbalance triangle
            center_x, center_y = process.x, process.y
            if abs(diff) > 1e-9:
                if process.direction in ('right', 'left'):
                    side = process.triangle_side or (
                        'top' if triangle_side == 'auto' else triangle_side)
                    if side not in ('top', 'bottom'):
                        side = 'top'
                    center_y = process.y + \
                        (tri_height / 2.0) if side == 'top' else process.y - \
                        (tri_height / 2.0)
                else:
                    side = process.triangle_side or (
                        'left' if triangle_side == 'auto' else triangle_side)
                    if side not in ('left', 'right'):
                        side = 'left'
                    center_x = process.x - \
                        (tri_height / 2.0) if side == 'left' else process.x + \
                        (tri_height / 2.0)
            if process.direction in ('right', 'left'):
                o_w = process.length
                o_h = overlay_mag
            else:
                o_w = overlay_mag
                o_h = process.length
            ox0 = center_x - o_w / 2.0
            ox1 = center_x + o_w / 2.0
            oy0 = center_y - o_h / 2.0
            oy1 = center_y + o_h / 2.0
            o_pts = [(ox0, oy0), (ox0, oy1), (ox1, oy1), (ox1, oy0)]
            edgecolor = process.overlay_edgecolor or process.edgecolor
            linewidth = process.overlay_linewidth if process.overlay_linewidth is not None else 0.8
            linestyle = process.overlay_linestyle if process.overlay_linestyle is not None else 'solid'
            alpha = process.overlay_alpha if process.overlay_alpha is not None else 1.0
            ax.add_patch(Polygon(o_pts, closed=True, facecolor='none',
                         edgecolor=edgecolor, linewidth=linewidth, linestyle=linestyle,
                         zorder=process.z + 2, alpha=alpha))

    # Optional triangle label (user-defined string + imbalance)
    if process.triangle_label and abs(diff) > 1e-9:
        # Place at the centroid of the opaque triangle (tri_pts_2)
        try:
            cx = sum(p[0] for p in tri_pts_2) / 3.0
            cy = sum(p[1] for p in tri_pts_2) / 3.0
        except Exception:
            cx, cy = process.x, process.y
        label = f"{process.triangle_label} {raw_diff:g}"
        tri_text_kwargs = _text_kwargs(
            triangle_label_style, {"fontsize": 8, "color": "black"})
        ax.text(
            cx + process.triangle_label_dx,
            cy + process.triangle_label_dy,
            label,
            ha=tri_text_kwargs.get("ha", "center"),
            va=tri_text_kwargs.get("va", "center"),
            zorder=process.z + 1,
            **{k: v for k, v in tri_text_kwargs.items() if k not in ("ha", "va")},
        )
    return None
