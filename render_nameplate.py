#!/usr/bin/env python3
"""Quick preview render of mackenzie_nameplate.stl"""
import struct, math, zlib, time

def write_png(fname, W, H, cbuf):
    def chunk(tag, data):
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', crc)
    sig = b'\x89PNG\r\n\x1a\n'
    with open(fname, 'wb') as f:
        f.write(sig)
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(bytes(cbuf), 6)))
        f.write(chunk(b'IEND', b''))
    print(f'  Saved {fname}')

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

def vn(v):
    l = math.sqrt(v[0]**2+v[1]**2+v[2]**2)
    return (v[0]/l, v[1]/l, v[2]/l) if l > 1e-12 else (0.0, 0.0, 1.0)
def vc(a,b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def vs(a,b): return (a[0]-b[0], a[1]-b[1], a[2]-b[2])
def vd(a,b): return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]

W, H = 680, 480
FOV  = 46

# Camera: higher up, looking down at the nameplate for readability
cam = (3.0, -50.0, 115.0)
tgt = (0.0,   0.0,   9.0)

zax = vn(vs(tgt, cam))
xax = vn(vc(zax, (0.0, 0.0, 1.0)))
yax = vc(xax, zax)
f_len = 1.0 / math.tan(math.radians(FOV/2))

def project(pt):
    d = vs(pt, cam)
    cz_ = vd(d, zax)
    if cz_ <= 0.1: return None
    cx_ = vd(d, xax); cy_ = vd(d, yax)
    sx = int(( f_len*cx_/cz_ + 1.0) * W * 0.5 + 0.5)
    sy = int((1.0 - f_len*cy_/cz_)  * H * 0.5 + 0.5)
    return sx, sy, cz_

# Lights
lights = [
    (vn((-0.3, -0.9, 0.6)), 0.72, (255, 230, 210)),
    (vn(( 0.8, -0.1, 0.5)), 0.28, (180, 200, 255)),
    (vn(( 0.0,  0.7, 0.2)), 0.16, (210, 230, 200)),
]
AMBIENT = 0.30

# Hot-pink / magenta base colour — girly!
BR, BG, BB = 220, 60, 130

def shade(nx, ny, nz):
    dr = dg = db = 0.0
    for ldir, lstr, lc in lights:
        diff = abs(vd((nx,ny,nz), ldir))
        dr += diff * lstr * lc[0]/255
        dg += diff * lstr * lc[1]/255
        db += diff * lstr * lc[2]/255
    ldir0 = lights[0][0]
    rfl  = vn(vs((nx*2*max(0,vd((nx,ny,nz),ldir0)), ny*2*max(0,vd((nx,ny,nz),ldir0)), nz*2*max(0,vd((nx,ny,nz),ldir0))), ldir0))
    spec = max(0.0, vd(rfl, vn(vs(cam, tgt)))) ** 22 * 0.7
    r = min(255, int(BR*(AMBIENT+dr) + 240*spec))
    g = min(255, int(BG*(AMBIENT+dg) + 200*spec))
    b = min(255, int(BB*(AMBIENT+db) + 210*spec))
    return r, g, b

# Background: soft pink gradient
cbuf = bytearray(H * (1 + W * 3))
for row in range(H):
    t = row / (H-1)
    cbuf[row*(1+W*3)] = 0
    for col in range(W):
        off = row*(1+W*3)+1+col*3
        cbuf[off]   = int(255 - 20*t)
        cbuf[off+1] = int(220 - 40*t)
        cbuf[off+2] = int(235 - 30*t)

# Shadow
for row in range(H):
    for col in range(W):
        sx = (col - W//2) / (W*0.44)
        sy = (row - int(H*0.84)) / (H*0.07)
        if sx*sx + sy*sy < 1.0:
            a = max(0.0, (1-(sx*sx+sy*sy))*0.45)
            off = row*(1+W*3)+1+col*3
            cbuf[off]   = int(cbuf[off]  *(1-a)+90*a)
            cbuf[off+1] = int(cbuf[off+1]*(1-a)+50*a)
            cbuf[off+2] = int(cbuf[off+2]*(1-a)+80*a)

zbuf = [1e18]*(W*H)

print('Loading STL...')
tris = load_stl('mackenzie_nameplate.stl')
print(f'  {len(tris):,} triangles')

print('Sorting...')
def cdepth(tri):
    v0,v1,v2=tri
    cx=(v0[0]+v1[0]+v2[0])/3-cam[0]
    cy=(v0[1]+v1[1]+v2[1])/3-cam[1]
    cz=(v0[2]+v1[2]+v2[2])/3-cam[2]
    return cx*cx+cy*cy+cz*cz
tris.sort(key=cdepth, reverse=True)

print('Rasterising...')
t0 = time.time()
drawn = 0
for v0,v1,v2 in tris:
    p0=project(v0); p1=project(v1); p2=project(v2)
    if not (p0 and p1 and p2): continue
    x0,y0,d0=p0; x1,y1,d1=p1; x2,y2,d2=p2
    lx=max(0,min(x0,x1,x2)); hx=min(W-1,max(x0,x1,x2))
    ly=max(0,min(y0,y1,y2)); hy=min(H-1,max(y0,y1,y2))
    if lx>hx or ly>hy: continue
    e1=vs(v1,v0); e2=vs(v2,v0)
    fn=vc(e1,e2); fl=math.sqrt(fn[0]**2+fn[1]**2+fn[2]**2)
    if fl<1e-12: continue
    nx_,ny_,nz_=fn[0]/fl,fn[1]/fl,fn[2]/fl
    r,g,b=shade(nx_,ny_,nz_)
    avg_d=(d0+d1+d2)/3
    def ef(ax,ay,bx,by,px,py): return (px-ax)*(by-ay)-(py-ay)*(bx-ax)
    area2=ef(x0,y0,x1,y1,x2,y2)
    if area2==0: continue
    for py in range(ly,hy+1):
        for px in range(lx,hx+1):
            w0=ef(x1,y1,x2,y2,px,py)
            w1=ef(x2,y2,x0,y0,px,py)
            w2=ef(x0,y0,x1,y1,px,py)
            ins=(w0>=0 and w1>=0 and w2>=0) if area2>0 else (w0<=0 and w1<=0 and w2<=0)
            if ins:
                idx=py*W+px
                if avg_d<zbuf[idx]:
                    zbuf[idx]=avg_d
                    off=py*(1+W*3)+1+px*3
                    cbuf[off]=r; cbuf[off+1]=g; cbuf[off+2]=b
    drawn+=1
print(f'  {drawn:,} triangles in {time.time()-t0:.1f}s')
write_png('nameplate_preview.png', W, H, cbuf)
