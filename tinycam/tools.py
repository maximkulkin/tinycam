import dataclasses
import enum


class CncToolType(enum.Enum):
    RECTANGULAR = 1
    VSHAPE = 2


@dataclasses.dataclass
class CncTool:
    type: CncToolType
    diameter: float
