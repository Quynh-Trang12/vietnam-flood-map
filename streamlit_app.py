"""Cloud entry point with HTTP compression for Streamlit frontend bundles."""
from pathlib import Path

import streamlit as st
from starlette.middleware import Middleware
from starlette.middleware.gzip import GZipMiddleware


class FrontendAssetCompression:
    """Compress JS/CSS only; preserve binary downloads and range responses."""

    def __init__(self, app):
        self.app = app
        self.compressed = GZipMiddleware(app, minimum_size=1024, compresslevel=3)

    async def __call__(self, scope, receive, send):
        path = scope.get('path', '')
        is_frontend = '/static/' in path and '/app/static/' not in path
        if (scope['type'] == 'http' and scope.get('method') == 'GET'
                and is_frontend and path.endswith(('.js', '.css'))
                and not any(key.lower() == b'range' for key, _ in scope.get('headers', []))):
            await self.compressed(scope, receive, send)
        else:
            await self.app(scope, receive, send)


class InitialStyles:
    """Deliver the existing stylesheet before React's first visible layout."""

    def __init__(self, app):
        self.app = app
        css = Path(__file__).with_name('ui_bilingual.css').read_text()
        # Page config and the sidebar arrive over WebSocket after the HTML.
        # Reserve the same wide layout and desktop sidebar slot during bootstrap.
        css += '''
.stMainBlockContainer { max-width:none !important; padding:1rem 1.5rem 1rem !important; }
@media(max-width:640px) {
 .stMainBlockContainer { padding:3.5rem 1rem 1rem !important; }
}
/* Streamlit auto-collapses the sidebar at widths <= 768px. */
@media(min-width:769px) {
 [data-testid="stAppViewContainer"]:not(:has([data-testid="stSidebar"]))
 > div:has(> [data-testid="stMain"]) { margin-left:300px; }
}
'''
        self.styles = ('<style id="flood-map-initial-styles">' + css + '</style>').encode()
        self.root_path = '/' + st.get_option('server.baseUrlPath').strip('/')

    async def __call__(self, scope, receive, send):
        if (scope['type'] != 'http' or scope.get('method') != 'GET'
                or scope.get('path', '').rstrip('/') != self.root_path.rstrip('/')):
            await self.app(scope, receive, send)
            return
        start = None
        chunks = []

        async def inject(message):
            nonlocal start
            if message['type'] == 'http.response.start':
                headers = dict(message.get('headers', []))
                if (message['status'] == 200 and b'text/html' in headers.get(b'content-type', b'')
                        and b'content-encoding' not in headers):
                    start = message
                    return
            if message['type'] == 'http.response.body' and start is not None:
                chunks.append(message.get('body', b''))
                if message.get('more_body', False):
                    return
                body = b''.join(chunks).replace(b'</head>', self.styles + b'</head>', 1)
                headers = [(k, v) for k, v in start.get('headers', [])
                           if k.lower() not in {b'content-length', b'etag'}]
                headers.append((b'content-length', str(len(body)).encode()))
                await send({**start, 'headers': headers})
                await send({'type': 'http.response.body', 'body': body})
                return
            await send(message)

        await self.app(scope, receive, inject)


app = st.App(
    Path(__file__).with_name('app_bilingual.py'),
    middleware=[Middleware(FrontendAssetCompression), Middleware(InitialStyles)],
)
