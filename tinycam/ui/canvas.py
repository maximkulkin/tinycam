import moderngl
from pyrr import Vector3
from PySide6 import QtOpenGLWidgets
from tinycam.ui.camera import Camera, PerspectiveCamera
from typing import Tuple


class RenderState:
    screen_size: Tuple[int, int]
    camera: Camera


class Renderable:
    def __init__(self, context):
        super().__init__()
        self._context = context

    @property
    def context(self):
        return self._context

    def render(self, state: RenderState):
        raise NotImplementedError()


class CncCanvas(QtOpenGLWidgets.QOpenGLWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._camera = PerspectiveCamera()
        self._camera.position += Vector3((0, 0, 5))
        self._camera.look_at(Vector3())

    @property
    def camera(self) -> Camera:
        return self._camera

    def initializeGL(self):
        super().initializeGL()
        self.ctx = moderngl.create_context(required=410)

    def resizeGL(self, width, height):
        super().resizeGL(width, height)

        self.ctx.viewport = (0, 0, width, height)
        self._camera.aspect = width / height if width > 0 else 1

    def paintGL(self):
        super().paintGL()

        state = RenderState()
        state.screen_size = self.width(), self.height()
        state.camera = self._camera

        for obj in self.objects:
            obj.render(state)
