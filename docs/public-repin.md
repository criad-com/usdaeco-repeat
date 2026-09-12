# Public re-pin verification

Release v0.2.1 uses toolchain v0.3.10, core v0.9.5, axis v0.1.5,
build-up v0.2.5 and data-centre v0.4.8. All five flake inputs use public
release tags. [dependencies.json](../dependencies.json) records each peeled
source revision checked against the forge tag and the clean sibling checkout.
Those revisions are provenance; public orphan trees have different commits.
The three schema requirement ranges and Python toolchain range are unchanged.

Build and validation used Python 3.13 and OpenUSD 26.8 from source, without
installing this package. Committed source plugin directories supply the exact
versions; the siblings' older generated installation directories were not used.
Core was explicitly importable and all eight validators loaded through
UsdValidation. No sibling checkout was changed.

| Acceptance | Measured result |
|---|---|
| Direct family pins | 5/5 target tags with checked revisions |
| Package version | 0.2.1 in library, Python project, source package and plugin |
| Family gate | 44 checks, 0 failed, 0 not run |
| Structure | 29/29 pass, including S05 tag and version checks |
| Source pytest | 18 passed |
| Registry | 8 core and 3 repeat validators loaded |
| Published result | 12,342 prims; 3,005,236 bytes across 17 files |
| Source preservation | 12,337 prims; 9,248 identities; 3,022 meshes; zero placement error |
| Core conformance | 0 errors; 2 existing source warnings; 0 added warnings |
| Repeat findings | 2 expected undeclared drift errors; 0 stale quantities |
| Result freshness | 26.331 s against the 180 s budget; ResultStale passes |
| Byte comparison | Crate and 14 archived USD layers unchanged; 16/17 result files identical |
| Findings and source | Expected findings, 3 source-layer hashes and source-manifest hash unchanged |
| Rendering | 4 fresh 1280×800 renders; committed image bytes retained |
| Sanitization | Publication sweep: 68 files, 0 findings; 0 obsolete public-owner refs |
| Whitespace | `git diff --check` clean |
| Nix | 1 offline attempt; exit 1 before evaluation; builds not proven |

The documented `bash build.sh` and `examples/datacentre/run.py --publish`
commands regenerated the schema, result, manifest and images. The source and
generated schema remain byte-identical to v0.2.0; plugin metadata advances its
version. The publication's only changed result file is the source-tag notice.
Its manifest changes only dependency tags/revisions, the data-centre tag and
the notice hash. Geometry, placement, identities, quantities and layers are
unchanged. The [machine-readable receipt](public-repin.json) records source
pins, gate measurements and hashes from the fresh image comparison.

Upstream data-centre CHANGELOG 0.4.7/0.4.8 explicitly retains published stage
bytes. Core 0.9.3–0.9.5 retains its schema contract; axis 0.1.2–0.1.5 and
build-up 0.2.2–0.2.5 change their own example provenance and packaging without
changing the consumed schema properties. Toolchain 0.3.10 changes tag checks
and pins while retaining its USD output. No geometry behavior change is
observed in this consumer.

## Deviations

- Fresh Embree samples differ from committed PNGs. Mean absolute RGB channel
  differences on the 0–255 scale are 0.110593 (L01), 0.110087 (L02), 0.048515
  (overview) and 0.049168 (vanilla). Keep the committed images after fresh-render
  verification, as S28 permits, to limit the final result diff to provenance.
- The single `nix flake check --offline --no-write-lock-file` attempt used nine
  local overrides: the five target siblings, the core and axis data inputs,
  an exported core v0.9.2 fixture, and an isolated kit v0.4.0 clone. The kit
  tag was available under the library forge owner after the documented
  kit-owner lookup failed. The attempt exited 1 because the kit clone was
  shallow and its Git override omitted Nix's required shallow flag. This
  setup error stopped evaluation; no builds or online resolution are proven.
  No retry was made and no lockfile is committed.
- Public tag availability follows the supplied release table. Independent
  online resolution, review, merge and release tagging remain pending. The
  earlier v0.2.0 relocation measurements remain historical evidence; this
  release verifies the current pinned run and the gate's plugin-free relocation.
