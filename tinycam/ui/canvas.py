import moderngl as mgl
from PySide6 import QtOpenGLWidgets
from tinycam.types import Vector2, Vector3
from tinycam.ui.camera import Camera, PerspectiveCamera


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
        self.ctx = None

        self.setMouseTracking(True)

        self._camera = PerspectiveCamera()
        self._camera.position += Vector3(0, 0, 5)
        self._camera.look_at(Vector3())

    @property
    def camera(self) -> Camera:
        return self._camera

    def initializeGL(self):
        super().initializeGL()
        self.ctx = Context(mgl.create_context(required=410))

    def resizeGL(self, width, height):
        super().resizeGL(width, height)

        self.ctx.viewport = (0, 0, width, height)
        self._camera.pixel_size = Vector2(width, height)

    def paintGL(self):
        super().paintGL()

        fbo = self.ctx.detect_framebuffer()
        fbo.use()

        state = RenderState(camera=self._camera)
        self._render(state)

    def _render(self, state: RenderState):
        pass
