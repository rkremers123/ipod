#!/usr/bin/env python3
"""
Pure-Python FDM slicer → G-code for Entina Tina2S V12
  Material : PLA 1.75 mm
  Nozzle   : 0.4 mm
  Bed      : 120 × 120 mm

Usage:
  python3 slicer.py mackenzie_nameplate.stl mackenzie_nameplate.gcode
  python3 slicer.py frenchie.stl frenchie.gcode
"""
import math, struct, sys, os, time

# ── Printer / material settings ───────────────────────────────────────────────
BED_X, BED_Y   = 120.0, 120.0
NOZZLE_D       = 0.40        # mm
FILAMENT_D     = 1.75        # mm
LAYER_H        = 0.20        # mm  (balance of speed & quality)
FIRST_LAYER_H  = 0.25        # mm  (thicker = better adhesion)
NOZZLE_T       = 210         # °C  PLA
BED_T          = 60          # °C  PLA
SPD_PERI       = 2400        # mm/min  40 mm/s
SPD_INFILL     = 3600        # mm/min  60 mm/s
SPD_TRAVEL     = 9000        # mm/min 150 mm/s
SPD_FIRST      = 1200        # mm/min  20 mm/s  (first layer slow)
INFILL_PCT     = 20          # %
RETRACT_D      = 1.5         # mm
RETRACT_SPD    = 1500        # mm/min
INFILL_SPACING = NOZZLE_D / (INFILL_PCT / 100.0)   # 2.0 mm

# Extrusion factor: mm of filament per mm of XY travel
_FA = math.pi * (FILAMENT_D / 2) ** 2
E_FACTOR       = (LAYER_H      * NOZZLE_D) / _FA
E_FACTOR_FIRST = (FIRST_LAYER_H * NOZZLE_D) / _FA


# ── STL loader ────────────────────────────────────────────────────────────────
def load_stl(fname):
    tris = []
    with open(fname, 'rb') as f:
        f.read(80)
        n = struct.unpack('<I', f.read(4))[0]
        for _ in range(n):
            f.read(12)
            v0 = struct.unpack('<3f', f.read(12))
            v1 = struct.unpack('<3f', f.read(12))
            v2 = struct.unpack('<3f', f.read(12))
            f.read(2)
            tris.append((v0, v1, v2))
    return tris


# ── Slicer: triangle → segments at plane z ────────────────────────────────────
def slice_layer(tris_sorted, z, eps=1e-5):
    """
    tris_sorted: list of (z_lo, z_hi, (v0,v1,v2)) sorted by z_lo
    Returns list of 2-point segments: [((x1,y1),(x2,y2)), ...]
    """
    segs = []
    for z_lo, z_hi, (v0, v1, v2) in tris_sorted:
        if z_lo > z + eps:
            break            # sorted → nothing more can cross z
        if z_hi < z - eps:
            continue         # entirely below

        verts = (v0, v1, v2)
        pts   = []
        for i in range(3):
            va = verts[i];        za = va[2]
            vb = verts[(i+1)%3];  zb = vb[2]
            if (za - z) * (zb - z) < 0:          # edge crosses plane
                t  = (z - za) / (zb - za)
                px = va[0] + t * (vb[0] - va[0])
                py = va[1] + t * (vb[1] - va[1])
                pts.append((round(px, 4), round(py, 4)))
            elif abs(za - z) < eps:               # vertex exactly on plane
                pts.append((round(va[0], 4), round(va[1], 4)))

        # Deduplicate
        unique = []
        for p in pts:
            if not unique or abs(p[0]-unique[-1][0]) > eps or abs(p[1]-unique[-1][1]) > eps:
                unique.append(p)

        if len(unique) == 2:
            segs.append((unique[0], unique[1]))

    return segs


# ── Polygon assembly ──────────────────────────────────────────────────────────
def connect_segments(segs, tol=0.05):
    """Stitch segments into closed polygons."""
    if not segs:
        return []

    # Build endpoint → [(seg_idx, which_end)] map
    ep = {}
    for i, (a, b) in enumerate(segs):
        ka = (round(a[0]/tol), round(a[1]/tol))
        kb = (round(b[0]/tol), round(b[1]/tol))
        ep.setdefault(ka, []).append((i, 0))
        ep.setdefault(kb, []).append((i, 1))

    used  = [False] * len(segs)
    loops = []

    for start in range(len(segs)):
        if used[start]:
            continue

        loop   = []
        ci     = start
        exit_e = 1          # we will exit through end-1 first

        for _ in range(len(segs) + 1):
            if used[ci]:
                break
            used[ci] = True
            a, b = segs[ci]

            if exit_e == 1:
                loop.append(a)
                cur = b
            else:
                loop.append(b)
                cur = a

            k = (round(cur[0]/tol), round(cur[1]/tol))
            found = False
            for ni, ne in ep.get(k, []):
                if not used[ni]:
                    na, nb = segs[ni]
                    ka_n = (round(na[0]/tol), round(na[1]/tol))
                    exit_e = 1 if ka_n == k else 0
                    ci    = ni
                    found = True
                    break
            if not found:
                loop.append(cur)
                break

        if len(loop) >= 3:
            loops.append(loop)

    return loops


def signed_area(pts):
    """Shoelace formula. Positive = CCW when Y-up."""
    n = len(pts)
    a = 0.0
    for i in range(n):
        j = (i+1) % n
        a += pts[i][0] * pts[j][1] - pts[j][0] * pts[i][1]
    return a * 0.5


# ── Infill ────────────────────────────────────────────────────────────────────
def make_infill(loops, spacing, angle_deg):
    """Scanline rectilinear infill inside multiple loops."""
    if not loops:
        return []

    c = math.cos(math.radians(angle_deg))
    s = math.sin(math.radians(angle_deg))

    def rot(p):   return ( p[0]*c + p[1]*s, -p[0]*s + p[1]*c)
    def unrot(p): return ( p[0]*c - p[1]*s,  p[0]*s + p[1]*c)

    rot_loops = [[rot(p) for p in lp] for lp in loops]
    all_rpts  = [p for lp in rot_loops for p in lp]
    ry0 = min(p[1] for p in all_rpts) + spacing * 0.5
    ry1 = max(p[1] for p in all_rpts)

    lines = []
    y = ry0
    while y <= ry1:
        xs = []
        for lp in rot_loops:
            n = len(lp)
            for i in range(n):
                pa, pb = lp[i], lp[(i+1)%n]
                if (pa[1] - y) * (pb[1] - y) < 0:
                    t = (y - pa[1]) / (pb[1] - pa[1])
                    xs.append(pa[0] + t * (pb[0] - pa[0]))
        xs.sort()
        for i in range(0, len(xs)-1, 2):
            x1 = xs[i]   + NOZZLE_D * 0.5
            x2 = xs[i+1] - NOZZLE_D * 0.5
            if x2 > x1 + 0.1:
                lines.append((unrot((x1, y)), unrot((x2, y))))
        y += spacing

    return lines


# ── G-code writer ─────────────────────────────────────────────────────────────
class GCodeWriter:
    def __init__(self, fname, ox, oy):
        """ox, oy: bed-space offset so model centre lands at bed centre."""
        self.f    = open(fname, 'w')
        self.E    = 0.0
        self.retracted = False
        self.cx   = None   # current bed X
        self.cy   = None   # current bed Y
        self.ox   = ox
        self.oy   = oy

    def _w(self, line):
        self.f.write(line + '\n')

    def _bed(self, mx, my):
        return mx + self.ox, my + self.oy

    def _dist(self, bx, by):
        if self.cx is None: return 0.0
        return math.sqrt((bx-self.cx)**2 + (by-self.cy)**2)

    # ── public API ────────────────────────────────────────────────────────────
    def header(self, stl_name):
        w = self._w
        w(f'; Sliced by python slicer  →  {os.path.basename(stl_name)}')
        w(f'; Printer : Entina Tina2S V12')
        w(f'; Material: PLA  Nozzle: {NOZZLE_D}mm  Filament: {FILAMENT_D}mm')
        w(f'; Layer h : {LAYER_H}mm   Infill: {INFILL_PCT}%')
        w('')
        w(f'M104 S{NOZZLE_T}      ; heat nozzle (no wait)')
        w(f'M140 S{BED_T}         ; heat bed (no wait)')
        w(f'M109 S{NOZZLE_T}      ; wait nozzle')
        w(f'M190 S{BED_T}         ; wait bed')
        w('')
        w('G28                  ; home all axes')
        w('G21                  ; mm')
        w('G90                  ; absolute XYZ')
        w('M82                  ; absolute E')
        w('G92 E0               ; zero E')
        w('')
        w('; --- purge line (left edge) ---')
        w('G1 Z0.3 F1200')
        w('G1 X3 Y15 F6000')
        w(f'G1 X3 Y85 E10 F{SPD_FIRST}')
        w('G92 E0')
        w('')
        # sync state
        self.E = 0.0
        self.retracted = False
        self.cx = 3.0
        self.cy = 85.0

    def layer(self, z):
        self._w(f'G1 Z{z:.3f} F1200')

    def travel(self, mx, my):
        bx, by = self._bed(mx, my)
        if not self.retracted:
            self.E -= RETRACT_D
            self._w(f'G1 E{self.E:.5f} F{RETRACT_SPD}  ; retract')
            self.retracted = True
        self._w(f'G1 X{bx:.3f} Y{by:.3f} F{SPD_TRAVEL}')
        self.cx, self.cy = bx, by

    def extrude(self, mx, my, e_fact, speed):
        bx, by = self._bed(mx, my)
        if self.retracted:
            self.E += RETRACT_D
            self._w(f'G1 E{self.E:.5f} F{RETRACT_SPD}  ; un-retract')
            self.retracted = False
        d = self._dist(bx, by)
        if d < 0.01:
            return
        self.E += d * e_fact
        self._w(f'G1 X{bx:.3f} Y{by:.3f} E{self.E:.5f} F{speed}')
        self.cx, self.cy = bx, by

    def footer(self):
        w = self._w
        w('')
        w('; --- end print ---')
        w('M104 S0             ; nozzle off')
        w('M140 S0             ; bed off')
        w('G91                 ; relative')
        w('G1 Z10 F1200        ; raise nozzle')
        w('G28 X0 Y0           ; home XY')
        w('M84                 ; motors off')

    def close(self):
        self.f.close()


# ── Main slicing pipeline ─────────────────────────────────────────────────────
def slice_to_gcode(stl_fname, gcode_fname):
    print(f'\n{"="*55}')
    print(f'  STL   : {stl_fname}')
    print(f'  G-code: {gcode_fname}')
    print(f'{"="*55}')

    # Load
    print('Loading STL ...')
    tris = load_stl(stl_fname)
    print(f'  {len(tris):,} triangles')

    # Bounds
    all_verts = [v for t in tris for v in t]
    xs = [v[0] for v in all_verts]
    ys = [v[1] for v in all_verts]
    zs_all = [v[2] for v in all_verts]
    z_min = max(0.0, min(zs_all))
    z_max = max(zs_all)
    model_cx = (max(xs) + min(xs)) / 2.0
    model_cy = (max(ys) + min(ys)) / 2.0
    model_w  = max(xs) - min(xs)
    model_d  = max(ys) - min(ys)
    ox = BED_X / 2.0 - model_cx
    oy = BED_Y / 2.0 - model_cy

    print(f'  Size  : {model_w:.1f} x {model_d:.1f} x {z_max-z_min:.1f} mm')
    print(f'  Bed XY: centred at ({BED_X/2:.0f},{BED_Y/2:.0f})  offset=({ox:.1f},{oy:.1f})')
    if model_w > BED_X - 2 or model_d > BED_Y - 2:
        print('  ** WARNING: model is very close to bed edges **')

    # Pre-sort triangles by z_lo (enables early-exit in slice_layer)
    print('Pre-sorting triangles ...')
    tris_sorted = sorted(
        [(min(t[0][2],t[1][2],t[2][2]), max(t[0][2],t[1][2],t[2][2]), t)
         for t in tris],
        key=lambda x: x[0]
    )

    # Build layer list
    layers = []
    z = z_min + FIRST_LAYER_H
    layers.append((z, True))   # first layer
    while True:
        z += LAYER_H
        if z > z_max + LAYER_H * 0.5:
            break
        layers.append((z, False))
    print(f'  {len(layers)} layers  (first {FIRST_LAYER_H}mm, rest {LAYER_H}mm)')

    # Slice & write
    print('Slicing ...')
    gw = GCodeWriter(gcode_fname, ox, oy)
    gw.header(stl_fname)

    t0 = time.time()
    for li, (lz, is_first) in enumerate(layers):
        if li % 25 == 0 or li == len(layers)-1:
            pct = (li+1) / len(layers) * 100
            ela = time.time() - t0
            eta = ela / (li+1) * (len(layers)-li-1) if li else 0
            print(f'  Layer {li+1:4d}/{len(layers)}  {pct:5.1f}%  '
                  f'elapsed {ela:5.0f}s  ETA {eta:5.0f}s', end='\r')

        e_fact = E_FACTOR_FIRST if is_first else E_FACTOR
        speed  = SPD_FIRST      if is_first else SPD_PERI

        gw._w(f'\n; layer {li+1}  z={lz:.3f}')
        gw.layer(lz)

        segs  = slice_layer(tris_sorted, lz)
        loops = connect_segments(segs)

        # Perimeters
        for loop in loops:
            if len(loop) < 3:
                continue
            if signed_area(loop) < 0:
                loop = list(reversed(loop))

            gw.travel(loop[0][0], loop[0][1])
            for pt in loop[1:]:
                gw.extrude(pt[0], pt[1], e_fact, speed)
            gw.extrude(loop[0][0], loop[0][1], e_fact, speed)

        # Infill (alternate ±45° for inter-layer strength)
        angle = 45 if li % 2 == 0 else 135
        for (p1, p2) in make_infill(loops, INFILL_SPACING, angle):
            gw.travel(p1[0], p1[1])
            gw.extrude(p2[0], p2[1], e_fact,
                       SPD_FIRST if is_first else SPD_INFILL)

    gw.footer()
    gw.close()

    elapsed = time.time() - t0
    size    = os.path.getsize(gcode_fname)
    print(f'\n  Done in {elapsed:.0f}s   {size/1024/1024:.2f} MB  →  {gcode_fname}')


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if len(sys.argv) == 3:
        slice_to_gcode(sys.argv[1], sys.argv[2])
    else:
        # Default: slice both models
        jobs = [
            ('mackenzie_nameplate.stl', 'mackenzie_nameplate.gcode'),
            ('frenchie.stl',            'frenchie.gcode'),
        ]
        for stl, gco in jobs:
            if os.path.exists(stl):
                slice_to_gcode(stl, gco)
            else:
                print(f'Skipping {stl} (not found)')
