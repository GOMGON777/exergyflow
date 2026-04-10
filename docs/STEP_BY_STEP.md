# Step-by-Step: Build a Grassmann/Sankey Diagram

This guide walks you through creating a diagram from scratch using the public API.

**Step 1: Install dependencies**
```bash
python -m pip install exergyflow
```

**Step 2: Import the API**
```python
from exergyflow import Diagram, DiagramConfig, RouteSegment
```

**Step 3: Define a configuration (optional but recommended)**
```python
cfg = DiagramConfig(
    auto_scale=True,
    auto_scale_target=1.0,
    flow_value_unit="kW",
    flow_value_format=".2f",
    flow_label_style={"fontsize": 8, "color": "#1d3557"},
    process_label_style={"fontsize": 9, "fontweight": "bold"},
    triangle_label_style={"fontsize": 8, "color": "#444444"},
)
```

**Step 4: Create the diagram and add processes**
```python
d = Diagram(config=cfg)

d.add_process("P1", direction="right", length=1.6)
d.add_process("P2", direction="right", length=1.2)
```

**Step 5: Add flows**
Use `source=None` for a source and `target=None` for a sink.
```python
d.add_flow("F1", 10, source=None, target="P1")
d.add_flow("F2", 8, source="P1", target="P2", label="Q_in")
d.add_flow("F3", 2, source="P1", target=None)
d.add_flow("F4", 6, source="P2", target=None)
```

**Step 6: (Optional) Add a manual route**
Manual routes must alternate `rect` and `elbow`, and start/end with `rect`.
```python
route = [
    RouteSegment(kind="rect", length=1.5, direction="right"),
    RouteSegment(kind="elbow", length=0.4, turn="rightup"),
    RouteSegment(kind="rect", length=1.0, direction="up"),
]

d.add_flow("F5", 3, source="P1", target="P2", route=route)
```

**Step 7: Draw and save**
```python
fig, ax = d.draw()
fig.savefig("diagram.png", dpi=300, bbox_inches="tight")
```
