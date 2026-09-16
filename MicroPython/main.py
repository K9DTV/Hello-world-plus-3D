import math, time, _thread
from machine import Pin, I2C
try:
    import ssd1306
except:
    ssd1306 = None
from font8x8_mp import font8x8_data
try:
    from machine import freq
    freq(280000000)
except:
    pass
SDA_PIN = 0
SCL_PIN = 1
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDRESS = 0x3C
i2c = I2C(0, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=800000)
oled = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDRESS)
# --- SPEED & SCALE KNOBS ---
lissa_speed = 0.15
smiley_speed = 0.002
cube_speed = 0.15
pyramid_speed = 0.15
octahedron_speed = 0.20
sphere_speed = 0.25
torus_speed = 0.08
teapot_speed = 0.10
star_speed = 0.16
enterprise_speed = 0.05
star_scale = 1.8
enterprise_scale = 1.15
lissa_phase = 0.0
_lock = _thread.allocate_lock()


def core1_main():
    # Core1 idle - we do angles in main for smooth timing (no lock jitter)
    while True:
        time.sleep_ms(100)


# Fast Bresenham without method lookups
def fast_line(x0, y0, x1, y1):
    dx = x1 - x0
    dy = y1 - y0
    sx = 1 if dx > 0 else -1
    sy = 1 if dy > 0 else -1
    dx = abs(dx)
    dy = abs(dy)
    if dx > dy:
        err = dx // 2
        while x0 != x1:
            oled.pixel(x0, y0, 1)
            err -= dy
            if err < 0:
                y0 += sy
                err += dx
            x0 += sx
        oled.pixel(x0, y0, 1)
    else:
        err = dy // 2
        while y0 != y1:
            oled.pixel(x0, y0, 1)
            err -= dx
            if err < 0:
                x0 += sx
                err += dy
            y0 += sy
        oled.pixel(x0, y0, 1)


def drawCustomChar(x, y, c, col=1):
    # Font bytes are HMSB (bit 7 = leftmost), same as Adafruit drawBitmap / font8x8.h
    if c < 32 or c > 126:
        return
    glyph = font8x8_data[c - 32]
    for row in range(8):
        b = glyph[row]
        if b:
            for bit in range(8):
                if b & (0x80 >> bit):
                    oled.pixel(x + bit, y + row, col)


def drawCustomText(x, y, text, col=1):
    cx = x
    for ch in text:
        drawCustomChar(cx, y, ord(ch), col)
        cx += 8


def grid(w=128, h=64, col=1):
    for d in range(w):
        oled.pixel(d, 0, col)
        oled.pixel(d, h // 2 - 1, col)
        oled.pixel(d, h - 1, col)
    for d in range(1, h):
        oled.pixel(0, d, col)
        oled.pixel(w // 4, d, col)
        oled.pixel(w // 2, d, col)
        oled.pixel(w // 4 * 3, d, col)
        oled.pixel(w - 1, d, col)


def circle(xo=64, yo=32, a0=0, a1=359, r1=32, r0=31, fill=1, col=1):
    clk = 90
    if fill == 0:
        r0 = r1 - 1
    for r in range(r0, r1):
        for deg in range(a0 - clk, a1 - clk):
            rad = deg * 0.01744
            oled.pixel(int(r * math.cos(rad) + xo), int(r * math.sin(rad) + yo), col)


def LissajousFrame(phase, col=1, Ax=0.48, Ay=0.48, a=1, b=2):
    cx = 64
    cy = 32
    ampX = Ax * 128
    ampY = Ay * 64
    oled.fill(0)
    # step 2: full waveform density (Arduino-like)
    for d in range(0, 360, 2):
        t = d * 0.017453292
        ix = int(cx + ampX * math.sin(a * t))
        iy = int(cy + ampY * math.sin(b * t + phase))
        if 0 <= ix < 128 and 0 <= iy < 64:
            oled.pixel(ix, iy, col)
    oled.show()


def grid_num():
    p = [13, 46, 76, 108]
    for i in range(4):
        drawCustomText(p[i], 13, str(i + 1))
        drawCustomText(p[i], 45, str(i + 5))


def clear_screen(col="black"):
    oled.fill(1 if col == "white" else 0)
    oled.show()


def flash_screen(t=4, d=0.5):
    for _ in range(t):
        try:
            oled.invert(1)
        except:
            pass
        oled.show()
        time.sleep(d)
        try:
            oled.invert(0)
        except:
            pass
        oled.show()
        time.sleep(d)


def hello_world():
    oled.fill(0)
    step = 8
    for l in range(0, 64, step):
        drawCustomText(0, l, f"Hello, World {(l // 8) + 1}!")
    oled.show()


# Pre-allocated projection buffers to avoid GC jitter
_px = [0] * 300
_py = [0] * 300


def drawObject3D(verts, edges, angleX, angleY, angleZ=0.0):
    oled.fill(0)
    sx = math.sin(angleX)
    cx1 = math.cos(angleX)
    sy = math.sin(angleY)
    cy1 = math.cos(angleY)
    sz = math.sin(angleZ)
    cz = math.cos(angleZ)
    px = _px
    py = _py
    zd = 60.0
    vlen = len(verts)
    for i in range(vlen):
        x, y, z = verts[i]
        x0 = x * cz - y * sz
        y0 = x * sz + y * cz
        y1 = y0 * cx1 - z * sx
        z1 = y0 * sx + z * cx1
        x2 = x0 * cy1 + z1 * sy
        z2 = -x0 * sy + z1 * cy1
        f = zd / (zd + z2) if zd + z2 != 0 else 1
        px[i] = int(x2 * f + 64)
        py[i] = int(y1 * f + 32)
    for a, b in edges:
        if a < vlen and b < vlen:
            fast_line(px[a], py[a], px[b], py[b])
    oled.show()


def smiley_project(x, y, z, angleX, angleY):
    cx = 64.0
    cy = 32.0
    zd = 60.0
    sx = math.sin(angleX)
    cx1 = math.cos(angleX)
    sy = math.sin(angleY)
    cy1 = math.cos(angleY)
    y1 = y * cx1 - z * sx
    z1 = y * sx + z * cx1
    x2 = x * cy1 + z1 * sy
    z2 = -x * sy + z1 * cy1
    f = zd / (zd + z2) if (zd + z2) != 0 else 1.0
    return x2 * f + cx, cy - y1 * f, z2


def smiley_point(x, y, z, roll, ax, ay):
    cr = math.cos(roll)
    sr = math.sin(roll)
    xr = x * cr - y * sr
    yr = x * sr + y * cr
    return smiley_project(xr, yr, z, ax, ay)


def smiley_fill_oval3d(cx, cy, cz, rx, ry, cr, sr, sx, cx1, sy, cy1, col):
    # Full oval density; trig passed in (no per-point sin/cos)
    step = 0.35
    zd = 60.0
    u = -1.0
    while u <= 1.0:
        v = -1.0
        while v <= 1.0:
            if u * u + v * v <= 1.0:
                x = cx + u * rx
                y = cy + v * ry
                z = cz
                xr = x * cr - y * sr
                yr = x * sr + y * cr
                y1 = yr * cx1 - z * sx
                z1 = yr * sx + z * cx1
                x2 = xr * cy1 + z1 * sy
                z2 = -xr * sy + z1 * cy1
                if z2 > 0.0:
                    f = zd / (zd + z2)
                    ix = int(x2 * f + 64)
                    iy = int(32.0 - y1 * f)
                    if 0 <= ix < OLED_WIDTH and 0 <= iy < OLED_HEIGHT:
                        oled.pixel(ix, iy, col)
            v += step
        u += step


def drawSmiley3D(t, scale=1.0):
    # Full resolution mesh; speed from caching trig once per frame
    R = 27.0 * scale
    S = R / 22.0
    faceZ = 19.0 * S
    maxTilt = 60.0 * 0.017453292
    ax = math.sin(t) * maxTilt
    ay = math.sin(t * 0.85) * maxTilt
    roll = math.sin(t * 0.5) * (2.0 * math.pi)
    cr = math.cos(roll)
    sr = math.sin(roll)
    sx = math.sin(ax)
    cx1 = math.cos(ax)
    sy = math.sin(ay)
    cy1 = math.cos(ay)
    zd = 60.0
    z_cut = -8.0 * S
    oled.fill(0)
    for i in range(0, 25):
        phi = (i / 24.0) * math.pi
        sp = math.sin(phi)
        cp = math.cos(phi)
        for j in range(32):
            th = (j / 32.0) * 2.0 * math.pi
            x = R * sp * math.cos(th)
            y = R * cp
            z = R * sp * math.sin(th)
            xr = x * cr - y * sr
            yr = x * sr + y * cr
            y1 = yr * cx1 - z * sx
            z1 = yr * sx + z * cx1
            x2 = xr * cy1 + z1 * sy
            z2 = -xr * sy + z1 * cy1
            if z2 > z_cut:
                f = zd / (zd + z2)
                ix = int(x2 * f + 64)
                iy = int(32.0 - y1 * f)
                for ddy in (-1, 0, 1):
                    for ddx in (-1, 0, 1):
                        xx = ix + ddx
                        yy = iy + ddy
                        if 0 <= xx < OLED_WIDTH and 0 <= yy < OLED_HEIGHT:
                            oled.pixel(xx, yy, 1)
    for deg in range(205, 336, 2):
        rad = deg * 0.017453292
        for k in range(4):
            rr = (12.0 + k * 0.85) * S
            x = rr * math.cos(rad)
            y = -7.0 * S + rr * math.sin(rad)
            xr = x * cr - y * sr
            yr = x * sr + y * cr
            y1 = yr * cx1 - faceZ * sx
            z1 = yr * sx + faceZ * cx1
            x2 = xr * cy1 + z1 * sy
            z2 = -xr * sy + z1 * cy1
            if z2 > 0.0:
                f = zd / (zd + z2)
                ix = int(x2 * f + 64)
                iy = int(32.0 - y1 * f)
                if 0 <= ix < OLED_WIDTH and 0 <= iy < OLED_HEIGHT:
                    oled.pixel(ix, iy, 0)
                if 0 <= ix + 1 < OLED_WIDTH and 0 <= iy < OLED_HEIGHT:
                    oled.pixel(ix + 1, iy, 0)
    for k, tickDeg in enumerate((208.0, 332.0)):
        rad = tickDeg * 0.017453292
        bx = 13.5 * S * math.cos(rad)
        by = -7.0 * S + 13.5 * S * math.sin(rad)

        def proj(x, y, z):
            xr = x * cr - y * sr
            yr = x * sr + y * cr
            y1 = yr * cx1 - z * sx
            z1 = yr * sx + z * cx1
            x2 = xr * cy1 + z1 * sy
            z2 = -xr * sy + z1 * cy1
            if z2 <= 0.0:
                return None
            f = zd / (zd + z2)
            return int(x2 * f + 64), int(32.0 - y1 * f)

        p0 = proj(bx, by, faceZ)
        p1 = proj(bx + (-3.0 if k == 0 else 3.0) * S, by + 2.5 * S, faceZ)
        if p0 and p1:
            x0, y0 = p0
            x1, y1 = p1
            dx = abs(x1 - x0)
            dy = abs(y1 - y0)
            ssx = 1 if x0 < x1 else -1
            ssy = 1 if y0 < y1 else -1
            err = dx - dy
            while True:
                if 0 <= x0 < OLED_WIDTH and 0 <= y0 < OLED_HEIGHT:
                    oled.pixel(x0, y0, 0)
                if x0 == x1 and y0 == y1:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += ssx
                if e2 < dx:
                    err += dx
                    y0 += ssy
    for eyeX in (-7.0 * S, 7.0 * S):
        smiley_fill_oval3d(eyeX, 7.0 * S, faceZ, 2.8 * S, 5.2 * S, cr, sr, sx, cx1, sy, cy1, 0)
    smiley_fill_oval3d(8.0 * S, 11.0 * S, 16.0 * S, 4.0 * S, 2.5 * S, cr, sr, sx, cx1, sy, cy1, 1)
    oled.show()


_torus_cache = None
_torus_scaled = None
_torus_last_scale = None


def drawTorusWireframe(ang, scale=1.0):
    global _torus_cache, _torus_scaled, _torus_last_scale
    if _torus_cache is None:
        U = 24
        V = 12
        R = 18
        r = 8
        verts = []
        edges = []
        for i in range(U):
            u = (i / U) * 2 * math.pi
            cu = math.cos(u)
            su = math.sin(u)
            for j in range(V):
                vv = (j / V) * 2 * math.pi
                cv = math.cos(vv)
                sv = math.sin(vv)
                verts.append(((R + r * cv) * cu, (R + r * cv) * su, r * sv))
        for i in range(U):
            for j in range(V):
                a = i * V + j
                b = ((i + 1) % U) * V + j
                c = i * V + (j + 1) % V
                edges.append((a, b))
                edges.append((a, c))
        _torus_cache = (verts, edges)
        _torus_scaled = None
        _torus_last_scale = None
    verts, edges = _torus_cache
    if scale != 1.0:
        if _torus_last_scale != scale:
            _torus_scaled = [(x * scale, y * scale, z * scale) for x, y, z in verts]
            _torus_last_scale = scale
        verts = _torus_scaled
    drawObject3D(verts, edges, ang, ang * 0.7)


_teapot_cache = None
_teapot_scaled = None
_teapot_last_scale = None


def drawTeapotWireframe(ang, scale=1.0):
    global _teapot_cache, _teapot_scaled, _teapot_last_scale
    if _teapot_cache is None:
        RADIAL = 16
        prof = [(0, -16), (8, -14), (13, -8), (13, 4), (10, 10), (5, 12), (0, 12)]
        verts = [(0, prof[0][1], 0)]
        for p in range(1, 6):
            pr, py = prof[p]
            for r in range(RADIAL):
                th = (r / RADIAL) * 2 * math.pi
                verts.append((pr * math.cos(th), py, pr * math.sin(th)))
        verts.append((0, prof[6][1], 0))
        edges = []
        base = 1
        for r in range(RADIAL):
            b0 = base + r
            b1 = base + (r + 1) % RADIAL
            edges.append((0, b0))
            edges.append((b0, b1))
        for p in range(4):
            curr = 1 + p * RADIAL
            nxt = curr + RADIAL
            for r in range(RADIAL):
                c0 = curr + r
                n0 = nxt + r
                c1 = curr + (r + 1) % RADIAL
                edges.append((c0, n0))
                edges.append((c0, c1))
        lastRing = 1 + 4 * RADIAL
        topIdx = len(verts) - 1
        for r in range(RADIAL):
            c0 = lastRing + r
            c1 = lastRing + (r + 1) % RADIAL
            edges.append((c0, c1))
            edges.append((c0, topIdx))
        _teapot_cache = (verts, edges)
    verts, edges = _teapot_cache
    if scale != 1.0:
        if _teapot_last_scale != scale:
            _teapot_scaled = [(x * scale, y * scale, z * scale) for x, y, z in verts]
            _teapot_last_scale = scale
        verts = _teapot_scaled
    drawObject3D(verts, edges, ang, ang * 0.7)


def drawCube3D(ang, scale=1.0):
    s = 20.0 * scale
    v = [
        (-s, -s, -s),
        (s, -s, -s),
        (s, s, -s),
        (-s, s, -s),
        (-s, -s, s),
        (s, -s, s),
        (s, s, s),
        (-s, s, s),
    ]
    e = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    ]
    drawObject3D(v, e, ang, ang * 0.7)


def drawPyramid3D(ang, scale=1.0):
    s = 22.0 * scale
    v = [(-s, -s, -s), (s, -s, -s), (s, -s, s), (-s, -s, s), (0, s, 0)]
    e = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)]
    drawObject3D(v, e, ang, ang * 0.7)


def drawOctahedron3D(ang, scale=1.0):
    s = 20.0 * scale
    v = [(0, s, 0), (0, -s, 0), (s, 0, 0), (-s, 0, 0), (0, 0, s), (0, 0, -s)]
    e = [
        (0, 2),
        (0, 3),
        (0, 4),
        (0, 5),
        (1, 2),
        (1, 3),
        (1, 4),
        (1, 5),
        (2, 4),
        (4, 3),
        (3, 5),
        (5, 2),
    ]
    drawObject3D(v, e, ang, ang * 0.7)


_sphere_cache = None


def drawSphere3D(ang, scale=1.0):
    global _sphere_cache
    if _sphere_cache is None:
        rings = 6
        segs = 12
        r = 22.0
        verts = []
        edges = []
        for i in range(rings):
            phi = (i / (rings - 1)) * math.pi
            sp = math.sin(phi)
            cp = math.cos(phi)
            for j in range(segs):
                th = (j / segs) * 2 * math.pi
                verts.append((r * sp * math.cos(th), r * cp, r * sp * math.sin(th)))
        for i in range(rings):
            for j in range(segs):
                a = i * segs + j
                b = i * segs + ((j + 1) % segs)
                edges.append((a, b))
                if i < rings - 1:
                    c = (i + 1) * segs + j
                    edges.append((a, c))
        _sphere_cache = (verts, edges)
    verts, edges = _sphere_cache
    if scale != 1.0:
        verts = [(x * scale, y * scale, z * scale) for x, y, z in verts]
    drawObject3D(verts, edges, ang, ang * 0.7)


_star_cache = None
_star_scaled = None
_star_last_scale = None


def drawStarfighterWireframe(ang, scale=1.0):
    global _star_cache, _star_scaled, _star_last_scale
    if _star_cache is None:
        base = [
            (22, 0, 0),
            (12, 2, -3),
            (12, -2, -3),
            (12, 2, 3),
            (12, -2, 3),
            (-4, 0, -5),
            (-4, 0, 5),
            (-18, 0, 0),
            (-4, 3, 0),
            (-4, -3, 0),
            (0, 0, 12),
            (-8, 0, 14),
            (-14, 0, 9),
            (0, 0, -12),
            (-8, 0, -14),
            (-14, 0, -9),
            (-14, 4, 0),
            (-20, 6, 0),
            (-20, 0, 0),
            (-14, -4, 0),
            (-20, -6, 0),
        ]
        edges = [
            (0, 1),
            (0, 2),
            (0, 3),
            (0, 4),
            (1, 2),
            (3, 4),
            (1, 3),
            (2, 4),
            (1, 5),
            (2, 5),
            (3, 6),
            (4, 6),
            (5, 7),
            (6, 7),
            (5, 8),
            (6, 8),
            (5, 9),
            (6, 9),
            (8, 7),
            (9, 7),
            (5, 10),
            (10, 11),
            (11, 12),
            (12, 5),
            (5, 11),
            (5, 13),
            (13, 14),
            (14, 15),
            (15, 5),
            (5, 14),
            (7, 16),
            (16, 17),
            (17, 18),
            (18, 7),
            (7, 19),
            (19, 20),
            (20, 18),
        ]
        _star_cache = (base, edges)
    base, edges = _star_cache
    if _star_last_scale != scale:
        _star_scaled = [(x * scale, y * scale, z * scale) for x, y, z in base]
        _star_last_scale = scale
    drawObject3D(_star_scaled, edges, ang * 0.9, ang, ang * 1.2)


_enterprise_cache = None
_enterprise_scaled = None
_enterprise_last_scale = None


def buildEnterprise():
    SEG = 16
    verts = []
    edges = []
    scx = 16.0

    def add_ring(r, y):
        start = len(verts)
        for i in range(SEG):
            th = (i / SEG) * 2 * math.pi
            verts.append((scx + math.cos(th) * r, y, math.sin(th) * r))
        return start

    topOuter = add_ring(14.0, 1.3)
    topInner = add_ring(6.0, 1.7)
    botOuter = add_ring(14.0, -1.3)
    botInner = add_ring(6.0, -1.7)
    bridgeRim = add_ring(2.2, 2.5)
    bridgeTop = len(verts)
    verts.append((scx, 3.6, 0))
    sensorRim = len(verts)
    for i in range(8):
        th = (i / 8) * 2 * math.pi
        verts.append((scx + math.cos(th) * 2.0, -2.3, math.sin(th) * 2.0))
    sensorBot = len(verts)
    verts.append((scx, -3.3, 0))
    secFT = len(verts)
    verts.append((6, -4.5, 0))
    secFB = len(verts)
    verts.append((6, -7.5, 0))
    secRT = len(verts)
    verts.append((-14, -4.5, 0))
    secRB = len(verts)
    verts.append((-14, -8.0, 0))
    defFront = len(verts)
    verts.append((-1, -6.0, 0))
    defRim = len(verts)
    for i in range(8):
        th = (i / 8) * 2 * math.pi
        verts.append((2 + math.cos(th) * 0.8, -6.0 + math.sin(th) * 1.6, 0))

    def add_nacelle(x, z):
        s = len(verts)
        for i in range(8):
            th = (i / 8) * 2 * math.pi
            verts.append((x + math.cos(th) * 1.0, -3.2 + math.sin(th) * 1.0, z))
        return s

    nacL_F = add_nacelle(5, 9.5)
    nacL_R = add_nacelle(-18, 9.5)
    nacR_F = add_nacelle(5, -9.5)
    nacR_R = add_nacelle(-18, -9.5)
    nacL_Bus = len(verts)
    verts.append((7.5, -3.2, 9.5))
    nacR_Bus = len(verts)
    verts.append((7.5, -3.2, -9.5))
    pylonL_H = len(verts)
    verts.append((-7, -5.0, 2.5))
    pylonL_N = len(verts)
    verts.append((-9, -3.8, 8.0))
    pylonR_H = len(verts)
    verts.append((-7, -5.0, -2.5))
    pylonR_N = len(verts)
    verts.append((-9, -3.8, -8.0))
    for i in range(SEG):
        n = (i + 1) % SEG
        edges.append((topOuter + i, topOuter + n))
        edges.append((botOuter + i, botOuter + n))
        edges.append((topInner + i, topInner + n))
        edges.append((botInner + i, botInner + n))
        edges.append((topOuter + i, topInner + i))
        edges.append((botOuter + i, botInner + i))
        edges.append((topOuter + i, botOuter + i))
    for i in range(0, SEG, 2):
        edges.append((topOuter + i, botOuter + (i + 8) % SEG))
    for i in range(SEG):
        n = (i + 1) % SEG
        edges.append((bridgeRim + i, bridgeRim + n))
        edges.append((bridgeRim + i, bridgeTop))
    for i in range(8):
        n = (i + 1) % 8
        edges.append((sensorRim + i, sensorRim + n))
        edges.append((sensorRim + i, sensorBot))
    edges.extend(
        [
            (secFT, secRT),
            (secFB, secRB),
            (secFT, secFB),
            (secRT, secRB),
            (secFT, defFront),
            (secFB, defFront),
        ]
    )
    for i in range(8):
        n = (i + 1) % 8
        edges.append((defRim + i, defRim + n))
        edges.append((defRim + i, defFront))
    edges.append((topInner + 12, secFT))
    edges.append((topInner + 4, secFT))
    edges.append((botInner + 12, secFB))
    for i in range(8):
        n = (i + 1) % 8
        edges.append((nacL_F + i, nacL_F + n))
        edges.append((nacL_R + i, nacL_R + n))
        edges.append((nacR_F + i, nacR_F + n))
        edges.append((nacR_R + i, nacR_R + n))
    for i in range(8):
        edges.append((nacL_F + i, nacL_R + i))
        edges.append((nacR_F + i, nacR_R + i))
        edges.append((nacL_F + i, nacL_Bus))
        edges.append((nacR_F + i, nacR_Bus))
    edges.extend(
        [
            (secRT, pylonL_H),
            (pylonL_H, pylonL_N),
            (pylonL_N, nacL_F + 2),
            (secRT, pylonR_H),
            (pylonR_H, pylonR_N),
            (pylonR_N, nacR_F + 2),
        ]
    )
    return verts, edges


def drawEnterpriseWireframe(ang, scale=1.0):
    global _enterprise_cache, _enterprise_scaled, _enterprise_last_scale
    if _enterprise_cache is None:
        _enterprise_cache = buildEnterprise()
    verts, edges = _enterprise_cache
    if _enterprise_last_scale != scale:
        _enterprise_scaled = [(x * scale, y * scale, z * scale) for x, y, z in verts]
        _enterprise_last_scale = scale
    drawObject3D(_enterprise_scaled, edges, ang * 0.9, ang, ang * 0.2)


def main():
    _thread.start_new_thread(core1_main, ())
    time.sleep_ms(500)
    oled.fill(0)
    oled.show()
    while True:
        oled.fill(0)
        hello_world()
        time.sleep(2)
        clear_screen("black")
        oled.fill(0)
        grid()
        oled.show()
        time.sleep(1.5)
        oled.fill(0)
        grid()
        grid_num()
        oled.show()
        time.sleep(1.5)
        flash_screen(4, 0.3)
        clear_screen("black")
        global lissa_phase
        s = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), s) < 2500:
            lissa_phase += lissa_speed
            if lissa_phase > 6.28318:
                lissa_phase -= 6.28318
            LissajousFrame(lissa_phase)
        clear_screen("black")
        # 3D smiley (~8s with scale bounce)
        s = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), s) < 8000:
            elapsed = time.ticks_diff(time.ticks_ms(), s)
            a = time.ticks_ms() * smiley_speed
            scale = 1.0
            if 1000 <= elapsed < 1500:
                scale = 1.0 + ((elapsed - 1000) / 500.0) * 0.5
            elif 1500 <= elapsed < 2000:
                scale = 1.5 - ((elapsed - 1500) / 500.0) * 1.0
            elif 2000 <= elapsed < 2250:
                scale = 0.5 + ((elapsed - 2000) / 250.0) * 0.5
            drawSmiley3D(a, scale)
        clear_screen("black")

        def run_for(ms, func, speed):
            st = time.ticks_ms()
            a = 0.0
            while time.ticks_diff(time.ticks_ms(), st) < ms:
                a += speed
                func(a)

        run_for(2000, lambda a: drawCube3D(a, 1.0), cube_speed)
        run_for(2000, lambda a: drawPyramid3D(a, 1.0), pyramid_speed)
        run_for(2000, lambda a: drawOctahedron3D(a, 1.0), octahedron_speed)
        run_for(2000, lambda a: drawSphere3D(a, 1.0), sphere_speed)
        run_for(4000, lambda a: drawTorusWireframe(a, 1.0), torus_speed)
        run_for(4000, lambda a: drawTeapotWireframe(a, 1.0), teapot_speed)
        run_for(5000, lambda a: drawStarfighterWireframe(a, star_scale), star_speed)
        run_for(8000, lambda a: drawEnterpriseWireframe(a, enterprise_scale), enterprise_speed)
        clear_screen("black")


if __name__ == "__main__":
    main()
