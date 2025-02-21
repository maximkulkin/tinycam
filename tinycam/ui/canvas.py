import moderngl
from PySide6 import QtOpenGLWidgets
from tinycam.types import Vector2, Vector3
from tinycam.ui.camera import Camera, PerspectiveCamera


class Scope:
    def __init__(self, context: 'Context', enable=0, disable=0, **kwargs):
        self._context = context
        self._enable = enable
        self._disable = disable
        self._attrs = kwargs
        self._old_flags = None
        self._old_values = {}

    def __enter__(self):
        self._old_flags = self._context.flags
        self._context.enable_only(
            self._context.flags & ~(self._disable) | self._enable
        )

        self._old_values = {k: getattr(self._context, k) for k in self._attrs.keys()}
        for k, v in self._attrs.items():
            setattr(self._context, k, v)

    def __exit__(self, exc_type, exc_value, traceback):
        self._context.enable_only(self._old_flags)
        for k, v in self._old_values.items():
            setattr(self._context, k, v)


class Context:
    def __init__(self, context: moderngl.Context):
        self._context = context
        self._flags = 0

    @property
    def flags(self) -> int:
        return self._flags

    def enable(self, flags: int):
        self._context.enable(flags)
        self._flags |= flags

    def disable(self, flags: int):
        self._context.disable(flags)
        self._flags &= ~flags

    def enable_only(self, flags: int):
        self._context.enable_only(flags)
        self._flags = flags

    def __getattr__(self, name: str) -> object:
        return getattr(self._context, name)

    def scope(self, **kwargs):
        return Scope(self, **kwargs)


class RenderState:
    camera: Camera


class Renderable:
    def __init__(self, context: Context):
        super().__init__()
        self._context = context

    @property
    def context(self) -> Context:
        return self._context

    def render(self, state: RenderState):
        raise NotImplementedError()


class CncCanvas(QtOpenGLWidgets.QOpenGLWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._camera = PerspectiveCamera()
        self._camera.position += Vector3(0, 0, 5)
        self._camera.look_at(Vector3())

    @property
    def camera(self) -> Camera:
        return self._camera

    def initializeGL(self):
        super().initializeGL()
        self.ctx = Context(moderngl.create_context(required=410))

    def resizeGL(self, width, height):
        super().resizeGL(width, height)

        self.ctx.viewport = (0, 0, width, height)
        self._camera.pixel_size = Vector2(width, height)

    def paintGL(self):
        super().paintGL()

        fbo = self.ctx.detect_framebuffer()
        fbo.use()

        self._render()

    def _render(self):
        state = RenderState()
        state.camera = self._camera

        for obj in self.objects:
            obj.render(state)
