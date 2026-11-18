"""Pinned RTC fusion demo: label-free inputs, native three-class argmax, CPU serving."""
import csv
import io
import json
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache

import numpy as np
import rasterio
from rasterio.io import MemoryFile
from demo_io import catalogue as base_catalogue, pixel_areas, png_bytes, sha256, resolve_input, RAW, ROOT, WORKSPACE

DEPLOYED = (ROOT/'deployment-manifest.json').is_file()
PROJECT = ROOT if DEPLOYED else WORKSPACE
TRAINING = ROOT/'architecture' if DEPLOYED else PROJECT/'04-Implementation/Training/Expanded-Flood'
sys.path.insert(0, str(TRAINING))
BANDS = [2,3,4,8,11,12]  # Training contract: B02/B03/B04/B08/B11/B12 (one-based).
from map_export import prediction_map

CHECKPOINT = ROOT/'resources/model/selected.pt' if DEPLOYED else PROJECT/'03-Data-and-Models/Models/Experimental/Expanded-Flood-Ablation/expanded_winner/selected.pt'
EXPORT_VERSION = 'geographic-png-analysis-only-v2'
MODEL_SHA = '8d41bd9ee0c8dda7cda28ae173e4fa8fddb4bc5f2a006bf2770cb7cbeb5198aa'
EVALUATION = ROOT/'resources/model/comparison.json' if DEPLOYED else PROJECT/'02-Research-and-Evidence/Evidence/Model-Evaluation/GRD-RTC-Native/comparison.json'
PALETTE = np.array([[215,227,234], [29,78,216], [6,182,212], [168,38,195]], dtype='uint8')


def model_signature():
    return MODEL_SHA + ':rtc-fusion-argmax-v1'


def catalogue():
    cases = []
    for source in base_catalogue():
        case = dict(source)
        if DEPLOYED:
            case['rtc_paths'] = {slot:str(ROOT/path) for slot,path in case['deployed_inputs'].items()}
            cases.append(case)
            continue
        paths = {'sar': resolve_input(RAW / case['post_file'])}
        for slot, token in [('optical','s2l2a'), ('cloud','cloudmask')]:
            name = f"{case['key']}_{token}_pre_20240810T032519.tif"
            candidates = [PROJECT / '03-Data-and-Models/Data/Processed/Multi-Event' / name,
                          PROJECT / '03-Data-and-Models/Data/Processed/Sprint1/fusion' / name]
            paths[slot] = next((resolve_input(p) for p in candidates if Path(resolve_input(p)).is_file()), None)
        # Never silently substitute a missing input or use labels to fill it.
        if not all(paths.values()):
            continue
        case['rtc_paths'] = {k:str(v) for k,v in paths.items()}
        case['optical_local'] = '10/08/2024 10:25'
        case['evaluation_role'] = 'EMSR754 exposed development demo; excluded from independent confirmation'
        case['caveats'] = ['Validation metrics are not accuracy on this Vietnam tile.']
        cases.append(case)
    return cases


@lru_cache(maxsize=1)
def _model_runtime():
    """Load the CPU inference stack only when an analysis actually needs it.

    Opening the map/catalogue must not wait for torch and torchvision imports.
    The same modules and network are used for every subsequent inference.
    """
    import torch
    from flood_network import Network
    return torch, Network


def load_model(expected_signature=None):
    if expected_signature is not None and expected_signature != model_signature():
        raise ValueError('RTC model signature changed.')
    if sha256(CHECKPOINT) != MODEL_SHA:
        raise ValueError('RTC checkpoint hash mismatch.')
    # GPU access remains exclusively with the protected worker; interactive serving uses CPU.
    torch, Network = _model_runtime()
    device = torch.device('cpu')
    torch.set_num_threads(4)
    model = Network(9).to(device)
    model.load_state_dict(torch.load(CHECKPOINT, map_location=device, weights_only=True))
    return model.eval(), device


def read_inputs(case):
    arrays, masks, profiles, hashes = {}, {}, {}, {}
    for slot, path in case['rtc_paths'].items():
        with rasterio.open(path) as src:
            bands = BANDS if slot == 'optical' else (1 if slot == 'cloud' else None)
            arrays[slot] = src.read(indexes=bands)
            mask = src.read_masks(indexes=bands) > 0
            masks[slot] = mask.all(0) if mask.ndim == 3 else mask
            profiles[slot] = src.profile
        hashes[Path(path).name] = sha256(path)
    profile = profiles['sar']
    if profile['count'] != 2 or profile['crs'] is None:
        raise ValueError('Expected georeferenced VV/VH RTC input.')
    for other in profiles.values():
        if any(profile[k] != other[k] for k in ('height','width','transform','crs')):
            raise ValueError('Optical, cloud and RTC grids differ.')
    if profile['height'] % 256 or profile['width'] % 256:
        raise ValueError('RTC demo requires complete 256-pixel windows.')
    if hashes[Path(case['rtc_paths']['sar']).name] != case['input_sha256'][case['post_file']]:
        raise ValueError('RTC image differs from admitted input.')
    sar, optical, cloud = (arrays[k] for k in ('sar','optical','cloud'))
    valid = masks['sar'] & np.isfinite(sar).all(0) & (sar > 0).all(0)
    if not valid.any():
        raise ValueError('No valid RTC observations.')
    # Same float32 conversion and masks as Expanded-Flood/flood_dataset.py, without label access.
    radar = (np.clip(10*np.log10(np.maximum(sar,1e-8)),-40,10)+40)/50
    radar = np.nan_to_num(radar,nan=0,posinf=0,neginf=0); radar[:,~valid] = 0
    clear = masks['optical'] & masks['cloud'] & (cloud == 0) & (optical > 0).any(0)
    reflectance = np.clip(optical.astype('float32')/10000,0,1); reflectance[:,~clear] = 0
    features = np.concatenate([radar,reflectance,clear[None].astype('float32')]).astype('float32')
    if not np.isfinite(features).all():
        raise ValueError('Non-finite fusion input.')
    return features, valid, clear, profile, hashes


def infer(case, model, device):
    torch, _ = _model_runtime()
    started = time.perf_counter()
    features, valid, clear, profile, hashes = read_inputs(case)
    h,w = valid.shape
    prediction = np.full((h,w),255,dtype='uint8')
    with torch.inference_mode():
        for y in range(0,h,256):
            for x in range(0,w,256):
                tile = torch.from_numpy(features[:,y:y+256,x:x+256].copy())[None].to(device)
                prediction[y:y+256,x:x+256] = model(tile).argmax(1)[0].cpu().numpy().astype('uint8')
    prediction[~valid] = 255
    areas = pixel_areas(profile)
    evidence = json.loads(EVALUATION.read_text())
    if evidence['incumbent_sha256'] != MODEL_SHA:
        raise ValueError('Evaluation refers to another checkpoint.')
    scores = evidence['metrics']['rtc']['native']
    meta = dict(case_id=case['key'], event_id=case['event_id'], country=case['country'],
                place=case['place'], area_name=case['area_name'], pre_local=case['optical_local'],
                post_local=case['post_local'], pre_date='20240810T032519', post_date='20240912T225139',
                model='RTC fusion ResNet-18 U-Net · epoch 9', model_sha256=MODEL_SHA,
                operating_point='three-class argmax; no calibrated threshold', flood_class=2,
                class_codes={'0':'land / non-water','1':'permanent water','2':'flood','255':'missing RTC observation'},
                validation_macro_flood_iou=scores['macro_event_iou_positive'],
                validation_pooled_flood_iou=scores['pooled']['iou'], evaluation_source=str(EVALUATION),
                evaluation_scope='14 validation events; native RTC support; not independent final test',
                input_sha256=hashes, input_files=case['rtc_paths'],
                channel_order=['post_VV','post_VH','pre_B02','pre_B03','pre_B04','pre_B08','pre_B11','pre_B12','pre_clear'],
                normalization='train-fitted mean/std stored in checkpoint',
                bounds_wgs84=case['bounds_wgs84'], shape=[h,w], crs=profile['crs'].to_string(),
                transform=list(profile['transform'])[:6], valid_pixels=int(valid.sum()), total_pixels=int(valid.size),
                predicted_flood_pixels=int((prediction==2).sum()),
                flood_area_km2=float(areas[prediction==2].sum()/1e6),
                permanent_water_area_km2=float(areas[prediction==1].sum()/1e6),
                valid_area_km2=float(areas[valid].sum()/1e6), footprint_area_km2=float(areas.sum()/1e6),
                optical_clear_fraction=float(clear.mean()), device=str(device),
                generated_utc=datetime.now(timezone.utc).isoformat(),
                limitations=['Research estimate; verify before reporting.',
                            'EMSR754 is exposed development data, not independent confirmation.',
                            'Reference labels are never opened during inference.',
                            'Cloudy optical pixels are zeroed; RTC may still support prediction.'])
    meta['analysis_seconds'] = time.perf_counter()-started
    return dict(prediction=prediction, profile=profile, metadata=meta, areas=areas,
                features=features, valid=valid, clear=clear)


def source_images(result):
    f = result['features']
    # Natural RGB from B04/B03/B02 with fixed reflectance stretch and display gamma.
    rgb = np.moveaxis(np.clip(f[[4,3,2]]/0.3,0,1)**(1/2.2),0,-1)
    rgb = (rgb*255).astype('uint8'); rgb[~result['clear']] = PALETTE[3]
    # Fixed false-color radar: VV, VH, and normalized VV/VH contrast; no class claims.
    vv = np.clip((f[0]*50-40+25)/25,0,1)
    vh = np.clip((f[1]*50-40+32)/27,0,1)
    ratio = np.clip(((f[0]-f[1])*50)/15,0,1)
    radar = (np.stack([vh,vv,0.5*vv+0.5*ratio],-1)**0.7*255).astype('uint8')
    radar[~result['valid']] = PALETTE[3]
    return png_bytes(rgb), png_bytes(radar)


def export_bundle(result, language='vi'):
    meta = dict(result['metadata'],report_language=language)
    pred = result['prediction']
    profile = result['profile'].copy()
    profile.update(driver='GTiff', count=1, dtype='uint8', nodata=255, compress='deflate')
    with MemoryFile() as mem:
        with mem.open(**profile) as ds:
            ds.write(pred,1)
            ds.update_tags(model_sha256=MODEL_SHA,classes=json.dumps(meta['class_codes']))
        geotiff = mem.read()
    preview, preview_info = prediction_map(result, language)
    meta['preview_map'] = preview_info
    stream = io.StringIO(newline='')
    fields = {'case_id':meta['case_id'],'flood_area_km2':meta['flood_area_km2'],
              'permanent_water_area_km2':meta['permanent_water_area_km2'],'valid_area_km2':meta['valid_area_km2']}
    writer=csv.DictWriter(stream,fieldnames=list(fields));writer.writeheader();writer.writerow(fields)
    files={'prediction.tif':geotiff,'prediction.png':preview,
           'summary.csv':stream.getvalue().encode('utf-8-sig'),
           'metadata.json':json.dumps(meta,ensure_ascii=False,indent=2).encode(),
           'README.txt': ((
               'KẾT QUẢ PHÂN TÍCH NGẬP THỬ NGHIỆM\n'
               'Cần kiểm chứng trước khi sử dụng. Diện tích do AI ước tính, chưa phải diện tích ngập đã xác nhận.\n'
               'prediction.tif: bản đồ có tọa độ; prediction.png: nền địa danh và lớp dự đoán trong phạm vi phân tích, có chú giải.\n'
               'summary.csv: bảng diện tích; metadata.json: nguồn dữ liệu và thông tin kỹ thuật.\n'
               'Mã lớp: 0 = đất/vùng không có nước; 1 = nước thường xuyên; 2 = ngập dự đoán; 255 = thiếu tín hiệu radar.\n'
               'Xanh dương = nước thường xuyên; xanh lơ = ngập dự đoán; tím = thiếu tín hiệu radar, không tính diện tích.\n'
               'Điểm validation không phải kết quả kiểm tra xác nhận độc lập.\n'
               'Nguồn: GEOID-Flood, kho links-ads/geoid-flood trên Hugging Face; CC BY 4.0; chứa dữ liệu Copernicus đã chỉnh sửa.\n'
           ) if language=='vi' else (
               'EXPERIMENTAL FLOOD ANALYSIS RESULTS\n'
               'Verify before use. AI-estimated area, not confirmed flooded area.\n'
               'prediction.tif: georeferenced map; prediction.png: place-name basemap and prediction within the analysis footprint, with a legend.\n'
               'summary.csv: area table; metadata.json: data provenance and technical details.\n'
               'Class codes: 0 = land/non-water; 1 = permanent water; 2 = predicted flood; 255 = missing radar signal.\n'
               'Blue = permanent water; cyan = predicted flood; purple = missing radar signal, excluded from area calculations.\n'
               'Validation scores are not independent confirmation-test results.\n'
               'Source: GEOID-Flood, links-ads/geoid-flood repository on Hugging Face; CC BY 4.0; contains modified Copernicus data.\n'
           )).encode('utf-8')}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=1) as archive:
        for name,content in files.items():archive.writestr(name,content)
    return buffer.getvalue()
