import math
import numpy as np
import pyrr


type number = int | float | np.number


class Vector1Proxy:
    def __init__(self, index: int):
        self._index = index

    def __get__(self, obj: np.ndarray, cls) -> np.float32:
        return obj[self._index]

    def __set__(self, obj: np.ndarray, value: number):
        obj[self._index] = value


class Vector2Proxy:
    def __init__(self, index: tuple[int, int]):
        self._index = index

    def __get__(self, obj: np.ndarray, cls) -> 'Vector2':
        return Vector2(obj[self._index,])

    def __set__(self, obj: np.ndarray, value: 'Vector2 | np.ndarray | tuple[number, number]'):
        obj[self._index,] = value


class Vector3Proxy:
    def __init__(self, index: tuple[int, int, int]):
        self._index = index

    def __get__(self, obj: np.ndarray, cls) -> 'Vector3':
        return Vector3(obj[self._index,])

    def __set__(self, obj: np.ndarray, value: 'Vector3 | np.ndarray | tuple[number, number, number]'):
        obj[self._index,] = value


class Vector2(np.ndarray):
    def __new__(
        cls,
        x_or_data: number | tuple[number, number] | np.ndarray = 0.0,
        y: number = 0.0,
    ):
        if isinstance(x_or_data, (int, float, np.number)):
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
        return Vector2(v1 * delta + v2 * (1.0 - delta))

    def __str__(self) -> str:
        return f'Vector2({self.x}, {self.y})'

    def __repr__(self) -> str:
        return str(self)


class Vector3(pyrr.Vector3):
    def __new__(
        cls,
        x_or_data: number | tuple[number, number, number] |  np.ndarray = 0.0,
        y: number = 0.0,
        z: number = 0.0
    ):
        if isinstance(x_or_data, (int, float, np.number)):
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
        x_or_data: number | np.ndarray | tuple[number, number, number, number] = 0.0,
        y: number = 0.0,
        z: number = 0.0,
        w: number = 0.0,
    ):
        if isinstance(x_or_data, (int, float, np.number)):
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

    @property
    def conjugate(self) -> 'Quaternion':
        return super().conjugate.view(Quaternion)

    @classmethod
    def from_x_rotation(cls, angle: float | np.number):
        return pyrr.Quaternion.from_x_rotation(angle).view(cls)

    @classmethod
    def from_y_rotation(cls, angle: float | np.number):
        return pyrr.Quaternion.from_y_rotation(angle).view(cls)

    @classmethod
    def from_z_rotation(cls, angle: float | np.number):
        return pyrr.Quaternion.from_z_rotation(angle).view(cls)

    def to_eulers(self) -> Vector3:
        t0 = 2.0 * (self.w * self.x + self.y * self.z)
        t1 = 1.0 - 2.0 * (self.x * self.x + self.y * self.y)
        roll = math.atan2(t0, t1)

        pitch = max(-1.0, min(1.0, 2.0 * (self.w * self.y - self.z * self.x)))

        t3 = 2.0 * (self.w * self.z + self.x * self.y)
        t4 = 1.0 - 2.0 * (self.y * self.y + self.z * self.z)
        yaw = math.atan2(t3, t4)

        return Vector3(roll, pitch, yaw)


class Matrix44(pyrr.Matrix44):
    def __new__(cls, value: 'Matrix44 | np.ndarray | list[number] | None') -> 'Matrix44':
        if value is None:
            return np.zeros((4, 4), dtype='f4').view(cls)
        return np.array(value, dtype='f4').view(cls)

    @classmethod
    def identity(cls) -> 'Matrix44':
        return pyrr.matrix44.create_identity(dtype='f4').view(cls)

    @classmethod
    def from_translation(cls, translation: Vector3) -> 'Matrix44':
        return pyrr.matrix44.create_from_translation(translation, dtype='f4').view(cls)

    @classmethod
    def from_rotation(cls, rotation: Quaternion) -> 'Matrix44':
        return pyrr.matrix44.create_from_quaternion(rotation, dtype='f4').view(cls)

    @classmethod
    def from_scale(cls, scale: Vector3) -> 'Matrix44':
        return pyrr.matrix44.create_from_scale(scale, dtype='f4').view(cls)

    @classmethod
    def look_at(cls, eye: Vector3, target: Vector3, up: Vector3) -> 'Matrix44':
        return pyrr.matrix44.create_look_at(eye, target, up, dtype='f4').view(cls)

    @classmethod
    def orthogonal_projection(
        cls,
        left: number,
        right: number,
        bottom: number,
        top: number,
        near: number,
        far: number,
    ) -> 'Matrix44':
        return pyrr.matrix44.create_orthogonal_projection(
            left=float(left), right=float(right),
            bottom=float(bottom), top=float(top),
            near=float(near), far=float(far),
            dtype='f4',
        ).view(cls)

    @classmethod
    def perspective_projection(
        cls,
        fov: number,
        aspect: number,
        near: number,
        far: number,
    ) -> 'Matrix44':
        return pyrr.matrix44.create_perspective_projection(
            fovy=float(fov), aspect=float(aspect),
            near=float(near), far=float(far),
            dtype='f4',
        ).view(cls)

    def __mul__(self, other: 'Vector4 | Matrix44') -> 'Vector4 | Matrix44':
        if isinstance(other, Matrix44):
            return super().__mul__(other).view(Matrix44)
        elif isinstance(other, Vector4):
            return super().__mul__(other).view(Vector4)
        else:
            raise ValueError(f'Invalid value type: {other}')

    @property
    def inverse(self) -> 'Matrix44':
        return super().inverse.view(Matrix44)

    def decompose(self) -> tuple[Vector3, Quaternion, Vector3]:
        scale, rotation, translation = pyrr.matrix44.decompose(self)
        return scale.view(Vector3), rotation.view(Quaternion), translation.view(Vector3)


class Rect(np.ndarray):
    def __new__(
        cls,
        x: number,
        y: number,
        width: number,
        height: number,
    ):
        return np.array([x, y, width, height]).view(cls)

    x = Vector1Proxy(0)
    y = Vector1Proxy(1)
    width = Vector1Proxy(2)
    height = Vector1Proxy(3)

    point = Vector2Proxy((0, 1))
    size = Vector2Proxy((2, 3))

    @staticmethod
    def from_point_and_size(bottom_left: Vector2, size: Vector2) -> 'Rect':
        return Rect(bottom_left.x, bottom_left.y, size.x, size.y)


__all__ = [
    'Vector2',
    'Vector3',
    'Vector4',
    'Quaternion',
    'Matrix44',
    'Rect',
]
