"""
Example script for the Grassmann/Sankey-like diagram generator.
"""

from pathlib import Path

from exergyflow import Diagram, DiagramConfig, RouteSegment
import matplotlib.pyplot as plt

# -----------------------------
# Advanced example usage
# -----------------------------

# Example: Branch then merge
cfg = DiagramConfig(auto_scale=True, auto_scale_target=2.0,
                    flow_label_mode='value_only', render_min_flow_width=0.015, triangle_label_style={'fontsize': 5}, flow_label_style={'fontsize': 6})
d = Diagram(cfg)
d.add_process('A', color="#f46924", overlay=True,
              overlay_linestyle='dashed', overlay_height=3.0, length=1.25, triangle_label='I =', triangle_label_dx=-0.2, triangle_label_dy=0.5)
d.add_process('B', color="#f46924", overlay=True,
              overlay_linestyle='dashed', length=0.75, triangle_label='I =', triangle_label_dx=-0.11, triangle_label_dy=0.15)
d.add_process('C', color="#f46924", overlay=True,
              overlay_linestyle='dashed', length=0.75, overlay_height=1.0, label_dy=-0.2, triangle_label='I =', triangle_label_dx=-0.11, triangle_label_dy=0.1)
d.add_process('D', color="#f46924", overlay=True,
              overlay_linestyle='dashed', length=0.75, overlay_height=1.0, triangle_label='I =', triangle_label_dx=-0.11, triangle_label_dy=0.1)
d.add_process('E', direction='down', color="#f46924", overlay=True,
              overlay_linestyle='dashed', length=0.5, overlay_height=1.0, triangle_label='I =', triangle_label_dx=-0.32, triangle_label_dy=0.42)
d.add_process('F', direction='down', color="#f46924", overlay=True,
              overlay_linestyle='dashed', length=0.75, overlay_height=1.5, triangle_label='I =', triangle_label_dx=-0.3, triangle_label_dy=-0.45)
d.add_process('G', direction='left', color="#f46924",
              overlay=True, overlay_linestyle='dashed', length=0.5, overlay_height=1.0, label_dy=-0.17, triangle_label='I =', triangle_label_dx=-0.62, triangle_label_dy=0.1)
d.add_flow('g', 890, source='G', target='A',
           color='#f46924', cycle_breaker=True, label_dx=-0.15)
d.add_flow('a', 42130, source=None, target='A',
           color="#f46924", label_dx=0.1)
d.add_flow('b', 16470, source='A', target='B', length=1.0, color='#f46924')
d.add_flow('f', 8400, source='B', target='F', route=[
    RouteSegment(kind='rect', length=0.75, direction='right'),
    RouteSegment(kind='elbow', length=0.5, turn='rightdown'),
    RouteSegment(kind='rect', length=0.75, direction='down')
], color="#f46924", label_dy=-0.8, label_dx=1.08, label_rotation=90)
d.add_flow('c', 1530, source='B', target='C',
           length=1.7, color='#f46924', label_dx=0.55, label_dy=0.1)
d.add_flow('e', 198, source='C', target='E', route=[
    RouteSegment(kind='rect', length=0.25, direction='right'),
    RouteSegment(kind='elbow', length=0.25, turn='rightdown'),
    RouteSegment(kind='rect', length=0.75, direction='down')
], color='#f46924', label_dy=0.15)
d.add_flow('cc', 961, source='C', target='D',
           color='#f46924', label_dx=0.5, label_dy=0.0)
d.add_flow('d', 5290, source='B', target='D', route=[
    RouteSegment(kind='rect', length=0.75, direction='right'),
    RouteSegment(kind='elbow', length=0.25, turn='rightup'),
    RouteSegment(kind='rect', length=0.5, direction='up'),
    RouteSegment(kind='elbow', length=0.25, turn='upright'),
    RouteSegment(kind='rect', length=1.0, direction='right'),
    RouteSegment(kind='elbow', length=0.25, turn='rightdown'),
    RouteSegment(kind='rect', length=0.1, direction='down'),
    RouteSegment(kind='elbow', length=0.25, turn='downright'),
    RouteSegment(kind='rect', length=0.1, direction='right'),
], color='#f46924')
d.add_flow('dd', 6000, source='D', target=None,
           length=0.7, color='#f46924')
d.add_flow('g1', 3, source='E', target='G', color='#f46924', label_dx=1.0)
d.add_flow('f2', 6955, source='F', target=None, route=[
    RouteSegment(kind='rect', length=0.75, direction='down'),
    RouteSegment(kind='elbow', length=0.25, turn='downright'),
    RouteSegment(kind='rect', length=0.25, direction='right'),
    RouteSegment(kind='elbow', length=0.25, turn='rightdown'),
    RouteSegment(kind='rect', length=0.25, direction='down')
], color='#f46924')
d.add_flow('g2', 986, source='F', target='G', route=[
    RouteSegment(kind='rect', length=2.0, direction='down'),
    RouteSegment(kind='elbow', length=0.25, turn='downleft'),
    RouteSegment(kind='rect', length=1.5, direction='left')
], color='#f46924', label_dy=-0.5, label_dx=-0.15)
fig, ax = d.draw()
output_path = Path(__file__).resolve().parents[1] / "docs" / "diagram.svg"
output_path.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(output_path, dpi=300, bbox_inches="tight")
plt.show()
