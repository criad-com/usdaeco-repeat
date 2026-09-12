# Repeated office floors in the full facility

Open `result/example.usdc` in stock USD. It contains the complete pinned floors
variant plus repeat registration, quantity stamps and presentation. The office
roof is hidden to reveal the changed partition (amber) and extra door (green).
Source prims, identities, meshes and world placements are preserved.

Configure the checkout variables in the root README, then run:

```sh
env -u PYTHONPATH "$AECO_PYTHON" examples/datacentre/run.py --publish
```

`AECO_DATACENTRE_ROOT` must select v0.4.8; its floors publication is unchanged
from v0.4.5. The harness creates the ignored `inputs/source` symlink to that
checkout. Archived source references stay inside the example via this alias
(S29); recreate it by running the example before opening individual archived
layers. The flattened crate needs neither the alias nor any family plugin.
Ordinary runs write `out/`; `--publish` refreshes result, renders and manifest.

`inputs/generate.py` regenerates the small overlays without modifying the source.
`repeat.usda` declares L02's prototype. `sections.usda` supplies homogeneous
wall widths. `cameras.usda` frames the facility; `studies/cameras.usda` frames
the two separate plans. `result/layers/out/context.usda` retains the source;
`quantities.usda` and `presentation.usda` carry the derived opinions.

`out/diff.json` records 28 matching pairs, one changed partition (1 m shift and
3.2 m extension) and one extra door. Quantities differ by +1 door and +3.2 m
of partition. Neither change is declared approved. The standalone reference
reconstruction and plan representations remain in `result/layers/out/`;
`renders/l01.png` and `renders/l02.png` show those studies.

`result/vanilla.png` renders the relocated full crate with all family plugins
and Python search paths removed. Renders are at most 1600 pixels per dimension
and 400 KB each. The result inventory, source hashes and manifest-derived census
are checked along with the expected findings.

The source export’s prototype hint is published as `aeco:props:DC_Repeat:Prototype`, preserving its value. USD cannot rename a weaker-layer property through an overlay, so this metadata migration runs on the flattened crate and archived own layers. Source files remain unchanged.
