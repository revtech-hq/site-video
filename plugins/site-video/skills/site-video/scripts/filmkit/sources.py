"""Picture sources for compose.py: CaptureSource (the per-frame blur samples capture.py wrote), StitchedSource (the whole
page from capture.stitch(), for an animatic), FootageSource (frames of a video file, decoded through an ffmpeg rgb24 pipe)
and StillSource (one image)."""
import json
import math
import os
import subprocess
from PIL import Image


class CaptureSource:
    """The raw frames of capture.py: raw_dir/00012-0.jpg, 00012-1.jpg ... (one file per blur sample).
    `viewport` = (width, height) in CSS px; the files are at device scale (their width / viewport width)."""

    def __init__(self, raw_dir, viewport, ground=(255, 255, 255)):
        self.dir, self.vw, self.vh, self.ground = raw_dir, viewport[0], viewport[1], tuple(ground)
        self.last = max(int(f.split('-')[0]) for f in os.listdir(raw_dir) if f[0].isdigit())

    def samples(self, j):
        """paths of frame j's blur samples, in order"""
        out, k = [], 0
        while os.path.exists(f'{self.dir}/{j:05d}-{k}.jpg'):
            out.append(f'{self.dir}/{j:05d}-{k}.jpg')
            k += 1
        return out

    def crop(self, j, box, size):
        """Frame j's samples, each cropped to box = (x0, y0, cw, ch) in page px and resized to `size` (LANCZOS), then
        averaged in order. A box running past the page's left edge (x0 < 0) is filled with `ground` there."""
        x0, y0, cw, ch = box
        acc, k = None, 0
        for path in self.samples(j):
            im = Image.open(path).convert('RGB')
            sc = im.width / self.vw
            if x0 < 0:
                pad = math.ceil(-x0 * sc)
                wide = Image.new('RGB', (im.width + pad, im.height), self.ground)
                wide.paste(im, (pad, 0))
                im = wide
                b = ((x0 * sc) + pad, y0 * sc, (x0 + cw) * sc + pad, (y0 + ch) * sc)
            else:
                b = (x0 * sc, y0 * sc, (x0 + cw) * sc, (y0 + ch) * sc)
            im = im.resize(size, Image.LANCZOS, box=b)
            acc = im if acc is None else Image.blend(acc, im, 1 / (k + 1))
            k += 1
        return acc



class StitchedSource:
    """An animatic's page: the tiles of capture.stitch() put back together (fixed elements hidden), with the page's fixed
    nav drawn over the top of every view at its measured height, in the look it had at that scroll position. crop() has
    CaptureSource's signature, so a film renders an animatic through its own code: for frame j it takes the scroll
    positions of that frame's blur samples from the timeline, crops each from the whole page, and averages them. The
    page itself never moves (no video, no carousel, no click result): judge the camera, the timing and the framing."""

    def __init__(self, stitch_dir, timeline, ground=(255, 255, 255)):
        meta = json.load(open(os.path.join(stitch_dir, 'stitch.json')))
        self.vw, self.vh = meta['viewport']
        self.sc, self.nav_h, self.ground = meta['scale'], meta['nav_h'], tuple(ground)
        tl = json.load(open(timeline)) if isinstance(timeline, str) else timeline
        self.s = [f['s'] for f in tl]
        self.last = len(self.s) - 1
        H = meta['height']
        self.page = Image.new('RGB', (round(self.vw * self.sc), round(H * self.sc)), self.ground)
        self.navs = []
        for y, tile, nav in meta['tiles']:
            im = Image.open(os.path.join(stitch_dir, tile)).convert('RGB')
            self.page.paste(im, (0, round(y * self.sc)))
            if nav:
                self.navs.append((y, Image.open(os.path.join(stitch_dir, nav)).convert('RGB')))

    def view(self, s):
        """the viewport at scroll s, as the browser would show it (device px)"""
        sc = self.sc
        top = round(s * sc)
        im = self.page.crop((0, top, self.page.width, top + round(self.vh * sc)))
        if self.navs:
            nav = [n for y, n in self.navs if y <= s + 0.5]
            im.paste(nav[-1] if nav else self.navs[0][1], (0, 0))
        return im

    def crop(self, j, box, size):
        x0, y0, cw, ch = box
        acc, k = None, 0
        for s in self.s[min(j, self.last)]:
            im = self.view(s)
            sc = self.sc
            if x0 < 0:
                pad = math.ceil(-x0 * sc)
                wide = Image.new('RGB', (im.width + pad, im.height), self.ground)
                wide.paste(im, (pad, 0))
                im = wide
                b = ((x0 * sc) + pad, y0 * sc, (x0 + cw) * sc + pad, (y0 + ch) * sc)
            else:
                b = (x0 * sc, y0 * sc, (x0 + cw) * sc, (y0 + ch) * sc)
            im = im.resize(size, Image.LANCZOS, box=b)
            acc = im if acc is None else Image.blend(acc, im, 1 / (k + 1))
            k += 1
        return acc

class FootageSource:
    """Frames of a video file. frame(n) / at(t) return PIL RGB images. Decoding is sequential through one ffmpeg
    rgb24 pipe; a request for an earlier frame, or one far ahead, restarts the pipe at that frame (the seek fallback)."""

    def __init__(self, path, gap=48):
        self.path, self.gap = path, gap
        info = json.loads(subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
             'stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,color_transfer', '-of', 'json', path], capture_output=True,
            check=True).stdout)['streams'][0]
        if info.get('color_transfer') in ('smpte2084', 'arib-std-b67'):   # HDR (PQ or HLG): composited as is, it looks washed out
            raise ValueError(f"{path}: HDR footage ({info['color_transfer']}); convert it to SDR BT.709 first and compare a frame")
        self.w, self.h = int(info['width']), int(info['height'])
        a, b = info['r_frame_rate'].split('/')
        self.fps = int(a) / int(b)
        a, b = info.get('avg_frame_rate', '0/0').split('/')
        avg = int(a) / int(b) if int(b) else 0
        if avg and abs(avg - self.fps) > 0.01 * self.fps:   # phone and screen recordings are often variable-rate
            raise ValueError(f'{path}: variable frame rate ({avg:.3f} average, {self.fps:.3f} nominal); make a constant-rate copy '
                             f'first: ffmpeg -i IN -fps_mode cfr -r 60 -c:v libx264 -crf 12 -pix_fmt yuv420p OUT.mp4')
        self.nb = int(info['nb_frames']) if str(info.get('nb_frames', '')).isdigit() else None
        self._p, self._next = None, 0

    def _open(self, n):
        self.close()
        cmd = ['ffmpeg', '-v', 'error', '-nostdin']
        if n > 0:   # accurate seek to just before frame n's timestamp; the first frame out is frame n
            cmd += ['-ss', f'{(n - 0.5) / self.fps:.6f}']
        cmd += ['-i', self.path, '-map', '0:v:0', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
        # killed mid-stream on a seek, ffmpeg complains of a broken pipe: that noise is expected
        self._p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._next = n

    def _read(self):
        size = self.w * self.h * 3
        buf = self._p.stdout.read(size)
        while buf is not None and len(buf) < size:
            more = self._p.stdout.read(size - len(buf))
            if not more:
                break
            buf += more
        if buf is None or len(buf) < size:
            raise IndexError(f'{self.path}: no frame {self._next}')
        self._next += 1
        return Image.frombytes('RGB', (self.w, self.h), buf)

    def frame(self, n):
        if self._p is None or n < self._next or n > self._next + self.gap:
            self._open(n)
        while self._next < n:
            self._read()
        return self._read()

    def at(self, t):
        """the frame showing at time t (seconds)"""
        return self.frame(max(0, int(math.floor(t * self.fps + 1e-6))))

    def close(self):
        if self._p is not None:
            self._p.stdout.close()
            self._p.kill()
            self._p.wait()
            self._p = None


class StillSource:
    """One image file, loaded once; get() returns a copy, optionally resized (LANCZOS)."""

    def __init__(self, path, mode='RGB'):
        self.im = Image.open(path).convert(mode)

    def get(self, size=None):
        return self.im.copy() if size is None else self.im.resize(size, Image.LANCZOS)
