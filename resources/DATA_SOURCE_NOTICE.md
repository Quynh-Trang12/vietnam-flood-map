---
license: cc-by-4.0
task_categories:
- image-segmentation
tags:
- geospatial
- earth-observation
- remote-sensing
- flood
- sentinel-1
- sentinel-2
- sar
- dem
size_categories:
- 10K<n<100K
---

# GEOID-Flood

[![arXiv](https://img.shields.io/badge/arXiv-2608.02315-b31b1b.svg)](https://arxiv.org/abs/2608.02315)
[![Code](https://img.shields.io/badge/GitHub-links--ads%2Fgeoid--flood-181717.svg?logo=github)](https://github.com/links-ads/geoid-flood)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

A large-scale multi-modal benchmark for flood segmentation, built from **219 Copernicus
EMS Rapid Mapping flood activations** across **65 countries** (2016-2026).

**165,329 rasters / 584 GB** across 319 shards. 14,282 tiles: 8,938 train / 1,241 val / 2,674 test, plus 1,429 held-out tiles from activations EMSR857-871 for out-of-distribution evaluation.

Each 1024x1024 tile at 10 m resolution provides co-registered Sentinel-1 GRD and RTC
(pre- and post-event, VV/VH), a pre-event Sentinel-2 L2A composite, a Copernicus GLO-30
DEM, and manually validated three-class labels
(0 = background, 1 = permanent water, 2 = flooded water).

![Representative GEOID-Flood tiles: pre- and post-event Sentinel-1 GRD and RTC, pre-event Sentinel-2 RGB, GLO-30 DEM, and the three-class label, for three events](assets/modality_samples.png)

*Three GEOID-Flood events, all layers of a tile side by side. Flooded water is cyan, permanent
water blue, invalid pixels gray.*

![Global distribution of GEOID-Flood areas of interest, coloured by split assignment, with an inset enlarging Europe](assets/global_aoi_map.png)

*The 219 activations span 65 countries. Splits are assigned per area of interest and touching
AoIs share a split, so no flood event straddles train, validation and test.*

## Layout

Rasters ship as **uncompressed tar shards of Cloud-Optimized GeoTIFFs**, grouped so you
can download only the modalities and splits you need:

```
{tree}/shards/{split}/{layer}/{split}-{layer}-NNNNN-of-NNNNN.tar
```

Tar members carry the canonical path (`EMSR151-1/s1grd/EMSR151-1-0_s1grd_post_*.tif`), so
extracting **any** shard into a tree root rebuilds the layout the training configs expect:

```bash
tar -xf train-s1grd-00000-of-00062.tar -C data/geoid-flood/
```

## Download

`get_data.py` fetches shards and unpacks them into the expected structure, deleting each
shard as soon as it is unpacked. It checks free space before starting and resumes if
interrupted.
```bash
pip install huggingface_hub tqdm
python get_data.py --dest data                                     # everything
python get_data.py --dest data --layer s1grd label                 # S1-GRD benchmark
python get_data.py --dest data --tree geoid-flood-heldout \
                   --layer s1rtc label                             # held-out eval only
python get_data.py --list --layer s1grd s2l2a dem label            # preview, no download
python get_data.py --dest data --layer s1grd --workers 8           # more shards in flight
```

Shards are fetched over the Xet protocol, several at a time. Peak disk usage is the size of
your selection plus roughly `--workers` x 2 GB for the shards in flight.

Typical selections:

| selection | flags | size |
|---|---|---|
| everything | *(no flags)* | ~584 GB |
| S1-GRD single-image benchmark | `--layer s1grd label` | ~205 GB |
| ...train+val only | `--layer s1grd label --split train val` | ~140 GB |
| early/mid fusion (S1+S2+DEM) | `--layer s1grd s2l2a dem label` | ~392 GB |
| held-out S1-RTC evaluation | `--tree geoid-flood-heldout --layer s1rtc label` | ~20 GB |

## Modalities

Every tile carries the same nine layers, all co-registered on one 1024x1024 event-UTM grid
at 10 m. Four are imagery, five are derived masks.

| layer | bands | passes | size | what it is |
|---|---|---|---|---|
| `s1grd` | 2 x float32 | pre + post | 204.6 GB | Sentinel-1 GRD backscatter as linear sigma0, bands ordered VV, VH. One acquisition before the event and one after. The loader converts to dB (`10*log10`) on read. |
| `s1rtc` | 2 x float32 | pre + post | 192.2 GB | The same two acquisitions, radiometrically terrain-corrected, also linear sigma0. `NaN` marks pixels outside the valid swath. |
| `s2l2a` | 12 x uint16 | pre | 177.6 GB | Cloud-filtered pre-event Sentinel-2 L2A surface-reflectance composite, 12 bands. |
| `dem` | 1 x float32 | static | 9.5 GB | Copernicus GLO-30 elevation in metres, resampled from 30 m onto the 10 m tile grid. |
| `label` | 1 x uint8 | static | 0.1 GB | **The training target.** Manually validated three classes: `0` background, `1` permanent water, `2` flooded water. `255` marks pixels outside the mapped area and is the ignore index. |
| `cloudmask` | 1 x uint8 | pre | 0.1 GB | Cloud and shadow over the S2 composite, from OmniCloudMask: `0` clear, `1` thick cloud, `2` thin cloud, `3` shadow. Not folded into `label`, so this is the only per-pixel record of cloud. |
| `floodmask` | 1 x uint8 | static | 0.1 GB | Binary CEMS Rapid Mapping flood delineation, one of the two products `label` was derived from. Retains extent the three-class label dropped. |
| `permwater` | 1 x uint8 | static | 0.1 GB | Binary permanent-water extent, the other source product behind `label`. No released config reads it. |
| `validity` | 1 x uint8 | static | 0.1 GB | Binary per-pixel validity: `1` where the tile was imaged and mapped. Largely redundant with `label == 255`. |
| | | | **584 GB** | **165,329 rasters** |

`sample/` holds two complete event-AoIs from activation EMSR712 -- `EMSR712-10` (train split)
and `EMSR712-3` (test split) -- with all nine layers for all 47 tiles, 8,076 chip rows, so the
loader can be exercised end to end without a full download. Both splits are present on purpose:
`EMSR712-10` makes `fit` runnable and `EMSR712-3` makes `test` runnable. It extracts to the same
canonical paths, so the only override needed is
`--data.init_args.metadata_filename data_tiles_s256_st128_sample.csv`.

## Metadata

| file | role |
|---|---|
| `data_tiles_s256_st128.csv` | **the only metadata the dataloader reads.** Enumerates 256x256 chips at stride 128 (train) / 256 (val, test), with `valid_proportion`, `positive_proportion`, `cloud_cover` and `split` per chip. This is the inventory the published models were trained on |
| `tile_catalog.parquet` | the 1024x1024 tile inventory: geometry, UTM CRS, delineation times, `is_valid`, `invalid_pixel_frac` and `split`. Nothing reads it at training time; query it to select events by geography or date. **`is_valid AND invalid_pixel_frac <= 0.95` is the paper's tile selection** -- 12,853 tiles here (8,938 train / 1,241 val / 2,674 test) and 1,429 in `geoid-flood-heldout`, the counts the paper reports |


## Citation

See `CITATION.cff` in the code repository.

## License

The GEOID-Flood compilation, splits and labels: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
Code: MIT, in the code repository. The `dem` layer is licensed separately (below).

Contains modified Copernicus data. Carry these notices forward when redistributing:

- Modified Copernicus Sentinel-1 and Sentinel-2 data (2016-2026).
- Copernicus Emergency Management Service Rapid Mapping products, © European Union.
- The `dem` layer is a resampled Copernicus WorldDEM-30 (instance COP-DEM-GLO-30-F), used under the
  [Copernicus WorldDEM-30 licence](https://docs.sentinel-hub.com/api/latest/static/files/data/dem/resources/license/License-COPDEM-30.pdf).