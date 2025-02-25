from collections.abc import Sequence
import moderngl as mgl
import numpy as np
from PySide6 import QtCore, QtOpenGLWidgets
from PySide6.QtCore import Qt
from tinycam.types import Vector2, Vector3
from tinycam.ui.camera import Camera, PerspectiveCamera


def selectable_id_to_color(object_id: int) -> np.ndarray:
    return np.array((
        object_id // 65536 & 0xff,
        object_id // 256 & 0xff,
        int(object_id & 0xff),
        255,
    ), dtype='u1')


def color_to_selectable_id(color: np.ndarray) -> int:
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

    def scope(self, **kwargs):
        return Scope(self, **kwargs)


class RenderState:
    camera: Camera
    selecting: bool = False

    def __init__(self, camera: Camera):
        self.camera = camera
        self._next_selectable_id = 1
        self._selectable_by_id = {}

    def register_selectable(self, item: 'ViewItem', tag: object | None = None):
        selectable_id = self._next_selectable_id
        self._next_selectable_id += 1
        self._selectable_by_id[selectable_id] = (item, tag)
        return selectable_id_to_color(selectable_id)

    def get_selectable_by_color(self, color: np.ndarray) -> 'tuple[ViewItem, object] | None':
        return self._selectable_by_id.get(color_to_selectable_id(color))


class ViewItem:
    def __init__(self, context: Context):
        super().__init__()
        self._context = context

    @property
    def context(self) -> Context:
        return self._context

    def render(self, state: RenderState):
        raise NotImplementedError()

    def on_click(self, tag):
        pass


class CncCanvas(QtOpenGLWidgets.QOpenGLWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ctx = None

        self.setMouseTracking(True)

        self._items = []
        self._camera = PerspectiveCamera()
        self._camera.position += Vector3(0, 0, 5)
        self._camera.look_at(Vector3())

        self._select_texture = None
        self._select_framebuffer = None

    @property
    def camera(self) -> Camera:
        return self._camera

    @property
    def items(self) -> Sequence[ViewItem]:
        return self._items

    def add_item(self, item: ViewItem):
        self._items.append(item)

    def remove_item(self, item: ViewItem):
        self._items.remove(item)

    def select_item(self, screen_point: Vector2) -> tuple[ViewItem, object] | None:
        w, h = int(self._camera.pixel_width), int(self._camera.pixel_height)
        if self._select_texture is None:
            self._select_texture = self.ctx.texture((w, h), 4)
        if self._select_framebuffer is None:
            self._select_framebuffer = self.ctx.framebuffer(
                color_attachments=[self._select_texture],
                depth_attachment=self.ctx.depth_renderbuffer((w, h)),
            )

        state = RenderState(camera=self._camera)
        state.selecting = True

        with self.ctx.scope(framebuffer=self._select_framebuffer, flags=mgl.DEPTH_TEST):
            self.ctx.clear(color=(0., 0., 0., 1.), depth=1.0)
            self._render(state)

        raw_data = self._select_texture.read()
        img = np.frombuffer(raw_data, dtype='u1')
        img = img.reshape(h, w, 4)
        img = np.flip(img, axis=0)

        color = img[int(screen_point.y), int(screen_point.x)]

        return state.get_selectable_by_color(color)

    def initializeGL(self):
        super().initializeGL()
        self.ctx = Context(mgl.create_context(required=410))

    def resizeGL(self, width, height):
        super().resizeGL(width, height)

        self.ctx.viewport = (0, 0, width, height)
        self._camera.pixel_size = Vector2(width, height)
        self._select_framebuffer = None
        self._select_texture = None

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

            p = event.position()
            selected = self.select_item(Vector2(p.x(), p.y()))
            if selected is not None:
                selectable, tag = selected
                selectable.on_click(tag)
                return True

        return super().event(event)

    def _render(self, state: RenderState):
        for item in self.items:
            item.render(state)
