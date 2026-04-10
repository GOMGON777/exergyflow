"""
Low-level geometry helpers for Grassmann/Sankey-like diagrams.

Includes rectangle/taper polygons, elbows, and route helpers.
See README.md for the full spec.
"""

from typing import List, Tuple
from matplotlib.patches import Wedge
from .grassmann_types import RouteSegment

# Geometry helpers
# -----------------------------
# Geometry helpers
# -----------------------------


def rect_poly(x0, y0, length, width, direction):
    """Return polygon points for a rectangle section and its end point."""
    w = width
    if direction == 'right':
        return [(x0, y0 - w / 2), (x0, y0 + w / 2), (x0 + length, y0 + w / 2), (x0 + length, y0 - w / 2)], (x0 + length, y0)
    if direction == 'left':
        return [(x0, y0 - w / 2), (x0, y0 + w / 2), (x0 - length, y0 + w / 2), (x0 - length, y0 - w / 2)], (x0 - length, y0)
    if direction == 'up':
        return [(x0 - w / 2, y0), (x0 + w / 2, y0), (x0 + w / 2, y0 + length), (x0 - w / 2, y0 + length)], (x0, y0 + length)
    if direction == 'down':
        return [(x0 - w / 2, y0), (x0 + w / 2, y0), (x0 + w / 2, y0 - length), (x0 - w / 2, y0 - length)], (x0, y0 - length)
    raise ValueError(f'Unknown direction: {direction}')


def _elbow_end(x0, y0, r_c, direction, turn):
    """Return end point of a quarter-turn arc on the centerline."""
    if direction == 'right' and turn == 'up':
        return (x0 + r_c, y0 + r_c)
    if direction == 'right' and turn == 'down':
        return (x0 + r_c, y0 - r_c)
    if direction == 'left' and turn == 'up':
        return (x0 - r_c, y0 + r_c)
    if direction == 'left' and turn == 'down':
        return (x0 - r_c, y0 - r_c)
    if direction == 'up' and turn == 'right':
        return (x0 + r_c, y0 + r_c)
    if direction == 'up' and turn == 'left':
        return (x0 - r_c, y0 + r_c)
    if direction == 'down' and turn == 'right':
        return (x0 + r_c, y0 - r_c)
    if direction == 'down' and turn == 'left':
        return (x0 - r_c, y0 - r_c)
    raise ValueError(f'Unsupported elbow: {direction} -> {turn}')


def elbow_wedge(x0, y0, inner_radius, width, direction, turn):
    """Return elbow wedge and end point with outer edge aligned to rectangle outer edge."""
    r_c = inner_radius + width / 2.0
    if direction == 'right' and turn == 'up':
        center = (x0, y0 + r_c)
    elif direction == 'right' and turn == 'down':
        center = (x0, y0 - r_c)
    elif direction == 'left' and turn == 'up':
        center = (x0, y0 + r_c)
    elif direction == 'left' and turn == 'down':
        center = (x0, y0 - r_c)
    elif direction == 'up' and turn == 'right':
        center = (x0 + r_c, y0)
    elif direction == 'up' and turn == 'left':
        center = (x0 - r_c, y0)
    elif direction == 'down' and turn == 'right':
        center = (x0 + r_c, y0)
    elif direction == 'down' and turn == 'left':
        center = (x0 - r_c, y0)
    else:
        raise ValueError(f'Unsupported elbow: {direction} -> {turn}')

    end = _elbow_end(x0, y0, r_c, direction, turn)
    # Compute wedge angles from start/end points on the centerline arc
    import math
    ang0 = math.degrees(math.atan2(y0 - center[1], x0 - center[0])) % 360
    ang1 = math.degrees(math.atan2(
        end[1] - center[1], end[0] - center[0])) % 360
    ccw = (ang1 - ang0) % 360
    if ccw > 180:
        ang0, ang1 = ang1, ang0
    wedge = Wedge(center, r=inner_radius + width, theta1=ang0, theta2=ang1,
                  width=width, facecolor='none', edgecolor='black')
    return wedge, end, center, ang0, ang1


def elbow_wedge_from_type(x0, y0, inner_radius, width, turn_type, current_dir):
    """Resolve elbow type and direction into a wedge, end point, and new direction."""
    change_to_elbow = {
        'rightup': 'rightdown',
        'rightdown': 'rightup',
        'leftup': 'leftdown',
        'leftdown': 'leftup',
        'upright': 'leftup',
        'upleft': 'rightup',
        'downright': 'leftdown',
        'downleft': 'rightdown',
        # common typos / aliases
        'lefttup': 'leftup',
        'lefttdown': 'leftdown',
    }
    turn_type = change_to_elbow.get(turn_type, turn_type)
    # Elbow type is defined by annulus quadrant, allowing two incoming directions
    if turn_type == 'rightup':
        if current_dir == 'right':
            out_dir = 'down'
        elif current_dir == 'up':
            out_dir = 'left'
        else:
            raise ValueError('rightup elbow requires current_dir right or up')
    elif turn_type == 'rightdown':
        if current_dir == 'right':
            out_dir = 'up'
        elif current_dir == 'down':
            out_dir = 'left'
        else:
            raise ValueError(
                'rightdown elbow requires current_dir right or down')
    elif turn_type == 'leftup':
        if current_dir == 'left':
            out_dir = 'down'
        elif current_dir == 'up':
            out_dir = 'right'
        else:
            raise ValueError('leftup elbow requires current_dir left or up')
    elif turn_type == 'leftdown':
        if current_dir == 'left':
            out_dir = 'up'
        elif current_dir == 'down':
            out_dir = 'right'
        else:
            raise ValueError(
                'leftdown elbow requires current_dir left or down')
    else:
        raise ValueError(f'Unknown elbow type: {turn_type}')

    wedge, end, center, ang0, ang1 = elbow_wedge(
        x0, y0, inner_radius, width, current_dir, out_dir)
    return wedge, end, out_dir, center, ang0, ang1


def _dir_vec(direction: str, length: float):
    """Convert a direction and length to a delta vector."""
    if direction == 'right':
        return (length, 0.0)
    if direction == 'left':
        return (-length, 0.0)
    if direction == 'up':
        return (0.0, length)
    if direction == 'down':
        return (0.0, -length)
    raise ValueError(f'Unknown direction: {direction}')


def _turn_type_from_dirs(current_dir: str, out_dir: str) -> str:
    """Map a direction change to a change-label (e.g., rightup, upright)."""
    if current_dir not in ('right', 'left', 'up', 'down') or out_dir not in ('right', 'left', 'up', 'down'):
        raise ValueError(
            f'Unsupported turn from {current_dir} to {out_dir}')
    return f'{current_dir}{out_dir}'


def _is_horizontal(direction: str) -> bool:
    return direction in ('left', 'right')


def _is_vertical(direction: str) -> bool:
    return direction in ('up', 'down')


def _is_opposite(a: str, b: str) -> bool:
    return (a == 'left' and b == 'right') or (a == 'right' and b == 'left') or (a == 'up' and b == 'down') or (a == 'down' and b == 'up')


def _route_displacement(route: List["RouteSegment"], width: float) -> Tuple[float, float]:
    """Compute total displacement of a routed flow (sections + elbows)."""
    dx = 0.0
    dy = 0.0
    current_dir = None
    for seg in route:
        if seg.kind == 'rect':
            if seg.direction is None:
                raise ValueError('rect segment requires direction')
            vx, vy = _dir_vec(seg.direction, seg.length)
            dx += vx
            dy += vy
            current_dir = seg.direction
        elif seg.kind == 'elbow':
            if seg.turn is None or current_dir is None:
                raise ValueError(
                    'elbow segment requires turn and a previous direction')
            _, end, current_dir, _, _, _ = elbow_wedge_from_type(
                0.0, 0.0, seg.length, width, seg.turn, current_dir)
            dx += end[0]
            dy += end[1]
        else:
            raise ValueError(f'Unknown segment kind: {seg.kind}')
    return dx, dy


def _validate_route(route: List["RouteSegment"]):
    """Validate route alternation and endpoints (rect/elbow/rect...)."""
    if not route:
        return
    if route[0].kind != 'rect' or route[-1].kind != 'rect':
        raise ValueError('route must start and end with rect')
    for i, seg in enumerate(route):
        if i % 2 == 0 and seg.kind != 'rect':
            raise ValueError(
                'route must alternate rect/elbow, starting with rect')
        if i % 2 == 1 and seg.kind != 'elbow':
            raise ValueError('route must alternate rect/elbow')
