from collections.abc import Callable, Sequence
import moderngl as mgl
from numbers import Number as number
import numpy as np
from typing import Any, cast
from PIL.Image import Image
from PySide6 import QtCore, QtGui, QtOpenGLWidgets
from PySide6.QtCore import Qt
from tinycam.types import Vector2, Vector3, Vector4, Rect
from tinycam.ui.camera import Camera, PerspectiveCamera


def pickable_id_to_color(object_id: int) -> np.ndarray:
    return np.array((
        object_id // 65536 & 0xff,
        object_id // 256 & 0xff,
        int(object_id & 0xff),
        255,
    ), dtype='u1')


def color_to_pickable_id(color: np.ndarray) -> int:
    return (color[0] << 16) | (color[1] << 8) | color[2]


class Scope:
    def __init__(
        self,
        context: 'Context',
        flags: int = 0,
        enable: int = 0,
        disable: int = 0,
        framebuffer: mgl.Framebuffer | None = None,
        depth_func: str | None = None,
        depth_clamp_range: tuple[float, float] | None = None,
        blend_func: tuple[int, int] | None = None,
        blend_equation: int | None = None,
        multisample: bool | None = None,
        viewport: tuple[int, int, int, int] | None = None,
        scissor: tuple[int, int, int, int] | None = None,
        front_face: str | None = None,
        cull_face: str | None = None,
        wireframe: bool | None = None,
    ):
        self._context = context

        self._flags = flags
        self._enable = enable
        self._disable = disable

        attrs = {
            'depth_func': depth_func,
            'depth_clamp_range': depth_clamp_range,
            'blend_func': blend_func,
            'blend_equation': blend_equation,
            'multisample': multisample,
            'viewport': viewport,
            'scissor': scissor,
            'front_face': front_face,
            'cull_face': cull_face,
            'wireframe': wireframe,
        }
        self._attrs = {k: v for k, v in attrs.items() if v is not None}
        self._framebuffer = framebuffer

        self._old_flags = None
        self._old_values = {}
        self._old_framebuffer = None

    def __enter__(self):
        flags = self._flags or (self._context.flags & ~(self._disable) | self._enable)

        self._old_flags = self._context.flags
        self._context.enable_only(flags)

        if self._framebuffer is not None:
            self._old_framebuffer = self._context.fbo
            self._framebuffer.use()

        self._old_values = {k: getattr(self._context, k) for k in self._attrs.keys()}
        for k, v in self._attrs.items():
            setattr(self._context, k, v)

    def __exit__(self, exc_type, exc_value, traceback):
        if self._old_framebuffer is not None:
            self._old_framebuffer.use()
            self._old_framebuffer = None

        for k, v in self._old_values.items():
            setattr(self._context, k, v)

        self._context.enable_only(self._old_flags)


class ContextProxy:
    def __set_name__(self, owner: object, name: str):
        self._name = name

    def __get__(self, obj: object, cls) -> object:
        return getattr(object._context, self._name)

    def __set__(self, obj: object, value: object):
        setattr(obj._context, self._name, value)


class Uniform:
    def __init__(self, uniform: mgl.Uniform):
        self._uniform = uniform

    @property
    def value(self) -> Any:
        return self._uniform.value

    @value.setter
    def value(self, value: float | np.ndarray | QtGui.QColor):
        if isinstance(value, (int, float)):
            self._uniform.value = value
        elif isinstance(value, QtGui.QColor):
            c = cast(QtGui.QColor, value)
            self.write(Vector4(c.redF(), c.greenF(), c.blueF(), c.alphaF()))
        else:
            self.write(value)

    def read(self) -> bytes:
        return self._uniform.read()

    def write(self, data: Any):
        self._uniform.write(data)


class Program:
    def __init__(self, program: mgl.Program):
        self._program = program

    def __getitem__(self, name: str) -> Uniform:
        inner = self._program[name]
        if not isinstance(inner, mgl.Uniform):
            raise ValueError(f'Unknown uniform: {name}')

        return Uniform(inner)

    def __setitem__(self, name: str, value: Any):
        self[name].value = value


class Context:
    def __init__(self, context: mgl.Context):
        self._context = context
        self._flags = 0

    # Context properties
    depth_clamp_range = ContextProxy()
    blend_func = ContextProxy()
    blend_equation = ContextProxy()
    multisample = ContextProxy()
    viewport = ContextProxy()
    scissor = ContextProxy()
    front_face = ContextProxy()
    cull_face = ContextProxy()
    wireframe = ContextProxy()

    @property
    def flags(self) -> int:
        return self._flags

    @flags.setter
    def flags(self, value: int):
        self._flags = value
        self._context.enable_only(value)

    def enable(self, flags: int):
        self._flags |= flags
        self._context.enable(flags)

    def disable(self, flags: int):
        self._flags &= ~flags
        self._context.disable(flags)

    def enable_only(self, flags: int):
        self._context.enable_only(flags)
        self._flags = flags

    # Workaround for non-implemented depth_func property getter in moderngl
    @property
    def depth_func(self) -> str:
        return self._context.mglo.depth_func

    @depth_func.setter
    def depth_func(self, value: str):
        self._context.depth_func = value

    def __getattr__(self, name: str) -> object:
        return getattr(self._context, name)

    def clear(
        self,
        color: Vector4 | tuple[number, number, number, number] | np.ndarray | QtGui.QColor = Vector4(),
        depth: float = 1.0,
        viewport: tuple[int, int, int, int] | Rect | None = None,
    ):
        if isinstance(color, QtGui.QColor):
            color = Vector4(color.redF(), color.greenF(), color.blueF(), color.alphaF())
        # Viewport is (x, y, width, height)
        self._context.clear(color=color, depth=depth, viewport=viewport)

    def scope(self, **kwargs):
        return Scope(self, **kwargs)

    def program(self, vertex_shader: str, fragment_shader: str) -> Program:
        return Program(
            self._context.program(vertex_shader=vertex_shader,
                                  fragment_shader=fragment_shader)
        )

    def buffer(self, data: bytes | np.ndarray) -> mgl.Buffer:
        return self._context.buffer(data)

    def vertex_array(
        self,
        program: Program,
        content: list[tuple[mgl.Buffer, str, str]],
        index_buffer: mgl.Buffer | None = None,
        index_element_size: int = 4,
        mode: int = mgl.TRIANGLES,
    ) -> mgl.VertexArray:
        return self._context.vertex_array(
            program=program._program,
            content=content,
            index_buffer=index_buffer,
            index_element_size=index_element_size,
            mode=mode,
        )

    def texture(
        self,
        size: tuple[int, int],
        components: int,
        data: bytes | np.ndarray | Image | None = None,
        samples: int = 0,
        alignment: int = 1,
        dtype: str = 'f1',
    ) -> mgl.Texture:
        if isinstance(data, (np.ndarray, Image)):
            data = data.tobytes()
        return self._context.texture(
            size=size,
            components=components,
            data=data,
            samples=samples,
            alignment=alignment,
            dtype=dtype,
        )

    def framebuffer(
        self,
        color_attachments: list[mgl.Texture],
        depth_attachment: mgl.Texture | None = None,
    ) -> mgl.Framebuffer:
        return self._context.framebuffer(
            color_attachments=color_attachments,
            depth_attachment=depth_attachment,
        )


class RenderState:
    camera: Camera
    picking: bool = False

    def __init__(self, camera: Camera):
        self.camera = camera
        self._next_pickable_id = 1
        self._pickable_by_id = {}

    def register_pickable(self, item: 'ViewItem', tag: object | None = None):
        pickable_id = self._next_pickable_id
        self._next_pickable_id += 1
        self._pickable_by_id[pickable_id] = (item, tag)
        return pickable_id_to_color(pickable_id)

    def get_pickable_by_color(self, color: np.ndarray) -> 'tuple[ViewItem, object] | None':
        return self._pickable_by_id.get(color_to_pickable_id(color))


class ViewItem:
    priority: int = 1

    def __init__(self, context: Context):
        super().__init__()
        self._context = context

    @property
    def context(self) -> Context:
        return self._context

    def render(self, state: RenderState):
        raise NotImplementedError()


class CncView(QtOpenGLWidgets.QOpenGLWidget):
    def __init__(self, camera: Camera | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = None

        self.setMouseTracking(True)

        self._items = []
        if camera is None:
            camera = PerspectiveCamera()
            camera.position += Vector3(0, 0, 5)
            camera.look_at(Vector3())

        self._camera = camera
        self._camera.pixel_size = Vector2(self.width(), self.height())

        self._pick_texture = None
        self._pick_framebuffer = None

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def items(self) -> Sequence[ViewItem]:
        return self._items

    def add_item(self, item: ViewItem):
        self.add_items([item])

    def add_items(self, items: Sequence[ViewItem]):
        self._items.extend(items)
        self._items.sort(key=lambda x: x.priority)
        self.update()

    def remove_item(self, item: ViewItem):
        self._items.remove(item)
        self.update()

    def remove_items(self, predicate: Callable[[ViewItem], bool]):
        self._items = self._items.filter(lambda item: not predicate(item))
        self.update()

    def pick_item(
        self,
        screen_point: Vector2 | QtCore.QPoint | QtCore.QPointF
    ) -> tuple[ViewItem, object] | None:
        if isinstance(screen_point, (QtCore.QPoint, QtCore.QPointF)):
            screen_point = Vector2(screen_point.x(), screen_point.y())

        w, h = int(self._camera.pixel_width), int(self._camera.pixel_height)
        if self._pick_texture is None:
            self._pick_texture = self.ctx.texture((w, h), 4)
        if self._pick_framebuffer is None:
            self._pick_framebuffer = self.ctx.framebuffer(
                color_attachments=[self._pick_texture],
                depth_attachment=self.ctx.depth_renderbuffer((w, h)),
            )

        state = RenderState(camera=self._camera)
        state.picking = True

        with self.ctx.scope(framebuffer=self._pick_framebuffer, flags=mgl.DEPTH_TEST):
            self.ctx.clear(color=(0., 0., 0., 1.), depth=1.0)
            self._render(state)

        raw_data = self._pick_texture.read()
        img = np.frombuffer(raw_data, dtype='u1')
        img = img.reshape(h, w, 4)
        img = np.flip(img, axis=0)

        color = img[int(screen_point.y), int(screen_point.x)]

        return state.get_pickable_by_color(color)

    def initializeGL(self):
        super().initializeGL()
        self.ctx = Context(mgl.create_context(required=410))
        self.context = self.ctx

    def resizeGL(self, width, height):
        super().resizeGL(width, height)

        self.ctx.viewport = (0, 0, width, height)
        self._camera.pixel_size = Vector2(width, height)
        self._camera.device_pixel_ratio = self.window().devicePixelRatio()
        self._pick_framebuffer = None
        self._pick_texture = None

    def paintGL(self):
        super().paintGL()

        fbo = self.ctx.detect_framebuffer()
        fbo.use()

        state = RenderState(camera=self._camera)
        self._render(state)

    def event(self, event: QtCore.QEvent):
        if (event.type() == QtCore.QEvent.MouseButtonRelease and
                event.button() == Qt.LeftButton and
                event.modifiers() == Qt.NoModifier):

            picked = self.pick_item(event.position())
            if picked is not None:
                pickable, tag = picked
                if hasattr(pickable, 'on_click'):
                    pickable.on_click(tag)
                    return True

        return super().event(event)

    def _render(self, state: RenderState):
        self.ctx.clear(color=(0.0, 0.0, 0.0, 1.0))

        for item in self.items:
            item.render(state)
