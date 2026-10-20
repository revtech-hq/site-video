"""review test: the independent review's verdict is kept in the sidecar beside the gates, stays there when the gates
re-run on the same bytes, is refused without the gates for those bytes, and carries to a remuxed copy only when its
decoded frames are the master's. Run: scripts/sv test review"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

FC = str(Path(__file__).resolve().parent.parent / 'scripts' / 'film_check.py')
d = tempfile.mkdtemp(prefix='film_check_review_')
master, copy, other = (os.path.join(d, n) for n in ('master.mp4', 'copy.mp4', 'other.mp4'))
ff = ['ffmpeg', '-v', 'error', '-y']
subprocess.run(ff + ['-f', 'lavfi', '-i', 'testsrc=size=1080x1080:rate=60', '-t', '1', '-pix_fmt', 'yuv420p', master], check=True)
subprocess.run(ff + ['-i', master, '-c', 'copy', '-map_metadata', '-1', '-metadata', 'title=copy', copy], check=True)
subprocess.run(ff + ['-f', 'lavfi', '-i', 'testsrc=size=1080x1080:rate=60', '-t', '1', '-vf', 'hflip', '-pix_fmt', 'yuv420p', other], check=True)


def fc(*args):
    r = subprocess.run([sys.executable, FC] + list(args), capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def review(path):
    try:
        return json.load(open(path + '.film_check.json')).get('review')
    except OSError:
        return None


bad = 0
def check(name, ok):
    global bad
    bad += not ok
    print(f"{'PASS' if ok else 'FAIL'} {name}")


rc, _ = fc('review', master, '--verdict', 'pass', '--by', 'film-reviewer')
check('a review without the gates for these bytes is refused', rc == 2 and review(master) is None)
fc('file', master)
rc, out = fc('review', master, '--verdict', 'pass', '--by', 'film-reviewer', '--note', 'checked at phone size')
check('the review is recorded beside the gates', rc == 0 and (review(master) or {}).get('verdict') == 'pass')
fc('file', master)
check('a gates run on the same bytes keeps the review', (review(master) or {}).get('by') == 'film-reviewer')
fc('file', copy)
rc, out = fc('review', copy, '--from', master)
check('a remuxed copy with the same frames takes the master\'s review', rc == 0 and (review(copy) or {}).get('via') == 'master.mp4')
fc('file', other)
rc, out = fc('review', other, '--from', master)
check('a file with other frames does not', rc == 1 and review(other) is None)
rc, out = fc('review', master, '--verdict', 'maybe', '--by', 'x')
check('a verdict is pass or fix', rc == 2)
print('review: OK' if not bad else f'review: {bad} FAILED')
sys.exit(1 if bad else 0)
