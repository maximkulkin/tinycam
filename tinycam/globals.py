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


GLOBALS = CncGlobals
