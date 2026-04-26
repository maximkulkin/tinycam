import math
import re
import xml.etree.ElementTree as ET

from tinycam.geometry import Geometry, Shape
from tinycam.types import Vector2, Matrix33


def loads(string: str) -> list[Shape]:
    parser = SvgParser()
    return parser.parse(string)


def load(filename: str) -> list[Shape]:
    with open(filename, 'r') as f:
        return loads(f.read())


def _quadratic_bezier_adaptive(p0: Vector2, p1: Vector2, p2: Vector2, tol_sq: float, out: list) -> None:
    d = p2 - p0
    d_sq = float(d[0]*d[0] + d[1]*d[1])
    if d_sq > 1e-10:
        c = p1 - p0
        cross = float(c[0]*d[1] - c[1]*d[0])
        if cross * cross > tol_sq * d_sq:
            p01  = (p0 + p1)  * 0.5
            p12  = (p1 + p2)  * 0.5
            p012 = (p01 + p12) * 0.5
            _quadratic_bezier_adaptive(p0, p01, p012, tol_sq, out)
            _quadratic_bezier_adaptive(p012, p12, p2, tol_sq, out)
            return
    out.append(p2)


def quadratic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, tolerance: float = 0.5) -> list[Vector2]:
    out: list[Vector2] = []
    _quadratic_bezier_adaptive(p0, p1, p2, tolerance * tolerance, out)
    return out


def _cubic_bezier_adaptive(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, tol_sq: float, out: list) -> None:
    d = p3 - p0
    d_sq = float(d[0]*d[0] + d[1]*d[1])
    if d_sq > 1e-10:
        c1 = p1 - p0
        c2 = p2 - p0
        cross1 = float(c1[0]*d[1] - c1[1]*d[0])
        cross2 = float(c2[0]*d[1] - c2[1]*d[0])
        if max(cross1 * cross1, cross2 * cross2) > tol_sq * d_sq:
            p01   = (p0 + p1)   * 0.5
            p12   = (p1 + p2)   * 0.5
            p23   = (p2 + p3)   * 0.5
            p012  = (p01 + p12) * 0.5
            p123  = (p12 + p23) * 0.5
            p0123 = (p012 + p123) * 0.5
            _cubic_bezier_adaptive(p0, p01, p012, p0123, tol_sq, out)
            _cubic_bezier_adaptive(p0123, p123, p23, p3, tol_sq, out)
            return
    out.append(p3)


def cubic_bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, tolerance: float = 0.5) -> list[Vector2]:
    out: list[Vector2] = []
    _cubic_bezier_adaptive(p0, p1, p2, p3, tolerance * tolerance, out)
    return out


def elliptical_arc(p1: Vector2, p2: Vector2, rx: float, ry: float, angle: float, large_arc: bool, cw: bool) -> list[Vector2]:
    # TODO: implement elliptical arc
    return [p2]


class SvgParser:
    def __init__(self):
        self.geo = Geometry()

    def parse(self, string: str) -> list[Shape]:
        root = ET.fromstring(string)
        return self._process_children(root)

    def _apply_transform(self, shape, transform: Matrix33):
        return self.geo.transform(shape, transform)

    def _parse_transform(self, transform_str: str) -> Matrix33:
        matrix = Matrix33.identity()

        transforms = re.findall(r'(\w+)\(([^)]+)\)', transform_str)
        for name, args_str in transforms:
            args = self._parse_floats(args_str)
            if name == 'translate':
                matrix = Matrix33.from_translation(Vector2(args[0], args[1])) * matrix
            elif name == 'scale':
                matrix = Matrix33.from_scale(Vector2(args[0], args[1])) * matrix
            elif name == 'rotate':
                m = Matrix33.from_z_rotation(args[0])
                if len(args) > 1:
                    m = Matrix33.transform_around_origin(m, Vector2(args[1], args[2]))
                matrix = m * matrix
        return matrix

    def _process_children(self, root: ET.Element) -> list[Shape]:
        shapes = []
        for elem in root.iter():
            tag = elem.tag.split('}')[-1]
            if hasattr(self, f'_process_element_{tag}'):
                new_shapes = getattr(self, f'_process_element_{tag}')(elem)
                if new_shapes:
                    transform_str = elem.attrib.get('transform')
                    if transform_str:
                        transform = self._parse_transform(transform_str)
                        new_shapes = [
                            self._apply_transform(shape, transform)
                            for shape in new_shapes
                        ]
                    shapes.extend(new_shapes)

        return shapes

    def _parse_floats(self, s: str) -> list[float]:
        return [
            float(c)
            for c in re.split(r'[\s]+|,|(?=-)', s.strip())
            if c
        ]

    def _process_g(self, elem: ET.Element) -> list[Shape]:
        return self._process_children(elem)

    def _process_element_rect(self, elem: ET.Element) -> list[Shape]:
        x = float(elem.attrib.get('x', 0))
        y = float(elem.attrib.get('y', 0))
        width = float(elem.attrib.get('width', 0))
        height = float(elem.attrib.get('height', 0))
        return [self.geo.box(Vector2(x, y), Vector2(x + width, y + height))]

    def _process_element_circle(self, elem: ET.Element) -> list[Shape]:
        cx = float(elem.attrib.get('cx', 0))
        cy = float(elem.attrib.get('cy', 0))
        r = float(elem.attrib.get('r', 0))
        return [self.geo.circle(r * 2, center=Vector2(cx, cy))]

    def _process_element_polygon(self, elem: ET.Element) -> list[Shape]:
        points_str = elem.attrib.get('points', '')
        points = [Vector2(list(map(float, p.split(',', 2)))) for p in points_str.split()]
        return [self.geo.polygon(points)]

    def _process_element_polyline(self, elem: ET.Element) -> list[Shape]:
        points_str = elem.attrib.get('points', '')
        points = [Vector2(list(map(float, p.split(',', 2)))) for p in points_str.split()]
        return [self.geo.line(points)]

    def _process_element_path(self, elem: ET.Element) -> list[Shape]:
        d = elem.attrib.get('d', '')

        lines = []
        points = []
        current_point = Vector2(0, 0)
        last_smooth_quadratic_bezier_control_point = None
        last_smooth_cubic_bezier_control_point = None

        commands = re.findall(r'([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)', d)

        for cmd, values in commands:
            coords = self._parse_floats(values)
            match cmd:
                case 'M':
                    if len(points) > 1:
                        lines.append(self.geo.line(points))
                        points = []

                    current_point = Vector2(coords[0], coords[1])
                    points.append(current_point)
                    for i in range(2, len(coords), 2):
                        points.append(Vector2(coords[i], coords[i+1]))
                        current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'm':
                    if len(points) > 1:
                        lines.append(self.geo.line(points))
                        points = []

                    current_point += Vector2(coords[0], coords[1])
                    points.append(current_point)
                    for i in range(2, len(coords), 2):
                        points.append(Vector2(coords[i], coords[i+1]))
                        current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'L':
                    for i in range(0, len(coords), 2):
                        points.append(Vector2(coords[i], coords[i+1]))
                    current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'l':
                    for i in range(0, len(coords), 2):
                        current_point += Vector2(coords[i], coords[i+1])
                        points.append(current_point)

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'H':
                    for x in coords:
                        current_point = Vector2(x, current_point.y)
                        points.append(current_point)

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'h':
                    for dx in coords:
                        current_point += Vector2(dx, 0)
                        points.append(current_point)

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'V':
                    for y in coords:
                        current_point = Vector2(current_point.x, y)
                        points.append(current_point)

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'v':
                    for dy in coords:
                        current_point += Vector2(0, dy)
                        points.append(current_point)

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'C':
                    # TODO: validate that number of coordinates is exactly 6
                    for i in range(0, len(coords), 6):
                        p1 = Vector2(coords[i], coords[i+1])
                        p2 = Vector2(coords[i+2], coords[i+3])
                        point = Vector2(coords[i+4], coords[i+5])
                        points.extend(cubic_bezier(current_point, p1, p2, point))
                        current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'c':
                    # TODO: validate that number of coordinates is exactly 6
                    for i in range(0, len(coords), 6):
                        p1 = current_point + Vector2(coords[i+0], coords[i+1])
                        p2 = current_point + Vector2(coords[i+2], coords[i+3])
                        point = current_point + Vector2(coords[i+4], coords[i+5])
                        points.extend(cubic_bezier(current_point, p1, p2, point))
                        current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'S':
                    for i in range(0, len(coords), 4):
                        p1 = current_point
                        if last_smooth_cubic_bezier_control_point is not None:
                            p1 = 2 * current_point - last_smooth_cubic_bezier_control_point

                        p2 = Vector2(coords[i+0], coords[i+1])
                        point = Vector2(coords[i+2], coords[i+3])
                        points.extend(cubic_bezier(current_point, p1, p2, point))

                        current_point = points[-1]
                        last_smooth_quadratic_bezier_control_point = None
                        last_smooth_cubic_bezier_control_point = p2

                    last_smooth_quadratic_bezier_control_point = None

                case 's':
                    for i in range(0, len(coords), 4):
                        p1 = current_point
                        if last_smooth_cubic_bezier_control_point is not None:
                            p1 = 2 * current_point - last_smooth_cubic_bezier_control_point

                        p2 = current_point + Vector2(coords[i+0], coords[i+1])
                        point = current_point + Vector2(coords[i+2], coords[i+3])
                        points.extend(cubic_bezier(current_point, p1, p2, point))

                        current_point = points[-1]
                        last_smooth_quadratic_bezier_control_point = None
                        last_smooth_cubic_bezier_control_point = p2

                    last_smooth_quadratic_bezier_control_point = None

                case 'Q':
                    for i in range(0, len(coords), 4):
                        p1 = Vector2(coords[i+0], coords[i+1])
                        point = Vector2(coords[i+2], coords[i+3])
                        points.extend(quadratic_bezier(current_point, p1, point))
                        current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'q':
                    for i in range(0, len(coords), 4):
                        p1 = current_point + Vector2(coords[i+0], coords[i+1])
                        point = current_point + Vector2(coords[i+2], coords[i+3])
                        points.extend(quadratic_bezier(current_point, p1, point))
                        current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'T':
                    for i in range(0, len(coords), 2):
                        p1 = current_point
                        if last_smooth_quadratic_bezier_control_point is not None:
                            p1 = 2 * current_point - last_smooth_quadratic_bezier_control_point

                        point = Vector2(coords[i+2], coords[i+3])
                        points.extend(quadratic_bezier(current_point, p1, point))
                        current_point = points[-1]
                        last_smooth_quadratic_bezier_control_point = p1

                    last_smooth_cubic_bezier_control_point = None

                case 't':
                    for i in range(0, len(coords), 2):
                        p1 = current_point
                        if last_smooth_quadratic_bezier_control_point is not None:
                            p1 = 2 * current_point - last_smooth_quadratic_bezier_control_point

                        point = current_point + Vector2(coords[i+2], coords[i+3])
                        points.extend(quadratic_bezier(current_point, p1, point))
                        current_point = points[-1]
                        last_smooth_quadratic_bezier_control_point = p1

                    last_smooth_cubic_bezier_control_point = None

                case 'A':
                    for i in range(0, len(coords), 7):
                        rx, ry = coords[i+0], coords[i+1]
                        angle = coords[i+2]
                        large_arc = coords[i+3]
                        cw = coords[i+4]
                        point = Vector2(coords[i+5], coords[i+6])
                        points.extend(elliptical_arc(
                            current_point, point, rx, ry, angle,
                            large_arc=math.isclose(large_arc, 1),
                            cw=math.isclose(cw, 1),
                        ))
                        current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'a':
                    for i in range(0, len(coords), 7):
                        rx, ry = coords[i+0], coords[i+1]
                        angle = coords[i+2]
                        large_arc = coords[i+3]
                        cw = coords[i+4]
                        point = current_point + Vector2(coords[i+5], coords[i+6])
                        points.extend(elliptical_arc(
                            current_point, point, rx, ry, angle,
                            large_arc=math.isclose(large_arc, 1),
                            cw=math.isclose(cw, 1),
                        ))
                        current_point = points[-1]

                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case 'Z' | 'z':
                    if len(points) > 1:
                        lines.append(self.geo.line(points, closed=True))

                    if len(points) > 0:
                        current_point = points[0]

                    points = []
                    last_smooth_quadratic_bezier_control_point = None
                    last_smooth_cubic_bezier_control_point = None

                case _:
                    # Unknown command
                    print(f'Unknown SVG path command: {cmd}')

        if len(points) > 1:
            lines.append(self.geo.line(points))

        return lines
