import enum
from itertools import chain
import moderngl as mgl
import numpy as np
from PIL import Image
from PySide6 import QtCore
from tinycam.types import Vector2, Vector3, Matrix44
from tinycam.ui.camera import Camera
from tinycam.ui.canvas import Context, ViewItem, RenderState


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


class OrientationCube(ViewItem, QtCore.QObject):
    OFFSET = Vector2(50, 50)
    SIZE = Vector2(100, 100)

    orientation_selected = QtCore.Signal(Orientation)

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
                layout(location = 0) out vec4 color;

                uniform sampler2D tex;

                void main() {
                    color = texture(tex, v_texcoord);
                }
            ''',
        )

        self._select_program = self.context.program(
            vertex_shader='''
                #version 410 core

                in vec3 position;
                in int face_id;

                flat out int v_face_id;

                uniform mat4 mvp;

                void main() {
                    gl_Position = mvp * vec4(position, 1);
                    v_face_id = face_id;
                }
            ''',
            fragment_shader='''
                #version 410 core

                flat in int v_face_id;
                out vec4 fragColor;

                uniform sampler2D tex;

                void main() {
                    float tex_coord = (v_face_id + 0.5) / 6.0;
                    fragColor = texture(tex, vec2(tex_coord, 0.0));
                }
            ''',
        )
        self._face_select_texture = self.context.texture((6, 1), 4, dtype='u1')
        self._face_select_texture.filter = (mgl.NEAREST, mgl.NEAREST)

        self._quad_program = self.context.program(
            vertex_shader='''
                #version 410 core

                in vec2 position;
                in vec2 texcoord;

                uniform vec2 center;
                uniform vec2 size;

                out vec2 v_texcoord;

                void main() {
                    gl_Position = vec4(center + position * size, 0, 1);
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

        self._face_id_buffer = self.context.buffer(
            np.array([
                0, 0, 0, 0, 0, 0,
                1, 1, 1, 1, 1, 1,
                2, 2, 2, 2, 2, 2,
                3, 3, 3, 3, 3, 3,
                4, 4, 4, 4, 4, 4,
                5, 5, 5, 5, 5, 5,
            ], dtype='i4').tobytes()
        )
        self._select_vao = self.context.vertex_array(self._select_program, [
            (self._vertex_buffer, '3f', 'position'),
            (self._face_id_buffer, 'i', 'face_id'),
        ])
        self._select_program['tex'] = 0

        quad_buffer = self.context.buffer(np.array([
            ( 0.5, -0.5, 1., 0.),
            ( 0.5,  0.5, 1., 1.),
            (-0.5, -0.5, 0., 0.),
            (-0.5,  0.5, 0., 1.),
        ], dtype='f4').tobytes())
        self._quad_vao = self.context.vertex_array(
            self._quad_program,
            [(quad_buffer, '2f 2f', 'position', 'texcoord')]
        )

        self._rendered_texture = self.context.texture((512, 512), 4)
        self._framebuffer = self.context.framebuffer(
            color_attachments=[self._rendered_texture],
            depth_attachment=self.context.depth_renderbuffer((512, 512)),
        )
        self._quad_program['tex'] = 0

    @property
    def orientation_cube_position(self) -> OrientationCubePosition:
        return self._orientation_cube_position

    @orientation_cube_position.setter
    def orientation_cube_position(self, value: OrientationCubePosition):
        self._orientation_cube_position = value

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
            self._camera.projection_matrix *
            # move away from camera
            Matrix44.from_translation(Vector3(0, 0, -2.5)) *
            # rotate as camera
            Matrix44.from_quaternion(self._camera.rotation.conjugate)
        )

        if state.selecting:
            data = np.array([
                state.register_selectable(self, Orientation.LEFT),
                state.register_selectable(self, Orientation.RIGHT),
                state.register_selectable(self, Orientation.FRONT),
                state.register_selectable(self, Orientation.BACK),
                state.register_selectable(self, Orientation.BOTTOM),
                state.register_selectable(self, Orientation.TOP),
            ], dtype='u1')
            self._face_select_texture.write(data.tobytes())
            self._select_program['mvp'].write(self._matrix.tobytes())
            with self.context.scope(
                framebuffer=self._framebuffer,
                flags=mgl.DEPTH_TEST,
            ):
                self.context.clear(color=(0.0, 0.0, 0.0, 0.0), depth=1.0)
                self._face_select_texture.use(0)
                self._select_vao.render(mgl.TRIANGLES)
        else:
            self._program['mvp'].write(self._matrix.tobytes())

            with self.context.scope(
                framebuffer=self._framebuffer,
                flags=mgl.DEPTH_TEST,
            ):
                self.context.clear(color=(0.0, 0.0, 0.0, 0.0), depth=1.0)
                self._texture.use(0)
                self._vao.render(mgl.TRIANGLES)

        size = (
            Vector2(self.SIZE.x * state.camera.aspect, self.SIZE.y) *
            2.0 / state.camera.pixel_size
        )
        self._quad_program['center'] = p.xy
        self._quad_program['size'] = size

        with self.context.scope(framebuffer=self.context.fbo, flags=mgl.BLEND):
            self._rendered_texture.use(0)
            self._quad_vao.render(mgl.TRIANGLE_STRIP)

    def on_select(self, tag):
        self.orientation_selected.emit(tag)
