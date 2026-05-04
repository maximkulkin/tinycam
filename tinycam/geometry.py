import math
from collections.abc import Sequence
from functools import reduce
from itertools import chain
from typing import overload

import numpy as np
import shapely.affinity
import shapely.ops
import shapely
from shapely.geometry.base import BaseGeometry as Shape

from tinycam.math_types import Vector2, Vector3, Quaternion, Rect, Matrix33


type number = int | float

Point = shapely.Point
Line = shapely.LineString
Ring = shapely.LinearRing
MultiLineString = shapely.MultiLineString
Polygon = shapely.Polygon
MultiPolygon = shapely.MultiPolygon
Group = shapely.GeometryCollection

type PointLike = Point | Vector2 | Vector3
type AnyShape = Shape | Point | Line | Polygon | Group | MultiLineString | MultiPolygon


# class Shape_:
#     def __init__(self, data):
#         self._data = data
#
#     @property
#     def points(self):
#         return self._data.coords
#
#     @property
#     def bounds(self):
#         return shapely.total_bounds(self._data)
#
#     def contains(self, point: PointLike):
#         return shapely.contains_xy(self._data, point[0], point[1])


def get_x(point: PointLike) -> float:
    if isinstance(point, shapely.Point):
        return point.x
    return point[0]


def get_y(point: PointLike) -> float:
    if isinstance(point, shapely.Point):
        return point.y
    return point[1]


class Geometry:
    def __init__(self):
        pass

    # geometry
    @overload
    def line(self, points: Sequence[PointLike] | np.ndarray, closed: bool = False) -> Line | Ring:
        ...

    @overload
    def line(self, points: Sequence[PointLike] | np.ndarray, closed: bool = False, width: number = 0.0) -> Polygon:
        ...

    def line(self, points: Sequence[PointLike] | np.ndarray, closed: bool = False, width: number = 0.0):
        if closed:
            line = shapely.LinearRing(points)
        else:
            line = shapely.LineString(points)

        if width > 0:
            line = line.buffer(width / 2)
        return line

    @overload
    def arc(
        self,
        center: PointLike,
        radius: number,
        start_angle: number,
        end_angle: number,
        *,
        angle_step: number = 1.0,
    ) -> Line:
        ...

    @overload
    def arc(
        self,
        center: PointLike,
        radius: number,
        start_angle: number,
        end_angle: number,
        *,
        width: number,
        angle_step: number = 1.0,
    ) -> Polygon:
        ...

    def arc(
        self,
        center: PointLike,
        radius: number,
        start_angle: number,
        end_angle: number,
        angle_step: number = 1.0,
        width: number = 0.0,
    ):
        angle = start_angle
        ccw = angle_step < 0

        points = []
        while (angle > end_angle if ccw else angle < end_angle):
            points.append((get_x(center) + math.cos(angle) * radius,
                           get_y(center) + math.sin(angle) * radius))
            angle += angle_step

        if angle != end_angle:
            points.append((math.cos(end_angle) * radius, math.sin(end_angle) * radius))

        arc = shapely.LineString(points)
        if width > 0:
            arc = arc.buffer(width / 2)
        return arc

    def circle(self, diameter: number, center: PointLike = Vector2(0, 0)) -> Polygon:
        return shapely.Point(center).buffer(diameter / 2)

    def box(self, pmin: PointLike, pmax: PointLike) -> Polygon:
        return shapely.box(get_x(pmin), get_y(pmin), get_x(pmax), get_y(pmax))

    def polygon(self, points: Sequence[PointLike] | np.ndarray) -> Polygon:
        return shapely.Polygon(points)

    # utils

    def bounds(self, *shapes: tuple[AnyShape, ...]) -> Rect:
        xmin, ymin, xmax, ymax = shapely.total_bounds(shapes)
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)

    def points(self, shape: AnyShape) -> Sequence[Vector2]:
        match shape:
            case shapely.MultiLineString() | shapely.MultiPolygon() | shapely.GeometryCollection():
                return chain(*[
                    self.points(geom)
                    for geom in shape.geoms
                ])
            case shapely.Polygon():
                return chain(*[
                    self.points(geom)
                    for geom in chain([shape.exterior], shape.interiors)
                ])
            case shapely.LineString() | shapely.LinearRing():
                return [
                    Vector2(coord[0], coord[1])
                    for coord in shape.coords
                ]
            case _:
                raise ValueError(f'Unknown shape: {shape}')

    def lines(self, shape: AnyShape) -> list[Line]:
        if isinstance(shape, shapely.LineString):
            return [shape]
        elif isinstance(shape, shapely.MultiLineString):
            return shape.geoms

        raise ValueError('Geometry is not a line: %s' % shape.__class__)

    def polygons(self, shape: Polygon | MultiPolygon) -> list[Polygon]:
        if isinstance(shape, shapely.Polygon):
            return [shape]
        elif isinstance(shape, shapely.MultiPolygon):
            return shape.geoms
        elif isinstance(shape, shapely.GeometryCollection):
            return [
                self.polygons(geom)
                for geom in shape.geoms
            ]

        raise ValueError('Geometry is not a polygon: %s' % shape.__class__)

    def shapes(self, shape: AnyShape) -> list[Shape]:
        if isinstance(shape, shapely.GeometryCollection):
            return shape.geoms
        elif isinstance(shape, shapely.MultiLineString):
            return shape.geoms
        elif isinstance(shape, shapely.MultiPolygon):
            return shape.geoms
        else:
            return [shape]

    def exteriors(self, shape: AnyShape) -> list[Line]:
        if isinstance(shape, shapely.Polygon):
            return [shape.exterior]
        elif isinstance(shape, shapely.MultiPolygon):
            return [
                geom.exterior
                for geom in shape.geoms
                if isinstance(geom, shapely.Polygon)
            ]

        return []

    def interiors(self, shape: AnyShape) -> list[Line]:
        if isinstance(shape, shapely.Polygon):
            return shape.interiors
        elif isinstance(shape, shapely.MultiPolygon):
            return [
                interior
                for geom in shape.geoms
                if isinstance(geom, shapely.Polygon)
                for interior in geom.interiors
            ]
        return []

    def contains(self, shape: AnyShape, point: PointLike) -> bool:
        return shapely.contains_xy(shape, get_x(point), get_y(point))

    def intersects(self, shape1: AnyShape, shape2: AnyShape) -> bool:
        return shapely.intersects(shape1, shape2)

    # boolean operations

    def group(self, *shapes: list[AnyShape]) -> Group:
        return shapely.GeometryCollection(shapes)

    def union(self, *shapes: list[AnyShape]) -> Shape:
        return shapely.union_all([shape for shape in shapes if shape is not None])

    def intersection(self, *shapes: list[AnyShape]) -> Shape:
        return shapely.intersection_all([shape for shape in shapes if shape is not None])

    def difference(self, shape_a: AnyShape, *shapes: list[AnyShape]):
        return reduce(lambda a, b: shapely.difference(a._data, b._data),
                      shapes, shape_a)

    # transforms

    def translate[T: AnyShape](self, shape: T, offset: Vector2 | Vector3) -> T:
        if len(offset) < 3:
            offset = Vector3(offset[0], offset[1], 0)
        return shapely.affinity.translate(shape, offset[0], offset[1], offset[2])

    def rotate[T: AnyShape](self, shape: T, angle: number, origin: PointLike = Vector2(0, 0)) -> T:
        """Rotate shape around origin by given angle in degrees counterclockwise."""
        return shapely.affinity.rotate(shape, angle, shapely.Point(origin))

    def scale[T: AnyShape](self, shape: T, factor: number | Vector2 | Vector3,
                           origin: PointLike = Vector2(0, 0)) -> T:
        """Scale shape by given factor."""
        if isinstance(factor, (int, float)):
            factor = Vector3(factor, factor, factor)
        elif len(factor) == 2:
            factor = Vector3(factor[0], factor[1], 1)
        return shapely.affinity.scale(
            shape,
            xfact=factor[0],
            yfact=factor[1],
            zfact=factor[2],
            origin=(get_x(origin), get_y(origin)),
        )

    def transform[T: AnyShape](self, shape: T, matrix: Matrix33) -> T:
        (a, b, xoff), (d, e, yoff), _ = matrix
        return shapely.affinity.affine_transform(shape, (a, b, d, e, xoff, yoff))

    def buffer(self, shape: AnyShape, offset: number) -> Polygon:
        return shape.buffer(offset)

    def simplify[T: AnyShape](self, shape: T, tolerance: number = 0.01) -> T:
        return shapely.simplify(shape, tolerance)

    def nearest(self, from_shape: AnyShape, to_shape: AnyShape) -> Point:
        _, point_b = shapely.ops.nearest_points(from_shape, to_shape)
        return point_b

    # type predicates

    def is_empty(self, shape: AnyShape) -> bool:
        return shape.is_empty

    def is_filled(self, shape: AnyShape) -> bool:
        """True when the shape contains at least one non-empty polygon."""
        if isinstance(shape, (shapely.Polygon, shapely.MultiPolygon)):
            return not shape.is_empty
        if isinstance(shape, shapely.GeometryCollection):
            return any(self.is_filled(g) for g in shape.geoms)
        return False

    def is_ring(self, shape: AnyShape) -> bool:
        return isinstance(shape, shapely.LinearRing)

    def is_line(self, shape: AnyShape) -> bool:
        """True for LineString only (not LinearRing, which is a LineString subclass)."""
        return isinstance(shape, shapely.LineString) and not isinstance(shape, shapely.LinearRing)

    def is_polygon(self, shape: AnyShape) -> bool:
        return isinstance(shape, shapely.Polygon)

    def is_collection(self, shape: AnyShape) -> bool:
        return isinstance(shape, (shapely.MultiLineString, shapely.MultiPolygon,
                                   shapely.GeometryCollection))

    def is_closed(self, shape: AnyShape) -> bool:
        return shape.is_closed

    def coords(self, shape: AnyShape) -> list[tuple[float, float]]:
        """Return the raw coordinate sequence of a Line or Ring as plain tuples."""
        return list(shape.coords)

    def to_wkt(self, shape: AnyShape) -> str:
        return shapely.to_wkt(shape)

    def from_wkt(self, wkt: str) -> AnyShape:
        return shapely.from_wkt(wkt)

    def total_bounds(self, shapes: list[AnyShape]) -> tuple[float, float, float, float]:
        """Return (xmin, ymin, xmax, ymax) bounding box over a list of shapes."""
        xmin, ymin, xmax, ymax = shapely.total_bounds(shapes)
        return xmin, ymin, xmax, ymax

    def symmetric_difference(self, shape1: AnyShape, shape2: AnyShape) -> Shape:
        return shapely.symmetric_difference(shape1, shape2)

    def symmetric_difference_all(self, shapes: list[AnyShape]) -> Shape:
        """XOR all shapes together (used to apply the SVG evenodd fill rule)."""
        result = shapely.Polygon()
        for shape in shapes:
            result = shapely.symmetric_difference(result, shape)
        return result

    def triangulate(self, polygon: Polygon, max_segment_length: float = 1.0) -> list[list[tuple]]:
        """Tessellate a polygon into triangles for rendering.

        Returns a list of triangles, each a list of three (x, y) coordinate tuples.
        """
        shapely.prepare(polygon)
        result = [
            list(triangle.exterior.coords[:-1])
            for triangle in shapely.delaunay_triangles(
                polygon.segmentize(max_segment_length)
            ).geoms
            if polygon.contains(triangle.centroid)
        ]
        shapely.destroy_prepared(polygon)
        return result

    def to_wkt(self, shape: AnyShape) -> str:
        return shapely.to_wkt(shape)

    def from_wkt(self, wkt: str) -> AnyShape:
        return shapely.from_wkt(wkt)
