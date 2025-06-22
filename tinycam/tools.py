import enum
import math

import tinycam.properties as p
import tinycam.settings as s


class CncToolType(enum.Enum):
    RECTANGULAR = 1
    VSHAPE = 2

    def __str__(self) -> str:
        match self:
            case self.RECTANGULAR: return 'Rectangular'
            case self.VSHAPE: return 'V-shape'


class CncTool(p.ReferenceType, p.EditableObject):
    def _update(self):
        self._signal_changed()

    type = p.Property[CncToolType](
        on_update=_update,
        default=CncToolType.RECTANGULAR,
        metadata=[
            p.Order(0),
        ],
    )

    # Rectangular tool properties
    diameter = p.Property[float](on_update=_update, default=1.0, metadata=[
        p.VisibleIf(lambda tool: tool.type == CncToolType.RECTANGULAR),
        p.Order(1),
        p.Suffix('{units}'),
    ])

    # V-shape tool properties
    angle = p.Property[int](on_update=_update, default=30, metadata=[
        p.VisibleIf(lambda tool: tool.type == CncToolType.VSHAPE),
        p.Order(2),
        p.Suffix('deg'),
    ])
    tip_diameter = p.Property[float](on_update=_update, default=0.1, metadata=[
        p.VisibleIf(lambda tool: tool.type == CncToolType.VSHAPE),
        p.Order(3),
        p.Suffix('{units}'),
    ])

    def get_diameter(self, depth: float) -> float:
        match self.type:
            case CncToolType.RECTANGULAR:
                return self.diameter
            case CncToolType.VSHAPE:
                return (
                    self.tip_diameter +
                    2 * math.tan(math.radians(self.angle)) * depth
                )

    def __str__(self) -> str:
        match self.type:
            case CncToolType.RECTANGULAR:
                return f'Rectangular dia={self.diameter}{p.format_suffix("{units}")}'
            case CncToolType.VSHAPE:
                return f'V-shape angle={self.angle}deg dia={self.tip_diameter}{p.format_suffix("{units}")}'

    @classmethod
    def all_instances(cls):
        return s.SETTINGS['tools/tools'].value


class CncToolSerializer(s.ObjectSerializer):
    type = CncTool


s.SETTINGS.register('tools/tools', s.CncListSetting[CncTool], default=[])
