"""frame_read test: the gates read single frames of a film through ffmpeg (frame_at). Three frames of known colours are
encoded, then each is read back. A read that comes back empty is a failure here, never a measurement of 0 px in a gate
(ffmpeg 9 dropped -vsync, and every text floor read 0 px on a film that was fine). Run: scripts/sv test frame_read"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
from filmkit import encode  # noqa: E402
import film_check  # noqa: E402

W = H = 64
COLOURS = [(220, 40, 40), (40, 160, 40), (40, 60, 220)]

with tempfile.TemporaryDirectory() as d:
    mp4 = os.path.join(d, 'three.mp4')
    wr = encode.Writer(mp4, W, H, 30)
    for c in COLOURS:
        wr.write(bytes(c) * (W * H))
    assert wr.close() == 0, 'encode failed'
    for i, c in enumerate(COLOURS):
        im = film_check.frame_at(mp4, i, W, H)
        assert im is not None, f'frame {i}: frame_at read nothing (an ffmpeg option this ffmpeg does not take?)'
        got = im.getpixel((W // 2, H // 2))
        assert all(abs(g - e) <= 24 for g, e in zip(got, c)), f'frame {i}: read {got}, wrote {c}'
print('frame_read: PASS')
