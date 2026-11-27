# RTC flood-mapping demo

This folder contains the runnable Streamlit app, the pinned epoch-9 RTC fusion model, all three admitted optical/radar/cloud input sets, exact geometry grids, reference basemap snapshots, fonts and licensing notices. It performs actual float32 CPU inference in 256×256 windows with the unchanged 9-channel preprocessing and three-class argmax. Prepared assets do not contain model predictions or ground-truth labels.

## Run locally

Use Python 3.13. In this folder:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open the address printed by Streamlit. The three Thanh Hóa cases and PNG/GeoTIFF/CSV/JSON downloads are available in Vietnamese and English. Inputs and model are bundled; inference does not require access to the original workstation or a GPU. The background is a dated reference snapshot; it is not a flood observation. Attribution is included in maps and `resources/DATA_SOURCE_NOTICE.md`.

## Deploy on free Streamlit Community Cloud

1. Put **this folder's contents** at the root of a GitHub repository, retaining `.streamlit/config.toml`, `resources/`, `architecture/` and `static/`.
2. Sign in to https://share.streamlit.io/ and choose **Create app**. Select that repository and the `streamlit_app.py` entry point.
3. In **Advanced settings**, select **Python 3.13**, then deploy. No GPU is needed. For the online basemap, add the MapTiler Free key in App settings → Secrets as described below.
4. Verify all three areas, switch VI/EN, and download a ZIP. The native GeoTIFF retains classes 0/1/2/255. Model SHA-256: `8d41bd9ee0c8dda7cda28ae173e4fa8fddb4bc5f2a006bf2770cb7cbeb5198aa`.

Official deployment instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

This is a prepared deployment artifact, not evidence of a live public deployment. Free-host CPU speed, resource sharing and cold starts have not been measured until the actual app is deployed; local measurements are not a Cloud latency guarantee. Treat predictions as estimates requiring verification.

## MapTiler Free basemap

Create an API key dedicated to this app. Set its **Allowed HTTP Origins** to
`vietnam-flood-map.streamlit.app` (without scheme or path); leave the User-Agent
restriction empty for browser use. In Streamlit App settings → Secrets, add:

```toml
MAPTILER_API_KEY = "your MapTiler key"
```

Do not commit the key or a secrets file. The key is necessarily visible in browser
tile requests; the origin restriction controls where it can be used. Local tests
need their own key allowing `localhost` or `127.0.0.1`; do not broaden the production
key for local tests. Missing/invalid keys, quota exhaustion or network failures
leave the existing dated reference background and show the basemap warning.
There is no automatic provider switch or upgrade. Keep the MapTiler Free plan,
logo and attribution. Maps use the Dataviz Light v4 raster style, 256px WebP tiles (no Retina multiplier).
The neutral background is intended for flood-class overlays and place context,
rather than navigation or satellite imagery. This uses the existing Leaflet
renderer; no vector/WebGL/3D runtime is added. All map styles still share the
provider infrastructure, so this choice does not establish a higher uptime SLA.

- API key restrictions: https://docs.maptiler.com/guides/developer/credentials/api-key/
- Leaflet integration: https://docs.maptiler.com/leaflet/examples/raster-tiles-in-leaflet-js/
- Free plan/quota behavior: https://www.maptiler.com/cloud/pricing/

## Separate SDK app (v2)

`streamlit_sdk_trial.py` is the entry point for the separate SDK app. Keep
`streamlit_app.py` as the existing app's entry point. The SDK app needs the same
Secret and its own hostname in the key's Allowed HTTP Origins.

The SDK now renders the same Dataviz Light basemap from 256px WebP tiles rather
than downloading vector geometry, glyphs and sprites. The SDK, controls, analysis
boundary and exact prediction image/coordinates remain in use. Raster labels can
look softer at fractional zoom or on high-density screens; the target desktop
uses 100% scaling. MapTiler branding and OpenStreetMap attribution remain visible.
Missing keys or failed tiles show an error, without changing provider or billing.

This change has browser functional checks; a deployed Lighthouse score must be
measured after committing the files and rebooting the separate v2 app.
