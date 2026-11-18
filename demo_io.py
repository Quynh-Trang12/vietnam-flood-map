"""Portable demo paths, lossless images and exact cached ellipsoidal geometry."""
import hashlib
import io
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from pyproj import CRS, Geod, Transformer
from rasterio import Affine

ROOT=Path(__file__).resolve().parent
WORKSPACE=next((p for p in ROOT.parents if (p/'04-Implementation/workspace_storage.py').is_file()),None)
if WORKSPACE is not None:
    sys.path.insert(0,str(WORKSPACE/'04-Implementation'))
    from workspace_storage import resolve_input
else:
    def resolve_input(value):
        return value

if WORKSPACE is None and not (ROOT/'deployment-manifest.json').is_file():
    raise RuntimeError('Use the complete deployment bundle outside the project workspace')

RAW=ROOT/'data/v1.1'
GEOMETRY=(ROOT/'resources/geometry' if (ROOT/'deployment-manifest.json').is_file() else
          WORKSPACE/'03-Data-and-Models/Data/Processed/RTC-Demo-Serving')
LEGACY_COLORS=np.array([[215,227,234],[225,91,35],[168,38,195]],dtype='uint8')


def sha256(path):
    digest=hashlib.sha256()
    with Path(resolve_input(path)).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):
            digest.update(chunk)
    return digest.hexdigest()


def png_bytes(array):
    buffer=io.BytesIO()
    Image.fromarray(array).save(buffer,format='PNG',compress_level=3)
    return buffer.getvalue()


def catalogue():
    path=ROOT/'data/eligible_vietnam_cases.json'
    if not path.is_file():return []
    rows=json.loads(path.read_text(encoding='utf-8'))
    return [row for row in rows if row['country']=='Việt Nam'
            and row['admission']=='passed_input_qa' and 0<row['gap_days']<=30]


def geometry_key(profile):
    values=[profile['width'],profile['height'],list(profile['transform'])[:6],profile['crs'].to_wkt()]
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()


def calculate_pixel_areas(profile):
    """Original WGS84 geodesic quadrilaterals, used once when preparing serving assets."""
    h,w,t=profile['height'],profile['width'],profile['transform']
    row,col=np.meshgrid(np.arange(h+1),np.arange(w+1),indexing='ij')
    lon,lat=Transformer.from_crs(CRS(profile['crs']),'EPSG:4326',always_xy=True).transform(
        t.a*col+t.b*row+t.c,t.d*col+t.e*row+t.f)
    geod=Geod(ellps='WGS84');areas=np.empty((h,w),dtype='float64')
    for r in range(h):
        for c in range(w):
            area,_=geod.polygon_area_perimeter(
                [lon[r,c],lon[r,c+1],lon[r+1,c+1],lon[r+1,c]],
                [lat[r,c],lat[r,c+1],lat[r+1,c+1],lat[r+1,c]])
            areas[r,c]=abs(area)
    return areas


@lru_cache(maxsize=16)
def _geometry(crs,transform,width,height):
    profile=dict(crs=CRS(crs),transform=Affine(*transform),width=width,height=height)
    key=hashlib.sha256(json.dumps([width,height,list(transform),crs],sort_keys=True).encode()).hexdigest()
    manifest=GEOMETRY/'geometry-manifest.json'
    path=GEOMETRY/f'areas-{key}.npy'
    records=json.loads(manifest.read_text()).get('grids',{}) if manifest.is_file() else {}
    if path.is_file() and key in records:
        if sha256(path)!=records[key]['sha256']:
            raise ValueError('Prepared area grid failed its integrity check')
        areas=np.load(path,mmap_mode='r',allow_pickle=False)
        if areas.shape!=(height,width) or areas.dtype!=np.float64 or not np.isfinite(areas).all() or (areas<=0).any():
            raise ValueError('Invalid prepared area grid')
    else:
        areas=calculate_pixel_areas(profile)
        areas.flags.writeable=False
    return areas


def pixel_areas(profile):
    return _geometry(profile['crs'].to_wkt(),tuple(profile['transform'])[:6],profile['width'],profile['height'])
