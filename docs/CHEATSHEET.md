# ExergyFlow Cheatsheet

Quick reference for `DiagramConfig`, `Diagram.add_process(...)`, and `Diagram.add_flow(...)`.

## Core Concepts
- **Diagram**: container for processes and flows; supports auto-layout and auto-routing.
- **Process**: a rectangular block that can show imbalance via a right triangle.
- **Flow**: a magnitude drawn as a band (rectangles + elbows); width scales with value.

## Key Rules
- Flow routes must start/end with a `rect` and alternate `rect`/`elbow`.
- Elbows are quarter-annulus turns; thickness equals the flow width.
- Elbow turns use labels like `rightup`, `rightdown`, `leftup`, `leftdown`, `upright`, `downright`, `upleft`, `downleft` which correspond to the change in direction (e.g. rightup is an elbow that changes the flow direction from right to up).
- `label_rotation` is in degrees; for flows, vertical segments auto-rotate to 90 if `None`.
- Process directions: `right`, `left`, `up`, `down`.
- Inlet flows must end with a direction that matches the process direction.
- Outlet flows must start with a direction that matches the process direction.

### RouteSegment (for manual `route`)

| Field | Type | Notes |
| --- | --- | --- |
| `kind` | `str` | `rect` or `elbow`. |
| `length` | `float` | Rect: section length. Elbow: inner radius. |
| `direction` | `str \| None` | Required for `rect`: `right`, `left`, `up`, `down`. |
| `turn` | `str \| None` | Required for `elbow`: `rightup`, `rightdown`, `leftup`, `leftdown`, `upright`, `downright`, `upleft`, `downleft` |

Manual routes must alternate `rect`/`elbow` segments and start/end with `rect`.

## DiagramConfig
Create with `DiagramConfig(...)` and pass into `Diagram(config=...)`.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `scale` | `float` | `1.0` | Multiplies all flow magnitudes for drawing. |
| `auto_scale` | `bool` | `False` | Auto-scales flows so the largest value maps to `auto_scale_target`. |
| `auto_scale_target` | `float` | `1.0` | Target width for the largest flow when `auto_scale=True`. |
| `flow_label_mode` | `str` | `"name_value_units"` | Options: `name_value_units`, `value_units`, `value_only`. |
| `flow_value_format` | `str \| None` | `None` | Python format spec, e.g. `".2f"` or `".3g"`. |
| `flow_value_unit` | `str \| None` | `None` | Unit label appended when enabled by `flow_label_mode`. |
| `flow_value_unit_sep` | `str` | `" "` | Separator between value and unit. |
| `render_min_flow_width` | `float` | `0.0` | Minimum visible thickness for drawing only. |
| `flow_label_style` | `dict` | `{"fontsize": 8, "color": "black"}` | Matplotlib text kwargs for flow labels. |
| `process_label_style` | `dict` | `{"fontsize": 9, "color": "black"}` | Matplotlib text kwargs for process labels. |
| `triangle_label_style` | `dict` | `{"fontsize": 8, "color": "black"}` | Matplotlib text kwargs for imbalance labels. |
| `flow_gap` | `float` | `0.0` | Gap between stacked flows on a process edge. |
| `layer_gap` | `float` | `2.0` | Gap between layout layers (auto-layout). |
| `process_gap` | `float` | `1.0` | Gap between processes within a layer (auto-layout). |
| `elbow_inner_radius` | `float` | `0.5` | Inner radius for elbow turns (auto-routing). |
| `layout_direction` | `str` | `"right"` | Global layout direction: `right`, `left`, `up`, `down`. |
| `min_straight` | `float` | `0.2` | Minimum straight length between elbows (auto-routing). |

## Diagram.add_process(...)

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `name` | `str` | required | Unique process name. |
| `direction` | `str \| None` | `DiagramConfig.layout_direction` | `right`, `left`, `up`, `down`. |
| `length` | `float \| None` | `1.8` | Process length along its direction. |
| `color` | `str \| None` | `"#cfd8dc"` | Fill color. |
| `triangle_side` | `str \| None` | `None` | If direction is `right/left`: `top` or `bottom`. If `up/down`: `left` or `right`. |
| `overlay` | `bool \| None` | `False` | Draws an outline-only overlay rectangle. |
| `overlay_height` | `float \| None` | `None` | Overlay size perpendicular to process direction. |
| `overlay_edgecolor` | `str \| None` | `None` | Overlay border color. |
| `overlay_linewidth` | `float \| None` | `None` | Overlay border width. |
| `overlay_linestyle` | `str \| None` | `None` | Overlay border style. |
| `overlay_alpha` | `float \| None` | `None` | Overlay border opacity. |
| `label_dx` | `float` | `0.0` | X offset for the process label. |
| `label_dy` | `float` | `0.0` | Y offset for the process label. |
| `label_rotation` | `float \| None` | `None` | Rotation in degrees for the process label. |
| `triangle_label` | `str \| None` | `None` | Optional label prefix for imbalance triangle. |
| `triangle_label_dx` | `float` | `0.0` | X offset for triangle label. |
| `triangle_label_dy` | `float` | `0.0` | Y offset for triangle label. |
| `x` | `float \| None` | `None` | Fixed X position (skips auto-layout if set). |
| `y` | `float \| None` | `None` | Fixed Y position (skips auto-layout if set). |

## Diagram.add_flow(...)

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `name` | `str` | required | Unique flow name. |
| `value` | `float` | required | Flow magnitude (must be non‑negative). |
| `source` | `str \| None` | `None` | Source process name or `None`/`"source"`. |
| `target` | `str \| None` | `None` | Target process name or `None`/`"sink"`. |
| `color` | `str \| None` | `"#7fb3d5"` | Flow fill color. |
| `length` | `float \| None` | `2.2` | Default straight length (used when no manual route). |
| `inlet_tri_height` | `float \| None` | `0.3` | Multiplier of flow width for inlet triangle depth. |
| `outlet_tri_height` | `float \| None` | `0.6` | Multiplier of flow width for outlet triangle depth. |
| `label_dx` | `float` | `0.0` | X offset for flow label. |
| `label_dy` | `float` | `0.0` | Y offset for flow label. |
| `label_rotation` | `float \| None` | `None` | Rotation in degrees for flow label. |
| `cycle_breaker` | `bool` | `False` | Marks a process→process flow to break layout cycles. |
| `route` | `list[RouteSegment] \| None` | `None` | Manual route; skips auto-routing. |
| `label` | `str \| None` | `None` | Custom label name used in `name = value` mode. |

## Where Things Live
- `exergyflow/grassmann_types.py`: dataclasses and config
- `exergyflow/grassmann_geometry.py`: geometry helpers
- `exergyflow/grassmann_layout.py`: auto layout + routing
- `exergyflow/grassmann_render.py`: drawing engine
- `exergyflow/grassmann_diagram.py`: public API
- `examples/grassmann_example.py`: example usage
- `docs/diagram.svg`: example output (generated by the example script)
