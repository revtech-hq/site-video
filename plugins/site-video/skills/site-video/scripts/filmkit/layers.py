"""Renders an HTML snippet to a transparent 2x PNG with a Python Playwright page, and returns the boxes of the
elements marked data-g (css px: x, y, w, h). The brand layers of a film (logos, bars, shadows, foot rows) come
from here; the snippet, its css and its fonts belong to the film."""
import os
from pathlib import Path


class LayerRenderer:
    """with LayerRenderer(w, h) as lr: boxes = lr.shot(out_dir, 'name', body_html, css=..., fonts=[...])"""

    def __init__(self, w, h, scale=2):
        from playwright.sync_api import sync_playwright
        self.w, self.h = w, h
        self._pw = sync_playwright().start()
        self._b = self._pw.chromium.launch()
        self.page = self._b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=scale).new_page()

    def shot(self, out_dir, name, body, css='', ground=None, clip=None, fonts=()):
        """writes name.html and name.png into out_dir. ground=None gives a transparent PNG. fonts = CSS font
        shorthands to load before the shot (e.g. '400 34px "Family"'). Returns {data-g name: [x, y, w, h]} in css px."""
        os.makedirs(out_dir, exist_ok=True)
        f = Path(out_dir) / f'{name}.html'
        g = f'html,body,.c{{background:{ground}}}' if ground else ''
        f.write_text(f'<!doctype html><meta charset="utf-8"><style>*{{box-sizing:border-box;margin:0}}'
                     f'html,body{{width:{self.w}px;height:{self.h}px;background:transparent}}'
                     f'.c{{position:relative;width:{self.w}px;height:{self.h}px;overflow:hidden}}{css}{g}</style>'
                     f'<div class="c">{body}</div>')
        self.page.goto(f.resolve().as_uri(), wait_until='load')
        self.page.evaluate('async (fonts) => { for (const f of fonts) await document.fonts.load(f); await document.fonts.ready; '
                           'for (const i of document.images) await i.decode() }', list(fonts))
        geo = self.page.evaluate('() => { const o = {}; for (const e of document.querySelectorAll("[data-g]")) '
                                 '{ const r = e.getBoundingClientRect(); o[e.dataset.g] = [r.x, r.y, r.width, r.height] } return o }')
        self.page.screenshot(path=str(Path(out_dir) / f'{name}.png'), omit_background=not ground, clip=clip)
        return geo

    def close(self):
        self._b.close()
        self._pw.stop()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
