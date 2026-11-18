"""Streamlit Community Cloud entry point."""
from pathlib import Path
exec(compile((Path(__file__).parent/"app_bilingual.py").read_text(), "app_bilingual.py", "exec"))
