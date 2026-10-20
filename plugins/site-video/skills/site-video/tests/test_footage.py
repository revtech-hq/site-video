"""FootageSource identity test: frame N from the rgb24 pipe must equal the frame ffmpeg's select filter extracts.
Makes its own clip (ffmpeg testsrc2, short GOP so seeks cross keyframes). Run: scripts/sv test footage"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from filmkit.sources import FootageSource  # noqa: E402


def reference(path, n, w, h):
    out = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-vf', f'select=eq(n\\,{n})', '-frames:v', '1', '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], capture_output=True, check=True).stdout
    assert len(out) == w * h * 3, f'reference frame {n} missing'
    return out


def main():
    with tempfile.TemporaryDirectory() as d:
        clip = os.path.join(d, 'clip.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', 'testsrc2=s=160x96:r=30:d=4', '-c:v', 'libx264', '-g', '15',
                        '-pix_fmt', 'yuv420p', clip], check=True)
        fs = FootageSource(clip)
        order = [0, 1, 2, 3, 14, 15, 16, 70, 119, 40, 5, 0, 100, 101]   # sequential runs, a jump ahead, backwards seeks
        bad = 0
        for n in order:
            ok = fs.frame(n).tobytes() == reference(clip, n, fs.w, fs.h)
            bad += not ok
            print(f"{'PASS' if ok else 'FAIL'} frame {n}")
        t_ok = fs.at(2.0).tobytes() == reference(clip, 60, fs.w, fs.h)
        bad += not t_ok
        print(f"{'PASS' if t_ok else 'FAIL'} at(2.0) == frame 60")
        fs.close()
        print('FootageSource identity:', 'OK' if not bad else f'{bad} FAILED')
        return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
