"""Separate renderer experiment. Run this entry point in its own Streamlit process.

Reuse the production UI text at runtime instead of forking it or monkeypatching
shared modules. Explicit substitutions fail closed if the UI changes.
The production streamlit_app.py entry point never imports this file.
"""
from pathlib import Path

from map_view_sdk import map_html as sdk_map_html

root = Path(__file__).resolve().parent
entry = root / 'app_bilingual.py'
source = entry.read_text()
old = 'localized_map(case, result, show and result is not None, language, maptiler_api_key=maptiler_api_key)'
new = 'sdk_map_html(case, result, show and result is not None, language=language, maptiler_api_key=maptiler_api_key)'
old_note = "st.caption(tr('Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Khu vực phân tích dùng nền tham chiếu đã chuẩn bị; bản đồ xung quanh cần Internet. © OpenStreetMap / OpenStreetMap France.'))"
new_note = "st.caption(sdk_context_note[language])"
old_css = "st.html(ROOT / 'ui_bilingual.css')"
replacements = ((old, new), (old_note, new_note), (old_css, 'st.html(sdk_initial_css)'))
for before, after in replacements:
    if source.count(before) != 1:
        raise RuntimeError('Production map integration changed; review SDK trial adapter before running.')
    source = source.replace(before, after)
# Streamlit streams the sidebar before the custom header. Apply the existing
# layout rules to its early native root, rather than switching them on later.
sdk_initial_css = '<style>' + (root / 'ui_bilingual.css').read_text().replace(
    'body:has(.st-key-app-header)', 'body:has(.stApp)') + '</style>'
exec(compile(source, str(entry), 'exec'), {
    '__file__': str(entry), '__name__': '__main__', 'sdk_map_html': sdk_map_html,
    'sdk_initial_css': sdk_initial_css,
    'sdk_context_note': {
        'vi': 'Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Nền MapTiler cung cấp bối cảnh địa lý, không phải ảnh quan sát ngập.',
        'en': 'Zoom or pan to identify places. The MapTiler basemap provides geographic context, not a flood observation.',
    },
})
