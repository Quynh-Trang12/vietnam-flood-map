"""Readable geographic context; raster overlays are reprojected into map coordinates."""
import base64
import html
import json
from urllib.parse import quote
from pathlib import Path
import numpy as np
from rasterio.warp import calculate_default_transform,reproject,Resampling
from rasterio.transform import array_bounds
from demo_io import png_bytes
from map_assets import prepared_map
ROOT=Path(__file__).parent
TILE_URL="https://api.maptiler.com/maps/streets-v4/256/{z}/{x}/{y}.png"


def overlay(result):
    profile=result['profile'];pred=result['prediction']
    h,w=pred.shape
    bounds=array_bounds(h,w,profile['transform'])
    transform,width,height=calculate_default_transform(profile['crs'],'EPSG:4326',w,h,*bounds)
    warped=np.full((height,width),255,dtype='uint8')
    # 255 is a visible unobserved class inside the footprint; padding is transparent.
    reproject(pred,warped,src_transform=profile['transform'],src_crs=profile['crs'],
              dst_transform=transform,dst_crs='EPSG:4326',resampling=Resampling.nearest)
    footprint=np.zeros_like(warped)
    reproject(np.ones_like(pred,dtype='uint8'),footprint,src_transform=profile['transform'],
              src_crs=profile['crs'],dst_transform=transform,dst_crs='EPSG:4326',resampling=Resampling.nearest)
    rgba=colorize(warped,footprint,result['metadata'].get('flood_class',1))
    west,south,east,north=array_bounds(height,width,transform)
    return 'data:image/png;base64,'+base64.b64encode(png_bytes(rgba)).decode(),[[south,west],[north,east]]


def colorize(warped,footprint,flood_class):
    rgba=np.zeros((*warped.shape,4),dtype='uint8')
    rgba[(warped==flood_class)&(footprint==1)]=[6,182,212,215] if flood_class==2 else [200,65,20,185]
    if flood_class==2:
        rgba[(warped==1)&(footprint==1)]=[29,78,216,215]
    rgba[(warped==255)&(footprint==1)]=[168,38,195,225]
    return rgba


def map_html(case,result=None,show_prediction=True,view_revision=0,*,maptiler_api_key=""):
    key = str(maptiler_api_key or "").strip()
    tile_url = TILE_URL + "?key=" + quote(key, safe="") if key else ""
    west,south,east,north=case['bounds_wgs84']
    bounds=[[south,west],[north,east]]
    image='';image_bounds=bounds
    asset=prepared_map(case['key'])
    reference='';reference_bounds=bounds
    if asset is not None:
        extension="webp" if (ROOT/f"static/maps/{case['key']}.webp").is_file() else "png"
        reference=f"app/static/maps/{case['key']}.{extension}?v={asset[1]['sha256'][:12]}"
        w,s,e,n=asset[1]['bounds_wgs84'];reference_bounds=[[s,w],[n,e]]
    if result is not None and show_prediction:image,image_bounds=overlay(result)
    status_message=('Nền bản đồ xung quanh chưa tải được; nền khu vực phân tích và kết quả vẫn được giữ.' if reference else 'Nền địa danh chưa tải được. Kiểm tra Internet; ranh khu vực và lớp kết quả vẫn được giữ.')
    css=(ROOT/'assets/leaflet.css').read_text()
    js=(ROOT/'assets/leaflet.js').read_text()
    fonts=(ROOT/'static/fonts/fonts.css').read_text().replace('.woff2','.ttf')
    title=html.escape(f"Thanh Hóa — {case['area_name'].lower()}")
    return f'''<!doctype html><html lang="vi" data-view-revision="{int(view_revision)}"><head><meta charset="utf-8"><style>{fonts}
{css}
html,body{{margin:0;height:100%;font-family:"Be Vietnam Pro",sans-serif}}#map{{height:100%;min-height:0;background:#e8eeec}}
.leaflet-container{{font:13px/1.5 "Be Vietnam Pro",sans-serif}}.map-note{{background:white;padding:8px 12px;color:#193c44;max-width:240px;border-radius:4px}}
#status{{display:none;background:#fff8df;padding:8px;position:absolute;bottom:30px;left:12px;z-index:800;font-size:13px;max-width:280px}}
</style></head><body><div id="map" role="region" aria-label="Bản đồ khu vực Thanh Hóa và lớp nghi ngập"></div>
<div id="status">{html.escape(status_message)}</div>
<script>{js}</script><script>
const map=L.map('map',{{scrollWheelZoom:false}}).fitBounds({json.dumps(bounds)},{{padding:[24,24]}});
window.demoMap=map;
window.addEventListener('message',event=>{{
 if(event.source===window.parent && event.origin===window.parent.location.origin && event.data?.type==='flood-map-reset')
  map.fitBounds({json.dumps(bounds)},{{padding:[24,24],animate:false}});
}});
const tileURL={json.dumps(tile_url)};
if(tileURL){{
 const base=L.tileLayer(tileURL,{{minZoom:1,maxZoom:18,crossOrigin:true,
  attribution:'© <a href="https://www.maptiler.com/copyright/" target="_blank" rel="noopener">MapTiler</a> © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · Reference style © <a href="https://www.openstreetmap.fr/" target="_blank" rel="noopener">OpenStreetMap France</a>'}}).addTo(map);
 let loaded=0;
 base.on('tileload',()=>{{loaded++;document.getElementById('status').style.display='none';}});
 base.on('tileerror',()=>{{if(!loaded)document.getElementById('status').style.display='block';}});
 const logo=L.control({{position:'bottomleft'}});
 logo.onAdd=()=>{{
  const link=L.DomUtil.create('a');link.href='https://www.maptiler.com/';
  link.target='_blank';link.rel='noopener';link.setAttribute('aria-label','MapTiler');
  const image=document.createElement('img');image.src='https://api.maptiler.com/resources/logo.svg';
  image.alt='MapTiler logo';image.style.width='100px';image.style.height='auto';
  link.appendChild(image);return link;
 }};logo.addTo(map);
}}else{{
 document.getElementById('status').style.display='block';
}}
// Keep the prepared fallback below live tiles: its fixed-resolution labels must
// never cover or cut labels rendered at the current map zoom.
const referencePane=map.createPane('reference-basemap');
referencePane.style.zIndex='190';
referencePane.style.pointerEvents='none';
const reference={json.dumps(reference)};
if(reference){{
 // Community Cloud serves the app under /~/+/. Resolve from its parent document,
 // rather than the outer Cloud shell or about:srcdoc, preserving that prefix.
 const referenceURL=new URL(reference,window.parent.document.baseURI).href;
 L.imageOverlay(referenceURL,{json.dumps(reference_bounds)},{{interactive:false,pane:'reference-basemap',className:'prepared-basemap'}})
  .on('error',function(){{map.removeLayer(this);}}).addTo(map);
}}
L.polygon({json.dumps(case['footprint_wgs84'])},{{color:'#11636a',weight:2,fill:false,dashArray:'7 5'}}).addTo(map).bindTooltip({json.dumps(title)},{{sticky:true}});
const image={json.dumps(image)};
if(image)L.imageOverlay(image,{json.dumps(image_bounds)},{{interactive:false,className:'prediction-overlay'}}).addTo(map);
L.control.scale({{imperial:false,position:'bottomleft'}}).addTo(map);
const note=L.control({{position:'topright'}});note.onAdd=()=>{{const el=L.DomUtil.create('div','map-note');el.textContent={json.dumps(title)};return el;}};note.addTo(map);
window.demoMapReady=true;
</script></body></html>'''

