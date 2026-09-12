# Changelog

## 0.2.1

- public re-pin: usdaeco-toolchain v0.3.10, usdaeco-core v0.9.5,
  usdaeco-axis v0.1.5, usdaeco-buildup v0.2.5, usdaeco-datacentre v0.4.8.
  Record each tagged revision separately from its public release ref;
  supported requirement ranges are unchanged.
- Advance the library, Python package and generated plugin metadata to v0.2.1.
- Rebuild the schema and republish through the documented example runner.
  The flattened crate, all 14 archived USD layers, source hashes and expected
  findings remain byte-identical. Only the result notice's source tag and
  manifest provenance change; 16 of 17 result files retain their bytes.
- Verify 44 checks, 0 failed, 0 not run; all 29 structure rules under toolchain
  v0.3.10; 18 pytest tests; eight core and three repeat validators loaded.
  The fresh example passes ResultStale in 26.331 s against its 180 s budget.
  Preserve all 12,337 source prims, 9,248 identities and 3,022 meshes with zero
  world-placement error. The result remains 12,342 prims and 3,005,236 bytes.
- Upstream data-centre 0.4.7/0.4.8 retain all published stage bytes; core
  0.9.3–0.9.5 retain the schema contract. Toolchain 0.3.10 changes tag checking
  and pins while retaining its USD output. No geometry behavior change is
  observed. Supported schema and Python requirement ranges remain unchanged.

### Deviations

- Fresh Embree samples change PNG bytes slightly. All four fresh 1280×800
  renders pass; retain the committed images and their hashes under S28.
  Mean absolute RGB channel differences on the 0–255 scale are 0.110593
  (L01), 0.110087 (L02), 0.048515 (overview) and 0.049168 (vanilla).
- Nix is not proven: one offline attempt with nine local source overrides
  exited 1 before evaluation. The temporary v0.4.0 kit clone was shallow and
  its Git override omitted Nix's required shallow flag. This was an override
  setup error; no package evaluation or build pass is claimed and no retry
  was made. The kit tag was found under the library forge owner after the
  documented kit-owner lookup failed. No lockfile is committed.
- Public tag availability follows the supplied release table. Independent
  online resolution, review, merge and release tagging remain pending.

## 0.2.0

- Renamed from usdaeco-typical: usdAecoRepeat, AecoRepeatAPI, aeco:repeat,
  usdAecoRepeatValidators, aeco-repeat and usdaeco_repeat. AecoQuantityAPI
  and aeco:qto remain unchanged.
- Public names → github.com/criad-com; pin toolchain v0.3.8 and datacentre
  v0.4.6. Its floors publication is byte-identical to v0.4.5. Other pins stay
  core v0.9.2, axis v0.1.2 and buildup v0.2.1.
- Preserve the full floors variant in the standalone result; show the office
  drift in facility context and retain the separate floor-plan studies.
- Retain all 12,337 source prims, 9,248 identities and 3,022 meshes with zero
  world-placement error. The result contains 12,342 prims and 3,005,236 bytes
  across 17 files. The 1280×800 vanilla render shows the complete facility;
  presentation hides only the office roof and adds three derived outlines.
- Keep 28 matched pairs, one shifted/extended partition and one extra door,
  with +3.2 m of partition and +1 door. Reconstruction verifies 71 prims and
  944 vertices through one reference, maximum error 8.89e-16. Its layers have
  267 differing, 686 occurrence and 50 addition lines.
- Verify 44 checks, 0 failed, 0 not run; all 29 structure rules under toolchain
  v0.3.8; 18 pytest tests; eight core and three local validators loaded. Both
  source layouts pass ResultStale, including relocation of the source and
  consumer into unrelated directories. Fresh runs take 30.080 / 30.357 s
  against the 180 s budget. S29 verifies all eight archived asset paths.
- The public-name sweep is clean in text, filenames and flattened crate data,
  apart from the rename notice above. No source checkout is modified.

### Deviations

- The moved and lengthened partition retains the existing `changed` category,
  rather than `moved` (which denotes equal shape with displacement). The
  quantities and two findings are unchanged. The drift site now names the
  original occurrence, because the facility result preserves source paths.
- The reference reconstruction remains a separate study to avoid duplicate
  identities from prototype-named children. The facility composes the complete
  source with repeat registration, quantity stamps and presentation overlays.
- One exported prototype-hint property is normalized to
  `aeco:props:DC_Repeat:Prototype` in the crate and archived own layer. Its value
  is preserved; USD overlays cannot rename weaker-layer properties.
- The full source has two `proxyClassified` utility-intake warnings. Both are
  reported and checked against the source baseline; core errors and added
  warnings remain zero. Neither local drift finding is silently approved.
- Nix is not proven: the single offline check with exact local overrides stopped
  before evaluation because an override traversed a filesystem symlink. No Nix
  package or build pass is claimed; no second attempt was made.

## 0.1.1

- Re-pin to train aeco-0.7.0: core v0.9.2, axis v0.1.2, buildup v0.2.1,
  toolchain v0.3.5 and datacentre v0.4.5; retain supported requirement ranges.
- Refresh the stale example result, plans, manifest and expected findings for
  the datacentre v0.4.5 floor corrections. The unchanged comparison reports
  one changed partition (shifted and extended) and one extra door, with zero
  declared deviations; partition lengths are 43.0 / 46.2 m, a +3.2 m delta.
  Update the two data-specific gate assertions to these measured expectations.
- Reproduce L02 through one reference across 71 prims and 944 mesh vertices
  within 8.89e-16 stage units; differing, occurrence and addition layers contain
  267, 686 and 50 lines. The standalone result has 261 prims / 557,234 bytes
  across its 13 files. Schema and tool algorithms are unchanged.
- Verify 42 checks, 0 failed, 0 not run; all 28 structure rules under toolchain
  v0.3.5; 15 pytest tests; eight core and three local validators loaded, with
  zero core errors or warnings and exactly two expected drift errors.
- Nix remains not proven: the single offline check with all five direct source
  overrides stopped at the nested axis/datacentre v0.4.2 input with outbound
  connections disabled. No package evaluation or build pass is claimed.

## 0.1.0

- Add codeless AecoRepeatAPI and AecoQuantityAPI with registered Python validators.
- Compare repeated containers by classification, type, shape and placement.
- Measure keyed and un-keyed quantities from axes, build-ups and mesh bodies.
- Reconstruct an occurrence through a prototype reference and explicit differing
  opinions, preserving occurrence identity and reporting path changes.
- Publish the pinned floors example, plans, quantity schedule and standalone USD.
- Record the source's additional drift, zero net partition-length delta and
  complete reconstruction layer lengths instead of assuming design values.
