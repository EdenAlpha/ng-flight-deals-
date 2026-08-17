# Compression Fingerprint v1

## Purpose

Testing data is classified for compression by **measured compressibility structure**, not by domain labels such as land, marine, DAS, raw, or migrated. Those remain provenance metadata only.

The classification object is **(dataset, error contract, scale)**. For the current general-seismic benchmark the primary error contract is epsilon = 0.10 * survey-global standard deviation with hard max-absolute reconstruction error <= epsilon.

## Why

Scientific lossy-compression research shows that compression behavior depends strongly on correlation structure, entropy after quantization, tolerated loss, dimensional structure, and local/nonstationary variation. A physical acquisition label alone is not a reliable compression class.

## Compression fingerprint

For each deterministic benchmark unit, compute the following without invoking any candidate production codec.

### 1. Quantization / information content
- Quantized entropy H(Q_epsilon) in bits/sample at the exact benchmark epsilon.
- Occupied-symbol count and effective alphabet size.
- Zero fraction after legal 2*epsilon scalar quantization.
- Value-distribution skewness, kurtosis, tail fractions, and robust dynamic range.

### 2. Axis-wise dependence
For every meaningful/native axis:
- lag-1, lag-2, lag-4, lag-8, lag-16 autocorrelation;
- correlation decay length / variogram range;
- mutual-information proxy where practical;
- first- and second-difference entropy;
- zero/nonzero transition fraction after quantization.

Report anisotropy: the ratios between strongest and weakest axis dependence.

### 3. Predictability probes
Use a small, frozen, codec-agnostic probe set only as measurements:
- previous-sample residual entropy on each axis;
- second-order linear residual entropy;
- fixed Lorenzo residual entropy for native 2-D/3-D arrays;
- fixed local-plane residual entropy where geometry supports it.

These probes do not select dataset-specific coefficients and are not headline compressors.

### 4. Transform concentration / intrinsic rank
- power-spectrum entropy and spectral concentration;
- low-frequency energy fraction;
- SVD/PCA effective rank on deterministic small blocks/slices;
- energy captured by the first k singular values;
- fixed wavelet/lifting coefficient sparsity by scale.

### 5. Stationarity / heterogeneity
Compute the fingerprint on deterministic local blocks as well as globally and report:
- block-to-block coefficient of variation for entropy and correlation features;
- distribution/divergence of local symbol histograms;
- range of local predictability;
- fraction of blocks in sparse vs dense transition states.

This determines whether the object is globally homogeneous or a mixture of local regimes.

### 6. Scale response
At a fixed sequence of spatial/temporal scales, measure how the above quantities change. In particular report:
- quantized entropy vs block size;
- correlation range relative to block size;
- effective rank vs block size;
- standardized probe residual entropy vs block size.

This is essential because large coherent volumes can expose redundancy invisible in small tiles.

### 7. Geometry metadata (not a compression class)
Keep physical provenance alongside the fingerprint:
- active/passive/DAS;
- raw/prestack/processed-prestack/poststack/migrated;
- sensor type;
- native dimensions and axis semantics;
- trace ordering and coordinate geometry;
- sample interval and spatial sampling.

These tags are used to ensure benchmark coverage and to interpret clusters, but they may not directly choose a codec.

## Classification method

1. Compute the fingerprint at the frozen benchmark error tolerance and deterministic scales.
2. Robust-normalize the numerical features across the corpus.
3. Cluster in fingerprint space without using survey names, land/marine/DAS labels, or compression results.
4. Do not preselect the number of classes. Prefer a stability-based clustering analysis; retain outliers as explicit uncovered regimes instead of forcing them into a class.
5. After clusters are frozen, inspect provenance labels only to understand what physical data ended up in each structural cluster.
6. A compression engine is considered general for a cluster only if it transfers to multiple independent surveys/positions in that cluster.

## Benchmark sampling rule

A benchmark corpus should cover **fingerprint space**, not merely count one dataset from each physical category. New datasets are most valuable when they occupy sparse/uncovered regions of fingerprint space.

For each structural cluster include, where available:
- at least 2 independent surveys/sources;
- multiple deterministic positions/scales per survey;
- one hard/outlier member near the cluster boundary;
- whole/native-scale validation in addition to small screening blocks.

## Production routing rule

The production Seismic Master Compressor may inspect geometry and compute cheap fingerprint features, then route by measured structure. It may not route by dataset ID, survey name, geography, or a bare label such as `DAS` or `marine`.

## Interpretation

There is no universal statement such as "DAS is easy" or "migrated marine is hard." A DAS recording can fall into a sparse-transition, coherent-wavefield, dense-high-entropy, or mixed/nonstationary region of fingerprint space. Likewise two physically different seismic forms can be compression-neighbors if their measured fingerprints are similar.

The project therefore separates two questions:
1. **Coverage:** What physical seismic forms have we tested?
2. **Compressibility:** What regions of statistical/structural fingerprint space have we tested and solved?

The second question drives compressor design and routing; the first ensures the benchmark remains representative of real seismic practice.
