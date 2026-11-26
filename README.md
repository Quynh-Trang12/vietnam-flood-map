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

The entry point uses `st.App` middleware to gzip frontend JavaScript/CSS and include the existing app stylesheet in the initial HTML. Binary imagery, model files and downloads pass through unchanged. Use `streamlit_app.py` as the deployment entry point.

Open the address printed by Streamlit. The three Thanh Hóa cases and PNG/GeoTIFF/CSV/JSON downloads are available in Vietnamese and English. Inputs and model are bundled; inference does not require access to the original workstation or a GPU. The background is a dated reference snapshot; it is not a flood observation. Attribution is included in maps and `resources/DATA_SOURCE_NOTICE.md`.

## Deploy on free Streamlit Community Cloud

1. Put **this folder's contents** at the root of a GitHub repository, retaining `.streamlit/config.toml`, `resources/`, `architecture/` and `static/`.
2. Sign in to https://share.streamlit.io/ and choose **Create app**. Select that repository and the `streamlit_app.py` entry point.
3. In **Advanced settings**, select **Python 3.13**, then deploy. No GPU, API key, private data or secrets are needed by this demo.
4. Verify all three areas, switch VI/EN, and download a ZIP. The native GeoTIFF retains classes 0/1/2/255. Model SHA-256: `8d41bd9ee0c8dda7cda28ae173e4fa8fddb4bc5f2a006bf2770cb7cbeb5198aa`.

Official deployment instructions: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

This is a prepared deployment artifact, not evidence of a live public deployment. Free-host CPU speed, resource sharing and cold starts have not been measured until the actual app is deployed; local measurements are not a Cloud latency guarantee. Treat predictions as estimates requiring verification.
