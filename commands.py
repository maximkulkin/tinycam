from dataclasses import dataclass
from typing import Optional


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
    speed: float


class CncCommandBuilder:
    def __init__(self, start_position=(0, 0, 0)):
        self._commands = []
        self._position = start_position

    @property
    def current_position(self):
        return self._position

    def travel(self, x=None, y=None, z=None):
        self._commands.append(CncTravelCommand(x=x, y=y, z=z))

    def cut(self, x=None, y=None, z=None, dx=None, dy=None, dz=None):
        self._commands.append(CncCutCommand(x=x, y=y, z=z))

    def set_cut_speed(self, speed):
        self._commands.append(CncSetCutSpeed(speed))

    def set_spindle_speed(self, speed):
        self._commands.append(CncSetSpindleSpeed(speed))

    def append(self, command):
        self._commands.append(command)

    def build(self):
        return self._commands
