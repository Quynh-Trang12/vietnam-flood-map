"""Separate renderer experiment. Run this entry point in its own Streamlit process.

Reuse the production UI text at runtime instead of forking it or monkeypatching
shared modules. The two explicit substitutions fail closed if the UI changes.
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
if source.count(old) != 1 or source.count(old_note) != 1:
    raise RuntimeError('Production map integration changed; review SDK trial adapter before running.')
source = source.replace(old, new).replace(old_note, new_note)
exec(compile(source, str(entry), 'exec'), {
    '__file__': str(entry), '__name__': '__main__', 'sdk_map_html': sdk_map_html,
    'sdk_context_note': {
        'vi': 'Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Nền MapTiler cung cấp bối cảnh địa lý, không phải ảnh quan sát ngập.',
        'en': 'Zoom or pan to identify places. The MapTiler basemap provides geographic context, not a flood observation.',
    },
})
