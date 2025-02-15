import enum
from itertools import chain
import moderngl
import numpy as np
from PIL import Image
from PySide6 import QtCore
from PySide6.QtCore import Qt
from tinycam.types import Vector2, Vector3, Vector4, Matrix44
from tinycam.ui.camera import Camera
from tinycam.ui.canvas import Context, Renderable, RenderState


Point2d = Vector2 | np.ndarray | tuple[float, float]
Point3d = Vector3 | np.ndarray | tuple[float, float, float]


def quad_triangles(p1: Point3d, p2: Point3d, p3: Point3d, p4: Point3d) -> list[Point3d]:
    return [p1, p3, p2, p1, p4, p3]


def uv(x: int, y: int) -> list[Point2d]:
    x1 = float(x)
    y1 = float(y)
    x2 = x1 + 1.0
    y2 = y1 + 1.0
    return [(x1, y1), (x2, y2), (x1, y2),
            (x1, y1), (x2, y1), (x2, y2)]


class Cube:
    LEFT = np.array([
        Vector3(-1,  1, -1),
        Vector3(-1,  1,  1),
        Vector3(-1, -1,  1),
        Vector3(-1, -1, -1),
    ])
    LEFT_NORMAL = Vector3(-1, 0, 0)

    RIGHT = np.array([
        Vector3( 1, -1, -1),
        Vector3( 1, -1,  1),
        Vector3( 1,  1,  1),
        Vector3( 1,  1, -1),
    ])
    RIGHT_NORMAL = Vector3(1, 0, 0)

    FRONT = np.array([
        Vector3(-1, -1, -1),
        Vector3(-1, -1,  1),
        Vector3( 1, -1,  1),
        Vector3( 1, -1, -1),
    ])
    FRONT_NORMAL = Vector3(0, -1, 0)

    BACK = np.array([
        Vector3( 1,  1, -1),
        Vector3( 1,  1,  1),
        Vector3(-1,  1,  1),
        Vector3(-1,  1, -1),
    ])
    BACK_NORMAL = Vector3(0, 1, 0)

    BOTTOM = np.array([
        Vector3(-1,  1, -1),
        Vector3(-1, -1, -1),
        Vector3( 1, -1, -1),
        Vector3( 1,  1, -1),
    ])
    BOTTOM_NORMAL = Vector3(0, 0, -1)

    TOP = np.array([
        Vector3(-1, -1,  1),
        Vector3(-1,  1,  1),
        Vector3( 1,  1,  1),
        Vector3( 1, -1,  1),
    ])
    TOP_NORMAL = Vector3(0, 0, 1)


def point_inside_polygon(p: Vector2, polygon: list[Vector2]) -> bool:
    count = 0
    for (p1, p2) in zip(polygon, chain(polygon[1:], [polygon[0]])):
        if (p.y < p1.y) == (p.y < p2.y):
            continue

        if ((p1.y == p2.y) or p.x < p1.x + (p.y - p1.y) / (p2.y - p1.y) * (p2.x - p1.x)):
            count += 1
    return count % 2 == 1


class OrientationCubePosition(enum.Enum):
    TOP_LEFT = enum.auto()
    TOP_RIGHT = enum.auto()
    BOTTOM_LEFT = enum.auto()
    BOTTOM_RIGHT = enum.auto()

    def __str__(self) -> str:
        match self:
            case self.TOP_LEFT: return 'Top Left'
            case self.TOP_RIGHT: return 'Top Right'
            case self.BOTTOM_LEFT: return 'Bottom Left'
            case self.BOTTOM_RIGHT: return 'Bottom Right'


class Orientation(enum.Enum):
    LEFT = enum.auto()
    RIGHT = enum.auto()
    FRONT = enum.auto()
    BACK = enum.auto()
    BOTTOM = enum.auto()
    TOP = enum.auto()


class OrientationCube(Renderable):
    OFFSET = Vector2(50, 50)

    class EventFilter(QtCore.QObject):
        orientation_selected = QtCore.Signal(Orientation)

        def __init__(self, cube: 'OrientationCube', size: float, camera: Camera):
            super().__init__()
            self._size = size
            self._camera = camera
            self.matrix = Matrix44.identity()

        def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                p = Vector2(
                    event.position().x() / widget.width() * 2.0 - 1.0,
                    1.0 - event.position().y() / widget.height() * 2.0,
                )

                def pick_quad(points: list[Vector3] | np.ndarray, normal: Vector3) -> bool:
                    ndc_normal = self.matrix * Vector4.from_vector3(normal, 0.0)
                    if ndc_normal.z >= 0.0:
                        return False

                    def to_ndc(point: Vector3) -> Vector4:
                        p = self.matrix * Vector4.from_vector3(point, 1.0)
                        return p / p.w

                    points = [
                        to_ndc(point * self._size * 0.5).xy
                        for point in points
                    ]

                    return point_inside_polygon(p, points)

                for side, points, normal in [(Orientation.FRONT, Cube.FRONT, Cube.FRONT_NORMAL),
                                             (Orientation.BACK, Cube.BACK, Cube.BACK_NORMAL),
                                             (Orientation.TOP, Cube.TOP, Cube.TOP_NORMAL),
                                             (Orientation.BOTTOM, Cube.BOTTOM, Cube.BOTTOM_NORMAL),
                                             (Orientation.LEFT, Cube.LEFT, Cube.LEFT_NORMAL),
                                             (Orientation.RIGHT, Cube.RIGHT, Cube.RIGHT_NORMAL)]:
                    if pick_quad(points, normal):
                        self.orientation_selected.emit(side)
                        return True

            return False

    def __init__(
        self,
        context: Context,
        camera: Camera,
        size: float = 1.0,
        position: OrientationCubePosition = OrientationCubePosition.TOP_RIGHT,
    ):
        super().__init__(context)

        self._camera = camera
        self._position = position
        self._size = size
        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                in vec3 position;
                in vec2 texcoord;

                out vec2 v_texcoord;

                uniform mat4 mvp;

                void main() {
                    gl_Position = mvp * vec4(position, 1);
                    v_texcoord = texcoord;
                }
            ''',
            fragment_shader='''
                #version 410 core

                in vec2 v_texcoord;
                out vec4 fragColor;

                uniform sampler2D tex;

                void main() {
                    fragColor = texture(tex, v_texcoord);
                }
            ''',
        )

        vertices = np.array([
            *quad_triangles(*Cube.LEFT),
            *quad_triangles(*Cube.RIGHT),
            *quad_triangles(*Cube.FRONT),
            *quad_triangles(*Cube.BACK),
            *quad_triangles(*Cube.BOTTOM),
            *quad_triangles(*Cube.TOP),
        ], dtype='f4') * self._size * 0.5

        uvs = np.array([
            point
            for y in range(2)
            for x in range(3)
            for point in uv(x, y)
        ], dtype='f4') * 0.333

        image = Image.open('textures/orientation_cube.png').transpose(Image.FLIP_TOP_BOTTOM)
        self._texture = self.context.texture(image.size, 3, image.tobytes())
        self._program['tex'] = 0

        self._vertex_buffer = self.context.buffer(vertices.tobytes())
        self._uv_buffer = self.context.buffer(uvs.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vertex_buffer, '3f', 'position'),
            (self._uv_buffer, '2f', 'texcoord'),
        ])

        self.eventFilter = self.EventFilter(self, self._size, self._camera)

    @property
    def position(self) -> OrientationCubePosition:
        return self._position

    @position.setter
    def position(self, value: OrientationCubePosition):
        self._position = value

    def render(self, state: RenderState):
        screen_position = None
        match self._position:
            case OrientationCubePosition.TOP_LEFT:
                screen_position = Vector2(
                    self.OFFSET.x,
                    self.OFFSET.y,
                )
            case OrientationCubePosition.TOP_RIGHT:
                screen_position = Vector2(
                    state.camera.pixel_width - self.OFFSET.x,
                    self.OFFSET.y,
                )
            case OrientationCubePosition.BOTTOM_LEFT:
                screen_position = Vector2(
                    self.OFFSET.x,
                    state.camera.pixel_height - self.OFFSET.y,
                )
            case OrientationCubePosition.BOTTOM_RIGHT:
                screen_position = Vector2(
                    state.camera.pixel_width - self.OFFSET.x,
                    state.camera.pixel_height - self.OFFSET.y,
                )

        p = state.camera.screen_to_ndc_point(screen_position)

        self._matrix = (
            # move into screen position
            Matrix44.from_translation(Vector3(p[0], p[1], 0)) *
            # project
            self._camera.projection_matrix *
            # move away from camera
            Matrix44.from_translation(Vector3(0, 0, -20)) *
            # rotate as camera
            Matrix44.from_quaternion(self._camera.rotation.conjugate)
        )

        self._program['mvp'].write(self._matrix.tobytes())

        with self.context.scope(enable=moderngl.DEPTH_TEST, front_face='ccw'):
            self._texture.use(0)
            self._vao.render(moderngl.TRIANGLES)

        self.eventFilter.matrix = self._matrix
