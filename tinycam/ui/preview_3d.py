import numpy as np
from OpenGL import GL
from PySide6 import Qt3DRender, QtGui, QtWidgets, QtOpenGL, QtOpenGLWidgets


_VERTEX_SHADER = '''
    uniform mat4 projection_matrix;
    uniform mat4 model_view_matrix;

    attribute vec3 position;

    void main() {
        gl_Position = projection_matrix * model_view_matrix * vec4(position, 1.0);
    }
'''

_FRAGMENT_SHADER = '''
    void main() {
        gl_FragColor = vec4(0.8, 0.8, 0.8, 1.0);
    }
'''


class CncPreviewView(QtOpenGLWidgets.QOpenGLWidget):
    # def __init__(self, parent=None):
    #     super().__init__(parent=parent)

    #     fmt = QtGui.QSurfaceFormat()
    #     fmt.setSamples(16)
    #     self.setFormat(fmt)

    def initializeGL(self):
        # self._context = QtGui.QOpenGLContext()
        # self._context.makeCurrent()
        self.f = QtGui.QOpenGLContext.currentContext().functions()
        self.f.glClearColor(0.8, 0.8, 0.8, 1.0)

        self._projection = QtGui.QMatrix4x4()

        self._camera = QtGui.QMatrix4x4()
        self._camera.setToIdentity()
        self._camera.translate(0.0, 0.0, -5.0)

        self._box_vao = QtOpenGL.QOpenGLVertexArrayObject()
        self._box_vao.create()

        vao_binder = QtOpenGL.QOpenGLVertexArrayObject.Binder(self._box_vao)

        self._box_vbo = QtOpenGL.QOpenGLBuffer()
        self._box_vbo.create()
        self._box_vbo.bind()
        self._box_vbo.allocate(np.array([
              0.0,   0.0, 0.0,
              0.0, 100.0, 0.0,
            100.0, 100.0, 0.0,
            100.0,   0.0, 0.0,
              0.0,   0.0, 0.0,
        ], dtype='float32'), 5)

        self._program = QtOpenGL.QOpenGLShaderProgram()
        self._program.addShaderFromSourceCode(QtOpenGL.QOpenGLShader.Vertex, _VERTEX_SHADER)
        self._program.addShaderFromSourceCode(QtOpenGL.QOpenGLShader.Fragment, _FRAGMENT_SHADER)
        self._program.bindAttributeLocation("position", 0)
        self._program.link()
        self._projection_matrix_location = self._program.uniformLocation("projection_matrix");
        self._model_view_matrix_location = self._program.uniformLocation("model_view_matrix");

    def resizeGL(self, w, h):
        self._projection.setToIdentity()
        self._projection.perspective(45.0, w / float(h), 0.001, 1000.0)

    def paintGL(self):
        self.f.glClear(GL.GL_COLOR_BUFFER_BIT | GL.GL_DEPTH_BUFFER_BIT)

        self._program.bind()
        self._program.setUniformValue(self._projection_matrix_location, self._projection)
        self._program.setUniformValue(self._model_view_matrix_location, self._camera)
        self.f.glDrawArrays(GL.GL_TRIANGLES, 0, self._box_vbo.size())

        self._program.release()
