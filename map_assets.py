"""Prepared reference basemaps shared by the UI and geographic PNG export."""
import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from demo_io import ROOT

DIRECTORY=ROOT/'static/maps'
VERSION='analysis-reference-v2'


@lru_cache(maxsize=12)
def _read(case_id,png_stamp,json_stamp):
    metadata=json.loads((DIRECTORY/f'{case_id}.json').read_text())
    payload=(DIRECTORY/f'{case_id}.png').read_bytes()
    if metadata['version']!=VERSION or hashlib.sha256(payload).hexdigest()!=metadata['sha256']:
        raise ValueError('Prepared basemap failed its version or integrity check')
    return payload,metadata


def prepared_map(case_id):
    if not re.fullmatch(r'[A-Z0-9-]+',case_id):
        raise ValueError('Invalid prepared-map identifier')
    image=DIRECTORY/f'{case_id}.png';metadata=DIRECTORY/f'{case_id}.json'
    if not image.is_file() or not metadata.is_file():return None
    return _read(case_id,image.stat().st_mtime_ns,metadata.stat().st_mtime_ns)
