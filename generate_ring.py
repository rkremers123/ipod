#!/usr/bin/env python3
"""
Solitaire diamond ring generator — sized for Ring Size 6 (16.5mm inner diameter)
Prints without supports on Entina Tina2S V12 (print standing upright)
"""
import math, struct

# ── Ring size 6 dimensions ────────────────────────────────────────────────────
INNER_R   = 8.25     # mm  inner radius  (16.5mm diameter = size 6)
BAND_T    = 1.8      # mm  band wall thickness
BAND_H    = 3.5      # mm  band height (comfortable to wear)
OUTER_R   = INNER_R + BAND_T

# ── Setting / gem ─────────────────────────────────────────────────────────────
GEM_R     = 4.0      # mm  girdle radius of diamond
CROWN_H   = 2.2      # mm  crown height
PAVIL_H   = 3.0      # mm  pavilion depth below girdle
TABLE_R   = GEM_R * 0.55  # table radius

SETTING_H = 3.5      # mm  height of cathedral shoulders above band top
SETTING_W = BAND_T   # base width of shoulders

# ── STL helpers ───────────────────────────────────────────────────────────────
def fn(v0, v1, v2):
    ax,ay,az = v1[0]-v0[0],v1[1]-v0[1],v1[2]-v0[2]
    bx,by,bz = v2[0]-v0[0],v2[1]-v0[1],v2[2]-v0[2]
    nx,ny,nz = ay*bz-az*by, az*bx-ax*bz, ax*by-ay*bx
    l = math.sqrt(nx*nx+ny*ny+nz*nz)
    return (nx/l,ny/l,nz/l) if l>1e-12 else (0,0,1)

def write_stl(path, tris):
    hdr = b'Diamond Ring - Size 6 - Entina Tina2S V12'
    hdr = hdr + b'\x00' * (80 - len(hdr))   # always exactly 80 bytes
    with open(path,'wb') as f:
        f.write(hdr[:80]); f.write(struct.pack('<I',len(tris)))
        for v0,v1,v2 in tris:
            n=fn(v0,v1,v2)
            f.write(struct.pack('<3f',*n))
            f.write(struct.pack('<3f',*v0))
            f.write(struct.pack('<3f',*v1))
            f.write(struct.pack('<3f',*v2))
            f.write(struct.pack('<H',0))

# ── Primitives ────────────────────────────────────────────────────────────────
pi = math.pi; cos = math.cos; sin = math.sin

def band(inner_r, outer_r, h, n=80):
    """Hollow ring band (torus cross-section = rectangle)"""
    T = []
    for i in range(n):
        a0, a1 = 2*pi*i/n, 2*pi*(i+1)/n
        # inner wall
        T.append(((inner_r*cos(a0),inner_r*sin(a0),0),
                  (inner_r*cos(a1),inner_r*sin(a1),0),
                  (inner_r*cos(a1),inner_r*sin(a1),h)))
        T.append(((inner_r*cos(a0),inner_r*sin(a0),0),
                  (inner_r*cos(a1),inner_r*sin(a1),h),
                  (inner_r*cos(a0),inner_r*sin(a0),h)))
        # outer wall
        T.append(((outer_r*cos(a0),outer_r*sin(a0),h),
                  (outer_r*cos(a1),outer_r*sin(a1),h),
                  (outer_r*cos(a1),outer_r*sin(a1),0)))
        T.append(((outer_r*cos(a0),outer_r*sin(a0),h),
                  (outer_r*cos(a1),outer_r*sin(a1),0),
                  (outer_r*cos(a0),outer_r*sin(a0),0)))
        # bottom face
        T.append(((0,0,0),
                  (outer_r*cos(a1),outer_r*sin(a1),0),
                  (outer_r*cos(a0),outer_r*sin(a0),0)))
        T.append(((0,0,0),
                  (inner_r*cos(a0),inner_r*sin(a0),0),
                  (inner_r*cos(a1),inner_r*sin(a1),0)))
        # top face
        T.append(((0,0,h),
                  (outer_r*cos(a0),outer_r*sin(a0),h),
                  (outer_r*cos(a1),outer_r*sin(a1),h)))
        T.append(((0,0,h),
                  (inner_r*cos(a1),inner_r*sin(a1),h),
                  (inner_r*cos(a0),inner_r*sin(a0),h)))
    return T

def diamond(cx, cy, cz, gem_r, table_r, crown_h, pavil_h, n=16):
    """
    Brilliant-cut diamond approximation.
    n main vertices around girdle (16 gives a nice round appearance).
    """
    T = []
    # Girdle ring
    G = [(cx+gem_r*cos(2*pi*k/n), cy+gem_r*sin(2*pi*k/n), cz) for k in range(n)]
    # Table ring (rotated by half-step)
    TBL = [(cx+table_r*cos(2*pi*k/n + pi/n), cy+table_r*sin(2*pi*k/n + pi/n), cz+crown_h)
           for k in range(n)]
    table_ctr = (cx, cy, cz+crown_h)
    culet     = (cx, cy, cz-pavil_h)

    for k in range(n):
        k1 = (k+1)%n
        # Crown: girdle → table (two triangles per panel)
        T.append((G[k],  G[k1],  TBL[k]))
        T.append((G[k1], TBL[k1], TBL[k]))
        # Table face (fan from centre)
        T.append((table_ctr, TBL[k], TBL[k1]))
        # Pavilion: girdle → culet
        T.append((G[k1], G[k], culet))

    return T

def prong(cx, cy, base_z, top_z, r_base, r_top, n=12):
    """Tapered cylinder for a setting prong"""
    T = []
    for i in range(n):
        a0,a1 = 2*pi*i/n, 2*pi*(i+1)/n
        b0=(cx+r_base*cos(a0),cy+r_base*sin(a0),base_z)
        b1=(cx+r_base*cos(a1),cy+r_base*sin(a1),base_z)
        t0=(cx+r_top*cos(a0), cy+r_top*sin(a0), top_z)
        t1=(cx+r_top*cos(a1), cy+r_top*sin(a1), top_z)
        T+=[(b0,b1,t1),(b0,t1,t0)]
        T.append(((cx,cy,base_z),b1,b0))
        T.append(((cx,cy,top_z), t0,t1))
    return T

def cathedral_shoulder(angle, inner_r, outer_r, band_h, setting_h, gem_r, n_pts=20):
    """
    One shoulder of the cathedral setting — sweeps from band top up to gem girdle.
    angle: angular position on the ring (radians), shoulder spans ±sweep around angle.
    """
    T = []
    sweep = pi * 0.30      # shoulder spans 54° either side of gem axis
    for i in range(n_pts):
        t0 = i / n_pts
        t1 = (i+1) / n_pts
        a0 = angle - sweep*(1-t0)
        a1 = angle - sweep*(1-t1)
        # radius interpolates from outer_r up to gem_r as we approach top
        r0_out = outer_r + (gem_r - outer_r) * t0**1.5
        r0_in  = inner_r
        r1_out = outer_r + (gem_r - outer_r) * t1**1.5
        r1_in  = inner_r
        z0 = band_h + setting_h * t0**0.7
        z1 = band_h + setting_h * t1**0.7

        # Outer face
        p00=(r0_out*cos(a0),r0_out*sin(a0),z0)
        p01=(r0_out*cos(a0),r0_out*sin(a0),z0)   # same (radial)
        p10=(r1_out*cos(a1),r1_out*sin(a1),z1)
        # Actually build quad strips around sweep
        for j in range(6):
            b0 = a0 + sweep*2*j/6
            b1 = a0 + sweep*2*(j+1)/6
            if abs(b0-angle)+abs(b1-angle) > sweep*2.1: continue
            ob0=(r0_out*cos(b0),r0_out*sin(b0),z0)
            ob1=(r0_out*cos(b1),r0_out*sin(b1),z0)
            ot0=(r1_out*cos(b0),r1_out*sin(b0),z1)
            ot1=(r1_out*cos(b1),r1_out*sin(b1),z1)
            T+=[(ob0,ob1,ot1),(ob0,ot1,ot0)]
            # inner face
            ib0=(r0_in*cos(b0),r0_in*sin(b0),z0)
            ib1=(r0_in*cos(b1),r0_in*sin(b1),z0)
            it0=(r1_in*cos(b0),r1_in*sin(b0),z1)
            it1=(r1_in*cos(b1),r1_in*sin(b1),z1)
            T+=[(ib1,ib0,it0),(ib1,it0,it1)]
    return T

# ── Assemble ──────────────────────────────────────────────────────────────────
def build_ring():
    T = []

    # 1. Band
    T += band(INNER_R, OUTER_R, BAND_H)

    # 2. Cathedral shoulders (two, at top of band, at ±90° to bridge the gap)
    for ang in (0, pi):
        T += cathedral_shoulder(ang, INNER_R, OUTER_R, BAND_H, SETTING_H, GEM_R)

    # 3. Bezel platform at top of setting to hold gem
    gem_z = BAND_H + SETTING_H
    bezel_h = 0.8
    bezel_inner_r = GEM_R - 0.3
    bezel_outer_r = GEM_R + 0.5
    T += band(bezel_inner_r, bezel_outer_r, bezel_h, n=48)
    # translate bezel to gem_z
    T_bezel = []
    for v0,v1,v2 in T[-48*8:]:
        T_bezel.append((
            (v0[0],v0[1],v0[2]+gem_z),
            (v1[0],v1[1],v1[2]+gem_z),
            (v2[0],v2[1],v2[2]+gem_z),
        ))
    T = T[:-48*8] + T_bezel

    # 4. Four prongs at cardinal points
    for ang in (0, pi/2, pi, 3*pi/2):
        px = GEM_R * cos(ang)
        py = GEM_R * sin(ang)
        T += prong(px, py,
                   base_z=gem_z - 0.5,
                   top_z=gem_z + CROWN_H + 0.8,
                   r_base=0.7, r_top=0.5)

    # 5. Diamond gem (girdle sits at gem_z + bezel_h)
    T += diamond(0, 0, gem_z + bezel_h,
                 GEM_R, TABLE_R, CROWN_H, PAVIL_H)

    return T


if __name__ == '__main__':
    import sys, os
    out = sys.argv[1] if len(sys.argv) > 1 else 'ring_size6.stl'
    print('Building ring (size 6, 16.5mm inner diameter)...')
    tris = build_ring()
    print(f'  {len(tris):,} triangles')
    write_stl(out, tris)
    sz = os.path.getsize(out)
    print(f'  {sz/1024:.0f} KB  →  {out}')
    print()
    print('Print tips for Entina Tina2S V12:')
    print('  Orientation : stand the ring upright on its side')
    print('  Layer height: 0.1 mm (finest detail)')
    print('  Infill      : 100% (solid — it needs to be strong)')
    print('  Supports    : none needed when printed upright')
    print('  Material    : PLA (white or clear looks like diamond/silver)')
    print('  Speed       : 25 mm/s (slow for quality)')
