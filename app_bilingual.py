"""Map workspace for Vietnamese post-flood report preparation."""
import time
import json
from pathlib import Path
import streamlit as st
from functools import partial
from concurrent.futures import ThreadPoolExecutor
ROOT = Path(__file__).resolve().parent
if st.query_params.get('demo') == '1' and not st.session_state.get('client_demo_initialized'):
    st.session_state.setdefault('selected_area', 1)
    st.session_state.setdefault('language', 'en')
    st.session_state.client_demo_initialized = True
language = st.session_state.get('language', 'vi')
# Send page geometry and styles before importing the ML runtime or emitting widgets.
# Otherwise the first visible frame uses Streamlit's centered/default layout.
st.set_page_config(page_title='Vietnam flood map' if language == 'en' else 'Bản đồ ngập Việt Nam', page_icon=':material/water:', layout='wide', initial_sidebar_state='auto')
# Create the sidebar before the first main-page element, so its desktop width
# is known before the app content is painted (auto still collapses on mobile).
sidebar_layout = st.sidebar.container(key='sidebar-layout', gap='small')
# Markdown renders the style with its element. st.html inserts styles in a
# frontend effect, which can run after the widgets have already been painted.
with st.container(key='bootstrap-assets'):
    st.markdown('<style>' + (ROOT / 'ui_bilingual.css').read_text() + '</style>', unsafe_allow_html=True)
    st.html('<script>' + (ROOT / 'cloud_chrome.js').read_text() + '</script>', unsafe_allow_javascript=True)
from pipeline_rtc import catalogue, infer, load_model, model_signature, source_images, EXPORT_VERSION
from bilingual_support import translate, area_name, local_date, localized_map, localized_bundle, message, radar_legend
language_changed = st.session_state.get('last_language', language) != language
tr = partial(translate, language=language)
ui = partial(message, language=language)
if language_changed:
    st.session_state.pop(f'area_{language}', None)
    st.session_state.pop('workspace-tab', None)
    st.session_state.tab_default = st.session_state.get('logical_tab', 0)
st.session_state.last_language = language

def interaction_controls(language, bounds):
    pan='Bật/tắt kéo bản đồ' if language=='vi' else 'Toggle map interaction'
    reset='Về khu vực phân tích' if language=='vi' else 'Reset to analysis area'
    return f'''<div class="map-compact-controls">
<button type="button" class="map-pan-control" title="{pan}" aria-label="{pan}" aria-pressed="false">

</button>
<button type="button" class="map-reset-control" title="{reset}" aria-label="{reset}">

</button></div>
<script>
(() => {{
 const root=document.querySelector('.map-compact-controls');
 if(!root)return;
 const pan=root.querySelector('.map-pan-control');
 pan.onclick=()=>{{const on=pan.getAttribute('aria-pressed')==='true';pan.setAttribute('aria-pressed',String(!on));}};
 root.querySelector('.map-reset-control').onclick=()=>{{
  const frame=root.closest('.st-key-map-canvas').querySelector('iframe');
  const map=frame?.contentWindow.demoMap;
  if(map) map.fitBounds({json.dumps(bounds)},{{padding:[24,24],animate:false}});
 }};
}})();
</script>'''

@st.cache_resource
def model_future(signature):
    # Warm weights in a worker while the map is rendered. No predictions or
    # Streamlit calls run in this worker; all sessions share the same future.
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='rtc-model')
    future = executor.submit(load_model, signature)
    executor.shutdown(wait=False)
    return future

def vn(value, places=1):
    formatted = f'{value:,.{places}f}'
    return formatted if language == 'en' else formatted.replace(',', '_').replace('.', ',').replace('_', '.')
signature = model_signature()
if st.session_state.get('active_model_signature') != signature:
    for key in ('result', 'bundle', 'bundle_language', 'error'):
        st.session_state.pop(key, None)
    st.session_state.active_model_signature = signature
cases = catalogue()
if not cases:
    st.warning(tr('Chưa có cặp ảnh Việt Nam đạt kiểm tra đầu vào. Không thể chạy phân tích bằng ảnh chưa phù hợp.'))
    st.stop()
pending_model = model_future(signature)
with sidebar_layout:
    with st.container(key='brand'):
        st.header(tr('Flood Mapping'), icon=':material/water:')
    with st.container(key='sidebar-scope'):
        st.selectbox(tr('Đợt mưa lũ'), [tr('Tháng 9/2024 — Thanh Hóa')], key='event')
        index = st.pills(tr('Khu vực muốn xem'), list(range(len(cases))), format_func=lambda i: area_name(cases[i]['area_name'], language), default=st.session_state.get('selected_area', 0), required=True, key=f'area_{language}', wrap=True, width='stretch')
    st.session_state.selected_area = index
    case = cases[index]
    if st.session_state.get('case_key') != case['key']:
        for key in ('result', 'bundle', 'error'):
            st.session_state.pop(key, None)
        st.session_state.case_key = case['key']
    with st.container(key='sidebar-dates'):
        st.html(f'<dl class="observation-dates"><dt>{ui("before_title")}</dt><dd>{local_date(case["optical_local"], language)} <small>GMT+7</small></dd><dt>{ui("observation_title")}</dt><dd>{local_date(case["post_local"], language)} <small>GMT+7</small></dd></dl>')
    st.badge(ui('input_badge'), color='green', icon=':material/check_circle:')
    run = st.button(tr('Phân tích khu vực này'), type='primary', icon=':material/play_arrow:', width='stretch', key='analyze')
    with st.container(key='sidebar-note'):
        st.markdown(tr('**Phạm vi dữ liệu**'))
        st.markdown(ui('coverage'))
    st.caption(tr('Bản thử nghiệm nghiên cứu · dữ liệu lịch sử'))
with st.container(key='app-header'):
    heading, status = st.columns([3, 2], vertical_alignment='center')
    with heading:
        with st.container(key='title-block', gap='small'):
            st.html('<h1>' + tr('Bản đồ ngập Việt Nam') + '</h1>' + tr('<div class="workspace-subtitle">Thanh Hóa – Mưa lũ tháng 9/2024</div><p class="mobile-scope-hint">Mở thanh bên từ mép trái để chọn khu vực và chạy phân tích.</p>'))
    with status:
        with st.container(horizontal=True, horizontal_alignment='right', vertical_alignment='center', key='language-controls'):
            st.segmented_control('Language / Ngôn ngữ', ['vi', 'en'], format_func=lambda code: code.upper(), default=None if 'language' in st.session_state else 'vi', required=True, key='language', label_visibility='collapsed', width='content')
            st.badge(tr('Bản thử nghiệm'), color='orange', icon=':material/science:')
tab_labels = [tr(label) for label in ['Bản đồ', 'Ảnh vệ tinh đầu vào', 'Nguồn & độ tin cậy']]
active_tab = st.session_state.get('tab_default', 0)
tabs = st.tabs(tab_labels, default=tab_labels[active_tab], key='workspace-tab', on_change='rerun')
for tab_index, tab in enumerate(tabs):
    if tab.open:
        st.session_state.logical_tab = tab_index
result = st.session_state.get('result')
if result and case.get('reference_alignment') and result['metadata'].get('reference_alignment') != case['reference_alignment']:
    result['metadata']['reference_alignment'] = case['reference_alignment']
    st.session_state.pop('bundle', None)
if run:
    st.session_state.pop('result', None)
    st.session_state.pop('bundle', None)
    st.session_state.pop('error', None)
    try:
        started = time.perf_counter()
        with st.spinner(tr('Đang đọc ảnh và tìm các vùng nghi ngập…')):
            model, device = pending_model.result()
            result = infer(case, model, device)
            result['metadata']['request_to_result_seconds'] = time.perf_counter() - started
        st.session_state.result = result
    except Exception as exc:
        if pending_model.done() and pending_model.exception() is not None:
            model_future.clear()
        result = None
        st.session_state.error = str(exc)
if 'error' in st.session_state:
    st.error(tr('Chưa tạo được bản đồ. Hãy thử lại hoặc chọn khu vực khác.'))
    st.code(st.session_state.error)
with tabs[0]:
    if tabs[0].open:
        map_column, result_column = st.columns([3.5, 1.3], gap='medium')
        with map_column:
            with st.container(border=True, key='map-panel', gap='xsmall'):
                show = st.session_state.get('overlay', True)
                with st.container(key='map-canvas', height=440, border=False):
                    with st.container(key='map-controls'):
                        st.html(interaction_controls(language, [[case['bounds_wgs84'][1],case['bounds_wgs84'][0]],[case['bounds_wgs84'][3],case['bounds_wgs84'][2]]]), unsafe_allow_javascript=True)
                    st.iframe(localized_map(case, result, show and result is not None, language), height='stretch', alt=tr('Bản đồ Thanh Hóa có địa danh, ranh khu vực khảo sát và lớp AI nghi ngập'))
                st.html(radar_legend(language))
            with st.container(key='map-note'):
                st.caption(tr('Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Khu vực phân tích dùng nền tham chiếu đã chuẩn bị; bản đồ xung quanh cần Internet. © OpenStreetMap / OpenStreetMap France.'))
        with result_column:
            with st.container(border=True, key='results-panel', gap='small'):
                st.subheader(tr('Kết quả'), icon=':material/analytics:')
                st.toggle(tr('Lớp vùng ngập dự đoán'), value=True, disabled=result is None, key='overlay')
                if result:
                    meta = result['metadata']
                    st.html(f'<p class="verification-required" role="note">{ui("verification_required")}</p>')
                    with st.container(key='result-area'):
                        st.metric(tr('Diện tích nghi ngập'), f'{vn(meta['flood_area_km2'] * 100, 0)} ha')
                        st.caption(ui('flood_estimate', area=vn(meta['flood_area_km2'], 2)))
                    st.markdown(ui('radar_coverage_heading'))
                    st.markdown(ui('coverage_summary', area=vn(meta['valid_area_km2']), percent=vn(100 * meta['valid_area_km2'] / meta['footprint_area_km2'], 2)))
                    with st.container(key='result-notes'):
                        st.markdown(ui('result_caution'))
                    try:
                        export_token = (meta['model_sha256'], meta['generated_utc'], EXPORT_VERSION)
                        if st.session_state.get('export_token') != export_token:
                            st.session_state.export_token = export_token
                            st.session_state.localized_bundles = {}
                        if language not in st.session_state.localized_bundles:
                            with st.spinner(ui('packaging_map')):
                                st.session_state.localized_bundles[language] = localized_bundle(result, language)
                        st.session_state.bundle = st.session_state.localized_bundles[language]
                        st.download_button(tr('Tải kết quả'), st.session_state.bundle, file_name=f'ThanhHoa_{case['key']}_20240913_{language}.zip', mime='application/zip', icon=':material/download:', width='stretch', key='download', on_click='ignore')
                    except Exception as exc:
                        st.error(tr('Chưa tạo được gói tải xuống; kết quả phân tích vẫn được giữ.'))
                        if st.button(tr('Thử tạo lại gói tải xuống'), key='retry-export'):
                            st.session_state.get('localized_bundles', {}).pop(language, None)
                            st.rerun()
                        st.code(str(exc))
                    st.caption(tr('Bản đồ, bảng diện tích và ghi chú nguồn trong một file ZIP.'))
                else:
                    st.markdown(tr('**Chưa có kết quả**'))
                    st.markdown(tr('Chọn khu vực ở thanh bên trái rồi bấm **Phân tích khu vực này**.'))
                    st.caption(tr('Kết quả sẽ gồm vùng nghi ngập, diện tích và gói bản đồ để tải về.'))
        with st.container(key='workspace-footer'):
            st.html(f'<p class="claim-text">{ui("observation_note")}</p>')
with tabs[1]:
    if tabs[1].open:
        st.subheader(tr('Ảnh dùng trong phân tích'))
        st.markdown(ui('image_intro'))
        if result:
            if st.session_state.get('source_image_token') != result['metadata']['generated_utc']:
                st.session_state.source_image_token = result['metadata']['generated_utc']
                st.session_state.source_image_bytes = source_images(result)
            optical_png, radar_png = st.session_state.source_image_bytes
            with st.container(key='satellite-pair'):
                cols = st.columns(2, gap='small', wrap=True)
                with cols[0]:
                    st.html(f'<h3 class="image-frame-title">{ui("before_title")}</h3>')
                    st.image(optical_png, caption=ui('optical_caption', date=local_date(case['optical_local'], language)), width='stretch', alt=ui('optical_alt'))
                with cols[1]:
                    st.html(f'<h3 class="image-frame-title">{ui("observation_title")}</h3>')
                    st.image(radar_png, caption=ui('radar_caption', date=local_date(case['post_local'], language)), width='stretch', alt=ui('radar_alt'))
            with st.container(key='image-reading-notes'):
                st.markdown(f"**{ui('reading_title')}**")
                st.markdown(ui('optical_help'))
                st.markdown(ui('radar_help'))
                st.markdown(ui('radar_channels'))
                st.markdown(ui('image_timing'))
        else:
            st.info(tr('Chạy phân tích ở thanh bên để mở hai ảnh nguồn của khu vực đã chọn.'))

with tabs[2]:
    if tabs[2].open:
        with st.container(key='report-notes'):
            st.subheader(tr('Nguồn dữ liệu và độ tin cậy'))
            origin, verification = st.columns(2, gap='large')
            with origin:
                with st.container(key='source-origin'):
                    st.markdown(tr('**Nguồn ảnh và quyền sử dụng**'))
                    st.markdown(ui('source_origin'))
                    st.markdown(tr('[Dataset GEOID-Flood](https://huggingface.co/datasets/links-ads/geoid-flood) · [Đợt lũ trên Copernicus](https://mapping.emergency.copernicus.eu/activations/EMSR754/)'))
            with verification:
                with st.container(key='source-verification'):
                    st.markdown(tr('**Phạm vi và kiểm tra đầu vào**'))
                    st.markdown(ui('model_scope'))
                    st.markdown(ui('reference_timing'))
            st.warning(ui('validation'))
            st.markdown(f"**{ui('concept_title')}**")
            st.markdown(ui('rtc_definition'))
            st.markdown(ui('concept_help'))
            st.subheader(tr('Thông tin kỹ thuật để kiểm lại'))
            st.caption(ui('technical_context', case=case['key']))
            technical_columns = st.columns(2, gap='large') if result else [st.container()]
            inputs = technical_columns[0]
            with inputs:
                with st.expander(tr('Đầu vào'), expanded=False):
                    st.json(case, expanded=True)
            if result:
                with technical_columns[1]:
                    with st.expander(tr('Kết quả'), expanded=False):
                        st.json(result['metadata'], expanded=True)
