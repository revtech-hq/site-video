"""media_rate test: a looping <video> on a page captured with blur samples (the rate drops to about 0.2). A bar on the
page is as wide as the video's currentTime x 40 px. Without media_rate the video keeps wall time and the bar grows several
times faster than the film; with it the bar grows with the film. Run: scripts/sv test media_rate"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
from filmkit import capture  # noqa: E402
from PIL import Image  # noqa: E402

FPS, N, PX_PER_S = 30, 45, 40
PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>*{margin:0} body{background:#fff}
#bar{position:absolute;left:0;top:200px;height:20px;width:0;background:#d02020}</style></head><body>
<video id="v" src="clip.webm" autoplay muted loop playsinline width="160" height="90"></video><div id="bar"></div>
<script>var v = document.getElementById('v'), bar = document.getElementById('bar');
(function f() { bar.style.width = (v.currentTime * %d) + 'px'; requestAnimationFrame(f) })();</script></body></html>""" % PX_PER_S


def bar_px(path):
    im = Image.open(path).convert('RGB')
    s = im.width // 480
    xs = [x for x in range(im.width) if (lambda p: p[0] > 180 and p[1] < 80 and p[2] < 80)(im.getpixel((x, 210 * s)))]
    return (xs[-1] + 1) / s if xs else 0.0


def run(media, d):
    out = os.path.join(d, 'on' if media else 'off')
    os.makedirs(out)
    cfg = {'viewport': [480, 320], 'device_scale': 1, 'fps': FPS, 'rate0': 0.2, 'media_rate': media,
           'pre': [{'goto': Path(d, 'page.html').as_uri(), 'wait_until': 'load', 'settle_ms': 500}]}
    json.dump([{'i': i, 's': [0] * 6, 'scale': 'device'} for i in range(N)], open(os.path.join(out, 'timeline.json'), 'w'))
    capture.run(cfg, os.path.join(out, 'timeline.json'), out, verbose=False)
    a, b = bar_px(os.path.join(out, '00005-0.jpg')), bar_px(os.path.join(out, f'{N - 1:05d}-0.jpg'))
    return (b - a) / PX_PER_S, (N - 1 - 5) / FPS   # seconds of video played, seconds of film


def main():
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=160x90:r=30:d=30', '-c:v', 'libvpx',
                        '-b:v', '200k', os.path.join(d, 'clip.webm')], check=True)
        Path(d, 'page.html').write_text(PAGE)
        off, film = run(False, d)
        on, _ = run(True, d)
    fast = off > 2 * film
    print(f"{'PASS' if fast else 'FAIL'} without media_rate the video runs ahead of the film: {off:.2f} s of video in {film:.2f} s of film")
    bad += not fast
    paced = 0.65 * film <= on <= 1.5 * film
    print(f"{'PASS' if paced else 'FAIL'} with media_rate the video keeps the film's time: {on:.2f} s of video in {film:.2f} s of film")
    bad += not paced
    print('media_rate:', 'OK' if not bad else f'{bad} FAILED')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
