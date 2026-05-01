from PySide6 import QtGui
import os.path

from tinycam.formats import excellon
from tinycam.globals import GLOBALS
from tinycam.project.item import CncProjectItem
from tinycam.math_types import Vector2


class ExcellonItem(CncProjectItem):
    def __init__(self):
        super().__init__()
        self.color = QtGui.QColor.fromRgbF(0.6, 0.0, 0.0, 0.6)
        self._tools = []
        self._drills = []
        self._mills = []

    @property
    def tools(self) -> list[excellon.Tool]:
        return self._tools

    @tools.setter
    def tools(self, value: list[excellon.Tool]):
        if self._tools == value:
            return
        self._tools = value
        self._signal_changed()

    @property
    def drills(self) -> list[excellon.Drill]:
        return self._drills

    @drills.setter
    def drills(self, value: list[excellon.Drill]):
        if self._drills == value:
            return
        self._drills = value
        self._signal_changed()

    @property
    def mills(self) -> list[excellon.Mill]:
        return self._mills

    @mills.setter
    def mills(self, value: list[excellon.Mill]):
        if self._mills == value:
            return
        self._mills = value
        self._signal_changed()

    def save(self) -> dict:
        data = super().save()
        data['geometry'] = GLOBALS.GEOMETRY.to_wkt(self._geometry)
        data['tools'] = [
            {'id': t.id, 'diameter': t.diameter}
            for t in self._tools
        ]
        data['drills'] = [
            {'tool_id': d.tool_id, 'position': [d.position.x, d.position.y]}
            for d in self._drills
        ]
        data['mills'] = [
            {'tool_id': m.tool_id, 'positions': [[p.x, p.y] for p in m.positions]}
            for m in self._mills
        ]
        return data

    def load(self, data: dict) -> None:
        super().load(data)
        if 'geometry' in data:
            self._geometry = GLOBALS.GEOMETRY.from_wkt(data['geometry'])
            self._bounds = None
        if 'tools' in data:
            self._tools = [
                excellon.Tool(id=t['id'], diameter=t['diameter'])
                for t in data['tools']
            ]
        if 'drills' in data:
            self._drills = [
                excellon.Drill(tool_id=d['tool_id'], position=Vector2(d['position'][0], d['position'][1]))
                for d in data['drills']
            ]
        if 'mills' in data:
            self._mills = [
                excellon.Mill(tool_id=m['tool_id'], positions=[Vector2(p[0], p[1]) for p in m['positions']])
                for m in data['mills']
            ]

    def translate(self, offset: Vector2):
        for drill in self._drills:
            drill.position += offset

        for mill in self._mills:
            mill.positions = [
                position + offset
                for position in mill.positions
            ]

        self.geometry = GLOBALS.GEOMETRY.translate(self.geometry, offset)

    def scale(self, scale: Vector2, origin: Vector2 = Vector2()):
        factor = min(scale.x, scale.y)

        for tool in self._tools:
            tool.diameter *= factor

        def do_scale(p: Vector2) -> Vector2:
            return origin + (p - origin) * scale

        if scale.x != scale.y:
            # TODO: convert drills into mills
            for drill in self._drills:
                drill.position = do_scale(drill.position)

        else:
            for drill in self._drills:
                drill.position = do_scale(drill.position)

            for mill in self._mills:
                mill.positions = [
                    do_scale(position)
                    for position in mill.positions
                ]

        self.geometry = GLOBALS.GEOMETRY.scale(
            self.geometry,
            factor=scale,
            origin=origin,
        )

    @staticmethod
    def from_file(path) -> 'ExcellonItem':
        with open(path, 'rt') as f:
            G = GLOBALS.GEOMETRY
            excellon_file = excellon.parse_excellon(f.read(), geometry=G)

            item = ExcellonItem()
            item.name = os.path.basename(path)
            item.geometry = excellon_file.geometry
            item.tools = excellon_file.tools
            item.drills = excellon_file.drills
            item.mills = excellon_file.mills

            return item
