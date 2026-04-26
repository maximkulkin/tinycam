# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True
"""
Cython-accelerated thick-line vertex generation for Line2D.

Replaces the pure-Python _generate_vertices() path when width is not None.
The algorithm is identical to the Python version; only the implementation
is moved to typed C code to eliminate per-vertex Python overhead.
"""

import numpy as np
cimport numpy as np
from libc.math cimport sqrt, cos, sin, atan2, atan2f, fabs, ceil

np.import_array()

ctypedef np.float32_t f32

# Match JointStyle enum (auto() starts at 1): MITER=1, BEVEL=2, ROUND=3
DEF JOINT_MITER = 1
DEF JOINT_BEVEL = 2
DEF JOINT_ROUND = 3

# Match CapStyle enum (auto() starts at 1): BUTT=1, ROUND=2, SQUARE=3
DEF CAP_BUTT   = 1
DEF CAP_ROUND  = 2
DEF CAP_SQUARE = 3

DEF PI = 3.141592653589793


# ---------------------------------------------------------------------------
# Low-level helpers (all nogil)
# ---------------------------------------------------------------------------

cdef inline float _len2(float x, float y) noexcept nogil:
    return sqrt(x * x + y * y)


cdef inline void _normal(
    float ax, float ay, float bx, float by,
    float* nx, float* ny,
) noexcept nogil:
    """Normalised left-perpendicular (rot90ccw) of the vector (b - a)."""
    cdef float dx = bx - ax, dy = by - ay
    cdef float l = _len2(dx, dy)
    if l > 1e-9:
        nx[0] = -dy / l
        ny[0] =  dx / l
    else:
        nx[0] = 0.0
        ny[0] = 1.0


cdef inline void _emit(
    float* pos, float* uv, int* cnt,
    float x, float y, float u,
) noexcept nogil:
    cdef int i = cnt[0]
    pos[i * 2]     = x
    pos[i * 2 + 1] = y
    uv[i * 2]      = u
    uv[i * 2 + 1]  = 0.0
    cnt[0] = i + 1


cdef void _emit_cap(
    float* pos, float* uv, int* cnt,
    float px, float py,
    float dx, float dy,   # normalised direction pointing *away* from the line end
    float hw,             # half_width
    int cap_style,
    bint is_start,
    float u,
) noexcept nogil:
    cdef float nx, ny, cx, cy
    cdef int j
    cdef float angle, ca, sa, rx, ry

    if cap_style == CAP_BUTT:
        return

    elif cap_style == CAP_SQUARE:
        # normal = rot90ccw(direction)
        nx = -dy; ny = dx
        cx = px + dx * hw
        cy = py + dy * hw
        if is_start:
            _emit(pos, uv, cnt, cx - nx * hw, cy - ny * hw, u)
            _emit(pos, uv, cnt, cx + nx * hw, cy + ny * hw, u)
        else:
            _emit(pos, uv, cnt, cx + nx * hw, cy + ny * hw, u)
            _emit(pos, uv, cnt, cx - nx * hw, cy - ny * hw, u)

    elif cap_style == CAP_ROUND:
        for j in range(11):   # num_segments = 10 → range(11)
            angle = PI * j / 10.0 - PI / 2.0
            ca = cos(angle); sa = sin(angle)
            rx = ca * dx - sa * dy
            ry = sa * dx + ca * dy
            _emit(pos, uv, cnt, px + rx * hw, py + ry * hw, u)
            _emit(pos, uv, cnt, px,           py,           u)


cdef void _emit_joint(
    float* pos, float* uv, int* cnt,
    float px, float py,
    float n1x, float n1y,   # normal of incoming segment
    float n2x, float n2y,   # normal of outgoing segment
    float hw,               # half_width
    bint ccw,
    int joint_style,
    float miter_limit,      # ≤ 0 means no limit
    float u,
) noexcept nogil:
    cdef float mx, my, ml, dv, miter_len
    cdef int j, ns, eff
    cdef float angle_f, angle, ba, a, ca, sa

    # miter_vec = normalise(n1 + n2)
    mx = n1x + n2x; my = n1y + n2y
    ml = _len2(mx, my)
    if ml > 1e-6:
        mx /= ml; my /= ml
    else:
        mx = n1x; my = n1y

    dv = mx * n1x + my * n1y
    if fabs(dv) < 1e-6:
        miter_len = hw
    else:
        miter_len = hw / dv

    eff = joint_style
    if joint_style == JOINT_MITER and miter_limit > 0.0 and miter_len > miter_limit:
        eff = JOINT_BEVEL

    if eff == JOINT_MITER:
        _emit(pos, uv, cnt, px + mx * miter_len, py + my * miter_len, u)
        _emit(pos, uv, cnt, px - mx * miter_len, py - my * miter_len, u)

    elif eff == JOINT_BEVEL:
        if ccw:
            _emit(pos, uv, cnt, px + mx * miter_len, py + my * miter_len, u)
            _emit(pos, uv, cnt, px - n1x * hw,       py - n1y * hw,       u)
            _emit(pos, uv, cnt, px + mx * miter_len, py + my * miter_len, u)
            _emit(pos, uv, cnt, px - n2x * hw,       py - n2y * hw,       u)
        else:
            _emit(pos, uv, cnt, px + n1x * hw,       py + n1y * hw,       u)
            _emit(pos, uv, cnt, px - mx * miter_len, py - my * miter_len, u)
            _emit(pos, uv, cnt, px + n2x * hw,       py + n2y * hw,       u)
            _emit(pos, uv, cnt, px - mx * miter_len, py - my * miter_len, u)

    elif eff == JOINT_ROUND:
        # Use atan2f (float32) for the segment count to match numpy's float32
        # precision, which Python uses when normals are Vector2 (float32 arrays).
        angle_f = atan2f(n1y, n1x) - atan2f(n2y, n2x)
        if angle_f >  <float>PI: angle_f -= 2.0 * PI
        if angle_f < -<float>PI: angle_f += 2.0 * PI
        angle = angle_f  # promote to double for arc computation below

        ns = <int>(fabs(angle_f) * 180.0 / PI / 10.0)
        if ns < 2: ns = 2
        ba = atan2(n1y, n1x)

        if ccw:
            for j in range(ns + 1):
                a = ba - angle * j / ns
                ca = cos(a); sa = sin(a)
                _emit(pos, uv, cnt, px + mx * miter_len, py + my * miter_len, u)
                _emit(pos, uv, cnt, px - ca * hw,        py - sa * hw,        u)
        else:
            for j in range(ns + 1):
                a = ba - angle * j / ns
                ca = cos(a); sa = sin(a)
                _emit(pos, uv, cnt, px + ca * hw,        py + sa * hw,        u)
                _emit(pos, uv, cnt, px - mx * miter_len, py - my * miter_len, u)


# ---------------------------------------------------------------------------
# Subdivision helper
# ---------------------------------------------------------------------------

cdef np.ndarray _subdivide(float[:, :] p, int n, float max_seg_len, bint closed):
    """
    Insert intermediate points so that no segment exceeds max_seg_len.
    Returns a new (M, 2) float32 array.
    """
    result = []
    cdef float dx, dy, seg_len, new_sl, vx, vy
    cdef int i, j, num_sub

    for i in range(n - 1):
        result.append((p[i, 0], p[i, 1]))
        dx = p[i+1, 0] - p[i, 0]
        dy = p[i+1, 1] - p[i, 1]
        seg_len = _len2(dx, dy)
        if seg_len > max_seg_len:
            num_sub = <int>ceil(seg_len / max_seg_len)
            new_sl  = seg_len / num_sub
            vx = dx / seg_len; vy = dy / seg_len
            for j in range(1, num_sub):
                result.append((p[i, 0] + vx * j * new_sl,
                               p[i, 1] + vy * j * new_sl))

    result.append((p[n-1, 0], p[n-1, 1]))

    if closed:
        dx = p[0, 0] - p[n-1, 0]
        dy = p[0, 1] - p[n-1, 1]
        seg_len = _len2(dx, dy)
        if seg_len > max_seg_len:
            num_sub = <int>ceil(seg_len / max_seg_len)
            new_sl  = seg_len / num_sub
            vx = dx / seg_len; vy = dy / seg_len
            for j in range(1, num_sub):
                result.append((p[n-1, 0] + vx * j * new_sl,
                               p[n-1, 1] + vy * j * new_sl))

    return np.array(result, dtype=np.float32)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_vertices_thick(
    object points_in,
    bint closed,
    float half_width,
    int joint_style,    # JointStyle.value  (1=MITER, 2=BEVEL, 3=ROUND)
    float miter_limit,  # pass -1.0 when None
    int cap_style,      # CapStyle.value    (1=BUTT,  2=ROUND, 3=SQUARE)
    float max_seg_len,  # pass -1.0 when None
) -> tuple:
    """
    Build triangle-strip vertex data for a thick 2-D polyline.

    Returns (positions_bytes, uvs_bytes), each a flat float32 byte string
    ready to upload to a ModernGL VBO (2 floats per vertex).
    """
    cdef np.ndarray[f32, ndim=2] pts
    pts = np.asarray(points_in, dtype=np.float32).reshape(-1, 2)
    cdef int n = pts.shape[0]

    if n < 2:
        return b'', b''

    # Strip duplicate closing point (matches Python pre-processing)
    if closed and pts[0, 0] == pts[n-1, 0] and pts[0, 1] == pts[n-1, 1]:
        n -= 1
        pts = pts[:n]

    # Optional subdivision
    cdef float[:, :] p_tmp
    if max_seg_len > 0.0:
        p_tmp = pts
        pts = _subdivide(p_tmp, n, max_seg_len, closed)
        n = pts.shape[0]

    # Upper-bound vertex count:
    #   round cap   = 22 verts
    #   round joint = 2*(ns+1) ≤ 38 verts  (ns=18 at 180°)
    #   per segment pair = 2 verts
    # → n*40 + 100 is comfortably safe
    cdef int max_v = n * 40 + 100
    cdef np.ndarray[f32, ndim=1] out_pos = np.empty(max_v * 2, dtype=np.float32)
    cdef np.ndarray[f32, ndim=1] out_uv  = np.empty(max_v * 2, dtype=np.float32)

    cdef float* pp = <float*> out_pos.data
    cdef float* pu = <float*> out_uv.data
    cdef float[:, :] p = pts

    cdef int  cnt = 0
    cdef float length = 0.0
    cdef float nx, ny, nx2, ny2, dx, dy, sl
    cdef bint ccw
    cdef int i

    with nogil:
        if not closed:
            # ── start cap ──────────────────────────────────────────────────
            dx = p[0, 0] - p[1, 0]; dy = p[0, 1] - p[1, 1]
            sl = _len2(dx, dy)
            if sl > 1e-9: dx /= sl; dy /= sl
            _emit_cap(pp, pu, &cnt,
                      p[0, 0], p[0, 1], dx, dy,
                      half_width, cap_style, True, 0.0)

            # ── first segment start pair ────────────────────────────────────
            _normal(p[0, 0], p[0, 1], p[1, 0], p[1, 1], &nx, &ny)
            _emit(pp, pu, &cnt, p[0, 0] + nx * half_width, p[0, 1] + ny * half_width, 0.0)
            _emit(pp, pu, &cnt, p[0, 0] - nx * half_width, p[0, 1] - ny * half_width, 0.0)

        else:
            # ── first joint (last-segment → first-segment wrap) ─────────────
            _normal(p[n-1, 0], p[n-1, 1], p[0, 0], p[0, 1], &nx,  &ny)
            _normal(p[0,   0], p[0,   1], p[1, 0], p[1, 1], &nx2, &ny2)
            dx = p[1, 0] - p[0, 0]; dy = p[1, 1] - p[0, 1]
            ccw = (nx * dx + ny * dy) > 0
            _emit_joint(pp, pu, &cnt,
                        p[0, 0], p[0, 1], nx, ny, nx2, ny2,
                        half_width, ccw, joint_style, miter_limit, 0.0)

        # ── main segment loop ───────────────────────────────────────────────
        for i in range(n - 2):
            _normal(p[i, 0], p[i, 1], p[i+1, 0], p[i+1, 1], &nx, &ny)
            length += _len2(p[i+1, 0] - p[i, 0], p[i+1, 1] - p[i, 1])

            _normal(p[i+1, 0], p[i+1, 1], p[i+2, 0], p[i+2, 1], &nx2, &ny2)
            dx = p[i+2, 0] - p[i+1, 0]; dy = p[i+2, 1] - p[i+1, 1]
            ccw = (nx * dx + ny * dy) > 0
            _emit_joint(pp, pu, &cnt,
                        p[i+1, 0], p[i+1, 1], nx, ny, nx2, ny2,
                        half_width, ccw, joint_style, miter_limit, length)

        if not closed:
            # ── last segment end pair ───────────────────────────────────────
            _normal(p[n-2, 0], p[n-2, 1], p[n-1, 0], p[n-1, 1], &nx, &ny)
            _emit(pp, pu, &cnt,
                  p[n-1, 0] + nx * half_width, p[n-1, 1] + ny * half_width, length)
            _emit(pp, pu, &cnt,
                  p[n-1, 0] - nx * half_width, p[n-1, 1] - ny * half_width, length)

            # ── end cap ─────────────────────────────────────────────────────
            dx = p[n-1, 0] - p[n-2, 0]; dy = p[n-1, 1] - p[n-2, 1]
            sl = _len2(dx, dy)
            if sl > 1e-9: dx /= sl; dy /= sl
            _emit_cap(pp, pu, &cnt,
                      p[n-1, 0], p[n-1, 1], dx, dy,
                      half_width, cap_style, False, length)

        else:
            # ── closing joint (at p[n-1]) ────────────────────────────────────
            _normal(p[n-2, 0], p[n-2, 1], p[n-1, 0], p[n-1, 1], &nx,  &ny)
            # Replicate Python: length += |p[n-2]→p[n-1]| a second time.
            length += _len2(p[n-1, 0] - p[n-2, 0], p[n-1, 1] - p[n-2, 1])
            _normal(p[n-1, 0], p[n-1, 1], p[0, 0], p[0, 1], &nx2, &ny2)
            dx = p[0, 0] - p[n-1, 0]; dy = p[0, 1] - p[n-1, 1]
            ccw = (nx * dx + ny * dy) > 0
            _emit_joint(pp, pu, &cnt,
                        p[n-1, 0], p[n-1, 1], nx, ny, nx2, ny2,
                        half_width, ccw, joint_style, miter_limit, length)

            # ── copy first 2 vertices to close the strip ────────────────────
            pp[cnt * 2]     = pp[0]; pp[cnt * 2 + 1] = pp[1]
            pu[cnt * 2]     = pu[0]; pu[cnt * 2 + 1] = pu[1]
            cnt += 1
            pp[cnt * 2]     = pp[2]; pp[cnt * 2 + 1] = pp[3]
            pu[cnt * 2]     = pu[2]; pu[cnt * 2 + 1] = pu[3]
            cnt += 1

    return out_pos[:cnt * 2].tobytes(), out_uv[:cnt * 2].tobytes()
