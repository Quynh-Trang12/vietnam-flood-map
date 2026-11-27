"""Separate renderer experiment. Run this entry point in its own Streamlit process.

Reuse the production UI text at runtime instead of forking it or monkeypatching
shared modules. Explicit substitutions fail closed if the UI changes.
The production streamlit_app.py entry point never imports this file.
"""
from pathlib import Path
import json
import tomllib

from map_view_sdk import map_html as sdk_map_html

root = Path(__file__).resolve().parent
entry = root / 'app_bilingual.py'
source = entry.read_text()
old = 'localized_map(case, result, show and result is not None, language, maptiler_api_key=maptiler_api_key)'
new = 'sdk_map_html(case, result, show and result is not None, language=language, maptiler_api_key=maptiler_api_key)'
old_note = "st.caption(tr('Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Khu vực phân tích dùng nền tham chiếu đã chuẩn bị; bản đồ xung quanh cần Internet. © OpenStreetMap / OpenStreetMap France.'))"
new_note = "st.caption(sdk_context_note[language])"
old_css = "st.html(ROOT / 'ui_bilingual.css')"
old_bootstrap = "(ROOT / 'cloud_chrome.js').read_text()"
replacements = ((old, new), (old_note, new_note), (old_css, 'st.html(sdk_initial_css)'),
                (old_bootstrap, 'sdk_bootstrap_js'))
for before, after in replacements:
    if source.count(before) != 1:
        raise RuntimeError('Production map integration changed; review SDK trial adapter before running.')
    source = source.replace(before, after)
# Streamlit streams the sidebar before the custom header. Apply the existing
# layout rules to its early native root, rather than switching them on later.
sdk_initial_css = '<style>' + (root / 'ui_bilingual.css').read_text().replace(
    'body:has(.st-key-app-header)', 'body:has(.stApp)') + '</style>'
# Start the observed above-fold font weights together, rather than waiting for
# each widget to discover its face. URLs come from the theme, including versions.
theme = tomllib.loads((root / '.streamlit/config.toml').read_text())['theme']
font_urls = [face['url'] for face in theme['fontFaces']
             if str(face.get('weight')) in ('400', '500', '600')]
sdk_bootstrap_js = r'''
(() => {
 const preload = (url, base=document.baseURI) => {
  const href=new URL(url,base).href;
  if([...document.querySelectorAll('link[rel="preload"][as="font"]')].some(link=>link.href===href))return;
  const link=document.createElement('link');
  link.rel='preload';link.as='font';link.type='font/woff2';link.crossOrigin='anonymous';
  link.href=href;link.dataset.floodFontPreload='true';document.head.append(link);
 };
 for(const url of __FONT_URLS__)preload(url);
 // Use the installed stylesheet's URL, not a hard-coded Streamlit build hash.
 for(const sheet of document.styleSheets){
  let rules;try{rules=sheet.cssRules;}catch{continue;}
  for(const rule of rules){
   if(rule.type!==CSSRule.FONT_FACE_RULE || !rule.style.fontFamily.includes('Material Symbols Rounded'))continue;
   const match=rule.style.src.match(/url\(([^)]+)\)/);
   if(match)preload(match[1].trim().replace(/^["']|["']$/g,''),sheet.href||document.baseURI);
   return;
  }
 }
})();
'''.replace('__FONT_URLS__', json.dumps(font_urls).replace('<', r'\u003c'))
sdk_bootstrap_js += (root / 'cloud_chrome.js').read_text()
exec(compile(source, str(entry), 'exec'), {
    '__file__': str(entry), '__name__': '__main__', 'sdk_map_html': sdk_map_html,
    'sdk_initial_css': sdk_initial_css,
    'sdk_bootstrap_js': sdk_bootstrap_js,
    'sdk_context_note': {
        'vi': 'Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Nền MapTiler cung cấp bối cảnh địa lý, không phải ảnh quan sát ngập.',
        'en': 'Zoom or pan to identify places. The MapTiler basemap provides geographic context, not a flood observation.',
    },
})
