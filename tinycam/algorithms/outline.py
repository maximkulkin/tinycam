#!/usr/bin/env python3
from collections.abc import Generator
import enum
from dataclasses import dataclass
from itertools import cycle, islice
from typing import Optional, override

import numpy as np
import shapely as s



EPSILON = 0.0001


type Point = np.ndarray[tuple[int, int], np.dtype[np.float32]]
type Vector = np.ndarray[tuple[int, int], np.dtype[np.float32]]


def _same_point(p1: Point, p2: Point) -> bool:
    v = p1 - p2
    return np.dot(v, v) < EPSILON


def _normalized(v: Vector) -> Vector:
    l = np.linalg.norm(v)
    if l == 0:
        return v
    return v / l


def _rotate90(v: Vector, ccw: bool=False):
    if ccw:
        return np.array([-v[1], v[0]])
    else:
        return np.array([v[1], -v[0]])


def _line_normal(p1: Point, p2: Point, ccw: bool=False) -> Vector:
    line = _normalized(np.array(p2) - np.array(p1))
    return _rotate90(line, ccw=ccw)


def _cross_product(v1: Vector, v2: Vector) -> float:
    return v1[0] * v2[1] - v1[1] * v2[0]


def _line_intersection(p1: Point, p2: Point, p3: Point, p4: Point) -> Point | None:
    n = _line_normal(p1, p2)
    d = np.dot(n, p3 - p1)
    if abs(d) < EPSILON:
        return p3

    step = np.dot(n, p4 - p3)
    if abs(step) < EPSILON:
        return None

    return p3 - (p4 - p3) * d / step


class StraightSkeleton:
    @dataclass
    class StillPoint:
        point: Point
        next_points: 'list[StraightSkeleton.StillPoint] | None' = None

        def __init__(
            self,
            point: Point,
            next_points: 'list[StraightSkeleton.StillPoint] | None' = None,
        ):
            self.point = point
            self.next_points = next_points or []

    @dataclass
    class Vertex:
        name: str
        point: Point
        direction: Vector
        offset: float = 0.0
        active: bool = True
        prev: 'StraightSkeleton.Vertex | None' = None
        next: 'StraightSkeleton.Vertex | None' = None
        is_reflex: bool = False
        still_point: 'StraightSkeleton.StillPoint | None' = None

        def __hash__(self) -> int:
            return id(self)

        def __eq__(self, other: object) -> bool:
            return id(self) == id(other)

        def __repr__(self) -> str:
            prev_name = 'None' if self.prev is None else self.prev.name
            next_name = 'None' if self.next is None else self.next.name
            return f'Vertex(name={self.name} point={self.point} direction={self.direction} offset={self.offset} prev={prev_name} next={next_name})'

        def point_at(self, offset: float) -> Point:
            return self.point + self.direction * (offset - self.offset)

    @dataclass(eq=True, frozen=True)
    class Event:
        distance: float

        @property
        def active(self) -> bool:
            return True

    @dataclass(eq=True, frozen=True)
    class MergeEvent(Event):
        vertex1: 'StraightSkeleton.Vertex'
        vertex2: 'StraightSkeleton.Vertex'

        @property
        def active(self) -> bool:
            return self.vertex1.active and self.vertex2.active

        def __repr__(self) -> str:
            point = self.vertex1.point_at(self.distance)
            return f'MergeEvent(distance={self.distance} point={point} vertex1={self.vertex1.name} vertex2={self.vertex2.name})'

    @dataclass(eq=True, frozen=True)
    class SplitEvent(Event):
        vertex: 'StraightSkeleton.Vertex'
        line_vertex1: 'StraightSkeleton.Vertex'
        line_vertex2: 'StraightSkeleton.Vertex'

        @property
        def active(self) -> bool:
            return self.vertex.active and self.line_vertex1.active and self.line_vertex2.active

        def __repr__(self) -> str:
            point = self.vertex.point_at(self.distance)
            return f'SplitEvent(distance={self.distance} point={point} vertex={self.vertex.name} line_point1={self.line_vertex1.name} line_point2={self.line_vertex2.name})'



    def __init__(self, shape: s.LineString, distance: float, event_count: int | None = None):
        super().__init__()
        self._log_enabled: bool = False
        self._vertex_next_index: int = 1
        self._ccw: bool = distance < 0
        self._distance: float = abs(distance)
        self._event_count: Optional[int] = event_count

        self._vertexes: list[StraightSkeleton.Vertex] = self._calculate_vertexes(shape)
        self._events: list[StraightSkeleton.Event] = self._calculate_events(self._vertexes)
        self._events.sort(key=lambda e: e.distance)
        self._points: list[StraightSkeleton.StillPoint] = []

        self._process_events(self._distance, event_count=self._event_count)

        self._shape = self._build_shape(self._distance)

    def _log(self, message: str):
        if not self._log_enabled:
            return

        print(message)
        print()

    @property
    def vertexes(self) -> list[Vertex]:
        return self._vertexes

    @property
    def events(self) -> list[Event]:
        return self._events

    @property
    def points(self) -> 'list[StraightSkeleton.StillPoint]':
        return self._points

    @property
    def shape(self) -> s.LineString | s.MultiLineString:
        return self._shape

    def _make_vertex(
        self,
        point: Point,
        direction: Vector,
        offset: float = 0.0,
        is_reflex: bool = False,
        prev: Vertex | None = None,
        next: Vertex | None = None,
        still_point: StillPoint | None = None,
    ) -> Vertex:
        idx = self._vertex_next_index
        self._vertex_next_index += 1
        name = str(idx)
        return self.Vertex(
            name=name,
            point=point,
            direction=direction,
            offset=offset,
            is_reflex=is_reflex,
            prev=prev,
            next=next,
            still_point=still_point,
        )

    def _calculate_vertex(
        self,
        p1: Point,
        p2: Point,
        p3: Point,
        offset: float = 0.0,
        prev: Vertex | None = None,
        next: Vertex | None = None,
        still_point: StillPoint | None = None,
    ) -> Vertex:
        pts = np.array([p1, p2, p3])
        v1 = _normalized(pts[1] - pts[0])
        v2 = _normalized(pts[2] - pts[1])
        n1 = _rotate90(v1)
        n2 = _rotate90(v2)
        v = (n1 + n2) / (1.0 + np.dot(n1, n2))
        is_reflex = _cross_product(v1, v2) > 0

        if self._ccw:
            v = -v
            is_reflex = not is_reflex

        return self._make_vertex(
            point=pts[1],
            direction=v,
            offset=offset,
            is_reflex=is_reflex,
            prev=prev,
            next=next,
            still_point=still_point,
        )

    def _calculate_vertexes(self, line: s.LineString | s.LinearRing) -> list[Vertex]:
        coords = line.coords
        if coords[0] == coords[-1]:
            coords = coords[:-1]

        vertexes = [
            self._calculate_vertex(np.array(p1), np.array(p2), np.array(p3))
            for p1, p2, p3 in zip(coords,
                                  islice(cycle(coords), 1, None),
                                  islice(cycle(coords), 2, None))
        ]

        for i, vertex in enumerate(vertexes):
            vertex.name = str(i)

        for i in range(1, len(vertexes) - 1):
            vertexes[i].prev = vertexes[i-1]
            vertexes[i].next = vertexes[i+1]
        vertexes[0].prev = vertexes[-1]
        vertexes[0].next = vertexes[1]
        vertexes[-1].prev = vertexes[-2]
        vertexes[-1].next = vertexes[0]

        return vertexes

    def vertex_loop(self, vertex: Vertex) -> Generator[Vertex, None, None]:
        yield vertex

        v = vertex.next
        while v is not None and v != vertex:
            yield v
            v = v.next

    def _calculate_merge_event(self, v1: Vertex, v2: Vertex) -> Event | None:
        self._log(f'calculating merge event v1 = {v1}, v2 = {v2}\n')
        offset = max([v1.offset, v2.offset])

        vp1 = v1.point_at(offset)
        vp2 = v2.point_at(offset)
        if np.allclose(vp1, vp2):
            self._log(f'too close')
            return None

        n = _rotate90(_normalized(v2.direction))
        d = np.dot(n, v1.direction)
        if abs(d) < EPSILON:
            self._log(f'parallel (d = {d})')
            return None

        l = np.dot(n, vp2 - vp1) / d
        if l <= 0.0:
            self._log(f'past it')
            return None

        self._log(f'creating merge event v1 = {v1}, v2 = {v2}, d = {offset + l}\n')
        return self.MergeEvent(
            distance=offset + l,
            vertex1=v1,
            vertex2=v2,
        )

    def _calculate_split_event(
        self,
        v: Vertex,
        line_vertex1: Vertex,
        line_vertex2: Vertex,
        log: bool = False,
    ) -> Event | None:
        if not v.is_reflex:
            if log:
                self._log('Vertex is not for reflex point')
            return None

        if line_vertex1 == v or line_vertex2 == v:
            if log:
                self._log('Vertex is one of lines')
            return None

        offset = max([v.offset, line_vertex1.offset, line_vertex2.offset])

        vp = v.point_at(offset)
        p1 = line_vertex1.point_at(offset)
        p2 = line_vertex2.point_at(offset)

        if log:
            self._log(f'offset = {offset}, vp={vp}, p1={p1}, p2={p2}')

        n = _line_normal(p1, p2)
        if self._ccw:
            n = -n
        dn = -np.dot(v.direction, n)  # minus because of supposedly opposite directions of vertex bisector and normal
        if log:
            self._log(f'n = {n}, dn = {dn}')
        if dn <= 0:
            if log:
                self._log(f'dn = {dn}, <= 0, exiting')
            return None

        d = np.dot(n, vp - p1) / (1 + dn)  # 1 is for line speed moving along its normal

        if log:
            self._log(f'd = {d}')

        p11 = p1 + line_vertex1.direction * d
        p21 = p2 + line_vertex2.direction * d

        vline = p21 - p11
        line_length_squared = np.dot(vline, vline)

        intersection = vp + v.direction * d

        if log:
            self._log(f'intersection = {intersection}, p11 = {p11}, p21 = {p21}')

        l2 = np.dot(vline, intersection - p11)
        if l2 < 0 or l2 > line_length_squared:
            if log:
                self._log(f'l2 = {l2}, exiting')
            return None

        self._log(f'creating split event v = {v}, l1 = {line_vertex1}, l2 = {line_vertex2}, d = {offset + d}\n')
        return self.SplitEvent(
            distance=offset + d,
            vertex=v,
            line_vertex1=line_vertex1,
            line_vertex2=line_vertex2,
        )

    def _calculate_events(self, vertexes: list[Vertex]) -> list[Event]:
        unique_events = set()

        merge_distances = dict()

        for v1 in vertexes:
            # Check for merge events
            v2 = v1.next
            assert(v2 is not None)

            event = self._calculate_merge_event(v1, v2)
            if event is not None:
                unique_events.add(event)
                # if b1 not in merge_distances or merge_distances[b1] > event.distance:
                #     merge_distances[b1] = event.distance
                # if b2 not in merge_distances or merge_distances[b2] > event.distance:
                #     merge_distances[b2] = event.distance

        for v1 in vertexes:
            # Check for split events
            self._log(f'Considering split events for vertex {v1}')

            seen = set()
            for vertex in vertexes:
                self._log(f'Considering line starting at {vertex}')
                if vertex in seen:
                    self._log(f'Already seen {vertex}')
                    continue

                for line_vertex1 in self.vertex_loop(vertex):
                    line_vertex2 = line_vertex1.next
                    assert(line_vertex2 is not None)

                    if line_vertex1 is v1 or line_vertex2 is v1:
                        continue

                    seen.add(line_vertex1)

                    self._log(f'Considering split between {v1} and line {line_vertex1} and {line_vertex1}')

                    event = self._calculate_split_event(v1, line_vertex1, line_vertex2)
                    if event is None:
                        continue

                    unique_events.add(event)

        return sorted(list(unique_events), key=lambda e: e.distance)

    def append_event(
                     self,
                     events: 'list[StraightSkeleton.Event]',
                     min_distance: float,
                     event: 'StraightSkeleton.Event | None'):
        if event is None:
            return
        if event.distance < min_distance:
            return
        events.append(event)

    def _process_event(self, event: 'StraightSkeleton.Event'):
        added_vertexes: list['StraightSkeleton.Vertex'] = []
        removed_events: list['StraightSkeleton.Event'] = []

        match event:
            case self.MergeEvent():
                self._log(f'Processing merge event: {event}')

                v1 = event.vertex1
                v2 = event.vertex2

                p = v1.point_at(event.distance)
                next_points = []
                if v1.still_point is not None:
                    next_points.append(v1.still_point)
                if v2.still_point is not None:
                    next_points.append(v2.still_point)
                new_still_point = StraightSkeleton.StillPoint(
                    p, next_points=next_points,
                )
                self._points.append(new_still_point)
                self._log(f'Adding still point {self._points[-1]}')

                if v1.prev == v2.next:
                    assert(v2.next is not None)

                    # It collapsed to a line, there is not point in continuing
                    self._points.append(StraightSkeleton.StillPoint(
                        v2.next.point_at(event.distance),
                        next_points=[new_still_point],
                    ))
                    self._log(f'Adding still point {self._points[-1]}')

                    v2.next.active = False
                else:
                    new_v = self._make_vertex(
                        point=p,
                        direction=v1.direction + v2.direction,
                        offset=event.distance,
                        prev=v1.prev,
                        next=v2.next,
                        still_point=new_still_point,
                    )
                    assert(new_v.prev is not None)
                    assert(new_v.next is not None)
                    new_v.prev.next = new_v
                    new_v.next.prev = new_v

                    added_vertexes.append(new_v)

                v1.active = False
                v2.active = False

            case self.SplitEvent():
                self._log(f'Processing split event: {event}')

                v = event.vertex
                l1 = event.line_vertex1
                l2 = event.line_vertex2
                vp = v.prev
                vn = v.next
                assert(l1 is not None)
                assert(l2 is not None)
                assert(vp is not None)
                assert(vn is not None)

                p = v.point_at(event.distance)
                next_points = []
                if v.still_point is not None:
                    next_points.append(v.still_point)

                # if bp == l2:
                #     l2_still_point = StraightSkeleton.StillPoint(
                #         l2.point_at(event.distance),
                #         next_points=[l2.still_point] if l2.still_point is not None else [],
                #     )
                #     if True or not _same_point(l2_still_point.point, p):
                #         self._points.append(l2_still_point)
                #         next_points.append(l2_still_point)
                #         self._log(f'Adding still point {self._points[-1]}')
                #     l2.active = False

                # if bn == l1:
                #     l1_still_point = StraightSkeleton.StillPoint(
                #         l1.point_at(event.distance),
                #         next_points=[l1.still_point] if l1.still_point is not None else [],
                #     )
                #     if True or not _same_point(l1_still_point.point, p):
                #         self._points.append(l1_still_point)
                #         next_points.append(l1_still_point)
                #         self._log(f'Adding still point {self._points[-1]}')
                #     l1.active = False

                new_still_point = StraightSkeleton.StillPoint(
                    p, next_points=next_points,
                )
                self._points.append(new_still_point)
                self._log(f'Adding still point {self._points[-1]}')

                v.active = False

                if vp != l2:
                    new_v1 = self._calculate_vertex(
                        vp.point + vp.direction * (event.distance - vp.offset),
                        p,
                        l2.point + l2.direction * (event.distance - l2.offset),
                        offset=event.distance,
                        prev=vp,
                        next=l2,
                        still_point=new_still_point,
                    )
                    vp.next = new_v1
                    l2.prev = new_v1
                    added_vertexes.append(new_v1)

                if vn != l1:
                    new_v2 = self._calculate_vertex(
                        l1.point + l1.direction * (event.distance - l1.offset),
                        p,
                        vn.point + vn.direction * (event.distance - vn.offset),
                        offset=event.distance,
                        prev=l1,
                        next=vn,
                        still_point=new_still_point,
                    )
                    vn.prev = new_v2
                    l1.next = new_v2
                    added_vertexes.append(new_v2)

                removed_events.extend([
                    event
                    for event in self._events
                    if (isinstance(event, self.MergeEvent) and
                        event.vertex1 in [l1, l2] and
                        event.vertex2 in [l1, l2])
                ])

        self._vertexes = [
            v
            for v in self._vertexes
            if v.active
        ]

        for v in added_vertexes:
            self._log(f'Adding vertex {v}')
            self._vertexes.append(v)

        removed_events.extend([
            event
            for event in self._events
            if not event.active
        ])
        for e in removed_events:
            self._log(f'Removing event {e}')

        self._events = [
            event
            for event in self._events
            if event.active
        ]
        self._log(f'Remaining event count: {len(self._events)}')

        for added_vertex in added_vertexes:
            assert(added_vertex.prev is not None)
            assert(added_vertex.next is not None)
            self._log(f'Processing added vertex {added_vertex}')

            new_events: list['StraightSkeleton.Event'] = []

            self.append_event(
                new_events, event.distance + EPSILON,
                self._calculate_merge_event(added_vertex.prev, added_vertex),
            )
            self.append_event(
                new_events, event.distance + EPSILON,
                self._calculate_merge_event(added_vertex, added_vertex.next),
            )

            for vertex in self._vertexes:
                # if vertex in added_vertexes or vertex.next in added_vertexes:
                if vertex in added_vertexes:
                    continue

                assert(vertex.next is not None)
                # Check if new vertex intersects any existing line
                if added_vertex != vertex.next:
                    self.append_event(
                        new_events, event.distance + EPSILON,
                        self._calculate_split_event(added_vertex, vertex, vertex.next),
                    )

                # Check if existing vertex bisector intersects line formed by added vertex
                self.append_event(
                    new_events, event.distance + EPSILON,
                    self._calculate_split_event(vertex, added_vertex.prev, added_vertex),
                )
                self.append_event(
                    new_events, event.distance + EPSILON,
                    self._calculate_split_event(vertex, added_vertex, added_vertex.next),
                )

            self._log(f'Generated {len(new_events)} new events')
            self._events.extend(new_events)

        self._log(f'Remaining event count {len(self._events)}')
        self._events.sort(key=lambda event: event.distance)
        self._log(f'Events: {self._events}')


    def _process_events(self, distance: float, event_count: int | None = None):
        self._log(f"Processing events up to distance: {distance}")
        self._events = [event for event in self._events if event.distance >= 0.0]

        count = 0
        while self._events and self._events[0].distance <= distance:
            event = self._events.pop(0)
            self._log(f"Processing event: {event}")
            self._process_event(event)

            count += 1
            if event_count is not None and count >= event_count:
                break

        self._log(f"Processed {count} events")

    def _build_shape(
        self,
        distance: float,
    ) -> s.LineString | s.MultiLineString:
        lines = []
        seen = set()
        for vertex in self._vertexes:
            if vertex in seen:
                continue

            seen.add(vertex)

            l = [vertex]
            v = vertex.next
            while v is not None and v != vertex:
                seen.add(v)
                l.append(v)
                v = v.next

            if v is not None:
                l.append(v)

            lines.append([
                v.point_at(distance)
                for v in l
            ])

        for vertex in self._vertexes:
            if vertex.still_point is None:
                continue

            lines.append([vertex.point_at(distance), vertex.still_point.point])

        for still_point in self._points:
            for next_point in (still_point.next_points or []):
                lines.append([still_point.point, next_point.point])

        return s.MultiLineString(lines) if len(lines) > 1 else s.LineString(lines[0])


def offset_line(line, distance: float) -> tuple[s.Geometry, StraightSkeleton]:
    skeleton = StraightSkeleton(s.LineString(line), distance)
    return skeleton.shape, skeleton


if __name__ == '__main__':
    v1 = StraightSkeleton.Vertex(name='0', point=np.array([300, 200]), direction=np.array([-1.118, 0]))
    v2 = StraightSkeleton.Vertex(name='1', point=np.array([150, 100]), direction=np.array([0, 2.236]))
    v3 = StraightSkeleton.Vertex(name='2', point=np.array([200, 200]), direction=np.array([0, 2.236]))

    skeleton = StraightSkeleton(s.LineString([v1.point, v2.point, v3.point]), 0.0)
    split_event = skeleton._calculate_split_event(v1, v2, v3, log=True)
