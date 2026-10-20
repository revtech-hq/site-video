"""frame_clock test: a tween that starts at performance.now() and steps by the rAF timestamp, clicked during a slowed
capture. Without the bridge its first frames read a time far in the past and the box leaves the view (the map that went
blank); with it the box travels 0 -> 300 px and never moves backwards. Run: scripts/sv test frame_clock"""
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
from filmkit import capture  # noqa: E402
from PIL import Image  # noqa: E402


def box_x(path):
    """the box's left edge in css px, or None when no box pixel is in view (the row through its middle)"""
    im = Image.open(path).convert('RGB')
    s = im.width // 480
    xs = [x for x in range(im.width) if (lambda p: p[2] > 150 and p[0] < 90)(im.getpixel((x, 150 * s)))]
    return xs[0] / s if xs else None


def run(clock, out):
    cfg = {'viewport': [480, 320], 'device_scale': 1, 'fps': 30, 'rate0': 0.2, 'frame_clock': clock,
           'pre': [{'goto': (HERE / 'fixture' / 'tween.html').as_uri(), 'wait_until': 'load', 'settle_ms': 200}]}
    frames = [dict({'i': i, 's': [0] * 6, 'scale': 'device', 'mouse': [80, 40]}, **({'act': [{'click': [80, 40]}]} if i == 20 else {}))
              for i in range(50)]
    json.dump(frames, open(os.path.join(out, 'timeline.json'), 'w'))
    capture.run(cfg, os.path.join(out, 'timeline.json'), out, verbose=False)
    return [box_x(os.path.join(out, f'{i:05d}-0.jpg')) for i in range(20, 50)]


def main():
    bad = 0
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(f'{d}/off'); os.makedirs(f'{d}/on')
        off, on = run(False, f'{d}/off'), run(True, f'{d}/on')
    gone = any(x is None or x < -1 for x in off)
    print(f"{'PASS' if gone else 'FAIL'} without the bridge the box leaves the view after the click: {off[:6]}")
    bad += not gone
    seen = [x for x in on if x is not None]
    moving = sum(1 for x in seen if 1 < x < 299)   # 400 ms at 30 fps: about 12 frames when paced, 8 measured; a jump is 0 or 1
    ok = len(seen) == len(on) and all(b >= a - 0.5 for a, b in zip(seen, seen[1:])) and abs(seen[-1] - 300) <= 1 and moving >= 5
    print(f"{'PASS' if ok else 'FAIL'} with the bridge the box travels to 300 over {moving} frames and never back: {on[:4]} ... {on[-2:]}")
    bad += not ok
    print('frame_clock:', 'OK' if not bad else f'{bad} FAILED')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
