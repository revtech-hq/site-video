#!/usr/bin/env python3
"""Capture smoke test, no server: plans a 4-second film (one ease-out scroll stop, a click on a link, page two),
captures it from file:// pages with filmkit.capture, renders it with filmkit and prints the result lines.
  scripts/sv python tests/fixture/run.py [OUT_DIR]      (default: a folder in the system temp dir)"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / 'scripts'))
from filmkit import motion, timeline, capture, sources, compose, encode  # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.gettempdir()) / 'filmkit-fixture-run'
OUT.mkdir(parents=True, exist_ok=True)
F = json.load(open(HERE / 'film.json'))

# plan
sc = F['scroll']
stop = motion.stop_scroll(sc['distance'], sc['t0'], sc['ramp'], sc['decel'], sc['t_end'])
scroll = lambda t: stop(t) if t < F['nav_t'] else 0.0
cam = lambda t: motion.camera_at(F['camera']['keys'], t)
frames = timeline.plan(F['fps'], F['cap_end'], scroll, cam, lambda t: None, F['nav_t'], F['viewport'][0], F['window'][0], tuple(F['sites']))
print(timeline.write(frames, OUT / 'timeline.json'))

# capture: relative goto steps become file:// URLs beside this file
cfg = json.loads(json.dumps(F['capture']))
for st in cfg['pre']:
    if 'goto' in st and '://' not in st['goto']:
        st['goto'] = (HERE / st['goto']).as_uri()
if os.environ.get('FILMKIT_DRAFT'):   # the rough cut's capture: 1x, one frame of settle, at most 3 samples
    cfg['draft'] = True
res = capture.run(cfg, str(OUT / 'timeline.json'), str(OUT / 'raw'), verbose=False)
print('capture seconds', round(res['seconds'], 1), '| draft' if cfg.get('draft') else '')

# render
vw, vh = F['viewport']
src = sources.CaptureSource(str(OUT / 'raw'), (vw, vh))
mp4 = OUT / 'fixture.mp4'
with encode.Writer(str(mp4), vw, vh, F['fps'], title=F['title']) as wr:
    for f in frames:
        win = compose.window(src, f['i'], (0, 0, vw, vh), (vw, vh))
        wr.write(win.tobytes())

print('frames written:', len(frames), '| jpgs:', len([n for n in os.listdir(OUT / 'raw') if n.endswith('.jpg')]), '| mp4 bytes:', mp4.stat().st_size)
print('posts', res['posts'])
print('url1 ends with page2.html:', str(res['url1']).endswith('page2.html'), res['url1'])
print('pacing log present:', len(res['log']) > 0, f"({len(res['log'])} lines)")
for line in res['log'][:3]:
    print('  ', line)
# the gates: the capture record, then the film file
import subprocess  # noqa: E402
FC = str(HERE.parent.parent / 'scripts' / 'film_check.py')
gates = [subprocess.run([sys.executable, FC, 'capture', str(OUT / 'raw' / 'capture.json'), '--timeline', str(OUT / 'timeline.json'),
                         '--expect-url', r'page2\.html$']),
         subprocess.run([sys.executable, FC, 'file', str(mp4), '--format', f'{vw}x{vh}', '--fps', str(F['fps']),
                         '--cuts', str(F['nav_t']), '--duration', str(F['cap_end'])])]
ok = (len(frames) == res['frames'] and res['posts'] == 0 and str(res['url1']).endswith('page2.html') and len(res['log']) > 0
      and all(g.returncode == 0 for g in gates))
print('FIXTURE', 'OK' if ok else 'FAILED')
sys.exit(0 if ok else 1)
