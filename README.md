# usdAecoRepeat — repeated floors, explicit drift and measured quantities

## Use case

Copied floors gradually diverge from their prototype. This library compares
classified, typed elements across their placement offset and measures the
quantities affected by that drift. USD references keep repetition connected;
see [the worked use case](docs/usecase.md).

## The schema on an index card

| Schema | Applies to | Contract |
|---|---|---|
| `AecoRepeatAPI` | `AecoSpatialBase` | Prototype relationship, derived offset matrix, built-in `CollectionAPI:deviations` |
| `AecoQuantityAPI` | `Imageable` | Derived `aeco:qto:length`, `area`, `volume`, `count`; source, method and input hash on each quantity |

Each deviation member carries a nonblank `customData` value at
`aeco:repeat:reason`. Missing elements are declared on their prototype member.
No new typed prims, kind tokens or identities are introduced.

## The example

Pinned input: `usdaeco-datacentre` **v0.4.6**, variant **floors**. Its floors
publication is unchanged from v0.4.5, as recorded by `dc.manifest.json`.
Open [result/example.usdc](examples/datacentre/result/example.usdc) in stock USD.
It includes the complete facility, both office floors, site equipment and the
repeat overlay. Source paths and identities remain intact. The office roof is
hidden for the cutaway; amber highlights the shifted and extended partition,
and green highlights the extra door. Derived outlines make both visible.

![Facility with the office drift highlighted](examples/datacentre/result/vanilla.png)

After configuring the paths below:

```sh
env -u PYTHONPATH "$AECO_PYTHON" examples/datacentre/run.py --publish
```

Outputs: [findings](examples/datacentre/expected/findings.json),
[manifest](examples/datacentre/manifest.json), [L01 plan](examples/datacentre/renders/l01.png)
and [L02 plan](examples/datacentre/renders/l02.png). The separate
[reference reconstruction](examples/datacentre/result/layers/out/composition)
preserves the occurrence identities while using prototype child names; its
path map, matching pairs and quantity schedules are in transient `out/`.
The full facility result keeps the source's original occurrence names.

| Observation | Measured result |
|---|---:|
| Matched element pairs | 28 |
| Partition change | 1 m shift and 3.2 m extension; reported as `changed` |
| Extra door / declared deviations | 1 / 0 |
| Partition length L01 / L02 | 43.0 / 46.2 m |
| Un-keyed minus prototype-repeated partition length | +3.2 m |
| Un-keyed minus prototype-repeated door count | +1 |
| Reference reconstruction | 71 prims, 944 mesh vertices, maximum error 8.89e-16 |
| Differing / occurrence / addition layer lines | 267 / 686 / 50 |

The quantity methods and geometric limits are documented in
[the use case](docs/usecase.md). Plan figures are measured bounding footprints;
they simplify openings and are not construction drawings.

The source export’s prototype hint is published as `aeco:props:DC_Repeat:Prototype`, preserving its value. USD cannot rename a weaker-layer property through an overlay, so this metadata migration runs on the flattened crate and archived own layers. Source files remain unchanged.

## Build and check

Use Python with OpenUSD, numpy, pytest and the family toolchain available.
No package installation is needed. Point these variables at your environment
and checkouts (use the exact checked pins below, including data v0.4.6):

```sh
export AECO_PYTHON="$(command -v python)"
export PYTHON="$AECO_PYTHON"
export TOOLCHAIN_DIR="$(cd ../usdaeco-toolchain && pwd)"
export CORE_DIR="$(cd ../usdaeco-core && pwd)"
export AXIS_DIR="$(cd ../usdaeco-axis && pwd)"
export BUILDUP_DIR="$(cd ../usdaeco-buildup && pwd)"
export AECO_DATACENTRE_ROOT="$(cd ../usdaeco-datacentre && pwd)"
export CORE_PLUGIN_DIR="$CORE_DIR/usdAeco"
export AXIS_PLUGIN_DIR="$AXIS_DIR/usdAecoAxis"
export BUILDUP_PLUGIN_DIR="$BUILDUP_DIR/usdAecoBuildUp"
export PXR_PLUGINPATH_NAME="$CORE_PLUGIN_DIR:$AXIS_PLUGIN_DIR:$BUILDUP_PLUGIN_DIR:$PWD/usdAecoRepeat"
bash build.sh
env -u PYTHONPATH PYTHONPATH="$CORE_DIR:$PWD" "$AECO_PYTHON" check.py
env -u PYTHONPATH "$AECO_PYTHON" -m pytest -q
nix flake check
```

`usdrecord` must be on `PATH` for the example gates. The gate fails loudly if
`usdAecoValidators` cannot import, lists all eight core validators and all three
local validators, and prints the family `N checks, M failed` summary. Expected
seeded drift errors are compared with committed findings; they do not imply a
clean architectural design.

The source CLI needs no installed entry point:

```sh
export FLOOR='/demo_datacentre_01/demo_datacentre_01_Site/demo_datacentre_01/L02_Office'
env -u PYTHONPATH "$AECO_PYTHON" tools/usdaeco_repeat/cli.py diff examples/datacentre/out/composition/composed.usda --instance "$FLOOR"
env -u PYTHONPATH "$AECO_PYTHON" tools/usdaeco_repeat/cli.py takeoff examples/datacentre/out/composition/composed.usda --by-level
env -u PYTHONPATH "$AECO_PYTHON" tools/usdaeco_repeat/cli.py takeoff examples/datacentre/out/composition/composed.usda --repeat-resolved
env -u PYTHONPATH "$AECO_PYTHON" tools/usdaeco_repeat/cli.py compose examples/datacentre/out/composition/composed.usda --instance "$FLOOR" --output out/recomposed
```

Installed packaging also exposes `aeco-repeat`. `takeoff --derived-layer FILE`
writes a quantity layer without changing the input. Use `--level PATH` repeatedly
to restrict a schedule. Without `--by-level`, rows are grouped across levels.

Flake inputs use public release refs. For local source resolution use
`nix flake check --override-input core path:"$CORE_DIR"` and corresponding
`axis`, `buildup`, `toolchain` and `datacentre` overrides, or an external registry
as described in the toolchain's `docs/repo-conventions.md`. Keep deployment
addresses and private lockfiles outside this repository.

## Family

| Dependency | Supported range | Checked pin |
|---|---|---|
| `usdAeco` | `>=0.9.2,<1.0` | v0.9.2 |
| `usdAecoBuildUp` | `>=0.2,<0.3` | v0.2.1 |
| `usdAecoAxis` | `>=0.1,<0.2` | v0.1.2 |
| Toolchain | `>=0.3.8,<0.4` | v0.3.8 |
| Data centre | Example input | v0.4.6 |

[Family board](https://github.com/criad-com/usdaeco-board) ·
[pin record](dependencies.json) · [version contract](library.json).
OpenUSD supplies composition and rendering; numpy is used by the shared
renderer. Their respective licences remain in force.

## Layout

`usdAecoRepeat/` is the codeless schema and user documentation;
`usdAecoRepeatValidators/` is the Python UsdValidation plugin;
`tools/usdaeco_repeat/` contains the tools; `testenv/` holds defect drills;
`examples/datacentre/` contains the reproducible study and committed result.
Build output installation is separate from the source schema directory.

## Status

v0.2.0: **44 checks, 0 failed, 0 not run; structure 29/0; 18 pytest tests passed**.
Both source-layout reproductions pass `ResultStale`. The standalone result has
12,342 prims and occupies 3,005,236 bytes across 17 files. The example and
schema are tested against the exact pins above.
The gate proves that all 12,337 source prims remain, with unchanged source
identities, meshes and world placement. Core validation retains the source's
two proxy-classification warnings and adds no errors or warnings. Exactly two
undeclared `RepeatDrift` findings remain; quantity stamps are current.

Final gate, test and relocation measurements are recorded in the
[changelog](CHANGELOG.md#020). Nix is not proven; its single offline attempt
and the remaining limits are recorded there. Static, non-instanced mesh floors,
lines and circular arcs are supported. Exact solids, joins, cost and approval
of deviations remain outside scope.

## Licence

MIT. See [LICENSE](LICENSE). OpenUSD and the Python runtime dependencies retain
their own licences; no dependency source is bundled.
