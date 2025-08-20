from collections.abc import Sequence
import enum
from typing import Optional

import moderngl as mgl
import numpy as np

from tinycam.types import Vector2, Vector4
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core import Node3D


type Point2 = Vector2


class JointStyle(enum.Enum):
    MITER = enum.auto()
    BEVEL = enum.auto()
    ROUND = enum.auto()


class CapStyle(enum.Enum):
    BUTT = enum.auto()
    ROUND = enum.auto()
    SQUARE = enum.auto()


def _create_cap(
    point: Vector2,
    direction: Vector2,
    half_width: float,
    cap_style: CapStyle = CapStyle.BUTT,
    is_start: bool = False,
) -> list[Vector2]:
    match cap_style:
        case CapStyle.BUTT:
            return []

        case CapStyle.SQUARE:
            normal = direction.rot90ccw
            p_cap = point + direction * half_width

            if is_start:
                return [
                    p_cap - normal * half_width,
                    p_cap + normal * half_width
                ]
            else:
                return [
                    p_cap + normal * half_width,
                    p_cap - normal * half_width
                ]

        case CapStyle.ROUND:
            cap_vertices = []

            num_segments = 10
            for j in range(num_segments + 1):
                angle = np.pi * j / num_segments - np.pi / 2
                # CCW rotation
                rot_matrix = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
                n_rot = rot_matrix @ direction
                cap_vertices.append(point + n_rot * half_width)
                cap_vertices.append(point)

            return cap_vertices


def _create_joint(
    point: Vector2,
    normal1: Vector2,
    normal2: Vector2,
    half_width: float,
    ccw: bool = True,
    joint_style: JointStyle = JointStyle.MITER,
    miter_limit: float | None = None,
) -> list[Vector2]:
    miter_vec = (normal1 + normal2).normalized

    miter_len = half_width / np.dot(miter_vec, normal1)

    if joint_style == JointStyle.MITER and miter_limit is not None and miter_len > miter_limit:
        joint_style = JointStyle.BEVEL

    match joint_style:
        case JointStyle.MITER:
            v = miter_vec * miter_len
            return [point + v, point - v]

        case JointStyle.BEVEL:
            if ccw:
                return [
                    point + miter_vec * miter_len,
                    point - normal1 * half_width,
                    point + miter_vec * miter_len,
                    point - normal2 * half_width,
                ]
            else:
                return [
                    point + normal1 * half_width,
                    point - miter_vec * miter_len,
                    point + normal2 * half_width,
                    point - miter_vec * miter_len,
                ]

        case JointStyle.ROUND:
            angle = np.arctan2(normal1[1], normal1[0]) - np.arctan2(normal2[1], normal2[0])
            if angle > np.pi:
                angle -= 2 * np.pi
            if angle < -np.pi:
                angle += 2 * np.pi

            num_segments = max(int(abs(angle) * 180 / np.pi / 10), 2)

            joint_vertices = []
            base_angle = np.arctan2(normal1[1], normal1[0])

            if ccw:
                for j in range(num_segments + 1):
                    a = base_angle - angle * j / num_segments
                    normal = Vector2(np.cos(a), np.sin(a))
                    joint_vertices.append(point + miter_vec * miter_len)
                    joint_vertices.append(point - normal * half_width)
            else:
                for j in range(num_segments + 1):
                    a = base_angle - angle * j / num_segments
                    normal = Vector2(np.cos(a), np.sin(a))
                    joint_vertices.append(point + normal * half_width)
                    joint_vertices.append(point - miter_vec * miter_len)

            return joint_vertices


def _generate_vertices(
    points: Sequence[Vector2],
    closed: bool = False,
    width: float | None = None,
    joint_style: JointStyle = JointStyle.MITER,
    max_segment_length: float | None = None,
    miter_limit: float | None = None,
    cap_style: CapStyle = CapStyle.BUTT,
) -> tuple[bytes, bytes]:
    if width is None:
        positions = np.array(points, dtype='f4')

        lengths = np.zeros(len(points), dtype='f4')
        for i in range(1, len(points)):
            lengths[i] = lengths[i - 1] + (points[i] - points[i - 1]).length
        uvs = np.zeros((positions.shape[0], 2), dtype='f4')
        uvs[:, 0] = lengths

        return positions.tobytes(), uvs.tobytes()

    if closed and points[0] == points[-1]:
        points = points[:-1]

    half_width = 0.5 * width

    vertices = []
    uvs = []
    length = 0.0

    if not closed:
        cap_vertices = _create_cap(
            points[0],
            (points[0] - points[1]).normalized,
            half_width,
            cap_style=cap_style,
            is_start=True,
        )
        vertices.extend(cap_vertices)
        uvs.extend([Vector2(length, 0) for _ in cap_vertices])

        p1 = points[0]
        p2 = points[1]
        n = (p2 - p1).normal

        vertices.extend([p1 + n * half_width, p1 - n * half_width])
        uvs.extend([Vector2(length, 0), Vector2(length, 0)])
    else:
        p1 = points[-1]
        p2 = points[0]
        p3 = points[1]

        n1 = (p2 - p1).normal
        n2 = (p3 - p2).normal

        ccw = n1.dot(p3 - p2) > 0

        joint_vertices = _create_joint(
            p2, n1, n2, half_width,
            ccw=ccw,
            joint_style=joint_style,
            miter_limit=miter_limit,
        )
        vertices.extend(joint_vertices)
        uvs.extend([Vector2(length, 0) for _ in joint_vertices])

    if max_segment_length is not None:
        def subdivide(p1: Vector2, p2: Vector2) -> list[Vector2]:
            length = (p2 - p1).length

            if length <= max_segment_length:
                return []

            n = int(length / max_segment_length) + (1 if length % max_segment_length > 0 else 0)
            new_segment_length = length / n
            v = (p2 - p1).normalized
            return [
                p1 + v * j * new_segment_length
                for j in range(1, n)
            ]

        new_points = []
        for i in range(len(points) - 1):
            new_points.append(points[i])
            new_points.extend(subdivide(points[i], points[i + 1]))

        new_points.append(points[-1])

        if closed:
            p1 = points[-1]
            p2 = points[0]
            new_points.extend(subdivide(points[-1], points[0]))

        points = new_points

    # Create vertices for each segment
    for i in range(len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        n = (p2 - p1).normal

        length += (p2 - p1).length

        if i < len(points) - 2:
            p3 = points[(i + 2) % len(points)]
            n_next = (p3 - p2).normal
            ccw = n.dot(p3 - p2) > 0
            joint_vertices = _create_joint(
                p2, n, n_next, half_width,
                ccw=ccw,
                joint_style=joint_style,
                miter_limit=miter_limit,
            )
            vertices.extend(joint_vertices)
            uvs.extend([Vector2(length, 0) for _ in joint_vertices])

    if not closed:
        p1 = points[-2]
        p2 = points[-1]
        n = (p2 - p1).normal
        vertices.extend([p2 + n * half_width, p2 - n * half_width])
        uvs.extend([Vector2(length, 0), Vector2(length, 0)])

        cap_vertices = _create_cap(p2, (p2 - p1).normalized, half_width, cap_style=cap_style)
        vertices.extend(cap_vertices)
        uvs.extend([Vector2(length, 0) for _ in cap_vertices])
    else:
        p1 = points[-2]
        p2 = points[-1]
        n = (p2 - p1).normal

        length += (p2 - p1).length

        p3 = points[0]
        n_next = (p3 - p2).normal
        ccw = n.dot(p3 - p2) > 0
        joint_vertices = _create_joint(
            p2, n, n_next, half_width,
            ccw=ccw,
            joint_style=joint_style,
            miter_limit=miter_limit,
        )
        vertices.extend(joint_vertices)
        uvs.extend([Vector2(length, 0) for _ in joint_vertices])

        vertices.extend(vertices[0:2])
        uvs.extend(uvs[0:2])

    vertices = np.array(vertices, dtype='f4')
    uvs = np.array(uvs, dtype='f4')
    return vertices.tobytes(), uvs.tobytes()


class Line2D(Node3D):
    def __init__(
        self,
        context: Context,
        points: Sequence[Vector2],
        closed: bool = False,
        color: Vector4 = Vector4(0.8, 0.8, 0.8, 1.0),
        width: Optional[float] = None,
        joint_style: JointStyle = JointStyle.MITER,
        miter_limit: float | None = None,
        max_segment_length: float | None = None,
        cap_style: CapStyle = CapStyle.SQUARE,
    ):
        super().__init__(context)

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                uniform mat4 mvp;
                in vec2 position;
                in vec2 uv;
                out vec2 v_uv;

                void main() {
                    gl_Position = mvp * vec4(position.x, position.y, 0.0, 1.0);
                    v_uv = uv;
                }
            ''',
            fragment_shader='''
                #version 410 core

                uniform vec4 color;
                out vec4 fragColor;
                in vec2 v_uv;

                void main() {
                    fragColor = color;
                }
            ''',
        )

        self._color = color
        self._width = width
        self._program['color'].write(color.astype('f4').tobytes())

        vertices, uvs = _generate_vertices(
            points,
            closed=closed,
            width=self._width,
            joint_style=joint_style,
            miter_limit=miter_limit,
            max_segment_length=max_segment_length,
            cap_style=cap_style,
        )

        self._vbo = self.context.buffer(vertices)
        self._uv_vbo = self.context.buffer(uvs)
        self._vao = self.context.vertex_array(
            self._program,
            [
                (self._vbo, '2f', 'position'),
                (self._uv_vbo, '2f', 'uv'),
            ],
            mode=mgl.LINE_STRIP if self._width is None else mgl.TRIANGLE_STRIP,
        )

    @property
    def color(self) -> Vector4:
        return self._color

    @color.setter
    def color(self, value: Vector4):
        self._color = value
        self._program['color'].write(self._color.astype('f4').tobytes())

    def render(self, state: RenderState):
        camera = state.camera
        self._program['mvp'].write(
            camera.projection_matrix * camera.view_matrix * self.world_matrix
        )

        self._vao.render()
