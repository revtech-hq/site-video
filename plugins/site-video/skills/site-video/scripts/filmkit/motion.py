"""Motion maths for a film's timeline: easing, the ease-out stop scroll, camera keyframes, the crop, the cursor path and
the blur-sample planner. Pure functions of time; no files, no brand values."""
import math


def ease(u):
    """in-out cubic, u clamped to 0..1"""
    u = min(1, max(0, u))
    return 4 * u ** 3 if u < .5 else 1 - (-2 * u + 2) ** 3 / 2


def soft(u):
    """in-out quintic (smootherstep), u clamped to 0..1: zero speed and zero acceleration at both ends, and a peak speed
    1.9x the move's average where the in-out cubic peaks at 3x. A camera move on the cubic reads as a jump at any length
    (an owner flagged a 1.4 s zoom twice); on this curve it reads as a glide."""
    u = min(1.0, max(0.0, u))
    return u * u * u * (u * (6 * u - 15) + 10)


def ease_out(u):
    """out cubic, u clamped to 0..1"""
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def prog(T, span):
    """progress of time T through span (a, b): 0 at a, 1 at b, unclamped"""
    return (T - span[0]) / (span[1] - span[0])


def breathe(u, rise=0.35, period=1.0, base=0.62, amp=0.38, blur_base=9.0, blur_amp=7.0):
    """a light that fades in over `rise` s, then breathes once per `period` s. u = seconds since it started.
    Returns (alpha, blur_px) or None before it starts."""
    if u < 0:
        return None
    env = ease_out(u / rise)
    p = 0.5 - 0.5 * math.cos(2 * math.pi * max(0.0, u - rise) / period)
    return env * (base + amp * p), blur_base + blur_amp * p


def stop_scroll(distance, t0, ramp, decel, t_end):
    """The ease-out stop: from t0 the speed rises as a smoothstep over `ramp` s, cruises, then falls as (1-u)^3 over
    the last `decel` s, so it settles with no second brake (a fling). The cruise speed is solved so the distance
    covered by t_end is exact. Returns f(t) -> scroll position (0 before t0, `distance` from t_end)."""
    cruise = t_end - t0 - ramp - decel
    vmax = distance / (ramp / 2 + cruise + decel / 4)

    def f(t):
        if t <= t0:
            return 0.0
        if t >= t_end:
            return float(distance)
        u = t - t0
        if u < ramp:
            x = u / ramp
            return vmax * ramp * (x ** 3 - x ** 4 / 2)
        p = vmax * ramp / 2
        u -= ramp
        if u < cruise:
            return p + vmax * u
        p += vmax * cruise
        x = (u - cruise) / decel
        return p + vmax * decel * (1 - (1 - x) ** 4) / 4
    return f


def camera_at(keys, t):
    """Camera keyframes: [(t, zoom, centre_x, centre_y, mode), ...]. Between two keys, zoom is interpolated in log
    space, the centre linearly; mode of the NEXT key is 'io' (in-out cubic), 'soft' (in-out quintic: a calmer peak, for
    moves the eye must follow) or 'lin'. Returns (zoom, cx, cy)."""
    if t <= keys[0][0]:
        return tuple(keys[0][1:4])
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0])
            u = ease(u) if b[4] == 'io' else soft(u) if b[4] == 'soft' else u
            return (math.exp(math.log(a[1]) + (math.log(b[1]) - math.log(a[1])) * u),
                    a[2] + (b[2] - a[2]) * u, a[3] + (b[3] - a[3]) * u)
    return tuple(keys[-1][1:4])


def crop_at(cam, t, vw, vh, padx=0):
    """The camera's crop of the page at time t: (zoom, x0, y0, cw, ch) in page pixels. The crop is kept inside the
    page, except that x0 may run `padx` px past the left edge (the compositor continues the page's ground there)."""
    z, cx, cy = cam(t)
    cw, ch = vw / z, vh / z
    return z, min(max(cx - cw / 2, -padx), vw - cw), min(max(cy - ch / 2, 0), vh - ch), cw, ch


def bezier_cursor(p0, pc, p1, span, hide_from, ease_fn=ease):
    """A cursor on a quadratic bezier p0 -> p1 via control pc, eased over span (a, b). None before a and from
    `hide_from` on. Returns f(t) -> (x, y) | None."""
    def f(t):
        if t < span[0] or t >= hide_from:
            return None
        u = ease_fn((t - span[0]) / (span[1] - span[0]))
        return ((1 - u) ** 2 * p0[0] + 2 * (1 - u) * u * pc[0] + u ** 2 * p1[0],
                (1 - u) ** 2 * p0[1] + 2 * (1 - u) * u * pc[1] + u ** 2 * p1[1])
    return f


def plan_samples(scroll, t, fps, zoom, win_w, view_w, nav_t=None, shutter=0.5, per_px=3.0, max_n=10):
    """The blur-sample planner: a 180-degree shutter (shutter=0.5 of a frame) centred on t. The on-screen travel in
    output px is |b - a| * win_w / (view_w / zoom); n = 1 if that is under 1 px, else min(max_n, ceil(travel/per_px)+1).
    No blur across a navigation, on either side of it: a nav time that falls exactly on a frame would otherwise average
    the old page's position with the new page's (a smear on the landing). Returns the list of scroll positions,
    rounded to 0.01."""
    half = (shutter / 2) / fps
    a, b = scroll(t - half), scroll(t + half)
    if nav_t is not None and t < nav_t <= t + half:   # the last frame of the old page: its window ends at the change
        b = a
    elif nav_t is not None and t - half < nav_t <= t:  # the first frame of the new page: its window starts there
        a = b
    travel = abs(b - a) * win_w / (view_w / zoom)
    n = 1 if travel < 1.0 else min(max_n, math.ceil(travel / per_px) + 1)
    if n == 1:
        return [round(scroll(t), 2)]
    return [round(a + (b - a) * k / (n - 1), 2) for k in range(n)]
