from collections.abc import Sequence

from PySide6 import QtCore


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
