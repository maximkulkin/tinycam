import numpy as np
from pyrr import Vector3, Vector4, Quaternion, Matrix44


class Vector2(np.ndarray):
    def __new__(cls, values):
        return np.array(values).view(cls)


__all__ = [
    'Vector2',
    'Vector3',
    'Vector4',
    'Quaternion',
    'Matrix44',
]
