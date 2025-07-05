from tinycam import grbl
from tinycam.geometry import Geometry
from tinycam.settings import SETTINGS, CncSettings
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from tinycam.application import CncApplication

__all__ = [
    'CncGlobals',
    'GLOBALS',
]


class CncGlobals:
    GEOMETRY: Geometry = Geometry()
    APP: 'CncApplication'
    SETTINGS: CncSettings = SETTINGS
    CNC_CONTROLLER: grbl.Controller = grbl.Controller()


GLOBALS = CncGlobals
