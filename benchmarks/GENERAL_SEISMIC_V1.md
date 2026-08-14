# General Seismic Benchmark v1

This benchmark is frozen before headline compression results are inspected. Its purpose is to test generalization across large, independent real seismic surveys rather than small favorable patches.

## Primary rules

- Public hard-error contract: `epsilon = 0.10 * global_std` of the selected numeric seismic payload for each survey benchmark unit.
- Every reconstructed sample must satisfy `abs(x - xhat) <= epsilon`.
- No primary test unit may be smaller than 5 GB. Datasets <=25 GB are tested in full. Larger datasets use three deterministic complete-file spans of at least 10 GB each, centered near 10%, 50%, and 90% of cumulative seismic bytes.
- Span selection is based only on canonical object/path order and byte size. Compression results, signal statistics, visual inspection, event labels, or the discovered hardness score cannot affect selection.
- Each independent survey counts once in the headline survey-level statistics, preventing a 100 TB archive from overwhelming a 6 GB survey.
- Report survey win rate, median baseline/ours gain, bootstrap 95% CI for the median, 10th percentile gain, and a separate byte-weighted aggregate.
- Primary comparison is matched SZ3 under the identical error contract. Additional matched competitors should be reported where executable and auditable (e.g. HPEZ/general scientific codecs and DAS-specific codecs for DAS cohorts).
- Codec-specific models, selectors, framing, dictionaries, and side information are charged. Shared file/container metadata excluded from the lossy amplitude benchmark must be excluded identically for every codec.
- The codec architecture and global hyperparameter menu are frozen before headline test results are inspected. Decoder-reproducible per-dataset fitting remains legal only when all required information is transmitted/charged or derived from already decoded data.

## Frozen v1 cohort

### Land seismic

1. Soda Lake 2010 raw 3D/3C reflection — 171.04 GB public SEG-Y.
2. Stratton 3D South Texas — ~6 GB prestack gathers, tested complete.
3. WHOLESCALE San Emidio 2021 — 466 GB raw nodal seismic (353 GB SmartSolo + 113 GB DataCube).
4. Crescent Valley 2016 — 469.57 GB public SEGD archive.

### Marine seismic

5. Waka 3D — 24 GB, complete volume.
6. Parihaka 3D — four 4.7 GB PSTM angle-stack volumes, 18.8 GB total, all four tested.
7. Opunake 3D — 10 GB, complete volume.
8. Penobscot 3D prestack — 101 GB.
9. BP 2010 Tiber WATS decimated raw small-area dataset — 130 GB.

### DAS

10. Imperial Valley Dark Fiber continuous DAS — 1.09 TB.
11. PoroTomo/Brady horizontal DAS raw SEG-Y — 46.4 TB.
12. Utah FORGE Neubrex well 16B continuous DAS, April 2024 — 97.48 TB.
13. EGS Collab Experiment 2 DAS — 212.2 TB.

The source paths and machine-readable selection policies are in `general_seismic_v1.json`.

## Interpretation thresholds fixed in advance

- General win: ours beats the strongest matched baseline on >=80% of independent surveys.
- Significant general win: median gain >=1.20x and the bootstrap 95% CI for the survey-level median remains above 1.0x.
- Strong general advantage: median >=1.50x.
- Broad robustness: 10th-percentile gain >=1.0x.

These are benchmark interpretation rules, not guarantees.
