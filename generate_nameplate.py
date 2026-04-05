#!/usr/bin/env python3
"""
"Mack" girly nameplate — solid raised block letters
For Entina Tina2S V12 (120×120×150 mm build volume)
Prints flat on the bed — each letter pixel is a solid 4×4×3 mm box
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
    hdr = b'Mack Nameplate - Entina Tina2S V12'
    hdr = hdr + b'\x00' * (80 - len(hdr))   # always exactly 80 bytes
    with open(path, 'wb') as f:
        f.write(hdr)
        f.write(struct.pack('<I', len(tris)))
        for v0, v1, v2 in tris:
            n = face_normal(v0, v1, v2)
            f.write(struct.pack('<3f', *n))
            f.write(struct.pack('<3f', *v0))
            f.write(struct.pack('<3f', *v1))
            f.write(struct.pack('<3f', *v2))
            f.write(struct.pack('<H', 0))

# ── Solid box (12 triangles) ──────────────────────────────────────────────────

def box(x0, y0, z0, x1, y1, z1):
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

# ── Heart (solid raised shape, FDM-friendly) ──────────────────────────────────

def heart_flat(cx, cy, z0, size=4.0, h=2.5, sl=16):
    """Heart as two rounded bumps + triangle tip, extruded — solid and printable"""
    T = []
    # Heart outline: parametric heart curve, extruded from z0 to z0+h
    n = sl * 4
    def hpt(t):
        # classic heart parametric
        x = 16*math.sin(t)**3
        y = 13*math.cos(t) - 5*math.cos(2*t) - 2*math.cos(3*t) - math.cos(4*t)
        # scale and flip (y points up in heart coords)
        scale = size / 16.0
        return (cx + x*scale, cy + y*scale)

    pts = [hpt(2*math.pi*i/n) for i in range(n)]

    # top face (fan triangulation from centroid)
    for i in range(n):
        p0 = pts[i]; p1 = pts[(i+1)%n]
        T.append(((cx,cy,z0+h),(p0[0],p0[1],z0+h),(p1[0],p1[1],z0+h)))
    # bottom face
    for i in range(n):
        p0 = pts[i]; p1 = pts[(i+1)%n]
        T.append(((cx,cy,z0),(p1[0],p1[1],z0),(p0[0],p0[1],z0)))
    # side walls
    for i in range(n):
        p0 = pts[i]; p1 = pts[(i+1)%n]
        b0=(p0[0],p0[1],z0); b1=(p1[0],p1[1],z0)
        t0=(p0[0],p0[1],z0+h); t1=(p1[0],p1[1],z0+h)
        T.append((b0,b1,t1)); T.append((b0,t1,t0))
    return T

# ── Star (extruded, solid) ─────────────────────────────────────────────────────

def star_flat(cx, cy, z0, r, h=2.0, pts=5):
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
        T.append(((cx,cy,z0+h),(verts[k][0],verts[k][1],z0+h),(verts[nk][0],verts[nk][1],z0+h)))
        T.append(((cx,cy,z0),(verts[nk][0],verts[nk][1],z0),(verts[k][0],verts[k][1],z0)))
        a0=(verts[k][0],verts[k][1],z0);   a1=(verts[k][0],verts[k][1],z0+h)
        b0=(verts[nk][0],verts[nk][1],z0); b1=(verts[nk][0],verts[nk][1],z0+h)
        T+=[(a0,b0,b1),(a0,b1,a1)]
    return T

# ── Letter pixel maps (5 wide × 7 tall, row 0 = top) ─────────────────────────

GLYPHS = {
    'M': ['10001','11011','10101','10001','10001','10001','10001'],
    'A': ['01110','10001','10001','11111','10001','10001','10001'],
    'C': ['01110','10001','10000','10000','10000','10001','01110'],
    'K': ['10001','10010','10100','11000','10100','10010','10001'],
}

# ── Nameplate assembly ────────────────────────────────────────────────────────

def build_nameplate():
    T = []

    WORD    = 'MACK'
    PX      = 4.0       # mm — pixel size (solid 4×4×3mm blocks, easy for 0.4mm nozzle)
    PX_H    = 3.0       # mm — raised letter height above plate
    ROWS    = 7
    COLS    = 5

    LTR_W   = COLS * PX          # 20 mm per letter
    LTR_H   = ROWS * PX          # 28 mm letter height
    LTR_GAP = PX * 1.5           # 6 mm gap between letters
    LTR_STEP= LTR_W + LTR_GAP   # 26 mm letter pitch

    N           = len(WORD)
    LETTERS_SPAN = LTR_W + (N-1)*LTR_STEP    # 20 + 3×26 = 98 mm

    MARGIN  = 9.0
    PLATE_W = LETTERS_SPAN + 2*MARGIN    # 98 + 18 = 116 mm
    PLATE_D = LTR_H + 2*MARGIN          # 28 + 18 = 46 mm  — give letters room
    PLATE_T = 3.5       # base plate thickness
    RIM_W   = 2.5       # rim width
    RIM_H   = 2.0       # rim height above plate top

    LTR_Z0  = PLATE_T
    LTR_CY0 = -LTR_H/2     # bottom Y of letters (centred in Y)

    ltr_start_x = -LETTERS_SPAN/2   # X of leftmost pixel column

    # ── Base plate ────────────────────────────────────────────────────────────
    hw, hd = PLATE_W/2, PLATE_D/2
    T += box(-hw, -hd, 0, hw, hd, PLATE_T)

    # Raised border rim (4 strips)
    z_rim = PLATE_T + RIM_H
    T += box(-hw,        -hd,          PLATE_T,  hw,         -hd+RIM_W,  z_rim)  # front
    T += box(-hw,         hd-RIM_W,    PLATE_T,  hw,          hd,        z_rim)  # back
    T += box(-hw,        -hd,          PLATE_T, -hw+RIM_W,    hd,        z_rim)  # left
    T += box( hw-RIM_W,  -hd,          PLATE_T,  hw,          hd,        z_rim)  # right

    # ── Solid raised block letters ────────────────────────────────────────────
    for li, ch in enumerate(WORD):
        grid = GLYPHS[ch]
        lx0 = ltr_start_x + li * LTR_STEP

        for row in range(ROWS):
            for col in range(COLS):
                if grid[row][col] == '1':
                    bx0 = lx0 + col * PX
                    by0 = LTR_CY0 + (ROWS-1-row) * PX
                    # Solid box: from plate top up by PX_H
                    T += box(bx0, by0, LTR_Z0,
                             bx0+PX, by0+PX, LTR_Z0+PX_H)

    # ── Hearts flanking the word ──────────────────────────────────────────────
    heart_y  = 0.0
    heart_z0 = PLATE_T
    T += heart_flat(ltr_start_x - MARGIN*0.6, heart_y, heart_z0, size=5.0, h=2.5)
    T += heart_flat(ltr_start_x + LETTERS_SPAN + MARGIN*0.6, heart_y, heart_z0, size=5.0, h=2.5)

    # ── Stars at the four corners ─────────────────────────────────────────────
    star_z0 = PLATE_T
    star_r  = 4.0
    inset   = RIM_W + star_r + 0.5
    for sx, sy in [(-hw+inset, -hd+inset), (hw-inset, -hd+inset),
                   (-hw+inset,  hd-inset), (hw-inset,  hd-inset)]:
        T += star_flat(sx, sy, star_z0, star_r, h=2.2)

    # ── Small heart above the letters (centre top) ────────────────────────────
    top_heart_z0 = PLATE_T
    top_cy = LTR_H/2 + MARGIN*0.45
    T += heart_flat(0.0, top_cy, top_heart_z0, size=4.5, h=2.5)

    return T


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys, os
    out = sys.argv[1] if len(sys.argv) > 1 else 'mack_nameplate.stl'
    print('Building Mack nameplate (solid block letters)...')
    tris = build_nameplate()
    print(f'  {len(tris):,} triangles')
    write_stl(out, tris)
    size = os.path.getsize(out)
    print(f'  {size/1024:.1f} KB  →  {out}')
    print()
    print('Print settings for Entina Tina2S V12:')
    print('  Orientation : flat on bed (letters point up)')
    print('  Layer height: 0.15 mm')
    print('  Infill      : 40 %  (plate needs to be solid)')
    print('  Supports    : NOT needed')
    print('  Material    : PLA — pink or purple looks great!')
    print('  Size        : ~116 mm × 46 mm × 8.5 mm')
