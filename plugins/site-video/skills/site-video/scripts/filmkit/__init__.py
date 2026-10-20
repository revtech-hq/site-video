"""filmkit: a small library for films of real websites.

A film is a timeline (scroll, camera, cursor, blur samples) planned in motion.py and timeline.py, captured frame by
frame from the live page by capture.py, and composed by compose.py from the captured frames (sources.py), drawn layers
(layers.py) and any footage, then written by encode.py. Nothing here knows a brand, a client or a machine path: a film
folder brings its own numbers (film.json), its own brand values (brand.json) and its own scenes.
"""
import json as _json
import os as _os

from . import motion, timeline, sources, compose, encode, capture, layers  # noqa: F401

__all__ = ['motion', 'timeline', 'sources', 'compose', 'encode', 'capture', 'layers', 'version']


def version():
    """the site-video plugin's version, from its plugin.json (four folders up from here), or None outside the plugin:
    every render record names the release that made it"""
    p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..', '..', '..', '.claude-plugin', 'plugin.json')
    try:
        return _json.load(open(p)).get('version')
    except (OSError, ValueError):
        return None
