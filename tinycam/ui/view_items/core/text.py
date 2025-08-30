from dataclasses import dataclass
import math
import string
from typing import cast

import moderngl as mgl
import numpy as np
from PySide6 import QtGui, QtCore

from tinycam.types import Vector2
from tinycam.ui.view import RenderState, Context
from tinycam.ui.view_items.core import Node3D


@dataclass
class GlyphInfo:
    size: tuple[int, int]
    coords: tuple[float, float, float, float]


class FontAtlas:
    def __init__(self, texture: mgl.Texture, glyphs: dict[str, GlyphInfo], line_height: int):
        self.texture = texture
        self._glyphs = glyphs
        self._line_height = line_height

    @property
    def line_height(self):
        return self._line_height

    def glyph_size(self, c: str) -> tuple[int, int] | None:
        if c not in self._glyphs:
            return None
        return self._glyphs[c].size

    def glyph_coords(self, c: str) -> tuple[float, float, float, float] | None:
        if c not in self._glyphs:
            return None
        return self._glyphs[c].coords

    @staticmethod
    def create(
        ctx: Context,
        font: QtGui.QFont,
        alphabet: str = string.printable + ' ',
    ) -> 'FontAtlas':
        metrics = QtGui.QFontMetrics(font)
        line_height = metrics.height()
        padding = 2

        # Determine glyph sizes
        glyph_sizes = {}
        for char in alphabet:
            rect = metrics.boundingRect(char)
            glyph_sizes[char] = (rect.width() + padding * 2, rect.height() + padding * 2)

        # Estimate texture size
        total_area = sum(w * h for w, h in glyph_sizes.values())
        side = int(math.sqrt(total_area))

        # Arrange glyphs
        rows = []
        row_width = 0
        row = []
        for char in sorted(glyph_sizes.keys(), key=lambda c: glyph_sizes[c][1], reverse=True):
            w = glyph_sizes[char][0]
            if row_width + w > side and row:
                rows.append((row, row_width))
                row = []
                row_width = 0
            row.append(char)
            row_width += w
        if row:
            rows.append((row, row_width))

        texture_width = max(w for _, w in rows)
        texture_height = sum(max(glyph_sizes[c][1] for c in row) for row, _ in rows)
        texture_size = (texture_width, texture_height)

        image = QtGui.QImage(texture_width, texture_height, QtGui.QImage.Format.Format_RGBA8888)
        image.fill(QtCore.Qt.GlobalColor.transparent)

        painter = QtGui.QPainter(image)
        painter.setFont(font)
        painter.setPen(QtCore.Qt.GlobalColor.white)

        glyphs = {}
        y = 0
        for row, _ in rows:
            x = 0
            max_h = max(glyph_sizes[c][1] for c in row)
            for char in row:
                w = metrics.horizontalAdvance(char)

                painter.drawText(x + padding, y + padding + metrics.ascent(), char)

                u0 = (x + padding) / texture_width
                v0 = (y + padding) / texture_height
                u1 = (x + padding + w) / texture_width
                v1 = (y + padding + line_height) / texture_height
                glyphs[char] = GlyphInfo(
                    size=(w, line_height),
                    coords=(u0, v0, u1, v1),
                )
                x += w
            y += max_h

        painter.end()

        texture = ctx.texture(texture_size, 4, cast(bytes, image.bits()))
        texture.filter = (mgl.LINEAR, mgl.LINEAR)
        return FontAtlas(texture, glyphs, line_height)


class Text(Node3D):
    def __init__(self, context, font: FontAtlas, text: str, centered: bool = False):
        super().__init__(context)

        self._program = self.context.program(
            vertex_shader='''
                #version 410 core

                uniform mat4 mvp;

                in vec2 aPosition;
                in vec2 aUV;

                out vec2 UV;

                void main() {
                    gl_Position = mvp * vec4(aPosition, 0.0, 1.0);
                    UV = aUV;
                }
            ''',
            fragment_shader='''
                #version 410 core

                uniform sampler2D font;

                in vec2 UV;
                out vec4 color;

                void main() {
                    color = texture(font, UV);
                    if (color.a == 0.0)
                        discard;
                }
            ''',
        )
        self._program["font"] = 0

        self.font_texture = font.texture

        glyph_count = sum(1 for c in text if c not in ' \n')

        x, y = 0, -font.line_height
        vertex_count = 4 * glyph_count + 2 * (glyph_count - 1) if glyph_count > 1 else 4 * glyph_count
        positions = np.zeros((vertex_count, 2), dtype='f4')
        uvs = np.zeros((vertex_count, 2), dtype='f4')
        idx = 0
        for i, c in enumerate(text):
            if c == '\n':
                x = 0
                y -= font.line_height
            elif c == ' ':
                space_size = font.glyph_size(' ')
                if space_size is None:
                    continue

                x += space_size[0]
            else:
                glyph_size = font.glyph_size(c)
                if glyph_size is None:
                    continue

                glyph_coords = font.glyph_coords(c)
                if glyph_coords is None:
                    continue

                if i > 0:
                    positions[idx] = positions[idx - 1]
                    uvs[idx] = uvs[idx - 1]
                    idx += 1

                    positions[idx] = (x, y)
                    uvs[idx] = (glyph_coords[0], glyph_coords[3])
                    idx += 1

                g_positions = positions[idx:idx + 4]
                g_uvs = uvs[idx:idx + 4]

                g_positions[0, 0:2] = (x, y)
                g_positions[1, 0:2] = (x + glyph_size[0], y)
                g_positions[2, 0:2] = (x, y + glyph_size[1])
                g_positions[3, 0:2] = (x + glyph_size[0], y + glyph_size[1])

                g_uvs[0, 0:2] = (glyph_coords[0], glyph_coords[3])
                g_uvs[1, 0:2] = (glyph_coords[2], glyph_coords[3])
                g_uvs[2, 0:2] = (glyph_coords[0], glyph_coords[1])
                g_uvs[3, 0:2] = (glyph_coords[2], glyph_coords[1])

                x += glyph_size[0]
                idx += 4

        self._width = x
        self._height = -y

        if centered:
            positions -= Vector2(self._width * 0.5, -self.height * 0.5)

        self._vbo_positions = self.context.buffer(positions.tobytes())
        self._vbo_uvs = self.context.buffer(uvs.tobytes())
        self._vao = self.context.vertex_array(
            self._program,
            [
                (self._vbo_positions, '2f', 'aPosition'),
                (self._vbo_uvs, '2f', 'aUV'),
            ],
            mode=mgl.TRIANGLE_STRIP,
        )

    @property
    def width(self) -> float:
        return self._width

    @property
    def height(self) -> float:
        return self._height

    def render(self, state: RenderState):
        self.font_texture.use(0)

        camera = state.camera
        self._program['mvp'] = (
            camera.projection_matrix * camera.view_matrix * self.world_matrix
        )
        with self.context.scope(enable=mgl.BLEND):
            self._vao.render()
