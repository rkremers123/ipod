#!/usr/bin/env python3
"""
Pure-Python software rasterizer: renders frenchie.stl → frenchie_preview.png
Uses only Python stdlib (struct, math, zlib).
"""
import struct, math, zlib, time

# ── PNG writer ────────────────────────────────────────────────────────────────
def write_png(fname, W, H, cbuf):
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)
    sig  = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(bytes(cbuf), 6))
    iend = chunk(b'IEND', b'')
    with open(fname, 'wb') as f:
        f.write(sig + ihdr + idat + iend)
    print(f"  Saved {fname}")

# ── STL loader ────────────────────────────────────────────────────────────────
def load_stl(fname):
    tris = []
    with open(fname, 'rb') as f:
        f.read(80)
        n = struct.unpack('<I', f.read(4))[0]
        for _ in range(n):
            f.read(12)                                # stored normal (ignored)
            v0 = struct.unpack('<3f', f.read(12))
            v1 = struct.unpack('<3f', f.read(12))
            v2 = struct.unpack('<3f', f.read(12))
            f.read(2)
            tris.append((v0, v1, v2))
    return tris

# ── Math ──────────────────────────────────────────────────────────────────────
def vn(v):
    l = math.sqrt(v[0]*v[0]+v[1]*v[1]+v[2]*v[2])
    return (v[0]/l, v[1]/l, v[2]/l) if l > 1e-12 else (0.0, 0.0, 1.0)
def vc(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def vd(a,b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def vs(a,b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def vm(a,s): return (a[0]*s, a[1]*s, a[2]*s)

# ── Camera ────────────────────────────────────────────────────────────────────
W, H  = 520, 580
FOV   = 44

cam = (75.0, -115.0, 88.0)
tgt = (-1.0,  -4.0,  44.0)

zax = vn(vs(tgt, cam))                   # camera forward
xax = vn(vc(zax, (0.0, 0.0, 1.0)))      # camera right
yax = vc(xax, zax)                       # camera up

f_len = 1.0 / math.tan(math.radians(FOV / 2.0))

def project(pt):
    d   = vs(pt, cam)
    cz_ = vd(d, zax)
    if cz_ <= 0.5:
        return None
    cx_ = vd(d, xax)
    cy_ = vd(d, yax)
    px  =  f_len * cx_ / cz_
    py  =  f_len * cy_ / cz_
    sx  = int(( px + 1.0) * W * 0.5 + 0.5)
    sy  = int((1.0 - py ) * H * 0.5 + 0.5)
    return sx, sy, cz_

# ── Lighting  (multiple lights so dark model gets lit from both sides) ────────
lights = [
    (vn((-0.5, -0.9, 0.7)), 0.70, (255, 240, 220)),   # key  – warm
    (vn(( 0.8, -0.2, 0.5)), 0.30, (160, 175, 255)),   # fill – cool blue
    (vn(( 0.1,  0.8, 0.2)), 0.18, (200, 220, 200)),   # rim  – back
]
AMBIENT = 0.28

# Dog base: dark brindle-black (#3A3028)
BR, BG, BB = 58, 50, 44

def shade(nx, ny, nz, abs_normal=False):
    """abs_normal=True means ignore backface (two-sided lighting)."""
    dr, dg, db = 0.0, 0.0, 0.0
    for ldir, lstr, lcol in lights:
        diff = vd((nx,ny,nz), ldir)
        if abs_normal:
            diff = abs(diff)
        else:
            diff = max(0.0, diff)
        dr += diff * lstr * lcol[0] / 255.0
        dg += diff * lstr * lcol[1] / 255.0
        db += diff * lstr * lcol[2] / 255.0

    # Specular (key light only)
    ldir0 = lights[0][0]
    rfl   = vs(vm((nx,ny,nz), 2.0*max(0,vd((nx,ny,nz), ldir0))), ldir0)
    cam_d = vn(vs(cam, tgt))
    spec  = max(0.0, vd(vn(rfl), cam_d)) ** 20 * 0.55

    ir = AMBIENT + dr
    ig = AMBIENT + dg
    ib = AMBIENT + db

    r = min(255, int(BR * ir + 230 * spec))
    g = min(255, int(BG * ig + 215 * spec))
    b = min(255, int(BB * ib + 205 * spec))
    return r, g, b

# ── Framebuffer ───────────────────────────────────────────────────────────────
# Background: warm off-white studio gradient
cbuf = bytearray(H * (1 + W * 3))
for row in range(H):
    t  = row / (H - 1)
    tr = int(215 - 20 * t)
    tg = int(212 - 18 * t)
    tb = int(205 - 15 * t)
    base = row * (1 + W * 3)
    cbuf[base] = 0
    for col in range(W):
        off = base + 1 + col * 3
        cbuf[off]   = tr
        cbuf[off+1] = tg
        cbuf[off+2] = tb

# shadow ellipse under the dog (rough AO)
shadow_cx, shadow_cy = W//2, int(H*0.885)
shadow_rx, shadow_ry = 95, 22
for row in range(max(0, shadow_cy - shadow_ry - 4),
                 min(H, shadow_cy + shadow_ry + 4)):
    for col in range(max(0, shadow_cx - shadow_rx - 4),
                     min(W, shadow_cx + shadow_rx + 4)):
        dx = (col - shadow_cx) / shadow_rx
        dy = (row - shadow_cy) / shadow_ry
        r2 = dx*dx + dy*dy
        if r2 < 1.0:
            alpha = max(0.0, (1.0 - r2) * 0.55)
            off = row * (1 + W * 3) + 1 + col * 3
            cbuf[off]   = int(cbuf[off]   * (1-alpha) + 80 * alpha)
            cbuf[off+1] = int(cbuf[off+1] * (1-alpha) + 72 * alpha)
            cbuf[off+2] = int(cbuf[off+2] * (1-alpha) + 62 * alpha)

zbuf = [1e18] * (W * H)

# ── Load + sort ───────────────────────────────────────────────────────────────
print("Loading STL...")
tris = load_stl('frenchie.stl')
print(f"  {len(tris):,} triangles")

print("Sorting back-to-front...")
def centroid_depth(tri):
    v0,v1,v2 = tri
    cx = (v0[0]+v1[0]+v2[0])/3 - cam[0]
    cy = (v0[1]+v1[1]+v2[1])/3 - cam[1]
    cz = (v0[2]+v1[2]+v2[2])/3 - cam[2]
    return cx*cx + cy*cy + cz*cz

tris.sort(key=centroid_depth, reverse=True)   # back-to-front (painter's)

# ── Rasterise ─────────────────────────────────────────────────────────────────
print("Rasterising...")
t0 = time.time()
drawn = 0

for v0, v1, v2 in tris:
    p0 = project(v0)
    p1 = project(v1)
    p2 = project(v2)
    if p0 is None or p1 is None or p2 is None:
        continue

    x0, y0, d0 = p0
    x1, y1, d1 = p1
    x2, y2, d2 = p2

    # Bounding box
    lx = max(0,   min(x0, x1, x2))
    hx = min(W-1, max(x0, x1, x2))
    ly = max(0,   min(y0, y1, y2))
    hy = min(H-1, max(y0, y1, y2))
    if lx > hx or ly > hy:
        continue

    # Face normal from world-space edges
    e1 = vs(v1, v0); e2 = vs(v2, v0)
    fn = vc(e1, e2)
    fl = math.sqrt(fn[0]*fn[0]+fn[1]*fn[1]+fn[2]*fn[2])
    if fl < 1e-12:
        continue
    nx_, ny_, nz_ = fn[0]/fl, fn[1]/fl, fn[2]/fl

    # Use two-sided lighting (no back-face cull; mesh has mixed winding)
    r, g, b = shade(nx_, ny_, nz_, abs_normal=True)

    # 2D edge functions (signed area)
    def ef(ax, ay, bx, by, px, py):
        return (px - ax) * (by - ay) - (py - ay) * (bx - ax)

    area2 = ef(x0, y0, x1, y1, x2, y2)
    if area2 == 0:
        continue

    avg_d = (d0 + d1 + d2) / 3.0

    for py in range(ly, hy + 1):
        for px in range(lx, hx + 1):
            w0 = ef(x1, y1, x2, y2, px, py)
            w1 = ef(x2, y2, x0, y0, px, py)
            w2 = ef(x0, y0, x1, y1, px, py)
            # inside test: same sign as area2
            if area2 > 0:
                inside = w0 >= 0 and w1 >= 0 and w2 >= 0
            else:
                inside = w0 <= 0 and w1 <= 0 and w2 <= 0
            if inside:
                idx = py * W + px
                if avg_d < zbuf[idx]:
                    zbuf[idx] = avg_d
                    off = py * (1 + W * 3) + 1 + px * 3
                    cbuf[off]   = r
                    cbuf[off+1] = g
                    cbuf[off+2] = b
    drawn += 1

elapsed = time.time() - t0
print(f"  Drew {drawn:,} triangles in {elapsed:.1f}s")

write_png('frenchie_preview.png', W, H, cbuf)
print("Done.")
