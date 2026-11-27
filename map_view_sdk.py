"""Opt-in SDK/vector renderer; production map_view.py remains the control arm.

Uses the same categorical overlay conversion. No model inference runs here.
"""
import json

from map_view import overlay

SDK_VERSION = "v5.0.0"


def map_html(case, result=None, show_prediction=True, view_revision=0, *,
             maptiler_api_key="", language="vi"):
    """Render the analytical map with a vector basemap and an image overlay."""
    west, south, east, north = case['bounds_wgs84']
    ring = [[lon, lat] for lat, lon in case['footprint_wgs84']]
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    image, image_bounds = "", None
    if result is not None and show_prediction:
        image, image_bounds = overlay(result)
    coordinates = None
    if image_bounds:
        (s, w), (n, e) = image_bounds
        coordinates = [[w, n], [e, n], [e, s], [w, s]]
    english = language == 'en'
    area = case['area_name'].lower().replace('phía ', '')
    if english:
        area = {'tây nam': 'Southwest', 'tây bắc': 'Northwest',
                'đông bắc': 'Northeast'}.get(area, area)
    data = {
        'key': str(maptiler_api_key or '').strip(),
        'bounds': [[west, south], [east, north]],
        'footprint': {'type': 'Feature', 'properties': {},
                      'geometry': {'type': 'Polygon', 'coordinates': [ring]}},
        'prediction': image, 'coordinates': coordinates,
        'title': f'Thanh Hóa — {area}', 'revision': int(view_revision),
        'language': 'en' if english else 'vi',
        'loading': 'Loading map…' if english else 'Đang tải bản đồ…',
        'failure': ('The online map could not load. Check the connection, key or quota.'
                    if english else 'Chưa tải được bản đồ trực tuyến. Kiểm tra kết nối, key hoặc quota.'),
        'missing': ('The online basemap is not configured.' if english else
                    'Nền bản đồ trực tuyến chưa được cấu hình.'),
        'unsupported': ('This renderer requires WebGL2. Use the Leaflet version on this device.'
                        if english else 'Bộ hiển thị này cần WebGL2. Dùng bản Leaflet trên thiết bị này.'),
    }
    # A public tile key still must not be able to terminate an inline script.
    payload = json.dumps(data, ensure_ascii=False).replace('<', r'\u003c')
    return TEMPLATE.replace('__VERSION__', SDK_VERSION).replace('__DATA__', payload)


TEMPLATE = r'''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdn.maptiler.com/maptiler-sdk-js/__VERSION__/maptiler-sdk.css">
<style>
html,body,#map{margin:0;width:100%;height:100%;background:#e8eeec}
body{font-family:"Be Vietnam Pro",sans-serif}
#status{position:absolute;bottom:48px;left:12px;max-width:280px;padding:8px 12px;
 background:#fff8df;color:#193c44;z-index:4;font-size:13px;line-height:1.5}
#area{position:absolute;top:10px;right:10px;max-width:240px;padding:8px 12px;
 background:#fff;color:#193c44;border-radius:4px;z-index:3;font-size:13px}
.maplibregl-ctrl-attrib{font-size:11px;max-width:calc(100vw - 130px)}
</style></head><body><div id="map" role="region"></div>
<div id="area"></div><div id="status" role="status"></div>
<script type="module">
const cfg=__DATA__;
document.documentElement.lang=cfg.language;
document.documentElement.dataset.viewRevision=String(cfg.revision);
document.getElementById('area').textContent=cfg.title;
document.getElementById('map').setAttribute('aria-label',cfg.title);
const status=document.getElementById('status');status.textContent=cfg.loading;
window.demoMapReady=false;
window.__mapTrialStats={renderer:'MapTiler SDK JS __VERSION__',startedMs:performance.now(),errors:0};
if(!cfg.key){status.textContent=cfg.missing;}else{
 try{
  const probe=document.createElement('canvas');const gl=probe.getContext('webgl2');
  if(!gl)throw new Error('webgl2-unavailable');
  gl.getExtension('WEBGL_lose_context')?.loseContext();
  const sdk=await import('https://cdn.maptiler.com/maptiler-sdk-js/__VERSION__/maptiler-sdk.min.mjs');
  sdk.config.apiKey=cfg.key;
  const map=new sdk.Map({container:'map',style:'dataviz-v4-light',
   bounds:cfg.bounds,fitBoundsOptions:{padding:24,duration:0},
   projection:'mercator',terrain:false,geolocate:false,geolocateControl:false,
   navigationControl:false,scaleControl:false,fullscreenControl:false,
   scrollZoom:false,dragRotate:false,pitchWithRotate:false,maxPitch:0,
   maptilerLogo:true,attributionControl:{compact:false},logSDKVersion:false});
  // Keep the existing app's Leaflet-shaped reset contract at the iframe boundary.
  const reset=b=>map.fitBounds([[b[0][1],b[0][0]],[b[1][1],b[1][0]]],{padding:24,duration:0});
  window.demoMap={fitBounds:reset};window.sdkMap=map;
  window.addEventListener('message',event=>{
   if(event.source===parent && event.origin===parent.location.origin && event.data?.type==='flood-map-reset')
    map.fitBounds(cfg.bounds,{padding:24,duration:0});
  });
  new ResizeObserver(()=>map.resize()).observe(document.getElementById('map'));
  map.addControl(new sdk.NavigationControl({showCompass:false}),'top-left');
  map.addControl(new sdk.ScaleControl({unit:'metric'}),'top-left');
  map.on('error',()=>{window.__mapTrialStats.errors++;status.textContent=cfg.failure;status.hidden=false;});
  map.on('load',()=>{
   map.addSource('analysis-footprint',{type:'geojson',data:cfg.footprint});
   map.addLayer({id:'analysis-footprint',type:'line',source:'analysis-footprint',
    paint:{'line-color':'#11636a','line-width':2,'line-dasharray':[3.5,2.5]}});
   if(cfg.prediction){
    map.addSource('flood-prediction',{type:'image',url:cfg.prediction,coordinates:cfg.coordinates});
    const labelLayer=map.getStyle().layers.find(layer=>layer.type==='symbol')?.id;
    map.addLayer({id:'flood-prediction',type:'raster',source:'flood-prediction',
     paint:{'raster-opacity':1,'raster-fade-duration':0,'raster-resampling':'nearest'}},labelLayer);
   }
  });
  map.once('idle',()=>{
   if(!map.getLayer('analysis-footprint'))return;
   status.hidden=true;window.demoMapReady=true;
   window.__mapTrialStats.readyMs=performance.now();
  });
 }catch(error){status.textContent=error.message==='webgl2-unavailable'?cfg.unsupported:cfg.failure;
  window.__mapTrialStats.errors++;}
}
</script></body></html>'''
