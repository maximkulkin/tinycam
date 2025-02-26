import moderngl
import numpy as np
from tinycam.types import Vector2
from tinycam.ui.tools import CncTool
from tinycam.ui.view import ViewItem, RenderState
from PySide6 import QtCore
from PySide6.QtCore import Qt


def vector2(point: QtCore.QPoint | QtCore.QPointF) -> Vector2:
    return Vector2(point.x(), point.y())


class SelectionBox(ViewItem):
    def __init__(
        self,
        context,
        point1: Vector2 | None = None,
        point2: Vector2 | None = None,
    ):
        super().__init__(context)

        self.point1 = point1 or Vector2()
        self.point2 = point2 or Vector2()

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                in vec2 position;

                uniform vec2 position1;
                uniform vec2 position2;
                uniform vec2 screen_size;

                void main() {
                    gl_Position = vec4(position, 0, 1);
                }
            ''',
            fragment_shader='''
                #version 410 core

                out vec4 color;

                void main() {
                    color = vec4(1, 1, 1, 1);
                }
            ''',
        )

        vertices = np.array([
            (-0.5,  0.5, 0.0),
            ( 0.5,  0.5, 0.0),
            (-0.5, -0.5, 0.0),
            ( 0.5, -0.5, 0.0),
        ], dtype='f4')

        self._vbo = self.context.buffer(vertices.tobytes())
        self._vao = self.context.vertex_array(self._program, [
            (self._vbo, '3f', 'position'),
        ])

    def render(self, state: RenderState):
        self._program['position1'] = self.position1
        self._program['position2'] = self.position2

        with self.context.scope(enable_only=[moderngl.DEPTH_TEST]):
            self._vao.render(moderngl.TRIANGLE_STRIP)


class SelectTool(CncTool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selecting = False
        self._p1: Vector2 | None = None
        self._p2: Vector2 | None = None

        self._box = None

    def cancel(self):
        if self._box:
            self.view.remove(self._box)
            self._box = None
        self._p1 = None
        self._p2 = None

    def deactivate(self):
        self.cancel()

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (event.type() == QtCore.QEvent.MouseButtonPress and
                event.button() & Qt.LeftMouseButton):
            self._p1 = vector2(event.position())
            self._p2 = self._p1
            return True
        elif (event.type() == QtCore.QEvent.MouseButtonRelease and
                event.button() & Qt.LeftMouseButton):
            if self._box:
                # TODO: do box select
                self.view.remove_item(self._box)
                self._box = None
            else:
                # TODO: do single select
                # selected = self.view.select_item(event.position())
                # if selected is not None:
                pass
            return True
        elif event.type() == QtCore.QEvent.MouseMove:
            self._p2 = vector2(event.position())

            if self._box is None and (self._p1 - self._p2).length > 10:
                self._box = SelectionBox(self.view.context, point1=self._p1, point2=self._p2)
                self.view.add_item(self._box)
            elif self._box is not None:
                self._box.position2 = self._p2

            event.widget().update()
            return True
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.code() == Qt.Key_Escape:
                self.cancel()
                return True

        return False
