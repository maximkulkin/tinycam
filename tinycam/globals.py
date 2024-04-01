from tinycam.geometry import Geometry
from tinycam.settings import SETTINGS

__all__ = [
    'CncGlobals',
    'GLOBALS',
]

class CncGlobals:
    GEOMETRY = Geometry()
    APP = None
    SETTINGS = SETTINGS

GLOBALS = CncGlobals
