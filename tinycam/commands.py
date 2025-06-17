from collections.abc import Sequence
import enum
from dataclasses import dataclass
from typing import Optional
from tinycam.types import Vector3


class CncCommand:
    pass


@dataclass
class CncTravelCommand(CncCommand):
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None


@dataclass
class CncCutCommand(CncCommand):
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None


@dataclass
class CncSetCutSpeed(CncCommand):
    speed: float


@dataclass
class CncSetSpindleSpeed(CncCommand):
    speed: int


class CncCommandBuilder:
    def __init__(self, start_position: Vector3 | None = None):
        self._commands = []
        self._position = start_position or Vector3()

    @property
    def current_position(self) -> Vector3:
        return self._position

    def travel(
        self, x: float | None = None,
        y: float | None = None,
        z: float | None = None,
    ):
        self._commands.append(CncTravelCommand(x=x, y=y, z=z))

    def cut(
        self,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
    ):
        self._commands.append(CncCutCommand(x=x, y=y, z=z))

    def set_cut_speed(self, speed: float):
        self._commands.append(CncSetCutSpeed(speed))

    def set_spindle_speed(self, speed: int):
        self._commands.append(CncSetSpindleSpeed(speed))

    def append(self, command: CncCommand):
        self._commands.append(command)

    def build(self) -> list[CncCommand]:
        return self._commands


class CncPathType(enum.Enum):
    TRAVEL = enum.auto()
    CUT = enum.auto()


@dataclass
class CncPath:
    type: CncPathType
    start: Vector3
    end: Vector3


class CncPathTracer:
    def __init__(self, start_position: Vector3 | None = None):
        self._position = start_position or Vector3()
        self._paths = []

    @property
    def paths(self) -> Sequence[CncPath]:
        return self._paths

    def execute_command(self, command: CncCommand):
        match command:
            case CncTravelCommand(x, y, z):
                next_position = self._update_position(self._position, x=x, y=y, z=z)
                self._paths.append(CncPath(
                    type=CncPathType.TRAVEL,
                    start=self._position,
                    end=next_position,
                ))
                self._position = next_position
            case CncCutCommand(x, y, z):
                next_position = self._update_position(self._position, x=x, y=y, z=z)
                self._paths.append(CncPath(
                    type=CncPathType.CUT,
                    start=self._position,
                    end=next_position,
                ))
                self._position = next_position
            case _:
                pass

    def execute_commands(self, commands: Sequence[CncCommand]):
        for command in commands:
            self.execute_command(command)

    def _update_position(
        self,
        position: Vector3,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None,
    ):
        x = x if x is not None else position.x
        y = y if y is not None else position.y
        z = z if z is not None else position.z
        return Vector3(x, y, z)
