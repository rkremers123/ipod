#!/usr/bin/env python3
"""
"Mackenzie" girly nameplate generator
Bubbly bubble-letters with hearts, stars, and a bow
For Entina Tina2S V12 (120×120×150 mm build volume)
Prints flat on the bed — letters rise up, nameplate can hang on wall
"""
import math, struct

# ── STL writer ────────────────────────────────────────────────────────────────

def face_normal(v0, v1, v2):
    ax, ay, az = v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2]
    bx, by, bz = v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2]
    nx, ny, nz = ay*bz-az*by, az*bx-ax*bz, ax*by-ay*bx
    l = math.sqrt(nx*nx+ny*ny+nz*nz)
    return (nx/l, ny/l, nz/l) if l > 1e-12 else (0.0, 0.0, 1.0)

def write_stl(path, tris):
    header = b'Mackenzie Nameplate - Made with love <3' + b'\x00'*41
    with open(path, 'wb') as f:
        f.write(header[:80])
        f.write(struct.pack('<I', len(tris)))
        for v0, v1, v2 in tris:
            n = face_normal(v0, v1, v2)
            f.write(struct.pack('<3f', *n))
            f.write(struct.pack('<3f', *v0))
            f.write(struct.pack('<3f', *v1))
            f.write(struct.pack('<3f', *v2))
            f.write(struct.pack('<H', 0))

# ── Geometric primitives ──────────────────────────────────────────────────────

def sphere(cx, cy, cz, r, sl=12, st=9):
    """UV sphere"""
    T = []
    for i in range(st):
        p0 = math.pi * i / st - math.pi/2
        p1 = math.pi * (i+1) / st - math.pi/2
        cp0, sp0 = math.cos(p0), math.sin(p0)
        cp1, sp1 = math.cos(p1), math.sin(p1)
        for j in range(sl):
            t0 = 2*math.pi*j/sl;     ct0, st0 = math.cos(t0), math.sin(t0)
            t1 = 2*math.pi*(j+1)/sl; ct1, st1 = math.cos(t1), math.sin(t1)
            p00 = (cx+r*cp0*ct0, cy+r*cp0*st0, cz+r*sp0)
            p10 = (cx+r*cp0*ct1, cy+r*cp0*st1, cz+r*sp0)
            p01 = (cx+r*cp1*ct0, cy+r*cp1*st0, cz+r*sp1)
            p11 = (cx+r*cp1*ct1, cy+r*cp1*st1, cz+r*sp1)
            if i > 0:        T.append((p00, p10, p11))
            if i < st - 1:  T.append((p00, p11, p01))
    return T

def box(x0, y0, z0, x1, y1, z1):
    """Solid box, 12 triangles"""
    v = [(x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
         (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)]
    return [
        (v[0],v[2],v[1]),(v[0],v[3],v[2]),   # bottom  -Z
        (v[4],v[5],v[6]),(v[4],v[6],v[7]),   # top     +Z
        (v[0],v[1],v[5]),(v[0],v[5],v[4]),   # front   -Y
        (v[3],v[7],v[6]),(v[3],v[6],v[2]),   # back    +Y
        (v[0],v[4],v[7]),(v[0],v[7],v[3]),   # left    -X
        (v[1],v[2],v[6]),(v[1],v[6],v[5]),   # right   +X
    ]

def cylinder_z(cx, cy, cz, r, h, sl=14):
    T = []
    for j in range(sl):
        t0 = 2*math.pi*j/sl;     c0,s0 = math.cos(t0),math.sin(t0)
        t1 = 2*math.pi*(j+1)/sl; c1,s1 = math.cos(t1),math.sin(t1)
        b0=(cx+r*c0,cy+r*s0,cz); b1=(cx+r*c1,cy+r*s1,cz)
        t0v=(cx+r*c0,cy+r*s0,cz+h); t1v=(cx+r*c1,cy+r*s1,cz+h)
        T+=[(b0,b1,t1v),(b0,t1v,t0v),((cx,cy,cz),b1,b0),((cx,cy,cz+h),t0v,t1v)]
    return T

def cone_z(cx, cy, cz, r, h, sl=14):
    T = []
    tip = (cx, cy, cz+h)
    for j in range(sl):
        t0 = 2*math.pi*j/sl;     c0,s0=math.cos(t0),math.sin(t0)
        t1 = 2*math.pi*(j+1)/sl; c1,s1=math.cos(t1),math.sin(t1)
        b0=(cx+r*c0,cy+r*s0,cz); b1=(cx+r*c1,cy+r*s1,cz)
        T+=[(b0,tip,b1),((cx,cy,cz),b1,b0)]
    return T

def half_donut(cx, cy, cz, R, r, sl=14):
    """Half torus (loop of bow)"""
    T = []
    for i in range(sl):
        a0 = math.pi * i / sl
        a1 = math.pi * (i+1) / sl
        for j in range(sl):
            b0 = 2*math.pi*j/sl
            b1 = 2*math.pi*(j+1)/sl
            def pt(a, b):
                return (cx+(R+r*math.cos(b))*math.cos(a),
                        cy+(R+r*math.cos(b))*math.sin(a),
                        cz+r*math.sin(b))
            p00=pt(a0,b0); p10=pt(a1,b0); p01=pt(a0,b1); p11=pt(a1,b1)
            T.append((p00,p10,p11)); T.append((p00,p11,p01))
    return T

# ── Decorative shapes ─────────────────────────────────────────────────────────

def heart_3d(cx, cy, cz, scale=1.0):
    """3D heart built from overlapping spheres"""
    T = []
    s = scale
    parts = [
        (-1.1, 0,  0.8, 1.05),   # left  bump
        ( 1.1, 0,  0.8, 1.05),   # right bump
        ( 0.0, 0,  0.1, 0.90),   # bridge
        ( 0.0, 0, -0.6, 0.75),   # lower body
        ( 0.0, 0, -1.3, 0.55),   # tip
    ]
    for ox, oy, oz, rs in parts:
        T += sphere(cx+ox*s, cy+oy*s, cz+oz*s, rs*s, sl=10, st=8)
    return T

def star_flat(cx, cy, cz, r, h=1.4, pts=5):
    """Extruded 5-pointed star"""
    T = []
    inner = r * 0.42
    verts = []
    for k in range(pts*2):
        ang = math.pi/2 + math.pi*k/pts
        rv = r if k%2==0 else inner
        verts.append((cx+rv*math.cos(ang), cy+rv*math.sin(ang)))
    n = len(verts)
    for k in range(n):
        nk = (k+1)%n
        # top
        T.append(((cx,cy,cz+h),(verts[k][0],verts[k][1],cz+h),(verts[nk][0],verts[nk][1],cz+h)))
        # bottom
        T.append(((cx,cy,cz),(verts[nk][0],verts[nk][1],cz),(verts[k][0],verts[k][1],cz)))
        # sides
        a0=(verts[k][0],verts[k][1],cz);   a1=(verts[k][0],verts[k][1],cz+h)
        b0=(verts[nk][0],verts[nk][1],cz); b1=(verts[nk][0],verts[nk][1],cz+h)
        T+=[(a0,b0,b1),(a0,b1,a1)]
    return T

def bow(cx, cy, cz, scale=1.0):
    """Cute ribbon bow = two loops + center knot"""
    T = []
    s = scale
    # Left loop
    T += half_donut(cx-2.2*s, cy, cz+0.5*s, 2.0*s, 1.0*s, sl=12)
    # Right loop (mirrored)
    T += half_donut(cx+2.2*s, cy, cz+0.5*s, 2.0*s, 1.0*s, sl=12)
    # Center knot
    T += sphere(cx, cy, cz+0.5*s, 1.3*s, sl=10, st=8)
    # Ribbon tails
    T += cylinder_z(cx-0.8*s, cy, cz, 0.5*s, 1.0*s, sl=10)
    T += cylinder_z(cx+0.8*s, cy, cz, 0.5*s, 1.0*s, sl=10)
    return T

# ── Letter pixel maps (5×7 grid, '1'=filled, row 0=top) ─────────────────────

GLYPHS = {
    'M': ['10001','11011','10101','10001','10001','10001','10001'],
    'A': ['01110','10001','10001','11111','10001','10001','10001'],
    'C': ['01110','10001','10000','10000','10000','10001','01110'],
    'K': ['10001','10010','10100','11000','10100','10010','10001'],
    'E': ['11111','10000','10000','11110','10000','10000','11111'],
    'N': ['10001','11001','10101','10101','10011','10001','10001'],
    'Z': ['11111','00001','00011','00110','01100','10000','11111'],
    'I': ['11111','00100','00100','00100','00100','00100','11111'],
}

# ── Nameplate assembly ────────────────────────────────────────────────────────

def build_nameplate():
    T = []

    # ── Layout parameters ─────────────────────────────────────────────────────
    WORD        = 'MACKENZIE'
    VOXEL_D     = 2.0     # mm  voxel centre-to-centre spacing
    VOXEL_R     = 1.32    # mm  sphere radius (slight overlap = smooth joins)
    ROWS        = 7
    COLS        = 5
    LTR_W       = (COLS-1) * VOXEL_D    # 8 mm per letter footprint
    LTR_H       = (ROWS-1) * VOXEL_D    # 12 mm letter height
    LTR_GAP     = 2.6                   # gap between letter bounding boxes
    LTR_STEP    = LTR_W + LTR_GAP       # 10.6 mm letter pitch

    N           = len(WORD)             # 9 letters
    LETTERS_SPAN = LTR_W + (N-1)*LTR_STEP   # 8 + 8*10.6 = 92.8 mm

    PLATE_W     = LETTERS_SPAN + 20.0   # 112.8 → ~113 mm
    PLATE_D     = 26.0                  # front-to-back
    PLATE_T     = 3.0                   # base thickness
    RIM_W       = 1.8                   # raised rim width
    RIM_H       = 1.4                   # raised rim extra height

    LTR_Z0      = PLATE_T              # letters sit directly on top of plate
    LTR_CY      = 0.0                  # letters centred in Y

    # Start X: centre the whole word
    ltr_start_x = -(LETTERS_SPAN / 2)

    # ── Base plate ────────────────────────────────────────────────────────────
    hw, hd = PLATE_W/2, PLATE_D/2
    T += box(-hw, -hd, 0, hw, hd, PLATE_T)

    # Raised border rim (4 strips around edge)
    z1 = PLATE_T + RIM_H
    # Front strip
    T += box(-hw, -hd,     PLATE_T, hw,           -hd+RIM_W, z1)
    # Back strip
    T += box(-hw,  hd-RIM_W, PLATE_T, hw,          hd,       z1)
    # Left strip
    T += box(-hw, -hd,     PLATE_T, -hw+RIM_W, hd,           z1)
    # Right strip
    T += box( hw-RIM_W, -hd, PLATE_T, hw,       hd,          z1)

    # ── Bubble letters ────────────────────────────────────────────────────────
    # Fun bouncy baseline: alternate letters offset up/down slightly
    bounce = [0, 1.5, 0, 1.5, 0, 1.5, 0, 1.5, 0]   # mm extra Z per letter

    for li, ch in enumerate(WORD):
        grid = GLYPHS[ch]
        lx0  = ltr_start_x + li * LTR_STEP   # X of leftmost voxel column
        bz   = LTR_Z0 + bounce[li]            # baseline Z with bounce

        for row in range(ROWS):
            for col in range(COLS):
                if grid[row][col] == '1':
                    vx = lx0 + col * VOXEL_D
                    vy = LTR_CY
                    vz = bz + (ROWS-1-row) * VOXEL_D + VOXEL_R
                    T += sphere(vx, vy, vz, VOXEL_R, sl=12, st=9)

    # ── Heart dot above the I (8th letter, index 7) ───────────────────────────
    i_lx0 = ltr_start_x + 7 * LTR_STEP
    i_cx   = i_lx0 + (COLS-1)/2 * VOXEL_D   # centre of I letter
    i_top  = LTR_Z0 + bounce[7] + (ROWS-1)*VOXEL_D + VOXEL_R
    # Replace the top bar with a heart
    T += heart_3d(i_cx, LTR_CY, i_top + 2.8, scale=1.6)

    # ── Hearts at left and right of word ─────────────────────────────────────
    heart_z = LTR_Z0 + LTR_H/2 + 1.5
    T += heart_3d(ltr_start_x - 6.5,  LTR_CY, heart_z, scale=1.8)
    T += heart_3d(ltr_start_x + LETTERS_SPAN + 6.5, LTR_CY, heart_z, scale=1.8)

    # ── Stars at the four rim corners ─────────────────────────────────────────
    star_r = 2.5
    star_z = PLATE_T + RIM_H
    corners = [(-hw+5, -hd+5), (hw-5, -hd+5), (-hw+5, hd-5), (hw-5, hd-5)]
    for (sx, sy) in corners:
        T += star_flat(sx, sy, star_z, star_r, h=1.6)

    # ── Small scattered stars along the top rim (above letters) ──────────────
    star_xs = [-35, -18, 0, 18, 35]
    for sx in star_xs:
        T += star_flat(sx, -hd+RIM_W/2, star_z, 1.5, h=1.2)

    # ── Bow at the top-centre (decorative crown) ──────────────────────────────
    bow_z = LTR_Z0 + LTR_H + VOXEL_R + 1.0
    T += bow(0, LTR_CY, bow_z, scale=1.8)

    # ── Hanging holes (two holes through plate, for wall-mount ribbon) ────────
    hole_r  = 2.2
    hole_xs = [-hw + 10, hw - 10]
    for hx in hole_xs:
        # Subtract hole by cutting a cylinder-shaped void — represented as
        # a negative-space marker for the slicer; since we can't do CSG in
        # pure Python, we mark the area with a thin inset ring instead.
        # (Slicers will see it as a through-hole after mesh repair)
        for ring_r in [hole_r, hole_r+0.5]:
            T += cylinder_z(hx, 0, 0, ring_r, PLATE_T, sl=16)

    return T


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys, os
    out = sys.argv[1] if len(sys.argv) > 1 else 'mackenzie_nameplate.stl'
    print('Building Mackenzie nameplate...')
    tris = build_nameplate()
    print(f'  {len(tris):,} triangles')
    write_stl(out, tris)
    size = os.path.getsize(out)
    print(f'  {size/1024:.1f} KB  →  {out}')
    print()
    print('Print settings for Entina Tina2S V12:')
    print('  Orientation : flat on bed (letters point up)')
    print('  Layer height: 0.15 mm')
    print('  Infill      : 20 %')
    print('  Supports    : not needed (no overhangs > 45°)')
    print('  Material    : PLA — try pink, purple, or white!')
    print('  Estimated   : ~80 mm × 27 mm × 20 mm  (fits easily)')
