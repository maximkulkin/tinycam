from tinycam.geometry import Geometry
from tinycam.settings import SETTINGS

__all__ = [
    'CncGlobals',
]

class CncGlobals:
    GEOMETRY = Geometry()
    APP = None
    SETTINGS = SETTINGS
