"""Readable geographic context; raster overlays are reprojected into map coordinates."""
import base64
import html
import json
from pathlib import Path
import numpy as np
from rasterio.warp import calculate_default_transform,reproject,Resampling
from rasterio.transform import array_bounds
from demo_io import png_bytes
from map_assets import prepared_map
ROOT=Path(__file__).parent
TILE_URL="https://a.tile.openstreetmap.fr/osmfr/{z}/{x}/{y}.png"
FALLBACK_TILE_URL="https://tile.openstreetmap.org/{z}/{x}/{y}.png"


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


def map_html(case,result=None,show_prediction=True,view_revision=0):
    west,south,east,north=case['bounds_wgs84']
    bounds=[[south,west],[north,east]]
    image='';image_bounds=bounds
    asset=prepared_map(case['key'])
    reference='';reference_bounds=bounds
    if asset is not None:
        preview=ROOT/f"static/maps/{case['key']}-preview.webp"
        extension="webp" if (ROOT/f"static/maps/{case['key']}.webp").is_file() else "png"
        filename=preview.name if preview.is_file() else f"{case['key']}.{extension}"
        # Keep the prepared reference available even when Cloud static requests
        # or the external tile service stall. The same image bytes travel with
        # the map document; no predictions or labels are embedded here.
        reference_path = ROOT / 'static/maps' / filename
        mime = 'image/webp' if reference_path.suffix == '.webp' else 'image/png'
        reference = f'data:{mime};base64,' + base64.b64encode(reference_path.read_bytes()).decode()
        w,s,e,n=asset[1]['bounds_wgs84'];reference_bounds=[[s,w],[n,e]]
    if result is not None and show_prediction:image,image_bounds=overlay(result)
    status_message=('Nền bản đồ xung quanh chưa tải được; nền khu vực phân tích và kết quả vẫn được giữ.' if reference else 'Nền địa danh chưa tải được. Kiểm tra Internet; ranh khu vực và lớp kết quả vẫn được giữ.')
    css=(ROOT/'assets/leaflet.css').read_text()
    js=(ROOT/'assets/leaflet.js').read_text()
    title=html.escape(f"Thanh Hóa — {case['area_name'].lower()}")
    return f'''<!doctype html><html lang="vi" data-view-revision="{int(view_revision)}"><head><meta charset="utf-8"><style>
{css}
html,body{{margin:0;height:100%;font-family:"Be Vietnam Pro",sans-serif}}#map{{height:100%;min-height:0;background:#e8eeec}}
.leaflet-container{{font:13px/1.5 "Be Vietnam Pro",sans-serif}}.map-note{{background:white;padding:8px 12px;color:#193c44;max-width:240px;border-radius:4px}}
#status{{display:none;background:#fff8df;padding:8px;position:absolute;bottom:30px;left:12px;z-index:800;font-size:13px;max-width:280px}}
</style></head><body><div id="map" role="region" aria-label="Bản đồ khu vực Thanh Hóa và lớp nghi ngập"></div>
<div id="status">{html.escape(status_message)}</div>
<script>{js}</script><script>
// Resolve font URLs from the app document, preserving the Community Cloud prefix.
const appBase=window.parent.document.baseURI;
const fontStyle=document.createElement('style');
fontStyle.textContent=[400,500,600,700].map((weight,i)=>`@font-face{{font-family:"Be Vietnam Pro";font-style:normal;font-weight:${{weight}};font-display:optional;src:url("${{new URL('app/static/fonts/be-vietnam-pro-'+i+'.woff2',appBase).href}}") format("woff2");}}`).join('');
document.head.appendChild(fontStyle);
const map=L.map('map',{{scrollWheelZoom:false}}).fitBounds({json.dumps(bounds)},{{padding:[24,24]}});
window.demoMap=map;
window.addEventListener('message',event=>{{
 if(event.source===window.parent && event.origin===window.parent.location.origin && event.data?.type==='flood-map-reset')
  map.fitBounds({json.dumps(bounds)},{{padding:[24,24],animate:false}});
}});
// Retry only visible tiles once through the independent standard OSM endpoint.
// A stalled request also falls back; there is no prefetch or retry loop.
const ResilientTiles=L.TileLayer.extend({{
 createTile(coords,done){{
  const tile=document.createElement('img');tile.alt='';tile.setAttribute('role','presentation');
  let fallback=false,settled=false,timer;
  const finish=error=>{{if(settled)return;settled=true;clearTimeout(timer);done(error,tile);}};
  const retry=()=>{{
   clearTimeout(timer);
   if(fallback){{finish(new Error('Basemap tile unavailable'));return;}}
   fallback=true;
   tile.src=L.Util.template({json.dumps(FALLBACK_TILE_URL)},coords);
   timer=setTimeout(()=>finish(new Error('Basemap tile timeout')),8000);
  }};
  tile.onload=()=>finish(null);tile.onerror=retry;
  tile._cancelBasemapLoad=()=>{{settled=true;clearTimeout(timer);tile.onload=null;tile.onerror=null;}};
  tile.src=this.getTileUrl(coords);timer=setTimeout(retry,5000);
  return tile;
 }}
}});
const base=new ResilientTiles({json.dumps(TILE_URL)},{{maxZoom:18,attribution:'© <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap contributors</a> · Reference/primary style © <a href="https://www.openstreetmap.fr/" target="_blank">OpenStreetMap France</a>'}}).addTo(map);
base.on('tileunload',event=>event.tile._cancelBasemapLoad?.());
let loaded=0;base.on('tileload',()=>{{loaded++;document.getElementById('status').style.display='none';}});
base.on('tileerror',()=>{{if(!loaded)document.getElementById('status').style.display='block';}});
// Keep the prepared fallback below live tiles: its fixed-resolution labels must
// never cover or cut labels rendered at the current map zoom.
const referencePane=map.createPane('reference-basemap');
referencePane.style.zIndex='190';
referencePane.style.pointerEvents='none';
const reference={json.dumps(reference)};
if(reference){{
 // The prepared reference is part of this document, independent of HTTP tiles.
 L.imageOverlay(reference,{json.dumps(reference_bounds)},{{interactive:false,pane:'reference-basemap',className:'prepared-basemap'}})
  .on('error',function(){{
   document.getElementById('status').textContent='Không tải được nền tham chiếu. Hãy tải lại bản đồ; đường viền không phải bản đồ nền.';
   document.getElementById('status').style.display='block';
  }}).addTo(map);
}}
L.polygon({json.dumps(case['footprint_wgs84'])},{{color:'#11636a',weight:2,fill:false,dashArray:'7 5'}}).addTo(map).bindTooltip({json.dumps(title)},{{sticky:true}});
const image={json.dumps(image)};
if(image)L.imageOverlay(image,{json.dumps(image_bounds)},{{interactive:false,className:'prediction-overlay'}}).addTo(map);
L.control.scale({{imperial:false,position:'bottomleft'}}).addTo(map);
const note=L.control({{position:'topright'}});note.onAdd=()=>{{const el=L.DomUtil.create('div','map-note');el.textContent={json.dumps(title)};return el;}};note.addTo(map);
window.demoMapReady=true;
</script></body></html>'''

