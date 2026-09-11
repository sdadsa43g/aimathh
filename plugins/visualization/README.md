# Visualization plugins

The backend emits two replaceable artifacts:

- **Plotly figure specs** (`aimathh.visualization.plots`): plain JSON the
  frontend renders. Add a builder returning `{"data": [...], "layout": {...}}`.
- **Scene graphs** (`aimathh.visualization.scene3d.Scene3D`): `surface`,
  `line3`, `arrows3` objects rendered by `apps/web/src/components/Scene3DView.tsx`.

To add a new glyph type, extend both the Python emitter and the TSX renderer
together and add a test asserting the emitted buffers match the inputs.
