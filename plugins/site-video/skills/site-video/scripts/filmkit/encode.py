"""The ffmpeg writer: raw RGB frames in, H.264 out (libx264 slow, crf 14, High 4.2, BT.709 tv range, faststart, no audio).
CLEAN mode (the default) strips every tool trace from the file (no Lavf/Lavc/x264 strings, no creation time, no
encoder tag) and leaves the decoded frames identical. legacy_encode=True omits the clean flags, which reproduces the
bytes of files written before filmkit."""
import hashlib
import json
import os
import shutil
import subprocess

CLEAN_FLAGS = ['-map_metadata', '-1', '-fflags', '+bitexact', '-flags:v', '+bitexact',
               '-bsf:v', 'filter_units=remove_types=6', '-metadata:s:v:0', 'encoder=']   # remove_types=6: the x264 SEI; encoder= drops the stream's encoder tag


def ffmpeg_args(out, w, h, fps, legacy_encode=False, title=None):
    args = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{w}x{h}',
            '-r', str(fps), '-i', '-',
            '-vf', 'scale=out_color_matrix=bt709:out_range=tv,format=yuv420p', '-c:v', 'libx264', '-preset', 'slow', '-crf', '14',
            '-profile:v', 'high', '-level', '4.2',
            '-x264-params', 'colorprim=bt709:transfer=bt709:colormatrix=bt709',
            '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-color_range', 'tv',
            '-movflags', '+faststart', '-an']
    if not legacy_encode:
        args += CLEAN_FLAGS
        if title:
            args += ['-metadata', f'title={title}']
    return args + [out]


class Writer:
    """with Writer(out, w, h, fps) as wr: wr.write(frame.tobytes()) ..."""

    def __init__(self, out, w, h, fps, legacy_encode=False, title=None):
        self.out = out
        self.p = subprocess.Popen(ffmpeg_args(out, w, h, fps, legacy_encode, title), stdin=subprocess.PIPE)

    def write(self, buf):
        self.p.stdin.write(buf)

    def close(self):
        self.p.stdin.close()
        self.p.wait()
        return self.p.returncode

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def record(mp4, film_dir, name, frames, inputs=('film.json', 'film.py', 'beats.json'), **extra):
    """Write the render's record, <mp4>.json: the film, its frames, the file's sha256 and each input's
    (film_json_sha256, ...). Each input is also kept as versions/by-sha/<sha12>-<input> in the film's folder, so a
    render replays from its record even when no version was saved by hand (two versions of one film were not,
    and their moves had to be profiled from the next version's settings). `extra` adds keys (legacy_encode=...)."""
    from . import version
    rec = {'film': name, 'frames': frames, 'site_video': version(), **extra}
    for f in inputs:
        src = os.path.join(film_dir, f)
        if not os.path.exists(src):
            continue
        h = hashlib.sha256(open(src, 'rb').read()).hexdigest()
        rec[f.replace('.', '_') + '_sha256'] = h
        keep = os.path.join(film_dir, 'versions', 'by-sha', f'{h[:12]}-{f}')
        if not os.path.exists(keep):
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copyfile(src, keep)
    rec['mp4_sha256'] = hashlib.sha256(open(mp4, 'rb').read()).hexdigest()
    with open(mp4 + '.json', 'w') as fh:
        json.dump(rec, fh, indent=1)
    return rec
