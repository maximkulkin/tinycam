import shapely
import shapely.affinity
from shapely.geometry.base import BaseGeometry as Shape

class Shape:
    def __init__(self, data):
        self._data = data

    @property
    def points(self):
        return self._data.coords

    @property
    def bounds(self):
        return shapely.total_bounds(self._data)

    def contains(self, point):
        return shapely.contains_xy(self._data, point[0], point[1])


class Geometry:
    def __init__(self):
        pass

    # geometry

    def line(self, points, width=0.0):
        line = shapely.LineString(points)
        if width > 0:
            line = line.buffer(width/2)
        return line

    def arc(self, center, radius, start_angle, end_angle, angle_step=1.0, width=0.0):
        angle = start_angle
        ccw = angle_step < 0

        points = []
        while (angle > end_angle if ccw else angle < end_angle):
            points.append((center[0] + math.cos(angle)*radius,
                           center[1] + math.sin(angle)*radius))
            angle += angle_step

        if angle != end_angle:
            points.append((math.cos(end_angle)*radius, math.sin(end_angle)*radius))

        arc = shapely.LineString(points)
        if width > 0:
            arc = arc.buffer(width/2)
        return arc

    def circle(self, diameter, center=(0, 0)):
        return shapely.Point(center).buffer(diameter/2)

    def box(self, pmin, pmax):
        return shapely.box(pmin[0], pmin[1], pmax[0], pmax[1])

    def polygon(self, points):
        return shapely.Polygon(points)

    # utils

    def points(self, shape):
        return shape.coords

    def bounds(self, *shapes):
        return shapely.total_bounds(shapes)

    def lines(self, shape):
        if isinstance(shape, shapely.LineString):
            return [shape]
        elif isinstance(shape, shapely.MultiLineString):
            return shape.geoms

        raise ValueError('Geometry is not a line: %s' % shape.__class__)

    def polygons(self, shape):
        if isinstance(shape, shapely.Polygon):
            return [shape]
        elif isinstance(shape, shapely.MultiPolygon):
            return shape.geoms

        raise ValueError('Geometry is not a polygon: %s' % shape.__class__)

    def exteriors(self, shape):
        if isinstance(shape, shapely.Polygon):
            return [shape.exterior]
        elif isinstance(shape, shapely.MultiPolygon):
            return [
                geom.exterior
                for geom in shape.geoms
                if isinstance(geom, shapely.Polygon)
            ]

        return []

    def interiors(self, shape):
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

    def contains(self, shape, point):
        return shapely.contains_xy(shape, point[0], point[1])

    # boolean operations

    def union(self, *shapes):
        return shapely.union_all([shape for shape in shapes if shape is not None])

    def intersection(self, *shapes):
        return shapely.intersection_all([shape for shape in shapes if shape is not None])

    def difference(self, shape_a, *shapes):
        return reduce(lambda a, b: shapely.difference(a._data, b._data),
                      shapes, shape_a)

    # transforms

    def translate(self, shape, offset):
        if len(offset) < 3:
            offset = (offset[0], offset[1], 0)
        return shapely.affinity.translate(shape, offset[0], offset[1], offset[2])

    def rotate(self, shape, angle, origin=(0, 0)):
        """Rotate shape around origin by given angle in degrees counterclockwise."""
        return shapely.affinity.rotate(shape, angle, origin)

    def scale(self, shape, factor):
        """Scale shape by given factor."""
        if isinstance(factor, (int, float)):
            factor = (factor, factor, factor)
        elif len(factor) == 2:
            factor = (factor[0], factor[1], 1)
        return shapely.affinity.scale(shape, factor[0], factor[1], factor[2])

    def buffer(self, shape, offset):
        return shape.buffer(offset)

    def simplify(self, shape, tolerance=0.01):
        return shapely.simplify(shape, tolerance)
