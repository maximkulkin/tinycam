# cython: language_level=3
# cython: boundscheck=False
# cython: wraparound=False
# cython: cdivision=True
# cython: nonecheck=False

"""
Cython implementation of the straight skeleton / polygon offsetting algorithm.

Points and vectors are stored as plain C doubles in a Vec2 struct, which
eliminates numpy array allocation overhead in tight loops.
"""

import shapely as s
from libc.math cimport sqrt, fabs

cdef double EPSILON = 0.0001


# ---------------------------------------------------------------------------
# Lightweight 2-D vector struct
# ---------------------------------------------------------------------------

cdef struct Vec2:
    double x
    double y


cdef inline Vec2 vec2(double x, double y) noexcept nogil:
    cdef Vec2 v
    v.x = x
    v.y = y
    return v


cdef inline double dot(Vec2 a, Vec2 b) noexcept nogil:
    return a.x * b.x + a.y * b.y


cdef inline double cross2(Vec2 a, Vec2 b) noexcept nogil:
    return a.x * b.y - a.y * b.x


cdef inline Vec2 normalize(Vec2 v) noexcept nogil:
    cdef double l = sqrt(v.x * v.x + v.y * v.y)
    if l == 0.0:
        return v
    return vec2(v.x / l, v.y / l)


cdef inline Vec2 rot90cw(Vec2 v) noexcept nogil:
    """Rotate 90° clockwise: (x,y) → (y,−x)"""
    return vec2(v.y, -v.x)


cdef inline Vec2 rot90ccw(Vec2 v) noexcept nogil:
    """Rotate 90° counter-clockwise: (x,y) → (−y,x)"""
    return vec2(-v.y, v.x)


cdef inline Vec2 line_normal(Vec2 p1, Vec2 p2, bint ccw) noexcept nogil:
    cdef Vec2 d = normalize(vec2(p2.x - p1.x, p2.y - p1.y))
    if ccw:
        return rot90ccw(d)
    return rot90cw(d)


# ---------------------------------------------------------------------------
# Extension types
# ---------------------------------------------------------------------------

cdef class StillPoint:
    cdef public double px, py
    cdef public list next_points  # list[StillPoint]

    def __cinit__(self, double px, double py, list next_points=None):
        self.px = px
        self.py = py
        self.next_points = next_points if next_points is not None else []


cdef class Vertex:
    cdef public str name
    cdef public double px, py        # origin point
    cdef public double dx, dy        # bisector direction
    cdef public double offset        # distance at which this vertex was created
    cdef public bint active
    cdef public bint is_reflex
    cdef public Vertex prev
    cdef public Vertex next
    cdef public StillPoint still_point

    def __cinit__(
        self,
        str name,
        double px, double py,
        double dx, double dy,
        double offset=0.0,
        bint is_reflex=False,
        Vertex prev=None,
        Vertex next=None,
        StillPoint still_point=None,
    ):
        self.name = name
        self.px = px
        self.py = py
        self.dx = dx
        self.dy = dy
        self.offset = offset
        self.active = True
        self.is_reflex = is_reflex
        self.prev = prev
        self.next = next
        self.still_point = still_point

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other

    def __repr__(self):
        prev_name = 'None' if self.prev is None else self.prev.name
        next_name = 'None' if self.next is None else self.next.name
        return (f'Vertex(name={self.name} point=({self.px},{self.py}) '
                f'dir=({self.dx},{self.dy}) offset={self.offset} '
                f'prev={prev_name} next={next_name})')

    cdef inline Vec2 c_point_at(self, double dist) noexcept nogil:
        cdef double dt = dist - self.offset
        return vec2(self.px + self.dx * dt, self.py + self.dy * dt)

    def point_at(self, double dist):
        import numpy as np
        cdef Vec2 p = self.c_point_at(dist)
        return np.array([p.x, p.y], dtype=np.float64)

    @property
    def point(self):
        import numpy as np
        return np.array([self.px, self.py], dtype=np.float64)

    @property
    def direction(self):
        import numpy as np
        return np.array([self.dx, self.dy], dtype=np.float64)


cdef class Event:
    cdef public double distance

    def __cinit__(self, double distance, *args, **kwargs):
        self.distance = distance

    @property
    def active(self):
        return True


cdef class MergeEvent(Event):
    cdef public Vertex vertex1
    cdef public Vertex vertex2

    def __cinit__(self, double distance, Vertex vertex1, Vertex vertex2):
        self.distance = distance
        self.vertex1 = vertex1
        self.vertex2 = vertex2

    @property
    def active(self):
        return self.vertex1.active and self.vertex2.active

    def __repr__(self):
        cdef Vec2 p = self.vertex1.c_point_at(self.distance)
        return (f'MergeEvent(distance={self.distance} point=({p.x},{p.y}) '
                f'vertex1={self.vertex1.name} vertex2={self.vertex2.name})')

    def __eq__(self, other):
        if not isinstance(other, MergeEvent):
            return False
        return (self.vertex1 is (<MergeEvent>other).vertex1 and
                self.vertex2 is (<MergeEvent>other).vertex2 and
                self.distance == (<MergeEvent>other).distance)

    def __hash__(self):
        return hash((self.distance, id(self.vertex1), id(self.vertex2)))


cdef class SplitEvent(Event):
    cdef public Vertex vertex
    cdef public Vertex line_vertex1
    cdef public Vertex line_vertex2

    def __cinit__(self, double distance, Vertex vertex,
                  Vertex line_vertex1, Vertex line_vertex2):
        self.distance = distance
        self.vertex = vertex
        self.line_vertex1 = line_vertex1
        self.line_vertex2 = line_vertex2

    @property
    def active(self):
        return (self.vertex.active and
                self.line_vertex1.active and
                self.line_vertex2.active)

    def __repr__(self):
        cdef Vec2 p = self.vertex.c_point_at(self.distance)
        return (f'SplitEvent(distance={self.distance} point=({p.x},{p.y}) '
                f'vertex={self.vertex.name} '
                f'line_point1={self.line_vertex1.name} '
                f'line_point2={self.line_vertex2.name})')

    def __eq__(self, other):
        if not isinstance(other, SplitEvent):
            return False
        return (self.vertex is (<SplitEvent>other).vertex and
                self.line_vertex1 is (<SplitEvent>other).line_vertex1 and
                self.line_vertex2 is (<SplitEvent>other).line_vertex2 and
                self.distance == (<SplitEvent>other).distance)

    def __hash__(self):
        return hash((self.distance, id(self.vertex),
                     id(self.line_vertex1), id(self.line_vertex2)))


# ---------------------------------------------------------------------------
# Event calculation (module-level cdef functions for zero-overhead dispatch)
# ---------------------------------------------------------------------------

cdef Event _calc_merge_event(Vertex v1, Vertex v2):
    cdef double offset = v1.offset if v1.offset > v2.offset else v2.offset

    cdef Vec2 vp1 = v1.c_point_at(offset)
    cdef Vec2 vp2 = v2.c_point_at(offset)

    if fabs(vp1.x - vp2.x) < EPSILON and fabs(vp1.y - vp2.y) < EPSILON:
        return None

    # Normal of v2's direction (CW 90°)
    cdef Vec2 n = rot90cw(vec2(v2.dx, v2.dy))
    cdef double d = dot(n, vec2(v1.dx, v1.dy))
    if fabs(d) < EPSILON:
        return None

    cdef double l = dot(n, vec2(vp2.x - vp1.x, vp2.y - vp1.y)) / d
    if l <= 0.0:
        return None

    return MergeEvent(distance=offset + l, vertex1=v1, vertex2=v2)


cdef Event _calc_split_event(Vertex v, Vertex line_v1, Vertex line_v2, bint ccw):
    if not v.is_reflex:
        return None
    if line_v1 is v or line_v2 is v:
        return None

    cdef double offset = v.offset
    if line_v1.offset > offset:
        offset = line_v1.offset
    if line_v2.offset > offset:
        offset = line_v2.offset

    cdef Vec2 vp = v.c_point_at(offset)
    cdef Vec2 p1 = line_v1.c_point_at(offset)
    cdef Vec2 p2 = line_v2.c_point_at(offset)

    cdef Vec2 n = line_normal(p1, p2, False)
    if ccw:
        n.x = -n.x
        n.y = -n.y

    cdef Vec2 vdir = vec2(v.dx, v.dy)
    cdef double dn = -dot(vdir, n)
    if dn <= 0.0:
        return None

    cdef double d = dot(n, vec2(vp.x - p1.x, vp.y - p1.y)) / (1.0 + dn)

    cdef Vec2 p11 = vec2(p1.x + line_v1.dx * d, p1.y + line_v1.dy * d)
    cdef Vec2 p21 = vec2(p2.x + line_v2.dx * d, p2.y + line_v2.dy * d)

    cdef Vec2 vline = vec2(p21.x - p11.x, p21.y - p11.y)
    cdef double line_len_sq = vline.x * vline.x + vline.y * vline.y

    cdef Vec2 inter = vec2(vp.x + vdir.x * d, vp.y + vdir.y * d)

    cdef double l2 = dot(vline, vec2(inter.x - p11.x, inter.y - p11.y))
    if l2 < 0.0 or l2 > line_len_sq:
        return None

    return SplitEvent(
        distance=offset + d,
        vertex=v,
        line_vertex1=line_v1,
        line_vertex2=line_v2,
    )


# ---------------------------------------------------------------------------
# Main algorithm class
# ---------------------------------------------------------------------------

cdef class StraightSkeleton:
    # Expose nested types as class attributes (mirrors Python version API)
    MergeEvent = MergeEvent
    SplitEvent = SplitEvent
    Vertex = Vertex
    StillPoint = StillPoint
    Event = Event

    cdef bint _ccw
    cdef double _distance
    cdef object _event_count   # int | None
    cdef int _vertex_next_index
    cdef list _vertexes        # list[Vertex]
    cdef list _events          # list[Event]
    cdef list _points          # list[StillPoint]
    cdef object _shape         # shapely geometry

    def __cinit__(self, shape, double distance, event_count=None):
        self._ccw = distance < 0.0
        self._distance = fabs(distance)
        self._event_count = event_count
        self._vertex_next_index = 1

        self._vertexes = self._calculate_vertexes(shape)
        self._events = self._calculate_events(self._vertexes)
        self._events.sort(key=lambda e: e.distance)
        self._points = []

        self._process_events(self._distance, event_count)
        self._shape = self._build_shape(self._distance)

    @property
    def vertexes(self):
        return self._vertexes

    @property
    def events(self):
        return self._events

    @property
    def points(self):
        return self._points

    @property
    def shape(self):
        return self._shape

    # ------------------------------------------------------------------
    # Vertex construction helpers
    # ------------------------------------------------------------------

    cdef Vertex _make_vertex(
        self,
        double px, double py,
        double dx, double dy,
        double offset,
        bint is_reflex,
        Vertex prev,
        Vertex next_v,
        StillPoint still_point,
    ):
        cdef int idx = self._vertex_next_index
        self._vertex_next_index += 1
        return Vertex(
            name=str(idx),
            px=px, py=py,
            dx=dx, dy=dy,
            offset=offset,
            is_reflex=is_reflex,
            prev=prev,
            next=next_v,
            still_point=still_point,
        )

    cdef Vertex _calculate_vertex(
        self,
        double p1x, double p1y,
        double p2x, double p2y,
        double p3x, double p3y,
        double offset,
        Vertex prev,
        Vertex next_v,
        StillPoint still_point,
    ):
        cdef Vec2 v1 = normalize(vec2(p2x - p1x, p2y - p1y))
        cdef Vec2 v2 = normalize(vec2(p3x - p2x, p3y - p2y))

        cdef Vec2 n1 = rot90cw(v1)
        cdef Vec2 n2 = rot90cw(v2)

        cdef double denom = 1.0 + dot(n1, n2)
        # Avoid division by zero for antiparallel edges
        if fabs(denom) < 1e-10:
            denom = 1e-10

        cdef Vec2 bisector = vec2((n1.x + n2.x) / denom, (n1.y + n2.y) / denom)
        cdef bint is_reflex = cross2(v1, v2) > 0.0

        if self._ccw:
            bisector.x = -bisector.x
            bisector.y = -bisector.y
            is_reflex = not is_reflex

        return self._make_vertex(
            px=p2x, py=p2y,
            dx=bisector.x, dy=bisector.y,
            offset=offset,
            is_reflex=is_reflex,
            prev=prev,
            next_v=next_v,
            still_point=still_point,
        )

    # ------------------------------------------------------------------
    # Event and vertex list construction
    # ------------------------------------------------------------------

    cdef list _calculate_vertexes(self, line):
        coords = list(line.coords)
        cdef int n_raw = len(coords)
        if n_raw > 1 and coords[0] == coords[n_raw - 1]:
            coords = coords[:n_raw - 1]

        cdef int n = len(coords)
        cdef list vertexes = []
        cdef int i, i_prev, i_next

        for i in range(n):
            i_prev = (i - 1 + n) % n
            i_next = (i + 1) % n
            p1 = coords[i_prev]
            p2 = coords[i]
            p3 = coords[i_next]
            v = self._calculate_vertex(
                p1[0], p1[1],
                p2[0], p2[1],
                p3[0], p3[1],
                0.0, None, None, None,
            )
            v.name = str(i)
            vertexes.append(v)

        # Wire circular doubly-linked list
        for i in range(n):
            (<Vertex>vertexes[i]).prev = <Vertex>vertexes[(i - 1 + n) % n]
            (<Vertex>vertexes[i]).next = <Vertex>vertexes[(i + 1) % n]

        return vertexes

    cdef list _calculate_events(self, list vertexes):
        cdef set unique_events = set()
        cdef Vertex v1, v2, vertex, line_v1, line_v2
        cdef Event event
        cdef set seen

        # Merge events: each adjacent pair
        for v1 in vertexes:
            v2 = v1.next
            event = _calc_merge_event(v1, v2)
            if event is not None:
                unique_events.add(event)

        # Split events: each reflex vertex vs every non-adjacent edge
        for v1 in vertexes:
            if not v1.is_reflex:
                continue
            seen = set()
            for vertex in vertexes:
                if vertex in seen:
                    continue
                line_v1 = vertex
                while True:
                    line_v2 = line_v1.next
                    if line_v1 is not v1 and line_v2 is not v1:
                        event = _calc_split_event(v1, line_v1, line_v2, self._ccw)
                        if event is not None:
                            unique_events.add(event)
                    seen.add(line_v1)
                    line_v1 = line_v1.next
                    if line_v1 is vertex:
                        break

        return sorted(list(unique_events), key=lambda e: e.distance)

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    cdef void _append_event(self, list events, double min_distance, Event event):
        if event is None:
            return
        if event.distance < min_distance:
            return
        events.append(event)

    cdef void _process_event(self, Event event):
        cdef list added_vertexes = []
        cdef list removed_events = []
        cdef Vertex v1, v2, new_v, v, l1, l2, vp, vn, new_v1, new_v2, vertex, av
        cdef StillPoint new_sp
        cdef double px, py, ex, ey
        cdef double l1px, l1py, l2px, l2py, vnpx, vnpy, vppx, vppy
        cdef list next_points, new_events
        cdef double min_d
        cdef Vec2 pt, pt2

        if isinstance(event, MergeEvent):
            v1 = (<MergeEvent>event).vertex1
            v2 = (<MergeEvent>event).vertex2

            pt = v1.c_point_at(event.distance)
            px = pt.x
            py = pt.y

            next_points = []
            if v1.still_point is not None:
                next_points.append(v1.still_point)
            if v2.still_point is not None:
                next_points.append(v2.still_point)
            new_sp = StillPoint(px, py, next_points)
            self._points.append(new_sp)

            if v1.prev is v2.next:
                pt2 = v2.next.c_point_at(event.distance)
                self._points.append(StillPoint(pt2.x, pt2.y, [new_sp]))
                v2.next.active = False
            else:
                new_v = self._make_vertex(
                    px=px, py=py,
                    dx=v1.dx + v2.dx,
                    dy=v1.dy + v2.dy,
                    offset=event.distance,
                    is_reflex=False,
                    prev=v1.prev,
                    next_v=v2.next,
                    still_point=new_sp,
                )
                new_v.prev.next = new_v
                new_v.next.prev = new_v
                added_vertexes.append(new_v)

            v1.active = False
            v2.active = False

        elif isinstance(event, SplitEvent):
            v = (<SplitEvent>event).vertex
            l1 = (<SplitEvent>event).line_vertex1
            l2 = (<SplitEvent>event).line_vertex2
            vp = v.prev
            vn = v.next

            pt = v.c_point_at(event.distance)
            px = pt.x
            py = pt.y

            next_points = []
            if v.still_point is not None:
                next_points.append(v.still_point)

            new_sp = StillPoint(px, py, next_points)
            self._points.append(new_sp)
            v.active = False

            if vp is not l2:
                pt = vp.c_point_at(event.distance)
                vppx = pt.x
                vppy = pt.y
                pt = l2.c_point_at(event.distance)
                l2px = pt.x
                l2py = pt.y
                new_v1 = self._calculate_vertex(
                    vppx, vppy, px, py, l2px, l2py,
                    event.distance, vp, l2, new_sp,
                )
                vp.next = new_v1
                l2.prev = new_v1
                added_vertexes.append(new_v1)

            if vn is not l1:
                pt = l1.c_point_at(event.distance)
                l1px = pt.x
                l1py = pt.y
                pt = vn.c_point_at(event.distance)
                vnpx = pt.x
                vnpy = pt.y
                new_v2 = self._calculate_vertex(
                    l1px, l1py, px, py, vnpx, vnpy,
                    event.distance, l1, vn, new_sp,
                )
                vn.prev = new_v2
                l1.next = new_v2
                added_vertexes.append(new_v2)

            # Remove merge events that solely concerned the now-split edge
            for e in self._events:
                if (isinstance(e, MergeEvent) and
                        (<MergeEvent>e).vertex1 in (l1, l2) and
                        (<MergeEvent>e).vertex2 in (l1, l2)):
                    removed_events.append(e)

        # Update vertex list
        self._vertexes = [v for v in self._vertexes if (<Vertex>v).active]
        for v in added_vertexes:
            self._vertexes.append(v)

        # Remove stale events
        removed_events.extend([e for e in self._events if not (<Event>e).active])
        cdef set removed_set = set(id(e) for e in removed_events)
        self._events = [e for e in self._events if id(e) not in removed_set]

        # Generate new events for newly added vertices
        min_d = event.distance + EPSILON
        for av in added_vertexes:
            new_events = []

            self._append_event(new_events, min_d,
                _calc_merge_event(av.prev, av))
            self._append_event(new_events, min_d,
                _calc_merge_event(av, av.next))

            for vertex in self._vertexes:
                if vertex in added_vertexes:
                    continue
                if av is not vertex.next:
                    self._append_event(new_events, min_d,
                        _calc_split_event(av, vertex, vertex.next, self._ccw))
                self._append_event(new_events, min_d,
                    _calc_split_event(vertex, av.prev, av, self._ccw))
                self._append_event(new_events, min_d,
                    _calc_split_event(vertex, av, av.next, self._ccw))

            self._events.extend(new_events)

        self._events.sort(key=lambda e: e.distance)

    cdef void _process_events(self, double distance, event_count):
        cdef int count = 0
        cdef int limit = -1
        cdef Event evt

        if event_count is not None:
            limit = int(event_count)

        self._events = [e for e in self._events if (<Event>e).distance >= 0.0]

        while self._events:
            evt = <Event>self._events[0]
            if evt.distance > distance:
                break
            self._events.pop(0)
            self._process_event(evt)
            count += 1
            if limit >= 0 and count >= limit:
                break

    cdef object _build_shape(self, double distance):
        cdef list lines = []
        cdef set seen = set()
        cdef Vertex vertex, v, vtx
        cdef StillPoint sp, npt
        cdef Vec2 p, p2

        for vertex in self._vertexes:
            if vertex in seen:
                continue
            seen.add(vertex)

            loop = [vertex]
            v = vertex.next
            while v is not None and v is not vertex:
                seen.add(v)
                loop.append(v)
                v = v.next

            if v is not None:
                loop.append(v)

            line_pts = []
            for vtx in loop:
                p = vtx.c_point_at(distance)
                line_pts.append((p.x, p.y))
            lines.append(line_pts)

        for vertex in self._vertexes:
            if vertex.still_point is None:
                continue
            p = vertex.c_point_at(distance)
            sp = vertex.still_point
            lines.append([(p.x, p.y), (sp.px, sp.py)])

        for sp in self._points:
            for npt in (sp.next_points or []):
                lines.append([(sp.px, sp.py), (npt.px, npt.py)])

        if len(lines) > 1:
            return s.MultiLineString(lines)
        elif lines:
            return s.LineString(lines[0])
        else:
            return s.LineString()


def offset_line(line, double distance):
    """Compute offset polygon using the straight skeleton algorithm."""
    skeleton = StraightSkeleton(s.LineString(line), distance)
    return skeleton.shape, skeleton
