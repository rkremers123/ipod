#!/usr/bin/env python3
"""
French Bulldog STL Generator
Sitting pose, sized for Entina Tina2S V12 (~120x120x150mm build volume)
Output: ~90mm tall sitting French Bulldog
"""

import math
import struct


# ── Vector math ──────────────────────────────────────────────────────────────

def vadd(a, b): return (a[0]+b[0], a[1]+b[1], a[2]+b[2])
def vsub(a, b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def vscale(a, s): return (a[0]*s, a[1]*s, a[2]*s)
def vdot(a, b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def vcross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def vnorm(v):
    l = math.sqrt(v[0]**2+v[1]**2+v[2]**2)
    return (v[0]/l, v[1]/l, v[2]/l) if l > 1e-12 else (0.0, 0.0, 1.0)
def face_normal(v0, v1, v2):
    return vnorm(vcross(vsub(v1, v0), vsub(v2, v0)))


# ── Transform helpers ─────────────────────────────────────────────────────────

def rotate_x(pt, angle):
    x, y, z = pt
    c, s = math.cos(angle), math.sin(angle)
    return (x, y*c - z*s, y*s + z*c)

def rotate_y(pt, angle):
    x, y, z = pt
    c, s = math.cos(angle), math.sin(angle)
    return (x*c + z*s, y, -x*s + z*c)

def rotate_z(pt, angle):
    x, y, z = pt
    c, s = math.cos(angle), math.sin(angle)
    return (x*c - y*s, x*s + y*c, z)

def translate(pt, dx, dy, dz):
    return (pt[0]+dx, pt[1]+dy, pt[2]+dz)

def apply_transform(tris, fn):
    return [(fn(a), fn(b), fn(c)) for a, b, c in tris]

def flip_normals(tris):
    return [(a, c, b) for a, b, c in tris]


# ── Primitive generators ──────────────────────────────────────────────────────

def ellipsoid(cx, cy, cz, rx, ry, rz, slices=24, stacks=18):
    """UV-sphere scaled to ellipsoid"""
    tris = []
    for i in range(stacks):
        phi0 = math.pi * i / stacks - math.pi / 2
        phi1 = math.pi * (i + 1) / stacks - math.pi / 2
        cp0, sp0 = math.cos(phi0), math.sin(phi0)
        cp1, sp1 = math.cos(phi1), math.sin(phi1)
        for j in range(slices):
            t0 = 2 * math.pi * j / slices
            t1 = 2 * math.pi * (j + 1) / slices
            ct0, st0 = math.cos(t0), math.sin(t0)
            ct1, st1 = math.cos(t1), math.sin(t1)

            def p(ct, st, cp, sp):
                return (cx + rx*cp*ct, cy + ry*cp*st, cz + rz*sp)

            p00 = p(ct0, st0, cp0, sp0)
            p10 = p(ct1, st1, cp0, sp0)
            p01 = p(ct0, st0, cp1, sp1)
            p11 = p(ct1, st1, cp1, sp1)

            if i > 0:
                tris.append((p00, p10, p11))
            if i < stacks - 1:
                tris.append((p00, p11, p01))
    return tris


def cylinder(cx, cy, cz, r_bot, r_top, height, slices=20, closed=True):
    """Tapered cylinder (frustum). r_bot==r_top for plain cylinder."""
    tris = []
    for j in range(slices):
        t0 = 2*math.pi*j/slices
        t1 = 2*math.pi*(j+1)/slices
        b0 = (cx+r_bot*math.cos(t0), cy+r_bot*math.sin(t0), cz)
        b1 = (cx+r_bot*math.cos(t1), cy+r_bot*math.sin(t1), cz)
        tp0 = (cx+r_top*math.cos(t0), cy+r_top*math.sin(t0), cz+height)
        tp1 = (cx+r_top*math.cos(t1), cy+r_top*math.sin(t1), cz+height)
        # Side faces
        tris.append((b0, b1, tp1))
        tris.append((b0, tp1, tp0))
        if closed:
            # Bottom cap
            tris.append(((cx, cy, cz), b1, b0))
            # Top cap
            tris.append(((cx, cy, cz+height), tp0, tp1))
    return tris


def half_sphere_cap(cx, cy, cz, rx, ry, rz, top=True, slices=24, stacks=9):
    """Half ellipsoid cap"""
    tris = []
    phi_start = 0 if top else -math.pi/2
    phi_end   = math.pi/2 if top else 0
    for i in range(stacks):
        phi0 = phi_start + (phi_end - phi_start) * i / stacks
        phi1 = phi_start + (phi_end - phi_start) * (i+1) / stacks
        cp0, sp0 = math.cos(phi0), math.sin(phi0)
        cp1, sp1 = math.cos(phi1), math.sin(phi1)
        for j in range(slices):
            t0 = 2*math.pi*j/slices
            t1 = 2*math.pi*(j+1)/slices
            def p(ct, st, cp, sp):
                return (cx+rx*cp*ct, cy+ry*cp*st, cz+rz*sp)
            p00 = p(math.cos(t0), math.sin(t0), cp0, sp0)
            p10 = p(math.cos(t1), math.sin(t1), cp0, sp0)
            p01 = p(math.cos(t0), math.sin(t0), cp1, sp1)
            p11 = p(math.cos(t1), math.sin(t1), cp1, sp1)
            tris.append((p00, p10, p11))
            tris.append((p00, p11, p01))
    return tris


def flat_disc(cx, cy, cz, r, axis_normal='z', slices=20):
    """Flat disc"""
    tris = []
    center = (cx, cy, cz)
    for j in range(slices):
        t0, t1 = 2*math.pi*j/slices, 2*math.pi*(j+1)/slices
        if axis_normal == 'z':
            p0 = (cx+r*math.cos(t0), cy+r*math.sin(t0), cz)
            p1 = (cx+r*math.cos(t1), cy+r*math.sin(t1), cz)
        elif axis_normal == 'y':
            p0 = (cx+r*math.cos(t0), cy, cz+r*math.sin(t0))
            p1 = (cx+r*math.cos(t1), cy, cz+r*math.sin(t1))
        tris.append((center, p0, p1))
    return tris


def ring_extrude(cx, cy, cz, r_outer, r_inner, height, slices=24):
    """Hollow ring/donut cross-section extruded — good for forehead wrinkle ridges"""
    tris = []
    for j in range(slices):
        t0, t1 = 2*math.pi*j/slices, 2*math.pi*(j+1)/slices
        # outer
        ob0 = (cx+r_outer*math.cos(t0), cy+r_outer*math.sin(t0), cz)
        ob1 = (cx+r_outer*math.cos(t1), cy+r_outer*math.sin(t1), cz)
        ot0 = (cx+r_outer*math.cos(t0), cy+r_outer*math.sin(t0), cz+height)
        ot1 = (cx+r_outer*math.cos(t1), cy+r_outer*math.sin(t1), cz+height)
        tris.append((ob0, ob1, ot1)); tris.append((ob0, ot1, ot0))
        # inner (flipped)
        ib0 = (cx+r_inner*math.cos(t0), cy+r_inner*math.sin(t0), cz)
        ib1 = (cx+r_inner*math.cos(t1), cy+r_inner*math.sin(t1), cz)
        it0 = (cx+r_inner*math.cos(t0), cy+r_inner*math.sin(t0), cz+height)
        it1 = (cx+r_inner*math.cos(t1), cy+r_inner*math.sin(t1), cz+height)
        tris.append((ib1, ib0, it0)); tris.append((ib1, it0, it1))
        # top/bottom annular faces
        tris.append((ob0, ot0, it0)); tris.append((ob0, it0, ib0))
        tris.append((ob1, ib1, it1)); tris.append((ob1, it1, ot1))
    return tris


def bat_ear(tip_x, tip_y, base_z, ear_h, ear_w, ear_thick, tilt_out, tilt_fwd,
            slices=28):
    """
    French Bulldog bat ear: tall, erect, rounded triangle.
    Built as a swept loft from a wide elliptical base to a narrow rounded tip.
    tip_x / tip_y = horizontal centre of ear base
    base_z        = Z of ear base (where it meets skull)
    ear_h         = height of ear
    ear_w         = half-width at base
    ear_thick     = front-to-back thickness
    """
    tris = []
    N = slices  # points around ear perimeter

    def ear_outline(frac):
        """
        Returns list of (local_x, local_y) points tracing the ear cross-
        section at height fraction frac (0=base, 1=tip).
        At frac=0: broad ellipse. At frac=1: near-point.
        """
        w = ear_w * (1 - frac)**0.7          # width tapers
        d = ear_thick * (1 - frac * 0.8)     # thickness tapers
        pts = []
        for k in range(N):
            ang = 2*math.pi*k/N
            px = w * math.cos(ang)
            py = d/2 * math.sin(ang)
            pts.append((px, py))
        return pts

    levels = 20
    stacks_pts = []
    for lev in range(levels + 1):
        frac = lev / levels
        z_local = frac * ear_h
        # slight forward lean as ear rises
        x_shift = math.sin(frac * tilt_out) * ear_h * 0.15
        y_shift = -math.sin(frac * tilt_fwd) * ear_h * 0.1
        ring2d = ear_outline(frac)
        ring3d = []
        for (lx, ly) in ring2d:
            wx = tip_x + lx + x_shift
            wy = tip_y + ly + y_shift
            wz = base_z + z_local
            ring3d.append((wx, wy, wz))
        stacks_pts.append(ring3d)

    # Side walls between levels
    for lev in range(levels):
        r0 = stacks_pts[lev]
        r1 = stacks_pts[lev + 1]
        for k in range(N):
            k1 = (k + 1) % N
            a, b = r0[k], r0[k1]
            c, d = r1[k], r1[k1]
            tris.append((a, b, d))
            tris.append((a, d, c))

    # Bottom cap (base of ear)
    base = stacks_pts[0]
    cx0 = sum(p[0] for p in base)/N
    cy0 = sum(p[1] for p in base)/N
    cz0 = base_z
    center_b = (cx0, cy0, cz0)
    for k in range(N):
        tris.append((center_b, base[(k+1)%N], base[k]))

    # Top cap (tip of ear)
    tip_ring = stacks_pts[-1]
    cx1 = sum(p[0] for p in tip_ring)/N
    cy1 = sum(p[1] for p in tip_ring)/N
    cz1 = base_z + ear_h
    center_t = (cx1, cy1, cz1)
    for k in range(N):
        tris.append((center_t, tip_ring[k], tip_ring[(k+1)%N]))

    return tris


def wrinkle_roll(cx, cy, cz, rx, ry, rz, angle_start, angle_end, slices=24):
    """
    Partial-torus-like roll to simulate forehead / nose wrinkle.
    Modelled as a partial ellipsoid ridge.
    """
    tris = []
    steps = slices
    stacks = 6
    for i in range(stacks):
        phi0 = math.pi * i / stacks
        phi1 = math.pi * (i+1) / stacks
        for j in range(steps):
            t0 = angle_start + (angle_end - angle_start) * j / steps
            t1 = angle_start + (angle_end - angle_start) * (j+1) / steps
            def p(t, phi):
                return (cx + rx*math.sin(phi)*math.cos(t),
                        cy + ry*math.sin(phi)*math.sin(t),
                        cz + rz*math.cos(phi))
            p00 = p(t0, phi0); p10 = p(t1, phi0)
            p01 = p(t0, phi1); p11 = p(t1, phi1)
            tris.append((p00, p10, p11))
            tris.append((p00, p11, p01))
    return tris


# ── Paw / leg builder ─────────────────────────────────────────────────────────

def paw_and_leg(cx, cy, foot_z, leg_top_z, leg_r, paw_rx, paw_ry, paw_rz):
    """Stubby leg + rounded paw"""
    tris = []
    # leg (slightly tapered cylinder)
    tris += cylinder(cx, cy, foot_z + paw_rz*0.7, leg_r, leg_r*0.9,
                     leg_top_z - foot_z - paw_rz*0.7, slices=16)
    # paw
    tris += ellipsoid(cx, cy, foot_z + paw_rz, paw_rx, paw_ry, paw_rz,
                      slices=20, stacks=14)
    # toe ridges (3 bumps on front of paw)
    for ti in range(3):
        tx = cx + (ti - 1) * paw_rx * 0.42
        ty = cy - paw_ry * 0.7
        tris += ellipsoid(tx, ty, foot_z + paw_rz*0.55,
                          paw_rx*0.22, paw_ry*0.18, paw_rz*0.28,
                          slices=10, stacks=8)
    return tris


# ── Assemble the dog ──────────────────────────────────────────────────────────

def build_frenchie():
    all_tris = []

    # ── Torso ──────────────────────────────────────────────────────────────
    # Stocky, barrel-chested body. Sitting so rear haunches support body.
    # Body centre at (0, 0, 30). Wide front-to-back, tall.
    body = ellipsoid(0, 0, 30, rx=23, ry=17, rz=26, slices=28, stacks=22)
    all_tris += body

    # Chest protrusion (French bulldogs have a prominent chest)
    chest = ellipsoid(0, -14, 22, rx=14, ry=9, rz=12, slices=20, stacks=14)
    all_tris += chest

    # ── Rear haunches (sitting) ────────────────────────────────────────────
    for side in (-1, 1):
        hx = side * 14
        haunch = ellipsoid(hx, 8, 20, rx=11, ry=12, rz=16, slices=18, stacks=14)
        all_tris += haunch
        # thigh connecting to body
        thigh = ellipsoid(hx*0.7, 4, 12, rx=7, ry=9, rz=10, slices=14, stacks=10)
        all_tris += thigh

    # ── Neck ───────────────────────────────────────────────────────────────
    neck = cylinder(0, -4, 44, r_bot=10, r_top=8, height=10, slices=20, closed=False)
    all_tris += neck

    # ── Head ───────────────────────────────────────────────────────────────
    # Large, square-ish, brachycephalic head
    head = ellipsoid(0, -4, 60, rx=21, ry=19, rz=19, slices=28, stacks=22)
    all_tris += head

    # ── Muzzle / Snout ─────────────────────────────────────────────────────
    # Very flat face — disc-like protrusion
    muzzle = ellipsoid(0, -22, 57, rx=11, ry=5, rz=9, slices=22, stacks=16)
    all_tris += muzzle

    # Upper lip split (philtrum) — small ridge
    philtrum = ellipsoid(0, -26, 56, rx=2.5, ry=2.5, rz=4, slices=12, stacks=8)
    all_tris += philtrum

    # Nostrils — two small elevated bumps
    for side in (-1, 1):
        nostril = ellipsoid(side*4.5, -26.5, 56,
                            rx=2.8, ry=2.0, rz=2.5, slices=12, stacks=8)
        all_tris += nostril

    # ── Forehead wrinkles ──────────────────────────────────────────────────
    # French bulldogs have characteristic forehead rolls
    for wz, wr, wd in [(68, 9, 1.5), (65, 11, 1.2)]:
        # wrinkle roll across forehead
        roll = wrinkle_roll(0, -8, wz, rx=wr, ry=wd, rz=wd*1.5,
                            angle_start=-math.pi*0.55, angle_end=math.pi*0.55)
        all_tris += roll

    # Nose wrinkle above muzzle
    nose_wrinkle = ellipsoid(0, -19, 63, rx=10, ry=2.5, rz=2,
                             slices=20, stacks=10)
    all_tris += nose_wrinkle

    # ── Eyes ───────────────────────────────────────────────────────────────
    # Large, round eyes set wide
    for side in (-1, 1):
        ex = side * 10
        # Eyeball bulge
        eye = ellipsoid(ex, -17, 61, rx=4.5, ry=3.0, rz=4.5,
                        slices=16, stacks=12)
        all_tris += eye
        # Eyelid ridge (half-ellipse above eye)
        lid = half_sphere_cap(ex, -16, 62, rx=5, ry=2, rz=2.5,
                              top=True, slices=16, stacks=6)
        all_tris += lid

    # ── Jowls / Cheeks ─────────────────────────────────────────────────────
    for side in (-1, 1):
        jx = side * 16
        jowl = ellipsoid(jx, -14, 55, rx=7, ry=6, rz=8, slices=18, stacks=12)
        all_tris += jowl

    # ── Bat Ears ───────────────────────────────────────────────────────────
    # Characteristic large, erect, rounded-triangle bat ears
    for side in (-1, 1):
        ex = side * 15
        tilt = side * 0.35   # tilt outward
        ear = bat_ear(
            tip_x=ex, tip_y=-6,
            base_z=71,
            ear_h=22,
            ear_w=9,
            ear_thick=4,
            tilt_out=tilt,
            tilt_fwd=0.2,
            slices=24,
        )
        all_tris += ear

        # Ear base connection bulge (where ear meets skull)
        ear_base = ellipsoid(ex, -7, 73, rx=8, ry=5, rz=6,
                             slices=16, stacks=10)
        all_tris += ear_base

    # ── Front legs & paws ──────────────────────────────────────────────────
    for side in (-1, 1):
        fx = side * 12
        paw = paw_and_leg(
            cx=fx, cy=-14,
            foot_z=0,
            leg_top_z=22,
            leg_r=5.5,
            paw_rx=7.5, paw_ry=6.5, paw_rz=4.5,
        )
        all_tris += paw

    # ── Tail (very short nub) ──────────────────────────────────────────────
    tail = ellipsoid(0, 16, 34, rx=4, ry=3, rz=3, slices=14, stacks=10)
    all_tris += tail

    # ── Ground plane baseline (flat bottom so dog can stand on printer bed) ─
    # Flatten anything below z=0 by clamping — slicers handle this fine.

    return all_tris


# ── STL writer ────────────────────────────────────────────────────────────────

def write_stl_binary(filepath, triangles):
    """Write binary STL (50-byte header + 4-byte count + 50 bytes/tri)"""
    header = b"French Bulldog - generated for Entina Tina2S V12" + b"\x00" * 32
    header = header[:80]
    with open(filepath, "wb") as f:
        f.write(header)
        f.write(struct.pack("<I", len(triangles)))
        for tri in triangles:
            v0, v1, v2 = tri
            n = face_normal(v0, v1, v2)
            f.write(struct.pack("<3f", *n))
            f.write(struct.pack("<3f", *v0))
            f.write(struct.pack("<3f", *v1))
            f.write(struct.pack("<3f", *v2))
            f.write(struct.pack("<H", 0))
    print(f"Written {len(triangles):,} triangles to {filepath}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, os
    out = sys.argv[1] if len(sys.argv) > 1 else "frenchie.stl"
    print("Building French Bulldog mesh...")
    tris = build_frenchie()
    print(f"  {len(tris):,} triangles generated")
    write_stl_binary(out, tris)
    size = os.path.getsize(out)
    print(f"  File size: {size/1024:.1f} KB")
    print("Done! Open frenchie.stl in your slicer (e.g. Cura) and print.")
    print("Recommended settings for Entina Tina2S V12:")
    print("  Layer height: 0.15mm (detail)")
    print("  Infill: 15-20%")
    print("  Supports: Yes (for ears and paws)")
    print("  Scale: ~85-95mm tall fits comfortably in build volume")
