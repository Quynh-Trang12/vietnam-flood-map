"""Geographic PNG export using the UI basemap and georeferenced predictions."""
import io
import math
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from urllib.request import Request, urlopen

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pyproj import Transformer
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from rasterio.transform import array_bounds

from map_view import TILE_URL, colorize
from map_assets import prepared_map
from demo_io import geometry_key

ORIGIN = math.pi * 6378137
MAP_SIZE = (1024, 1024)
CANVAS_SIZE = (1088, 1344)
MAP_OFFSET = (32, 108)


class BasemapUnavailable(RuntimeError):
    """A geographic preview must never silently degrade to a class-only image."""


@lru_cache(maxsize=256)
def tile_png(z, x, y, cache_hour):
    """Reuse tiles for one hour without writing over source imagery or evidence."""
    request = Request(TILE_URL.format(z=z,x=x,y=y), headers={
        'User-Agent':'FloodMappingResearchDemo/1.0 (local educational map export)'})
    with urlopen(request, timeout=15) as response:
        payload = response.read(2_000_001)
    if len(payload)>2_000_000:
        raise ValueError('Unexpected map tile size')
    with Image.open(io.BytesIO(payload)) as image:
        if image.size != (256,256):
            raise ValueError('Expected a 256-pixel map tile')
        image.verify()
    return payload


def viewport(profile, shape):
    """Match XYZ tiles and model pixels on a single Web Mercator grid."""
    h,w = shape
    bounds = array_bounds(h,w,profile['transform'])
    west,south,east,north = transform_bounds(profile['crs'],'EPSG:3857',*bounds)
    width,height = MAP_SIZE
    # Fit only the footprint, with square map pixels and no surrounding context.
    resolution = max((east-west)/width,(north-south)/height)
    map_west = (west+east)/2-width*resolution/2
    map_north = (south+north)/2+height*resolution/2
    transform = from_origin(map_west,map_north,resolution,resolution)
    zoom = max(0,min(18,math.ceil(math.log2(2*ORIGIN/(256*resolution)))))
    tile_resolution = 2*ORIGIN/(256*2**zoom)
    left = (map_west+ORIGIN)/tile_resolution
    top = (ORIGIN-map_north)/tile_resolution
    tile_width = width*resolution/tile_resolution
    tile_height = height*resolution/tile_resolution
    indices = [(zoom,x,y) for y in range(math.floor(top/256),math.ceil((top+tile_height)/256))
               for x in range(math.floor(left/256),math.ceil((left+tile_width)/256))]
    if any(not (0<=x<2**zoom and 0<=y<2**zoom) for _,x,y in indices):
        raise ValueError('Map viewport lies outside the supported tile grid')
    return transform, indices, left, top


def map_layers(result, transform):
    width,height = MAP_SIZE
    pred = result['prediction']; profile = result['profile']
    # Sample the source class at each output pixel center with the exact transform.
    # This avoids approximate warp tolerances shifting classes at native pixel edges.
    rows,cols=np.indices((height,width),dtype='float64')
    mx=transform.c+(cols+.5)*transform.a
    my=transform.f+(rows+.5)*transform.e
    inverse=Transformer.from_crs('EPSG:3857',profile['crs'],always_xy=True)
    sx,sy=inverse.transform(mx,my)
    px,py=(~profile['transform'])*(sx,sy)
    inside=np.isfinite(px)&np.isfinite(py)&(px>=0)&(py>=0)&(px<pred.shape[1])&(py<pred.shape[0])
    warped=np.full((height,width),255,dtype='uint8')
    warped[inside]=pred[py[inside].astype('int64'),px[inside].astype('int64')]
    footprint=inside.astype('uint8')
    return warped, footprint, colorize(warped,footprint,result['metadata'].get('flood_class',2))


def dashed_outline(draw, points):
    for a,b in zip(points,points[1:]+points[:1]):
        distance=math.hypot(b[0]-a[0],b[1]-a[1])
        for start in range(0,math.ceil(distance),14):
            end=min(start+8,distance)
            draw.line([(a[0]+(b[0]-a[0])*start/distance,a[1]+(b[1]-a[1])*start/distance),
                       (a[0]+(b[0]-a[0])*end/distance,a[1]+(b[1]-a[1])*end/distance)],
                      fill='#11636a',width=2)


def reference_background(result, language='vi', use_prepared=True):
    transform, indices, left, top = viewport(result['profile'],result['prediction'].shape)
    asset=prepared_map(result['metadata']['case_id']) if use_prepared else None
    if asset is not None:
        payload,info=asset
        if info['geometry_key']!=geometry_key(result['profile']) or not np.allclose(info['transform'],list(transform)[:6],rtol=0,atol=1e-9):
            raise ValueError('Prepared basemap does not match the analysis grid')
        return Image.open(io.BytesIO(payload)).convert('RGBA'),transform,indices
    hour=int(time.time()//3600)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            tiles=list(pool.map(lambda index:tile_png(*index,hour),indices))
    except Exception as exc:
        message=('Không tải được nền bản đồ để tạo PNG. Kiểm tra Internet rồi thử tạo lại gói tải xuống.'
                 if language=='vi' else
                 'Could not load the basemap for the PNG. Check your Internet connection and retry package creation.')
        raise BasemapUnavailable(message) from exc
    width,height=MAP_SIZE
    min_x=min(i[1] for i in indices);max_x=max(i[1] for i in indices)
    min_y=min(i[2] for i in indices);max_y=max(i[2] for i in indices)
    mosaic=Image.new('RGBA',((max_x-min_x+1)*256,(max_y-min_y+1)*256),'white')
    for (_,x,y),payload in zip(indices,tiles):
        with Image.open(io.BytesIO(payload)) as tile:
            mosaic.paste(tile.convert('RGBA'),((x-min_x)*256,(y-min_y)*256))
    tile_resolution=2*ORIGIN/(256*2**indices[0][0])
    box=(left-min_x*256,top-min_y*256,
         left-min_x*256+width*transform.a/tile_resolution,
         top-min_y*256+height*transform.a/tile_resolution)
    background=mosaic.transform(MAP_SIZE,Image.Transform.EXTENT,box,resample=Image.Resampling.BICUBIC)
    return background,transform,indices


def prediction_map(result, language='vi'):
    background,transform,indices=reference_background(result,language)
    width,height=MAP_SIZE
    _,footprint,rgba=map_layers(result,transform)
    if not footprint.any():
        raise ValueError('Prediction footprint does not overlap exported map')
    geographic=Image.alpha_composite(background,Image.fromarray(rgba))
    geographic=Image.composite(geographic,Image.new('RGBA',MAP_SIZE,'white'),Image.fromarray(footprint*255))
    draw=ImageDraw.Draw(geographic)
    h,w=result['prediction'].shape
    source=result['profile']['transform']
    corners=[source*p for p in [(0,0),(w,0),(w,h),(0,h)]]
    projector=Transformer.from_crs(result['profile']['crs'],'EPSG:3857',always_xy=True)
    pixels=[(~transform)*projector.transform(*p) for p in corners]
    dashed_outline(draw,pixels)
    # North points up on this Web Mercator map.
    draw.rounded_rectangle((width-58,10,width-10,88),radius=5,fill='white')
    draw.line((width-34,72,width-34,35),fill='#172B40',width=3)
    draw.polygon([(width-34,27),(width-42,42),(width-26,42)],fill='#172B40')
    font_path=str(Path(__file__).parent/'static/fonts/DejaVuSans.ttf') if (Path(__file__).parent/'static/fonts/DejaVuSans.ttf').is_file() else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    font=ImageFont.truetype(font_path,18)
    draw.text((width-41,10),'N',fill='#172B40',font=font)
    canvas=Image.new('RGB',CANVAS_SIZE,'white');canvas.paste(geographic.convert('RGB'),MAP_OFFSET)
    draw=ImageDraw.Draw(canvas);meta=result['metadata']
    title='Bản đồ vùng ngập dự đoán — Thanh Hóa' if language=='vi' else 'Predicted flood map — Thanh Hóa'
    draw.text((32,20),title,fill='#172B40',font=ImageFont.truetype(font_path,26))
    observed=meta['post_local'] if language=='vi' else datetime.strptime(meta['post_local'],'%d/%m/%Y %H:%M').strftime('%d %b %Y %H:%M')
    caption=(f"{meta['case_id']} · Quan sát radar: {observed} GMT+7" if language=='vi' else
             f"{meta['case_id']} · Radar observation: {observed} GMT+7")
    draw.text((32,65),caption,fill='#172B40',font=font)
    labels=(['Vùng ngập dự đoán','Vùng nước thường xuyên','Vùng thiếu tín hiệu radar','Phạm vi phân tích'] if language=='vi' else
            ['Predicted flood extent','Permanent water','Missing radar coverage','Analysis area'])
    for (x,y),label,color in zip([(32,1150),(544,1150),(32,1184),(544,1184)],labels,
                                 ['#06b6d4','#1d4ed8','#a826c3',None]):
        if color:
            draw.rectangle((x,y+3,x+18,y+21),fill=color)
        else:
            draw.line((x,y+3,x+18,y+3),fill='#11636a',width=2)
            draw.line((x,y+21,x+18,y+21),fill='#11636a',width=2)
        draw.text((x+30,y),label,fill='#172B40',font=font)
    warning=('Cần kiểm chứng trước khi sử dụng. Diện tích do AI ước tính, chưa phải diện tích ngập đã xác nhận.' if language=='vi' else
             'Verify before use. AI-estimated area, not confirmed flooded area.')
    context=('Nền địa danh tham chiếu dùng để định vị; không phải ảnh hiện trường ngày quan sát.' if language=='vi' else
             'The reference basemap provides location context; it is not imagery from the observation date.')
    small=ImageFont.truetype(font_path,16)
    for y,line in [(1225,warning),(1254,context),(1283,'© OpenStreetMap contributors · Style © OpenStreetMap France'),
                   (1312,'https://www.openstreetmap.org/copyright · GEOID-Flood: CC BY 4.0; modified Copernicus data')]:
        draw.text((32,y),line,fill='#172B40',font=small)
    buffer=io.BytesIO();canvas.save(buffer,format='PNG',compress_level=3)
    info=dict(crs='EPSG:3857',transform=list(transform)[:6],map_pixel_size=list(MAP_SIZE),map_offset=list(MAP_OFFSET),canvas_size=list(CANVAS_SIZE),
              extent_mode='analysis-footprint-only',outside_footprint='white',
              basemap_url_template=TILE_URL,zoom=indices[0][0],tile_indices=[list(i) for i in indices],
              class_colors={'1':[29,78,216,215],'2':[6,182,212,215],'255':[168,38,195,225]},
              bounds=list(array_bounds(height,width,transform)),context='Prepared reference basemap; historical radar-derived prediction')
    return buffer.getvalue(),info
