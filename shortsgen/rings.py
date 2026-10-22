"""Escape-the-rings physics Short.

A ball bounces under gravity inside concentric rotating rings. Each ring has a
gap; when the ball slips through, the ring shatters. The video ends when the
ball escapes the last ring.
"""
import math
import random
import subprocess
from dataclasses import dataclass, field

import cairo

from . import audio

W, H = 1080, 1920
CX, CY = W / 2, 1000
FPS = 60


@dataclass
class Params:
    rings: int = 20
    gap_deg: float = 55         # angular width of each gap
    r_min: float = 70
    r_max: float = 470
    ball_r: float = 13
    gravity: float = 1400       # px/s^2
    min_speed: float = 900      # bounces never lose more energy than this
    spin_min: float = 0.6       # rad/s
    spin_max: float = 1.6
    hook: str = "Can the ball escape\nall {n} rings?"
    palette: str = "rainbow"    # rainbow | fire | ice | neon
    seed: int = 1
    target_min: float = 25      # acceptable sim duration window (seconds)
    target_max: float = 45
    outro: float = 2.0


@dataclass
class Ring:
    r: float
    phase: float
    spin: float
    gap: float                  # half-angle of gap
    alive: bool = True
    died_at: float = -1


@dataclass
class Sim:
    p: Params
    rings: list
    events: list = field(default_factory=list)   # (t, kind, ring_index)
    frames: list = field(default_factory=list)   # per-frame (bx, by, alive_mask_index)
    duration: float = 0


def build_rings(p, rng):
    rings = []
    for i in range(p.rings):
        r = p.r_min + (p.r_max - p.r_min) * i / max(1, p.rings - 1)
        spin = rng.uniform(p.spin_min, p.spin_max) * (1 if i % 2 == 0 else -1)
        rings.append(Ring(r=r, phase=rng.uniform(0, 2 * math.pi), spin=spin,
                          gap=math.radians(p.gap_deg) / 2))
    return rings


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def simulate(p, max_t=90.0):
    rng = random.Random(p.seed)
    rings = build_rings(p, rng)
    sim = Sim(p=p, rings=rings)
    x, y = CX, CY
    ang = rng.uniform(0, 2 * math.pi)
    vx, vy = math.cos(ang) * p.min_speed, math.sin(ang) * p.min_speed
    sub = 8
    dt = 1 / FPS / sub
    t = 0.0
    k = 0                        # innermost alive ring
    escaped_at = None
    thick = ring_thickness(p)
    while t < max_t:
        for _ in range(sub):
            vy += p.gravity * dt
            x += vx * dt
            y += vy * dt
            t += dt
            if k < len(rings):
                ring = rings[k]
                dx, dy = x - CX, y - CY
                d = math.hypot(dx, dy)
                inner = ring.r - thick / 2
                if d + p.ball_r >= inner:
                    a = math.atan2(dy, dx)
                    rel = _wrap(a - (ring.phase + ring.spin * t))
                    margin = p.ball_r / ring.r
                    if abs(rel) < ring.gap - margin * 0.6:
                        ring.alive = False
                        ring.died_at = t
                        sim.events.append((t, "break", k))
                        k += 1
                        if k == len(rings):
                            escaped_at = t
                    else:
                        nx, ny = dx / d, dy / d
                        vn = vx * nx + vy * ny
                        if vn > 0:
                            vx -= 2 * vn * nx
                            vy -= 2 * vn * ny
                            # tiny tangential nudge so it never settles into a loop
                            jitter = rng.uniform(-60, 60)
                            vx += -ny * jitter
                            vy += nx * jitter
                            s = math.hypot(vx, vy)
                            if s < p.min_speed:
                                vx, vy = vx / s * p.min_speed, vy / s * p.min_speed
                            sim.events.append((t, "bounce", k))
                        push = inner - p.ball_r - 0.5
                        x, y = CX + nx * push, CY + ny * push
        sim.frames.append((x, y, k))
        if escaped_at is not None and t >= escaped_at + p.outro:
            break
        if escaped_at is not None and math.hypot(x - CX, y - CY) > 1400:
            # ball has flown off-screen; keep the camera still until outro ends
            vx = vy = 0
    sim.duration = t
    sim.escaped = escaped_at is not None
    sim.escaped_at = escaped_at
    return sim


def find_seed(p, tries=400):
    """Pick a seed whose run ends inside the target window."""
    base = p.seed
    best = None
    for s in range(base, base + tries):
        p.seed = s
        sim = simulate(p, max_t=p.target_max + p.outro + 5)
        if sim.escaped and p.target_min <= sim.escaped_at <= p.target_max:
            return sim
        if sim.escaped and (best is None or abs(sim.escaped_at - p.target_max) < abs(best.escaped_at - p.target_max)):
            best = sim
    if best is None:
        raise RuntimeError("no seed escaped; widen gaps or lengthen target window")
    p.seed = best.p.seed
    return best


def ring_thickness(p):
    spacing = (p.r_max - p.r_min) / max(1, p.rings - 1)
    return max(4.0, min(14.0, spacing * 0.45))


PALETTES = {
    "rainbow": lambda f: _hsv(f * 0.85, 0.85, 1.0),
    "fire": lambda f: _hsv(0.0 + f * 0.14, 0.95, 1.0),
    "ice": lambda f: _hsv(0.5 + f * 0.17, 0.75, 1.0),
    "neon": lambda f: _hsv((0.83 + f * 0.5) % 1, 0.9, 1.0),
}


def _hsv(h, s, v):
    i = int(h * 6) % 6
    f = h * 6 - int(h * 6)
    p_, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return [(v, t, p_), (q, v, p_), (p_, v, t), (p_, q, v), (t, p_, v), (v, p_, q)][i]


def render(sim, out_path, wav_path):
    p = sim.p
    color = PALETTES[p.palette]
    thick = ring_thickness(p)
    rng = random.Random(p.seed * 7 + 1)
    particles = []
    trail = []
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "bgra", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-i", wav_path,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart",
        out_path,
    ], stdin=subprocess.PIPE)
    breaks = {round(t * FPS): i for t, kind, i in sim.events if kind == "break"}
    hook = p.hook.format(n=p.rings)
    for fi, (bx, by, k) in enumerate(sim.frames):
        t = fi / FPS
        if fi in breaks:
            ring = sim.rings[breaks[fi]]
            col = color(breaks[fi] / max(1, p.rings - 1))
            for _ in range(70):
                a = rng.uniform(0, 2 * math.pi)
                sp = rng.uniform(150, 650)
                particles.append([CX + math.cos(a) * ring.r, CY + math.sin(a) * ring.r,
                                  math.cos(a) * sp, math.sin(a) * sp, 1.0, col])
        # background
        ctx.set_source_rgb(0.035, 0.035, 0.07)
        ctx.paint()
        # rings
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        for i, ring in enumerate(sim.rings):
            if i < k:
                continue
            col = color(i / max(1, p.rings - 1))
            start = ring.phase + ring.spin * t + ring.gap
            end = start + 2 * math.pi - 2 * ring.gap
            for width, alpha in ((thick * 2.6, 0.12), (thick, 1.0)):
                ctx.set_line_width(width)
                ctx.set_source_rgba(*col, alpha)
                ctx.new_path()
                ctx.arc(CX, CY, ring.r, start, end)
                ctx.stroke()
        # particles
        alive_particles = []
        for pt in particles:
            pt[0] += pt[2] / FPS
            pt[1] += pt[3] / FPS
            pt[3] += 900 / FPS
            pt[4] -= 1.6 / FPS
            if pt[4] > 0:
                ctx.set_source_rgba(*pt[5], pt[4])
                ctx.arc(pt[0], pt[1], 4, 0, 2 * math.pi)
                ctx.fill()
                alive_particles.append(pt)
        particles = alive_particles
        # trail + ball
        trail.append((bx, by))
        trail = trail[-14:]
        for j, (tx, ty) in enumerate(trail):
            a = (j + 1) / len(trail)
            ctx.set_source_rgba(1, 1, 1, 0.25 * a)
            ctx.arc(tx, ty, p.ball_r * (0.4 + 0.6 * a), 0, 2 * math.pi)
            ctx.fill()
        ctx.set_source_rgba(1, 1, 1, 0.25)
        ctx.arc(bx, by, p.ball_r * 1.9, 0, 2 * math.pi)
        ctx.fill()
        ctx.set_source_rgb(1, 1, 1)
        ctx.arc(bx, by, p.ball_r, 0, 2 * math.pi)
        ctx.fill()
        # text
        _text(ctx, hook, 250, 66)
        left = p.rings - k
        if left > 0:
            _text(ctx, f"{left}", 1660, 150, col=(1, 1, 1))
            _text(ctx, "rings left", 1730, 44, col=(0.7, 0.7, 0.8))
        else:
            _text(ctx, "ESCAPED!", 1690, 120, col=(1, 0.85, 0.2))
        ff.stdin.write(surf.get_data())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg failed")


def _text(ctx, s, y, size, col=(1, 1, 1)):
    ctx.select_font_face("DejaVu Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    for li, line in enumerate(s.split("\n")):
        ext = ctx.text_extents(line)
        x = (W - ext.width) / 2 - ext.x_bearing
        yy = y + li * size * 1.2
        ctx.set_source_rgba(0, 0, 0, 0.7)
        ctx.move_to(x + 3, yy + 3)
        ctx.show_text(line)
        ctx.set_source_rgb(*col)
        ctx.move_to(x, yy)
        ctx.show_text(line)


def make(p, out_path):
    sim = find_seed(p)
    wav = out_path.rsplit(".", 1)[0] + ".wav"
    audio.write(sim.events, sim.duration, wav, seed=p.seed)
    render(sim, out_path, wav)
    return sim
