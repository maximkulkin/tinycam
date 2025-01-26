from tinycam.cnc_controller import CncController
from tinycam.geometry import Geometry
from tinycam.settings import SETTINGS, CncSettings

__all__ = [
    'CncGlobals',
    'GLOBALS',
]


class CncGlobals:
    GEOMETRY: Geometry = Geometry()
    APP = None
    SETTINGS: CncSettings = SETTINGS
    CNC_CONTROLLER: CncController = CncController()


GLOBALS = CncGlobals
