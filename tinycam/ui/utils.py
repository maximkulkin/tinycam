from collections.abc import Sequence
import math
from pyrr import Vector3, Vector4, Quaternion
from PySide6 import QtCore
from tinycam.ui.camera import Camera
from typing import Tuple


class Point:
    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            if hasattr(args[0], 'x') and hasattr(args[0], 'y'):
                self._data = (args[0].x(), args[0].y())
            elif hasattr(args[0], 'width') and hasattr(args[0], 'height'):
                self._data = (args[0].width(), args[0].height())
            elif isinstance(args[0], (int, float)):
                self._data = (args[0], args[0])
            elif isinstance(args[0], Sequence) and len(args[0]) == 2:
                self._data = (args[0][0], args[0][1])
            else:
                raise ValueError('Invalid point data')
        elif len(args) == 2:
            self._data = (args[0], args[1])
        elif len(args) == 0 and 'x' in kwargs and 'y' in kwargs:
            self._data = (kwargs['x'], kwargs['y'])
        else:
            raise ValueError('Invalid point data')

    def __str__(self):
        return '(%g, %g)' % (self._data[0], self._data[1])

    def __repr__(self):
        return 'Point(%g, %g)' % (self._data[0], self._data[1])

    def __neg__(self):
        return self.__class__(-self._data[0], -self._data[1])

    def __add__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] + o, self._data[1] + o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] + o[0], self._data[1] + o[1])
        else:
            return self + Point(o)

    def __radd__(self, o):
        return Point(o) + self

    def __sub__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] - o, self._data[1] - o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] - o[0], self._data[1] - o[1])
        else:
            return self - Point(o)

    def __rsub__(self, o):
        return Point(o) - self

    def __mul__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] * o, self._data[1] * o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] * o[0], self._data[1] * o[1])
        else:
            return self * Point(o)

    def __rmul__(self, o):
        return Point(o) * self

    def __truediv__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] / o, self._data[1] / o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] / o[0], self._data[1] / o[1])
        else:
            return self / Point(o)

    def __rtruediv__(self, o):
        return Point(o) / self

    def __floordiv__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] // o, self._data[1] // o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] // o[0], self._data[1] // o[1])
        else:
            return self // Point(o)

    def __rfloordiv__(self, o):
        return Point(o) // self

    def __mod__(self, o):
        if isinstance(o, (int, float)):
            return self.__class__(self._data[0] % o, self._data[1] % o)
        elif isinstance(o, (Point, tuple)) and len(o) == 2:
            return self.__class__(self._data[0] % o[0], self._data[1] % o[1])
        else:
            return self % Point(o)

    def __rmod__(self, o):
        return Point(o) % self

    def __iter__(self):
        yield self._data[0]
        yield self._data[1]

    def __len__(self):
        return 2

    def __getitem__(self, index):
        if index < 0 or index > 1:
            raise ValueError('Invalid index')

        return self._data[index]

    def x(self):
        return self._data[0]

    def y(self):
        return self._data[1]

    def abs(self):
        return self.__class__(abs(self._data[0]), abs(self._data[1]))

    def toTuple(self):
        return self._data

    def toPoint(self):
        return QtCore.QPoint(self._data[0], self._data[1])

    def toPointF(self):
        return QtCore.QPointF(self._data[0], self._data[1])

Point.ZERO = Point(0.0, 0.0)
Point.ONES = Point(1.0, 1.0)


def quaternion_to_eulers(q: Quaternion) -> Vector3:
    t0 = 2.0 * (q.w * q.x + q.y * q.z)
    t1 = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
    roll = math.atan2(t0, t1)

    pitch = max(-1.0, min(1.0, 2.0 * (q.w * q.y - q.z * q.x)))

    t3 = 2.0 * (q.w * q.z + q.x * q.y)
    t4 = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    yaw = math.atan2(t3, t4)

    return roll, pitch, yaw


def unproject(point: Tuple[float, float],
              screen_size: Tuple[float, float],
              camera: 'Camera') -> Vector3:
    vp = camera.projection_matrix * camera.view_matrix
    ivp = vp.inverse

    x = 2.0 * point[0] / screen_size[0] - 1.0
    y = 2.0 * point[1] / screen_size[1] - 1.0

    p = Vector4((x, -y, 0.0, 1.0))
    v = ivp * p
    if v.w != 0.0:
        v /= v.w

    r = Vector3((v.x, v.y, v.z))
    r -= r.z * (camera.position - r) / (camera.position.z - r.z)
    return r
