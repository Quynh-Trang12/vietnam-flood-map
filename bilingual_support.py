"""Presentation-only localization for the separate bilingual demo.

The approved app, processing modules and source records are not modified.
Language is passed explicitly; no shared mutable language state is used.
"""
import csv
import html
import io
import json
import zipfile
from datetime import datetime
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from demo_io import png_bytes, LEGACY_COLORS as COLORS
from map_view import map_html

EN = {'Bản đồ ngập Việt Nam': 'Vietnam flood map',
 'Bản thử nghiệm': 'Prototype',
 'Bản đồ': 'Map',
 'Ảnh vệ tinh': 'Satellite images',
 'Nguồn & độ tin cậy': 'Sources & reliability',
 'Đợt mưa lũ': 'Flood event',
 'Tháng 9/2024 — Thanh Hóa': 'Sep 2024 · Thanh Hóa',
 'Khu vực muốn xem': 'Study area',
 'Cặp ảnh cách 12 ngày · đã kiểm': 'Checked · 12-day pair',
 'Phân tích khu vực này': 'Analyze area',
 '**Phạm vi dữ liệu**': '**Data coverage**',
 'Bốn ô ảnh lân cận tại Thanh Hóa, không phải ranh phường/xã hoặc toàn tỉnh.': 'Four adjacent tiles; not '
                                                                               'wards or province-wide '
                                                                               'coverage.',
 'Prototype nghiên cứu · dữ liệu lịch sử': 'Research prototype · historical data',
 'Chưa có cặp ảnh Việt Nam đạt kiểm tra đầu vào. Không thể chạy phân tích bằng ảnh chưa phù hợp.': 'No valid '
                                                                                                   'Vietnamese '
                                                                                                   'image '
                                                                                                   'pairs. '
                                                                                                   'Prepare '
                                                                                                   'eligible '
                                                                                                   'data '
                                                                                                   'before '
                                                                                                   'analysis.',
 'Đang đọc ảnh và tìm các vùng nghi ngập…': 'Analyzing imagery…',
 'Chưa tạo được bản đồ. Hãy thử lại hoặc chọn khu vực khác.': 'Analysis failed. Retry or choose another '
                                                              'area.',
 'Kết quả': 'Results',
 'Lớp nghi ngập': 'Flood overlay',
 'Cần đối chiếu': 'Verify before use',
 'Diện tích nghi ngập': 'Suspected flood area',
 'Khoảng ': 'About ',
 ' km² được mô hình đánh dấu.': ' km² flagged by AI.',
 '**Vùng có đủ ảnh**': '**Valid coverage**',
 '% khu vực': '% of area',
 'Ước tính AI, chưa phải diện tích ngập đã xác nhận.': 'AI estimate; flooding is unconfirmed.',
 'Tải kết quả': 'Download',
 'Chưa tạo được file tải; kết quả vẫn được giữ.': 'Download failed. Analysis retained.',
 'Thử đóng gói lại': 'Retry download',
 'Bản đồ, bảng diện tích và ghi chú nguồn trong một file ZIP.': 'ZIP: map, area table and source notes.',
 '**Chưa có kết quả**': '**No result yet**',
 'Chọn khu vực ở thanh bên trái rồi bấm **Phân tích khu vực này**.': 'Choose an area, then **Analyze area**.',
 'Kết quả sẽ gồm vùng nghi ngập, diện tích và gói bản đồ để tải về.': 'View flood estimates and download the '
                                                                      'map.',
 'Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Nền địa danh © OpenStreetMap / OpenStreetMap France cần Internet.': 'Zoom '
                                                                                                                      'or '
                                                                                                                      'drag '
                                                                                                                      'to '
                                                                                                                      'explore. '
                                                                                                                      'Basemap '
                                                                                                                      'needs '
                                                                                                                      'Internet.',
 'Bản đồ Thanh Hóa có địa danh, ranh khu vực khảo sát và lớp AI nghi ngập': 'Map of Thanh Hóa with place '
                                                                            'names, study-area boundary and '
                                                                            'AI suspected flooding',
 'Ảnh dùng trong phân tích': 'Source images',
 'Radar ghi phản hồi của bề mặt nên có màu xám, không giống ảnh chụp thông thường. Màu tối không tự có nghĩa là ngập; mô hình so sánh hai lần chụp để tìm vùng nghi ngập.': 'Radar '
                                                                                                                                                                            'shows '
                                                                                                                                                                            'surface '
                                                                                                                                                                            'reflections, '
                                                                                                                                                                            'not '
                                                                                                                                                                            'photos. '
                                                                                                                                                                            'Dark '
                                                                                                                                                                            'pixels '
                                                                                                                                                                            'alone '
                                                                                                                                                                            'do '
                                                                                                                                                                            'not '
                                                                                                                                                                            'mean '
                                                                                                                                                                            'flooding; '
                                                                                                                                                                            'AI '
                                                                                                                                                                            'compares '
                                                                                                                                                                            'both '
                                                                                                                                                                            'dates.',
 'Trước đợt lũ · ': 'Before · ',
 'Ảnh quan sát · ': 'Observation · ',
 ' (giờ Việt Nam)': ' (GMT+7)',
 'Ảnh radar trước đợt lũ, thang xám': 'Grayscale radar image before the flood event',
 'Ảnh radar quan sát sau, cùng thang hiển thị': 'Later radar observation using the same display scale',
 'Chạy phân tích ở thanh bên để mở hai ảnh nguồn của khu vực đã chọn.': 'Analyze the selected area to view '
                                                                        'both source images.',
 'Nguồn dữ liệu và độ tin cậy': 'Sources & reliability',
 '**Nguồn ảnh và quyền sử dụng**': '**Imagery & license**',
 'Ảnh Sentinel-1 từ GEOID-Flood v1.1 của LINKS, giấy phép CC BY 4.0, có dữ liệu Copernicus đã chỉnh sửa. Nhãn tham chiếu không được dùng để tạo dự đoán.': 'Sentinel-1 '
                                                                                                                                                           'from '
                                                                                                                                                           'LINKS '
                                                                                                                                                           'GEOID-Flood '
                                                                                                                                                           'v1.1 '
                                                                                                                                                           '(CC '
                                                                                                                                                           'BY '
                                                                                                                                                           '4.0), '
                                                                                                                                                           'including '
                                                                                                                                                           'modified '
                                                                                                                                                           'Copernicus '
                                                                                                                                                           'data. '
                                                                                                                                                           'Reference '
                                                                                                                                                           'labels '
                                                                                                                                                           'are '
                                                                                                                                                           'not '
                                                                                                                                                           'model '
                                                                                                                                                           'inputs.',
 '[Dataset GEOID-Flood](https://huggingface.co/datasets/links-ads/geoid-flood) · [Đợt lũ trên Copernicus](https://mapping.emergency.copernicus.eu/activations/EMSR754/)': '[GEOID-Flood '
                                                                                                                                                                          'dataset](https://huggingface.co/datasets/links-ads/geoid-flood) '
                                                                                                                                                                          '· '
                                                                                                                                                                          '[Copernicus '
                                                                                                                                                                          'flood '
                                                                                                                                                                          'activation](https://mapping.emergency.copernicus.eu/activations/EMSR754/)',
 '**Phạm vi và kiểm tra đầu vào**': '**Scope & checks**',
 'Bốn khu vực cùng thuộc một sự kiện. Toàn bộ EMSR754 dành cho demo/phát triển, không dùng cho test xác nhận cuối.': 'One '
                                                                                                                     'event, '
                                                                                                                     'four '
                                                                                                                     'tiles. '
                                                                                                                     'EMSR754 '
                                                                                                                     'is '
                                                                                                                     'for '
                                                                                                                     'demos/development '
                                                                                                                     'and '
                                                                                                                     'excluded '
                                                                                                                     'from '
                                                                                                                     'the '
                                                                                                                     'final '
                                                                                                                     'test.',
 'Các cặp đã được kiểm ngày chụp, quỹ đạo, hai kênh radar và sự khớp nhau của lưới ảnh trước khi đưa vào danh sách.': 'Checked: '
                                                                                                                      'dates, '
                                                                                                                      'orbit, '
                                                                                                                      'VV/VH '
                                                                                                                      'channels '
                                                                                                                      'and '
                                                                                                                      'grid '
                                                                                                                      'alignment.',
 'Kiểm đầu vào không xác nhận độ chính xác. Model huấn luyện trên v1.0, còn ảnh hiện tại thuộc v1.1; cần đánh giá lại. Chưa có căn cứ công bố đạt accuracy Việt Nam.': 'Input '
                                                                                                                                                                       'checks '
                                                                                                                                                                       'do '
                                                                                                                                                                       'not '
                                                                                                                                                                       'prove '
                                                                                                                                                                       'accuracy. '
                                                                                                                                                                       'The '
                                                                                                                                                                       'model '
                                                                                                                                                                       'needs '
                                                                                                                                                                       'revalidation '
                                                                                                                                                                       'on '
                                                                                                                                                                       'v1.1 '
                                                                                                                                                                       'data '
                                                                                                                                                                       'after '
                                                                                                                                                                       'v1.0 '
                                                                                                                                                                       'training. '
                                                                                                                                                                       'Vietnam '
                                                                                                                                                                       'targets '
                                                                                                                                                                       'remain '
                                                                                                                                                                       'unverified.',
 'Thông tin kỹ thuật để kiểm lại': 'Technical details',
 'Cùng khu vực ': 'Same area ',
 ' · hồ sơ đầu vào và kết quả phân tích': ' · input and output',
 '**Đầu vào**': '**Input**',
 '**Kết quả**': '**Output**',
 'Flood Mapping': 'Flood Mapping',
 ' km² · ': ' km² · ',
 ' ha': ' ha',
 '<dl class="observation-dates">\n    <dt>Ảnh trước đợt lũ</dt><dd>': '<dl class="observation-dates">\n'
                                                                      '    <dt>Before the event</dt><dd>',
 '<small>GMT+7</small></dd>\n    <dt>Ảnh quan sát</dt><dd>': '<small>GMT+7</small></dd>\n'
                                                             '    <dt>Observation</dt><dd>',
 '<small>GMT+7</small></dd>\n    </dl>': '<small>GMT+7</small></dd>\n    </dl>',
 '<div class="workspace-subtitle">Thanh Hóa – Mưa lũ tháng 9/2024</div><p class="mobile-scope-hint">Mở thanh bên từ mép trái để chọn khu vực và chạy phân tích.</p>': '<div '
                                                                                                                                                                          'class="workspace-subtitle">Thanh '
                                                                                                                                                                          'Hóa '
                                                                                                                                                                          '– '
                                                                                                                                                                          'Sep '
                                                                                                                                                                          '2024 '
                                                                                                                                                                          'flooding</div><p '
                                                                                                                                                                          'class="mobile-scope-hint">Open '
                                                                                                                                                                          'the '
                                                                                                                                                                          'sidebar '
                                                                                                                                                                          'to '
                                                                                                                                                                          'choose '
                                                                                                                                                                          'an '
                                                                                                                                                                          'area '
                                                                                                                                                                          'and '
                                                                                                                                                                          'analyze.</p>',
 '<div class="map-legend" aria-label="Chú giải bản đồ">\n<span><i></i>Cam: AI đánh dấu nghi ngập</span>\n<span><i class="missing"></i>Xám: thiếu ảnh, không tính diện tích</span>\n<span><i class="extent"></i>Nét đứt: phạm vi phân tích</span></div>\n<p class="legend-note">Không tô màu chưa khẳng định không ngập; AI có thể báo nhầm sông, hồ. Sông hồ trên nền bản đồ không phải kết quả AI.</p>': '<div '
                                                                                                                                                                                                                                                                                                                                                                                                          'class="map-legend" '
                                                                                                                                                                                                                                                                                                                                                                                                          'aria-label="Map '
                                                                                                                                                                                                                                                                                                                                                                                                          'legend">\n'
                                                                                                                                                                                                                                                                                                                                                                                                          '<span><i></i>Orange: '
                                                                                                                                                                                                                                                                                                                                                                                                          'suspected '
                                                                                                                                                                                                                                                                                                                                                                                                          'flood</span>\n'
                                                                                                                                                                                                                                                                                                                                                                                                          '<span><i '
                                                                                                                                                                                                                                                                                                                                                                                                          'class="missing"></i>Gray: '
                                                                                                                                                                                                                                                                                                                                                                                                          'no '
                                                                                                                                                                                                                                                                                                                                                                                                          'valid '
                                                                                                                                                                                                                                                                                                                                                                                                          'data; '
                                                                                                                                                                                                                                                                                                                                                                                                          'area '
                                                                                                                                                                                                                                                                                                                                                                                                          'excluded</span>\n'
                                                                                                                                                                                                                                                                                                                                                                                                          '<span><i '
                                                                                                                                                                                                                                                                                                                                                                                                          'class="extent"></i>Dashed: '
                                                                                                                                                                                                                                                                                                                                                                                                          'study '
                                                                                                                                                                                                                                                                                                                                                                                                          'boundary</span></div>\n'
                                                                                                                                                                                                                                                                                                                                                                                                          '<p '
                                                                                                                                                                                                                                                                                                                                                                                                          'class="legend-note">Uncolored '
                                                                                                                                                                                                                                                                                                                                                                                                          'does '
                                                                                                                                                                                                                                                                                                                                                                                                          'not '
                                                                                                                                                                                                                                                                                                                                                                                                          'mean '
                                                                                                                                                                                                                                                                                                                                                                                                          'flood-free. '
                                                                                                                                                                                                                                                                                                                                                                                                          'Rivers/lakes '
                                                                                                                                                                                                                                                                                                                                                                                                          'may '
                                                                                                                                                                                                                                                                                                                                                                                                          'be '
                                                                                                                                                                                                                                                                                                                                                                                                          'false '
                                                                                                                                                                                                                                                                                                                                                                                                          'positives; '
                                                                                                                                                                                                                                                                                                                                                                                                          'basemap '
                                                                                                                                                                                                                                                                                                                                                                                                          'water '
                                                                                                                                                                                                                                                                                                                                                                                                          'is '
                                                                                                                                                                                                                                                                                                                                                                                                          'not '
                                                                                                                                                                                                                                                                                                                                                                                                          'AI '
                                                                                                                                                                                                                                                                                                                                                                                                          'output.</p>',
 '<p class="claim-text">Kết quả mô tả thời điểm chụp 13/09/2024 (giờ Việt Nam). Cần đối chiếu trước khi dùng trong báo cáo; không phản ánh tình hình ngập hiện tại.</p>': '<p '
                                                                                                                                                                          'class="claim-text">Observed '
                                                                                                                                                                          '13 '
                                                                                                                                                                          'Sep '
                                                                                                                                                                          '2024 '
                                                                                                                                                                          '(GMT+7), '
                                                                                                                                                                          'not '
                                                                                                                                                                          'current '
                                                                                                                                                                          'flooding. '
                                                                                                                                                                          'Verify '
                                                                                                                                                                          'before '
                                                                                                                                                                          'reporting.</p>'}
AREAS={'Phía tây nam':'Southwest','Phía tây bắc':'Northwest','Phía đông nam':'Southeast','Phía đông bắc':'Northeast'}

EN.update({
    'Notebook train ở phía tây, validation ở đông bắc, test phát triển ở đông nam. Chưa test đợt lũ độc lập.': 'Notebook: train west, validate northeast, development test southeast. No independent event test.',
    'Model mới được train trong Notebook trên dữ liệu Việt Nam v1.1. Điểm kiểm tra còn thấp; chưa dùng để xác nhận ngập.': 'Trained in the notebook on Vietnam v1.1 data. Low measured accuracy; cannot confirm flooding.',
})

EN.update({'Cặp ảnh cách 12 ngày. Catalog ghi tham chiếu ngày 14/9; SAR quan sát ngày 13/9 giờ Việt Nam. Chưa xác minh nhãn đồng thời với ảnh.': '12-day image pair. Reference dated 14 Sep; radar observed 13 Sep (GMT+7). Timing alignment is unverified.'})

EN.update({'Demo · vùng đã học': 'Demo · training area'})

EN.update({'Tham chiếu WorldView-2 được chụp sau SAR gần 29 giờ. Điểm số chỉ đo mức khớp với tham chiếu khác thời điểm.': 'WorldView-2 reference is ~29 h after SAR. Scores measure agreement across different observation times.'})

EN.update({'Quang học trước lũ + radar RTC sau lũ': 'Pre-flood optical + post-flood RTC radar', 'Ba ô ảnh có đủ quang học và radar RTC tại Thanh Hóa; không phải toàn tỉnh.': 'Three Thanh Hóa tiles with optical and RTC inputs; not province-wide coverage.', 'Đầu vào model RTC là ảnh quang học trước lũ và radar sau lũ. Blue/cyan trong GEOID là màu nhãn, không phải màu ảnh vệ tinh gốc.': 'The RTC model uses pre-flood optical and post-flood radar imagery. GEOID blue/cyan are label colors, not raw satellite colors.', 'Quang học màu tự nhiên · ': 'Natural-color optical · ', 'Radar RTC màu giả · ': 'False-color RTC radar · ', 'Ảnh quang học trước lũ, màu tự nhiên': 'Pre-flood optical imagery, natural color', 'Ảnh radar sau lũ, tổ hợp màu giả VV VH': 'Post-flood radar, VV VH false-color composite', 'Trái: RGB B04/B03/B02; tím là vùng bị che mây hoặc thiếu quang học, không đưa màu hiển thị vào model. Phải: tổ hợp VV, VH và tương phản VV/VH; màu chỉ biểu diễn tín hiệu radar, không xác nhận nước hay ngập.': 'Left: B04/B03/B02 RGB; purple marks cloud or missing optical pixels. Display colors never enter the model. Right: VV, VH and VV/VH contrast; colors show radar signals, not confirmed water or flooding.', 'RTC fusion ResNet-18 U-Net, checkpoint epoch 9. Thanh Hóa EMSR754 là dữ liệu demo phát triển, không phải test độc lập.': 'RTC fusion ResNet-18 U-Net, epoch 9 checkpoint. Thanh Hóa EMSR754 is exposed development data, not an independent test.', 'RTC validation: macro IoU ngập 41,09%; pooled IoU 55,43% trên 14 sự kiện, vùng RTC quan sát được. Đây không phải độ chính xác riêng tại Thanh Hóa hay test xác nhận độc lập.': 'RTC validation: macro flood IoU 41.09%; pooled IoU 55.43% across 14 events on native RTC support. These are not Thanh Hóa-specific accuracy or independent confirmation-test results.', 'Ảnh Sentinel-1 RTC và Sentinel-2 từ GEOID-Flood của LINKS, giấy phép CC BY 4.0, có dữ liệu Copernicus đã chỉnh sửa. Nhãn tham chiếu không được dùng để tạo dự đoán.': 'Sentinel-1 RTC and Sentinel-2 from LINKS GEOID-Flood, CC BY 4.0, containing modified Copernicus data. Reference labels are not used in inference.'})

EN['<div class="map-legend" aria-label="Chú giải bản đồ">\n<span><i></i>Cyan: AI đánh dấu nghi ngập</span>\n<span><i class="permanent"></i>Xanh dương: AI phân loại nước thường xuyên</span>\n<span><i class="missing"></i>Tím: thiếu quan sát RTC, không tính diện tích</span>\n<span><i class="extent"></i>Nét đứt: phạm vi phân tích</span></div>\n<p class="legend-note">Các lớp màu là dự đoán AI, không phải nhãn tham chiếu. Không tô màu chưa khẳng định không ngập.</p>'] = '<div class="map-legend" aria-label="Map legend">\n<span><i></i>Cyan: AI suspected flooding</span>\n<span><i class="permanent"></i>Blue: AI permanent water</span>\n<span><i class="missing"></i>Purple: missing RTC, excluded from area</span>\n<span><i class="extent"></i>Dashed: analysis footprint</span></div>\n<p class="legend-note">Colored layers are AI predictions, not reference labels. Uncolored does not confirm flood-free conditions.</p>'

EN['<dl class="observation-dates">\n    <dt>Ảnh quang học trước lũ</dt><dd>'] = '<dl class="observation-dates">\n    <dt>Pre-flood optical image</dt><dd>'

EN['Quang học + radar RTC'] = 'Optical + RTC radar'

# Paired complete messages keep meaning and placeholders aligned across languages.
RTC_MESSAGES = {'input_badge': ('Quang học + radar', 'Optical + radar'),
 'coverage': ('Ba ô ảnh có đủ ảnh quang học và tín hiệu radar tại Thanh Hóa; không phải toàn tỉnh.',
              'Three Thanh Hóa tiles with optical imagery and radar signals; not province-wide coverage.'),
 'before_title': ('Ảnh trước đợt lũ', 'Pre-flood image'),
 'observation_title': ('Ảnh quan sát đợt lũ', 'Flood-event observation'),
 'flood_estimate': ('Khoảng {area} km² được mô hình đánh dấu nghi ngập.',
                    'About {area} km² flagged by the model as suspected flooding.'),
 'legend_title': ('Chú giải bản đồ', 'Map legend'),
 'legend_flood': ('Vùng ngập dự đoán', 'Predicted flood extent'),
 'legend_permanent': ('Vùng nước thường xuyên', 'Permanent water'),
 'legend_missing': ('Vùng thiếu tín hiệu radar', 'Missing radar coverage'),
 'legend_extent': ('Phạm vi phân tích', 'Analysis area'),
 'legend_note': ('Nước thường xuyên là vùng như sông, hồ vốn có nước. Vùng tím thiếu tín hiệu radar nên '
                 'không được tính diện tích. Các lớp màu là dự đoán AI, không phải nhãn tham chiếu; không tô '
                 'màu chưa khẳng định không ngập.',
                 'Permanent water means areas such as rivers and lakes that normally contain water. Purple '
                 'areas lack radar signals and are excluded from area calculations. Colored layers are AI '
                 'predictions, not reference labels; uncolored does not confirm flood-free conditions.'),
 'image_intro': ('Hai ảnh cùng khu vực: ảnh quang học trước đợt lũ và ảnh radar dùng để quan sát đợt lũ. Màu '
                 'xanh dương/xanh lơ trong GEOID là màu nhãn phân loại, không phải màu ảnh vệ tinh gốc.',
                 'Two images of the same area: an optical image before the flood event and a radar image '
                 'used to observe it. GEOID blue/cyan are class-label colors, not the original '
                 'satellite-image colors.'),
 'optical_caption': ('Ảnh quang học · màu tự nhiên · {date} GMT+7',
                     'Optical image · natural color · {date} GMT+7'),
 'radar_caption': ('Ảnh radar · màu giả · {date} GMT+7', 'Radar image · false color · {date} GMT+7'),
 'optical_alt': ('Ảnh trước đợt lũ: quang học màu tự nhiên',
                 'Pre-flood image: natural-color optical imagery'),
 'radar_alt': ('Ảnh quan sát đợt lũ: radar màu giả', 'Flood-event observation: false-color radar imagery'),
 'reading_title': ('Cách đọc hai ảnh', 'How to read the images'),
 'optical_help': ('**Ảnh quang học** ghi ánh sáng phản xạ từ bề mặt; màu tự nhiên ghép ba kênh đỏ, lục, lam '
                  'để gần với cách mắt nhìn. Màu tím đánh dấu vùng bị che mây hoặc thiếu ảnh quang học; '
                  'không phải vùng ngập.',
                  '**Optical imagery** records light reflected from the surface. Natural color combines red, '
                  'green and blue channels to approximate human vision. Purple marks cloud-covered or '
                  'missing optical pixels, not flooding.'),
 'radar_help': ('**Ảnh radar** ghi tín hiệu sóng phản hồi từ bề mặt. Màu giả là màu do ứng dụng gán để làm '
                'rõ khác biệt tín hiệu: xanh lam đậm có thành phần VV yếu hơn thành phần tương phản; xanh lơ '
                'có VV trội hơn VH; vùng vàng/nâu có thành phần VH tương đối mạnh hơn so với phần xanh lam. '
                'Đây là các cách đọc tương đối, không phải bảng phân loại đất, nước hay ngập.',
                '**Radar imagery** records microwave signals returned from the surface. False color is '
                'assigned by the app to reveal signal differences: dark blue has a weaker VV component '
                'relative to the contrast component; cyan has stronger VV than VH; yellow/brown has a '
                'relatively stronger VH component than the blue component. These are relative visual cues, '
                'not land, water or flood classes.'),
 'radar_channels': ('**VV và VH** là hai cách radar thu sóng phản hồi: phát dọc–thu dọc và phát dọc–thu '
                    'ngang. Ảnh màu giả ghép VH vào đỏ, VV vào lục, còn lam kết hợp VV với độ tương phản '
                    'VV/VH. Không thể kết luận một vùng ngập chỉ từ màu này. Tím là thiếu tín hiệu radar.',
                    '**VV and VH** are two radar polarization channels: vertical transmit–vertical receive '
                    'and vertical transmit–horizontal receive. This false-color image maps VH to red, VV to '
                    'green, and a mix of VV and VV/VH contrast to blue. A color alone cannot establish '
                    'flooding. Purple marks missing radar signals.'),
 'image_timing': ('Ngày chụp: 10/08/2024 và 13/09/2024 (GMT+7). “Ảnh quan sát đợt lũ” không có nghĩa là lũ '
                  'đã kết thúc; ảnh trước đợt lũ cũng không chứng minh mọi nơi đều khô. Hai ảnh dùng cảm '
                  'biến khác nhau nên không so màu trực tiếp để kết luận ngập.',
                  'Acquisition dates: 10 Aug and 13 Sep 2024 (GMT+7). “Flood-event observation” does not '
                  'mean the flood had ended; the pre-flood image does not establish that every location was '
                  'dry. The images use different sensors, so their colors cannot be compared directly to '
                  'establish flooding.'),
 'rtc_definition': ('**Radar RTC** là tín hiệu radar đã hiệu chỉnh để giảm ảnh hưởng địa hình lên độ mạnh '
                    'tín hiệu (Radiometric Terrain Correction). Đây là bước xử lý ảnh, không phải một loại '
                    'ngập. [Giải thích RTC của '
                    'NASA](https://www.jpl.nasa.gov/go/opera/products/rtc-product/).',
                    '**RTC radar** is radar backscatter corrected to reduce terrain effects on signal '
                    'strength (Radiometric Terrain Correction). It is an image-processing step, not a flood '
                    'category. [NASA explanation of '
                    'RTC](https://www.jpl.nasa.gov/go/opera/products/rtc-product/).'),
 'source_origin': ('Ảnh radar Sentinel-1 và ảnh quang học Sentinel-2 từ bộ dữ liệu GEOID-Flood, được tải từ '
                   'kho links-ads/geoid-flood trên Hugging Face. Bộ dữ liệu dùng giấy phép CC BY 4.0 và chứa '
                   'dữ liệu Copernicus đã chỉnh sửa. Nhãn tham chiếu không được dùng để tạo dự đoán.',
                   'Sentinel-1 radar and Sentinel-2 optical imagery from GEOID-Flood, downloaded from the '
                   'links-ads/geoid-flood repository on Hugging Face. The dataset is licensed under CC BY '
                   '4.0 and contains modified Copernicus data. Reference labels are not used to generate '
                   'predictions.'),
 'model_scope': ('Mô hình kết hợp ảnh quang học và radar RTC: ResNet-18 U-Net, bản trọng số được chọn ở vòng '
                 'huấn luyện 9. Thanh Hóa EMSR754 là dữ liệu demo phát triển, không phải kiểm tra độc lập.',
                 'The model combines optical imagery and RTC radar signals: ResNet-18 U-Net, with weights '
                 'selected at training epoch 9. Thanh Hóa EMSR754 is exposed development data, not an '
                 'independent test.'),
 'reference_timing': ('Ảnh WorldView-2 dùng làm tham chiếu tại Thanh Hóa được chụp sau ảnh radar gần 29 giờ. '
                      'Đối chiếu hai ảnh khác thời điểm có thể chịu ảnh hưởng do nước thay đổi.',
                      'The WorldView-2 reference image for Thanh Hóa was acquired almost 29 hours after the '
                      'radar image. Comparisons across these acquisition times may be affected by changing '
                      'water conditions.'),
 'validation': ('Kiểm tra trên tập validation với radar RTC: macro IoU ngập 41,09%; pooled IoU 55,43% trên '
                '14 sự kiện, trong vùng radar quan sát được. Đây không phải độ chính xác riêng tại Thanh Hóa '
                'hay kiểm tra xác nhận độc lập.',
                'Validation with RTC radar: macro flood IoU 41.09%; pooled IoU 55.43% across 14 events on '
                'observed radar coverage. These are not Thanh Hóa-specific accuracy or independent '
                'confirmation-test results.'),
 'concept_title': ('Các thuật ngữ trong kết quả', 'Terms used in the results'),
 'concept_help': ('**AI:** mô hình học từ dữ liệu để đưa ra dự đoán.\n'
                  '\n'
                  '**Nhãn tham chiếu:** bản phân loại dùng để đối chiếu kết quả; không phải đầu vào của mô '
                  'hình khi dự đoán.\n'
                  '\n'
                  '**IoU:** chỉ số cho biết vùng ngập dự đoán khớp với vùng ngập tham chiếu đến đâu. Cách '
                  'tính: lấy diện tích được cả hai cùng đánh dấu là ngập, chia cho tổng diện tích được ít '
                  'nhất một bên đánh dấu là ngập. Phần trùng nhau chỉ tính một lần. Chỉ số càng cao, hai '
                  'vùng càng khớp.\n'
                  '\n'
                  '**Macro IoU ngập:** tính IoU riêng cho từng sự kiện có ngập trong nhãn tham chiếu, rồi '
                  'lấy trung bình. Mỗi sự kiện có trọng số như nhau.\n'
                  '\n'
                  '**Pooled IoU:** gộp số điểm ảnh của các sự kiện, rồi tính một IoU chung. Sự kiện có nhiều '
                  'điểm ảnh hơn sẽ đóng góp nhiều hơn.\n'
                  '\n'
                  '**Validation:** tập dữ liệu dùng trong quá trình phát triển và chọn mô hình; không phải '
                  'bài kiểm tra độc lập cuối cùng.',
                  '**AI:** a model trained on data to make predictions.\n'
                  '\n'
                  '**Reference labels:** classifications used to check the results; they are not model '
                  'inputs during prediction.\n'
                  '\n'
                  '**IoU:** a score showing how closely predicted and reference flood areas agree. To '
                  'calculate it, divide the area that both mark as flooded by the total area that either '
                  'marks as flooded. Count overlapping areas only once. A higher score means closer '
                  'agreement.\n'
                  '\n'
                  '**Macro flood IoU:** calculate IoU for each event with reference flooding, then take the '
                  'average. Each event has equal weight.\n'
                  '\n'
                  '**Pooled IoU:** combine pixel counts across events, then calculate one overall IoU. '
                  'Events with more pixels contribute more.\n'
                  '\n'
                  '**Validation:** data used during model development and selection; it is not a final '
                  'independent test.'),
 'verification_required': ('Cần kiểm chứng trước khi sử dụng', 'Verify before use'),
 'radar_coverage_heading': ('**Vùng có tín hiệu radar hợp lệ**', '**Valid radar coverage**'),
 'coverage_summary': ('{area} km² · {percent}% diện tích khu vực',
                      '{area} km² · {percent}% of the study area'),
 'result_caution': ('Diện tích do AI ước tính, chưa phải diện tích ngập đã được xác nhận.',
                    'AI-estimated area, not confirmed flooded area.'),
 'observation_note': ('Kết quả mô tả lần quan sát radar ngày 13/09/2024 (giờ Việt Nam, GMT+7). Cần kiểm '
                      'chứng kết quả trước khi đưa vào báo cáo; kết quả không phản ánh tình hình ngập hiện '
                      'tại.',
                      'The results describe the radar observation on 13 Sep 2024 (Vietnam time, GMT+7). '
                      'Verify the results before using them in a report; they do not represent current flood '
                      'conditions.'),
 'technical_context': ('Khu vực {case} · hồ sơ đầu vào và kết quả phân tích',
                       'Area {case} · input records and analysis results')}

def message(key, language, **values):
    return RTC_MESSAGES[key][1 if language == "en" else 0].format(**values)

def radar_legend(language):
    items = [("", "legend_flood"), ("permanent", "legend_permanent"), ("missing", "legend_missing"), ("extent", "legend_extent")]
    cells = "".join(f'<span><i class="{style}" aria-hidden="true"></i>{html.escape(message(key, language))}</span>' for style, key in items)
    return f'<div class="map-legend" aria-label="{message("legend_title", language)}">{cells}</div><p class="legend-note">{html.escape(message("legend_note", language))}</p>'

EN['Đầu vào'] = 'Inputs'

# Complete meanings for the currently served interface.
EN.update({'Chưa có cặp ảnh Việt Nam đạt kiểm tra đầu vào. Không thể chạy phân tích bằng ảnh chưa phù hợp.': 'No '
                                                                                                   'Vietnamese '
                                                                                                   'image '
                                                                                                   'pairs '
                                                                                                   'have '
                                                                                                   'passed '
                                                                                                   'the '
                                                                                                   'input '
                                                                                                   'checks. '
                                                                                                   'Analysis '
                                                                                                   'cannot '
                                                                                                   'run on '
                                                                                                   'unsuitable '
                                                                                                   'imagery.',
 'Chưa tạo được bản đồ. Hãy thử lại hoặc chọn khu vực khác.': 'Could not generate the map. Try again or '
                                                              'choose another area.',
 'Đang đọc ảnh và tìm các vùng nghi ngập…': 'Reading imagery and identifying potentially flooded areas…',
 'Bản thử nghiệm nghiên cứu · dữ liệu lịch sử': 'Research prototype · historical data',
 'Lớp vùng ngập dự đoán': 'Predicted flood overlay',
 'Chưa tạo được gói tải xuống; kết quả phân tích vẫn được giữ.': 'Could not prepare the download package; '
                                                                 'the analysis result is retained.',
 'Thử tạo lại gói tải xuống': 'Retry package creation',
 'Bản đồ, bảng diện tích và ghi chú nguồn trong một file ZIP.': 'One ZIP file containing the map, area table '
                                                                'and source notes.',
 'Chọn khu vực ở thanh bên trái rồi bấm **Phân tích khu vực này**.': 'Choose an area in the left sidebar, '
                                                                     'then select **Analyze area**.',
 'Kết quả sẽ gồm vùng nghi ngập, diện tích và gói bản đồ để tải về.': 'Results will include predicted flood '
                                                                      'extent, estimated area and a '
                                                                      'downloadable map package.',
 'Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Nền địa danh © OpenStreetMap / OpenStreetMap France cần Internet.': 'Zoom '
                                                                                                                      'or '
                                                                                                                      'drag '
                                                                                                                      'the '
                                                                                                                      'map '
                                                                                                                      'to '
                                                                                                                      'identify '
                                                                                                                      'locations. '
                                                                                                                      'The '
                                                                                                                      'place-name '
                                                                                                                      'basemap '
                                                                                                                      '© '
                                                                                                                      'OpenStreetMap '
                                                                                                                      '/ '
                                                                                                                      'OpenStreetMap '
                                                                                                                      'France '
                                                                                                                      'requires '
                                                                                                                      'Internet '
                                                                                                                      'access.',
 '**Nguồn ảnh và quyền sử dụng**': '**Imagery sources & usage rights**',
 '**Phạm vi và kiểm tra đầu vào**': '**Scope & input checks**',
 'Thông tin kỹ thuật để kiểm lại': 'Technical details for verification',
 'Chạy phân tích ở thanh bên để mở hai ảnh nguồn của khu vực đã chọn.': 'Run the analysis from the sidebar '
                                                                        'to view both source images for the '
                                                                        'selected area.',
 '<div class="workspace-subtitle">Thanh Hóa – Mưa lũ tháng 9/2024</div><p class="mobile-scope-hint">Mở thanh bên từ mép trái để chọn khu vực và chạy phân tích.</p>': '<div '
                                                                                                                                                                      'class="workspace-subtitle">Thanh '
                                                                                                                                                                      'Hóa '
                                                                                                                                                                      '– '
                                                                                                                                                                      'Sep '
                                                                                                                                                                      '2024 '
                                                                                                                                                                      'flooding</div><p '
                                                                                                                                                                      'class="mobile-scope-hint">Open '
                                                                                                                                                                      'the '
                                                                                                                                                                      'sidebar '
                                                                                                                                                                      'from '
                                                                                                                                                                      'the '
                                                                                                                                                                      'left '
                                                                                                                                                                      'edge '
                                                                                                                                                                      'to '
                                                                                                                                                                      'choose '
                                                                                                                                                                      'an '
                                                                                                                                                                      'area '
                                                                                                                                                                      'and '
                                                                                                                                                                      'run '
                                                                                                                                                                      'the '
                                                                                                                                                                      'analysis.</p>'})

EN['Ảnh vệ tinh đầu vào'] = 'Input satellite imagery'
RTC_MESSAGES['packaging_map'] = ('Đang tạo ảnh bản đồ và gói tải xuống…', 'Creating the map image and download package…')

EN['Phóng to hoặc kéo bản đồ để nhận biết địa điểm. Khu vực phân tích dùng nền tham chiếu đã chuẩn bị; bản đồ xung quanh cần Internet. © OpenStreetMap / OpenStreetMap France.'] = 'Zoom or drag the map to identify locations. The analysis area uses a prepared reference background; the surrounding map requires Internet access. © OpenStreetMap / OpenStreetMap France.'

RTC_MESSAGES.update({
    'map_interaction': ('Tương tác bản đồ', 'Interact with map'),
    'map_reset': ('Về phạm vi phân tích', 'Reset to analysis area'),
    'map_scroll_hint': ('Vuốt trên bản đồ để cuộn trang. Bật “Tương tác bản đồ” khi muốn kéo hoặc phóng to bản đồ.', 'Swipe over the map to scroll the page. Turn on “Interact with map” to pan or zoom the map.'),
    'map_interaction_hint': ('Đang tương tác bản đồ. Tắt công tắc để vuốt cuộn trang; bấm “Về phạm vi phân tích” nếu kéo bản đồ đi xa.', 'Map interaction is on. Turn it off to swipe-scroll the page; select “Reset to analysis area” if you pan too far.')
})

def translate(text,language):
    return EN.get(text,text) if language=='en' else text

def area_name(name,language):
    return AREAS[name] if language=='en' else name.replace('Phía ','')

def local_date(value,language):
    if language=='vi':return value
    return datetime.strptime(value,'%d/%m/%Y %H:%M').strftime('%d %b %Y %H:%M')

def localized_map(case,result,show_prediction,language,view_revision=0,*,maptiler_api_key=""):
    markup=map_html(case,result,show_prediction,view_revision,maptiler_api_key=maptiler_api_key)
    if language=='en':
        markup=markup.replace('Nền bản đồ xung quanh chưa tải được; nền khu vực phân tích và kết quả vẫn được giữ.', 'The surrounding basemap could not load; the analysis-area background and prediction are retained.')
    if language=='en':
        old=html.escape(f"Thanh Hóa — {case['area_name'].lower()}")
        new=html.escape(f"Thanh Hóa — {area_name(case['area_name'],language)}")
        markup=markup.replace(json.dumps(old),json.dumps(new))
        markup=markup.replace('<html lang="vi">','<html lang="en">')
        markup=markup.replace('Bản đồ khu vực Thanh Hóa và lớp nghi ngập','Thanh Hóa study area and suspected flooding')
        markup=markup.replace('Nền địa danh chưa tải được. Kiểm tra Internet; ranh khu vực và lớp kết quả vẫn được giữ.',
                              'The basemap could not load. Check your connection; the study boundary and prediction are retained.')
    return markup


def english_preview(result):
    meta=result['metadata'];canvas=Image.new('RGB',(1080,1280),'white');draw=ImageDraw.Draw(canvas)
    path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    title=ImageFont.truetype(path,26);body=ImageFont.truetype(path,18);small=ImageFont.truetype(path,16)
    draw.text((28,22),'AI suspected flood map — Thanh Hóa',fill='#164e55',font=title)
    draw.text((28,68),f"Area: {area_name(meta['area_name'],'en')} | Observation: {local_date(meta['post_local'],'en')} (GMT+7)",fill='#243e44',font=body)
    draw.text((28,98),f"Before: {local_date(meta['pre_local'],'en')} | Acquisitions 12 days apart",fill='#243e44',font=body)
    rgb=COLORS[np.where(result['prediction']==255,2,result['prediction'])]
    canvas.paste(Image.fromarray(rgb).resize((880,880),Image.Resampling.NEAREST),(100,148))
    draw.text((1010,156),'N',fill='#243e44',font=body);draw.line((1030,220,1030,185),fill='#243e44',width=3)
    draw.polygon([(1030,174),(1022,189),(1038,189)],fill='#243e44')
    for y,(label,color) in zip([1052,1084,1116],[('AI suspected flooding',(225,91,35)),('Not flagged by AI; not confirmed flood-free',(215,227,234)),('Missing valid imagery; excluded from area',(168,38,195))]):
        draw.rectangle((28,y,48,y+17),fill=color);draw.text((60,y-2),label,fill='#243e44',font=body)
    draw.text((28,1160),f"Estimated: {meta['flood_area_km2']:.2f} km² within {meta['valid_area_km2']:.2f} km² of usable coverage.",fill='#243e44',font=body)
    draw.text((28,1194),'Research prototype. Rivers/lakes may be false positives. Verify before reporting.',fill='#243e44',font=small)
    draw.text((28,1224),'Source: GEOID-Flood v1.1 / LINKS / Copernicus. GeoTIFF retains map coordinates.',fill='#243e44',font=small)
    return png_bytes(np.asarray(canvas))


def localized_bundle(result,language):
    if result['metadata'].get('flood_class') == 2:
        from pipeline_rtc import export_bundle as rtc_bundle
        return rtc_bundle(result, language)
    # Compatibility boundary: historical notebook exports are not part of RTC deployment.
    from pipeline import export_bundle
    base=export_bundle(result)
    if language=='vi':return base
    meta=result['metadata']
    with zipfile.ZipFile(io.BytesIO(base)) as archive:
        files={name:archive.read(name) for name in archive.namelist()}
    fields={'Location':meta['place'],'Area':area_name(meta['area_name'],'en'),
            'Before image (Vietnam time)':local_date(meta['pre_local'],'en'),
            'Observation (Vietnam time)':local_date(meta['post_local'],'en'),
            'Suspected flooded area (km²)':meta['flood_area_km2'],
            'Area with usable imagery (km²)':meta['valid_area_km2'],
            'Interpretation':'AI estimate, not confirmed flooding; rivers/lakes may be false positives',
            'Case ID':meta['case_id']}
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=list(fields));writer.writeheader();writer.writerow(fields)
    files['summary.csv']=stream.getvalue().encode('utf-8-sig')
    files['prediction.png']=english_preview(result)
    files['metadata.json']=json.dumps({**meta,'report_language':'en'},ensure_ascii=False,indent=2).encode()
    files['README.txt']=('RESEARCH PROTOTYPE: SUSPECTED FLOOD MAP\n'
                         'prediction.png: labelled preview with dates and legend.\n'
                         'prediction.tif: georeferenced map for GIS software.\n'
                         'Codes: 1 = AI suspected flood; 0 = not flagged; 255 = missing observations.\n'
                         'summary.csv: area and dates; metadata.json: provenance and technical fields.\n'
                         'Source identifiers and technical metadata retain their original values.\n'
                         'This is an AI estimate, not confirmed flooding. Permanent water is not separately classified.\n').encode()
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,content in files.items():archive.writestr(name,content)
    return output.getvalue()
