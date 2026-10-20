"""The motion profile: what the eye sees move, frame by frame, before anything is captured.

A film's camera (zoom and centre) and its scroll together move every point of the page across the window. The eye
judges the fastest point it can see, so the profile follows nine points of the window (corners, edge centres, centre)
and keeps the worst one: its travel per film frame in output pixels (speed) and the change of that travel from one frame
to the next (acceleration). A move is a stretch where the view never rests; a dip is a moment inside a move where the
speed falls to a fraction of the peaks on both sides (two motions joined by a near-stop, read as stop-and-go).

Units: output pixels of the window per film frame (px/f) and per frame squared (px/f2). Pure functions; no files."""
import math

GRID = [(fx, fy) for fy in (0.0, 0.5, 1.0) for fx in (0.0, 0.5, 1.0)]


def view_at(crop, scroll, t):
    """The window's view of the page at t in page px: (x0, y0, cw, ch). `crop(t)` -> (zoom, x0, y0, cw, ch) with y0
    relative to the viewport; `scroll(t)` -> the page's scroll offset."""
    z, x0, y0, cw, ch = crop(t)
    return (x0, y0 + scroll(t), cw, ch)


def travel(va, vb, win_w):
    """The worst on-screen travel (px) of a page point between two views, and the share of it that is zoom, pan and
    scroll is left to `parts`. The point is fixed on the page; its screen position is (p - x0) * win_w / cw."""
    xa, ya, wa, ha = va
    xb, yb, wb, hb = vb
    sa, sb = win_w / wa, win_w / wb
    best = 0.0
    for fx, fy in GRID:
        px, py = xa + wa * fx, ya + ha * fy                      # the page point under this window point at a
        dx = (px - xb) * sb - (px - xa) * sa
        dy = (py - yb) * sb - (py - ya) * sa
        best = max(best, math.hypot(dx, dy))
    return best


def parts(va, vb, win_w):
    """How a frame's motion splits: (zoom, pan, scroll) as on-screen px at the window's corner. Zoom is the radial
    travel of a corner from the change of scale; pan the travel of the centre across the page; scroll is reported
    by the caller (it is already inside y)."""
    xa, ya, wa, ha = va
    xb, yb, wb, hb = vb
    zoom = abs(win_w / wb - win_w / wa) * math.hypot(wa, ha) / 2
    pan = math.hypot((xb + wb / 2) - (xa + wa / 2), (yb + hb / 2) - (ya + ha / 2)) * win_w / wa
    return zoom, pan


def profile(crop, scroll, t0, t1, fps, win_w):
    """[(t, speed, accel, zoom_px, pan_px, scroll_px)] per frame from t0 to t1. speed is the worst point's travel to
    the next frame; accel the change of speed from the previous frame."""
    out, prev = [], None
    n0, n1 = round(t0 * fps), round(t1 * fps)
    for i in range(n0, n1 + 1):
        t = i / fps
        va, vb = view_at(crop, scroll, t), view_at(crop, scroll, t + 1 / fps)
        v = travel(va, vb, win_w)
        zp, pp = parts(va, vb, win_w)
        sp = abs(scroll(t + 1 / fps) - scroll(t)) * win_w / va[2]
        out.append((t, v, 0.0 if prev is None else v - prev, zp, max(0.0, pp - sp), sp))
        prev = v
    return out


def moves(prof, fps, rest=0.5, min_rest=0.1, dip=0.4):
    """Split a profile into moves: stretches where speed > `rest` px/f, separated by at least `min_rest` s of rest.
    For each: t0, t1, duration, peak speed, mean speed, peak |accel|, the dominant kind (zoom, pan or scroll, by the
    sum of each part), and dips: local minima under `dip` x the smaller of the highest peaks before and after them."""
    out, cur, still = [], None, 0
    for row in prof:
        t, v = row[0], row[1]
        if v > rest:
            if cur is None:
                cur = [row]
            else:
                cur.append(row)
            still = 0
        elif cur is not None:
            still += 1
            cur.append(row)
            if still >= round(min_rest * fps):
                out.append(cur[:-still]); cur, still = None, 0
    if cur:
        out.append(cur[:len(cur) - still] if still else cur)
    res = []
    for m in out:
        if not m:
            continue
        vs = [r[1] for r in m]
        sums = {'zoom': sum(r[3] for r in m), 'pan': sum(r[4] for r in m), 'scroll': sum(r[5] for r in m)}
        tot = sum(sums.values()) or 1.0
        dips = []
        for k in range(1, len(vs) - 1):
            if vs[k] <= vs[k - 1] and vs[k] <= vs[k + 1]:
                before, after = max(vs[:k]), max(vs[k + 1:])
                low = min(before, after)
                if low > 2.0 and vs[k] < dip * low:
                    dips.append((round(m[k][0], 3), round(vs[k], 1), round(vs[k] / low, 2)))
        res.append({'t0': round(m[0][0], 3), 't1': round(m[-1][0], 3), 'dur': round(m[-1][0] - m[0][0], 3),
                    'peak': round(max(vs), 1), 'mean': round(sum(vs) / len(vs), 1),
                    'accel': round(max(abs(r[2]) for r in m[1:]) if len(m) > 1 else 0.0, 1),
                    'kind': {k: round(v / tot, 2) for k, v in sums.items()}, 'dips': dips})
    return res
