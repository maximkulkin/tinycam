import numpy as np
from numbers import Number as number
import pyrr


class Vector1Proxy:
    def __init__(self, index: int):
        self._index = index

    def __get__(self, obj: object, cls) -> np.float32:
        return obj[self._index]

    def __set__(self, obj: object, value: number | np.number):
        obj[self._index] = value


class Vector2Proxy:
    def __init__(self, index: tuple[int, int]):
        self._index = index

    def __get__(self, obj: object, cls) -> 'Vector2':
        return Vector2(obj[self._index,])

    def __set__(self, obj: object, value: 'Vector2 | np.ndarray | list[number | np.number]'):
        obj[self._index,] = value


class Vector3Proxy:
    def __init__(self, index: tuple[int, int, int]):
        self._index = index

    def __get__(self, obj: object, cls) -> 'Vector3':
        return Vector3(obj[self._index,])

    def __set__(self, obj: object, value: 'Vector3 | np.ndarray | list[number | np.number]'):
        obj[self._index,] = value


class Vector2(np.ndarray):
    def __new__(
        cls,
        x_or_data: number = 0.0,
        y: number = 0.0,
    ):
        if isinstance(x_or_data, (number, np.number)):
            return np.array([np.float32(x_or_data), np.float32(y)], dtype='f4').view(cls)
        return np.array(x_or_data, dtype='f4').view(cls)

    x = Vector1Proxy(0)
    y = Vector1Proxy(1)

    @property
    def length(self) -> np.float32:
        return pyrr.vector.length(self)

    @property
    def normalized(self) -> 'Vector2':
        v = Vector2(self.x, self.y)
        v.normalize()
        return v

    def normalize(self):
        l = self.length
        if l != 0.0:
            self /= l

    # @staticmethod
    # def dot(v1: 'Vector2', v2: 'Vector2') -> float:
    #     return np.dot(v1, v2)

    @staticmethod
    def lerp(v1: 'Vector2', v2: 'Vector2', delta: float) -> 'Vector2':
        return v1 * delta + v2 * (1.0 - delta)

    def __str__(self) -> str:
        return f'Vector2({self.x}, {self.y})'

    def __repr__(self) -> str:
        return str(self)


class Vector3(pyrr.Vector3):
    def __new__(
        cls,
        x_or_data: number | np.ndarray = 0.0,
        y: number = 0.0,
        z: number = 0.0
    ):
        if isinstance(x_or_data, (number, np.number)):
            return np.array([np.float32(x_or_data), np.float32(y), np.float32(z)], dtype='f4').view(cls)
        return np.array(x_or_data, dtype='f4').view(cls)

    xy = Vector2Proxy((0, 1))
    xz = Vector2Proxy((0, 2))
    yz = Vector2Proxy((1, 2))

    @property
    def length(self) -> np.float32:
        return pyrr.vector.length(self)

    @property
    def normalized(self) -> 'Vector3':
        v = Vector3(self.x, self.y, self.z)
        v.normalize()
        return v

    def normalize(self):
        l = self.length
        if l != 0.0:
            self /= l

    # @staticmethod
    # def dot(v1: 'Vector3', v2: 'Vector3') -> float:
    #     return np.dot(v1, v2)

    @classmethod
    def lerp(cls, v1: 'Vector3', v2: 'Vector3', delta: float) -> 'Vector3':
        return pyrr.vector.interpolate(v1, v2, delta).view(cls)

    def __add__(self, other) -> 'Vector3':
        return super().__add__(other).view(Vector3)

    def __sub__(self, other) -> 'Vector3':
        return super().__sub__(other).view(Vector3)

    def __mul__(self, other) -> 'Vector3':
        return super().__mul__(other).view(Vector3)

    def __div__(self, other) -> 'Vector3':
        return super().__div__(other).view(Vector3)

    def __truediv__(self, other) -> 'Vector3':
        return super().__truediv__(other).view(Vector3)

    def __str__(self) -> str:
        return f'Vector3({self.x}, {self.y}, {self.z})'

    def __repr__(self) -> str:
        return str(self)


class Vector4(pyrr.Vector4):
    def __new__(
        cls,
        x_or_data: number | np.ndarray | list | tuple = 0.0,
        y: number = 0.0,
        z: number = 0.0,
        w: number = 0.0,
    ):
        if isinstance(x_or_data, (number, np.number)):
            return np.array([
                np.float32(x_or_data), np.float32(y), np.float32(z), np.float32(w),
            ], dtype='f4').view(cls)
        return np.array(x_or_data, dtype='f4').view(cls)

    xy = Vector2Proxy((0, 1))
    xz = Vector2Proxy((0, 2))
    yz = Vector2Proxy((1, 2))
    xyz = Vector3Proxy((0, 1, 2))

    def __add__(self, other) -> 'Vector4':
        return super().__add__(other).view(Vector4)

    def __sub__(self, other) -> 'Vector4':
        return super().__sub__(other).view(Vector4)

    def __mul__(self, other) -> 'Vector4':
        return super().__mul__(other).view(Vector4)

    def __div__(self, other) -> 'Vector4':
        return super().__div__(other).view(Vector4)

    def __truediv__(self, other) -> 'Vector4':
        return super().__truediv__(other).view(Vector4)

    def __str__(self) -> str:
        return f'Vector4({self.x}, {self.y}, {self.z}, {self.w})'

    def __repr__(self) -> str:
        return str(self)


class Quaternion(pyrr.Quaternion):
    def __mul__(self, other):
        return super().__mul__(other).view(other.__class__)

    def __str__(self) -> str:
        return f'Quaternion({self[0]}, {self[1]}, {self[2]}, {self[3]})'

    def __repr__(self) -> str:
        return str(self)


class Matrix44(pyrr.Matrix44):
    def __new__(cls, value: 'Matrix44 | np.ndarray | list[number | np.number] | None') -> 'Matrix44':
        if value is None:
            return np.zeros((4, 4), dtype='f4').view(cls)
        return np.array(value, dtype='f4').view(cls)

    @classmethod
    def identity(cls) -> 'Matrix44':
        return pyrr.matrix44.create_identity(dtype='f4').view(cls)

    @classmethod
    def from_translation(cls, translation: Vector3) -> 'Matrix44':
        return pyrr.matrix44.create_from_translation(translation).view(cls)

    @classmethod
    def from_rotation(cls, rotation: Quaternion) -> 'Matrix44':
        return pyrr.matrix44.create_from_quaternion(rotation).view(cls)

    @classmethod
    def from_scale(cls, scale: Vector3) -> 'Matrix44':
        return pyrr.matrix44.create_from_scale(scale).view(cls)

    @classmethod
    def look_at(cls, eye: Vector3, target: Vector3, up: Vector3) -> 'Matrix44':
        return pyrr.matrix44.create_look_at(eye, target, up).view(cls)

    @classmethod
    def orthogonal_projection(
        cls,
        left: number | np.number,
        right: number | np.number,
        bottom: number | np.number,
        top: number | np.number,
        near: number | np.number,
        far: number | np.number,
    ) -> 'Matrix44':
        return pyrr.matrix44.create_orthogonal_projection(
            float(left), float(right),
            float(bottom), float(top),
            float(near), float(far),
        ).view(cls)

    @classmethod
    def perspective_projection(
        cls,
        fov: number | np.number,
        aspect: number | np.number,
        near: number | np.number,
        far: number | np.number,
    ) -> 'Matrix44':
        return pyrr.matrix44.create_perspective_projection(
            float(fov), float(aspect),
            float(near), float(far),
            dtype='f4',
        ).view(cls)

    def __mul__(self, other: 'Vector4 | Matrix44') -> 'Vector4 | Matrix44':
        if isinstance(other, Matrix44):
            return super().__mul__(other).view(Matrix44)
        elif isinstance(other, Vector4):
            return super().__mul__(other).view(Vector4)
        else:
            raise ValueError(f'Invalid value type: {other}')


__all__ = [
    'Vector2',
    'Vector3',
    'Vector4',
    'Quaternion',
    'Matrix44',
]
