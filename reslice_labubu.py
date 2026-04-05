#!/usr/bin/env python3
"""
Convert labubu.891.gcode from large-format printer → Entina Tina2S V12
- Scales 149×116mm model to 115×89mm (77.1%) to fit 120×120mm bed
- Re-centres on Tina2S bed (60,60)
- Rescales Z for correct proportions
- Recalculates extrusion (E) values for new path lengths
- Replaces Anycubic G9111 and EXCLUDE_OBJECT with standard Marlin
- Inserts confirmed Tina2S start/end G-code
"""
import re, math, os

SCALE    = 0.771          # fit 149mm → 115mm on 120mm bed
SCALE_E  = SCALE ** 2     # E scales with area (layer_h × path_len both × SCALE)
MODEL_CX = 175.4          # original model centre (from coordinate analysis)
MODEL_CY = 162.2
BED_CX   = BED_CY = 60.0 # Tina2S bed centre
NOZZLE_T = 220
BED_T    = 60

def txy(x, y):
    return (x - MODEL_CX) * SCALE + BED_CX, (y - MODEL_CY) * SCALE + BED_CY

def tz(z):
    return z * SCALE

# ── Read source ───────────────────────────────────────────────────────────────
with open('labubu.891.gcode', 'r') as f:
    src = f.readlines()

# Strip header lines we already prepended
while src and src[0].strip().startswith((';MachineType', ';FilamentType')):
    src.pop(0)

# ── Tina2S header + start G-code ─────────────────────────────────────────────
out = [
    ';MachineType:TINA2S\n',
    ';FilamentType:PLA\n',
    f';NozzleTemperature:{NOZZLE_T}\n',
    f';BedTemperature:{BED_T}\n',
    f'; Labubu - rescaled {SCALE:.3f}x for Entina Tina2S V12\n',
    '\n',
    f'M104 S150          ; preheat\n',
    f'M203 Z15           ; max Z speed\n',
    'G28                ; home all\n',
    'G29                ; auto bed level\n',
    'M107               ; fan off\n',
    'G90                ; absolute XYZ\n',
    'M82                ; absolute E\n',
    f'M109 S{NOZZLE_T}  ; wait for nozzle\n',
    f'M190 S{BED_T}     ; wait for bed\n',
    'G92 E0\n',
    'G1 E-3 F300\n',
    'G92 E0\n',
    'G1 X0 Y0 Z0.3 F3000\n',
    'G1 X60 E9 F1000\n',
    'G1 X100 E12.5 F1000\n',
    'G92 E0\n',
    '\n',
]

# ── State ─────────────────────────────────────────────────────────────────────
cx = cy = cz = 0.0   # current pos in original coords
ce = 0.0             # current E in original coords
ne = 0.0             # current E in new coords
in_skip = True       # skip until EXECUTABLE_BLOCK_START

g92_pat  = re.compile(r'G92\b')
e_pat    = re.compile(r'E([-\d.]+)')
x_pat    = re.compile(r'X([-\d.]+)')
y_pat    = re.compile(r'Y([-\d.]+)')
z_pat    = re.compile(r'Z([-\d.]+)')
f_pat    = re.compile(r'F([-\d.]+)')

for raw in src:
    line = raw.strip()

    # ── skip everything before the executable block ───────────────────────────
    if 'EXECUTABLE_BLOCK_START' in line:
        in_skip = False
        continue
    if in_skip:
        continue

    # ── Anycubic-specific: replace G9111 with standard temps ─────────────────
    if line.startswith('G9111'):
        m_b = re.search(r'bedTemp=(\d+)', line)
        m_e = re.search(r'extruderTemp=(\d+)', line)
        bt  = int(m_b.group(1)) if m_b else BED_T
        et  = int(m_e.group(1)) if m_e else NOZZLE_T
        out.append(f'M140 S{bt}\n')
        out.append(f'M190 S{bt}\n')
        out.append(f'M104 S{et}\n')
        out.append(f'M109 S{et}\n')
        continue

    # ── Skip EXCLUDE_OBJECT lines (not supported on Tina2S) ──────────────────
    if line.startswith('EXCLUDE_OBJECT'):
        continue

    # ── Skip empty M117 ───────────────────────────────────────────────────────
    if line == 'M117':
        continue

    # ── G92 resets ───────────────────────────────────────────────────────────
    if g92_pat.match(line):
        me = e_pat.search(line)
        if me:
            reset_val = float(me.group(1))
            ce = reset_val
            ne = reset_val
            out.append(f'G92 E{reset_val:.5f}\n')
        else:
            out.append(raw)
        continue

    # ── G0 / G1 moves ────────────────────────────────────────────────────────
    if line.startswith(('G0 ', 'G1 ', 'G0\t', 'G1\t',
                         'G0;',  'G1;',  'G0\n', 'G1\n')):
        mx = x_pat.search(line)
        my = y_pat.search(line)
        mz = z_pat.search(line)
        me = e_pat.search(line)
        mf = f_pat.search(line)

        parts = [line.split()[0]]  # G0 or G1

        # XY transform
        new_cx = float(mx.group(1)) if mx else cx
        new_cy = float(my.group(1)) if my else cy
        nx_val, ny_val = txy(new_cx, new_cy)
        if mx: parts.append(f'X{nx_val:.3f}'); cx = new_cx
        if my: parts.append(f'Y{ny_val:.3f}'); cy = new_cy

        # Z transform (scale for proportions)
        if mz:
            old_z = float(mz.group(1))
            parts.append(f'Z{tz(old_z):.3f}')
            cz = old_z

        # E recalculation
        if me:
            target_e = float(me.group(1))
            delta_e  = target_e - ce
            ce       = target_e

            has_move = bool(mx or my or mz)
            if delta_e > 0 and has_move:
                # Extrusion move: scale by SCALE² (both layer_h and path_len scale)
                ne += delta_e * SCALE_E
            else:
                # Retraction or pure-E: keep absolute amount unchanged
                ne += delta_e
            parts.append(f'E{ne:.5f}')

        if mf:
            parts.append(f'F{float(mf.group(1)):.0f}')

        # Preserve inline comments
        if ';' in line:
            comment = line[line.index(';'):]
            parts.append(comment)

        out.append(' '.join(parts) + '\n')
        continue

    # ── Everything else: pass through ────────────────────────────────────────
    out.append(raw)

# ── Tina2S end G-code ─────────────────────────────────────────────────────────
out += [
    '\n',
    '; --- end print ---\n',
    'M104 S0\n', 'M140 S0\n',
    'G91\n',
    'G1 E-1 F300\n',
    'G1 Z10 E-5 F3000\n',
    'G90\n',
    'G1 X0 Y100 F3000\n',
    'M84\n',
    'M107\n',
]

out_name = 'labubu_tina2s.gcode'
with open(out_name, 'w') as f:
    f.writelines(out)

# ── Verify ────────────────────────────────────────────────────────────────────
with open(out_name, 'r') as f:
    lines = f.readlines()

xs, ys, zs = [], [], []
for l in lines:
    if l.startswith(('G0 ','G1 ')):
        m = re.search(r'X([-\d.]+)', l); xs.append(float(m.group(1))) if m else None
        m = re.search(r'Y([-\d.]+)', l); ys.append(float(m.group(1))) if m else None
        m = re.search(r'Z([-\d.]+)', l); zs.append(float(m.group(1))) if m else None

print(f"Output : {out_name}  ({os.path.getsize(out_name)/1024/1024:.1f} MB)")
print(f"Lines  : {len(lines):,}")
print(f"X range: {min(xs):.1f} – {max(xs):.1f} mm  (bed 0–120)")
print(f"Y range: {min(ys):.1f} – {max(ys):.1f} mm  (bed 0–120)")
print(f"Z range: {min(zs):.1f} – {max(zs):.1f} mm")
print(f"Fits bed: {'YES' if max(xs)<=120 and min(xs)>=0 and max(ys)<=120 and min(ys)>=0 else 'NO'}")
