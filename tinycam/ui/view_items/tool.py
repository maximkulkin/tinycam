import moderngl as mgl
import numpy as np

from tinycam.tools import CncTool, CncToolType
from tinycam.math_types import Vector2, Vector4
from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core.node3d import Node3D


class Tool(Node3D):
    def __init__(self, context: Context, tool: CncTool):
        super().__init__(context)

        self._tool = tool

        segments = 16
        height = 15.0

        match tool.type:
            case CncToolType.RECTANGULAR:
                radius = tool.diameter

                positions = np.zeros((segments * 2 + 2, 3), dtype='f4')
                for i in range(segments):
                    angle = 2 * np.pi * i / segments

                    positions[i, 0:2] = (
                        np.cos(angle) * radius,
                        np.sin(angle) * radius
                    )

                positions[segments:2*segments] = positions[:segments]
                positions[segments:2*segments, 2] = height

                bottom_point_idx = 2 * segments
                top_point_idx = bottom_point_idx + 1

                positions[bottom_point_idx] = (0., 0., 0.)
                positions[top_point_idx] = (0., 0., height)

                indexes = np.zeros(segments * 12, dtype='i4')
                idx = 0
                for i in range(segments):
                    i_next = (i + 1) % segments
                    indexes[idx:idx + 12] = (
                        i, i_next + segments, i + segments,
                        i, i_next, i_next + segments,
                        bottom_point_idx, i_next, i,
                        top_point_idx, i + segments, i_next + segments,
                    )
                    idx += 12

            case CncToolType.VSHAPE:
                r1 = tool.tip_diameter
                r2 = 1.5

                h1 = (r2 - r1) * 0.5 / np.tan(tool.angle * 0.5 / 180 * np.pi)

                positions = np.zeros((segments * 3 + 2, 3), dtype='f4')
                for i in range(segments):
                    angle = 2 * np.pi * i / segments

                    v = Vector2(np.cos(angle), np.sin(angle))
                    positions[i, 0:2] = v * r1
                    positions[i + segments, 0:2] = v * r2
                    positions[i + 2 *segments, 0:2] = v * r2

                positions[1*segments:2*segments, 2] = h1
                positions[2*segments:3*segments, 2] = height

                bottom_point_idx = 3 * segments
                top_point_idx = bottom_point_idx + 1

                positions[bottom_point_idx] = (0., 0., 0.)
                positions[top_point_idx] = (0., 0., height)

                indexes = np.zeros(segments * 18, dtype='i4')
                idx = 0
                for i in range(segments):
                    i_next = (i + 1) % segments
                    indexes[idx:idx + 18] = (
                        i, i_next + segments, i + segments,
                        i, i_next, i_next + segments,
                        i + segments, i_next + 2 * segments, i + 2 * segments,
                        i + segments, i_next + segments, i_next + 2 * segments,
                        bottom_point_idx, i_next, i,
                        top_point_idx, i + 2 * segments, i_next + 2 * segments,
                    )
                    idx += 18

        self._program = context.program(
            vertex_shader='''
                #version 410 core

                in vec3 position;
                uniform mat4 mvp;

                void main() {
                    gl_Position = mvp * vec4(position, 1.0);
                }
            ''',
            fragment_shader='''
                #version 410 core

                uniform vec4 color;
                out vec4 fragment_color;

                void main() {
                    fragment_color = color;
                }
            '''
        )

        self._positions_vbo = self.context.buffer(positions)
        self._ibo = self.context.buffer(indexes)

        self._vao = self.context.vertex_array(
            self._program,
            [(self._positions_vbo, '3f', 'position')],
            index_buffer=self._ibo,
            mode=mgl.TRIANGLES,
        )

    @property
    def tool(self) -> CncTool:
        return self._tool

    def render(self, state: RenderState):
        self._program['color'] = Vector4(1, 1, 1, 1)
        self._program['mvp'] = (
            state.camera.projection_matrix *
            state.camera.view_matrix *
            self.world_matrix
        )

        with self.context.scope(enable=mgl.DEPTH_TEST):
            self._vao.render()

        super().render(state)
