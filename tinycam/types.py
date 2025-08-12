import math
import numpy as np
import pyrr
from typing import overload


type number = int | float | np.number
type Point2Like = 'Vector2 | tuple[number, number]'
type Point3Like = 'Vector3 | tuple[number, number, number]'


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

    def __add__(self, other: 'number | Vector2') -> 'Vector2':
        return super().__add__(other).view(Vector2)

    def __sub__(self, other: 'number | Vector2') -> 'Vector2':
        return super().__sub__(other).view(Vector2)

    def __mul__(self, other: 'number | Vector2') -> 'Vector2':
        return super().__mul__(other).view(Vector2)

    def __div__(self, other: 'number | Vector2') -> 'Vector2':
        return super().__div__(other).view(Vector2)

    def __truediv__(self, other: 'number | Vector2') -> 'Vector2':
        return super().__truediv__(other).view(Vector2)

    def __eq__(self, other: 'Vector2') -> bool:
        return np.array_equal(self, other)

    def __ne__(self, other: 'Vector2') -> bool:
        return not np.array_equal(self, other)

    def __str__(self) -> str:
        return f'Vector2({self.x}, {self.y})'

    def __repr__(self) -> str:
        return str(self)


class Vector3(pyrr.Vector3):
    def __new__(
        cls,
        x_or_data: number | tuple[number, number, number] | np.ndarray = 0.0,
        y: number = 0.0,
        z: number = 0.0
    ):
        if isinstance(x_or_data, (int, float, np.number)):
            return np.array([np.float32(x_or_data), np.float32(y), np.float32(z)], dtype='f4').view(cls)
        return np.array(x_or_data, dtype='f4').view(cls)

    xy = Vector2Proxy((0, 1))
    xz = Vector2Proxy((0, 2))
    yz = Vector2Proxy((1, 2))

    @classmethod
    def from_vector2(cls, v: Vector2, z: number = 0.0) -> 'Vector3':
        return Vector3(v[0], v[1], z)

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

    def __add__(self, other: 'number | Vector3') -> 'Vector3':
        return super().__add__(other).view(Vector3)

    def __sub__(self, other: 'number | Vector3') -> 'Vector3':
        return super().__sub__(other).view(Vector3)

    def __mul__(self, other: 'number | Vector3') -> 'Vector3':
        return super().__mul__(other).view(Vector3)

    def __div__(self, other: 'number | Vector3') -> 'Vector3':
        return super().__div__(other).view(Vector3)

    def __truediv__(self, other: 'number | Vector3') -> 'Vector3':
        return super().__truediv__(other).view(Vector3)

    def __eq__(self, other: 'Vector3') -> bool:
        return np.array_equal(self, other)

    def __ne__(self, other: 'Vector3') -> bool:
        return not np.array_equal(self, other)

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
        w: number = 1.0,
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

    @classmethod
    def from_vector2(cls, v: Vector2, z: number = 0.0, w: number = 1.0) -> 'Vector4':
        return Vector4(v[0], v[1], z, w)

    @classmethod
    def from_vector3(cls, v: Vector3, w: number = 1.0) -> 'Vector4':
        return Vector4(v[0], v[1], v[2], w)

    def dehomogenize(self) -> 'Vector4':
        w = self.w
        if w == 0.0:
            raise ValueError('Cant dehomogenize, W component is zero')
        return Vector4(self[0] / w, self[1] / w, self[2] / w, 1.0)

    def __add__(self, other: 'number | Vector4') -> 'Vector4':
        return super().__add__(other).view(Vector4)

    def __sub__(self, other: 'number | Vector4') -> 'Vector4':
        return super().__sub__(other).view(Vector4)

    def __mul__(self, other: 'number | Vector4') -> 'Vector4':
        return super().__mul__(other).view(Vector4)

    def __div__(self, other: 'number | Vector4') -> 'Vector4':
        return super().__div__(other).view(Vector4)

    def __truediv__(self, other: 'number | Vector4') -> 'Vector4':
        return super().__truediv__(other).view(Vector4)

    def __eq__(self, other: 'Vector4') -> bool:
        return np.array_equal(self, other)

    def __ne__(self, other: 'Vector4') -> bool:
        return not np.array_equal(self, other)

    def __str__(self) -> str:
        return f'Vector4({self.x}, {self.y}, {self.z}, {self.w})'

    def __repr__(self) -> str:
        return str(self)


class Quaternion(pyrr.Quaternion):
    @overload
    def __mul__(self, other: Vector3) -> Vector3:
        ...

    @overload
    def __mul__(self, other: Vector4) -> Vector4:
        ...

    @overload
    def __mul__(self, other: 'Quaternion') -> 'Quaternion':
        ...

    def __mul__(self, other):
        return super().__mul__(other).view(other.__class__)

    def __eq__(self, other: 'Quaternion') -> bool:
        return np.array_equal(self, other)

    def __ne__(self, other: 'Quaternion') -> bool:
        return not np.array_equal(self, other)

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

    @overload
    def __mul__(self, other: 'Matrix44') -> 'Matrix44':
        ...

    @overload
    def __mul__(self, other: Vector4) -> Vector4:
        ...

    def __mul__(self, other):
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

    @property
    def xmin(self) -> float:
        return self[0]

    @property
    def ymin(self) -> float:
        return self[1]

    @property
    def xmax(self) -> float:
        return self[0] + self[2]

    @property
    def ymax(self) -> float:
        return self[1] + self[3]

    @property
    def xmid(self) -> float:
        return self.x + self.width * 0.5

    @property
    def ymid(self) -> float:
        return self.y + self.height * 0.5

    @property
    def pmin(self) -> Vector2:
        return Vector2(self.xmin, self.ymin)

    @property
    def pmax(self) -> Vector2:
        return Vector2(self.xmax, self.ymax)

    @property
    def center(self) -> Vector2:
        return Vector2(self.xmid, self.ymid)

    point = Vector2Proxy((0, 1))
    rect_size = Vector2Proxy((2, 3))

    def extend(self, dx: number, dy: number) -> 'Rect':
        return Rect.from_coords(
            self.xmin - dx,
            self.ymin - dy,
            self.xmax + dx,
            self.ymax + dy,
        )

    def translated(self, offset: Vector2) -> 'Rect':
        return Rect(self.x + offset.x, self.y + offset.y, self.width, self.height)

    def scaled(self, scale: Vector2) -> 'Rect':
        return Rect(
            self.x, self.y,
            self.width * scale.x, self.height * scale.y,
        )

    def __eq__(self, other: 'Rect') -> bool:
        return np.array_equal(self, other)

    def __ne__(self, other: 'Rect') -> bool:
        return not self == other

    def __str__(self) -> str:
        return f'Rect(x={self.x}, y={self.y}, width={self.width}, height={self.height})'

    def contains(self, obj: 'Rect | Vector2') -> bool:
        match obj:
            case Rect():
                xmin, ymin, xmax, ymax = obj.xmin, obj.ymin, obj.xmax, obj.ymax
                return (self.xmin <= xmin and xmax <= self.xmax and
                        self.ymin <= ymin and ymax <= self.ymax)
            case Vector2():
                return (
                    self.xmin >= obj[0] and self.xmax <= obj[0] and
                    self.ymin >= obj[1] and self.ymax <= obj[1]
                )

    def intersect(self, rect: 'Rect') -> 'Rect | None':
        x1, x2 = max(self.xmin, rect.xmin), min(self.xmax, rect.xmax)
        if x2 < x1:
            return None

        y1, y2 = max(self.ymin, rect.ymin), min(self.ymax, rect.ymax)
        if y2 < y1:
            return None

        return Rect.from_coords(x1, y1, x2, y2)

    def merge(self, rect: 'Rect') -> 'Rect':
        return Rect.from_coords(
            x1=min(self.xmin, rect.xmin),
            y1=min(self.ymin, rect.ymin),
            x2=max(self.xmax, rect.xmax),
            y2=max(self.ymax, rect.ymax),
        )

    @staticmethod
    def from_two_points(p1: Vector2, p2: Vector2) -> 'Rect':
        xmin = min(p1.x, p2.x)
        xmax = max(p1.x, p2.x)
        ymin = min(p1.y, p2.y)
        ymax = max(p1.y, p2.y)
        return Rect(xmin, ymin, xmax - xmin, ymax - ymin)

    @staticmethod
    def from_point_and_size(bottom_left: Vector2, size: Vector2) -> 'Rect':
        return Rect(bottom_left.x, bottom_left.y, size.x, size.y)

    @staticmethod
    def from_center_and_size(center: Vector2, size: Vector2) -> 'Rect':
        return Rect(center.x - size.x * 0.5, center.y - size.y * 0.5, size.x, size.y)

    @staticmethod
    def from_coords(x1: number, y1: number, x2: number, y2: number) -> 'Rect':
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1

        return Rect(x1, y1, x2 - x1, y2 - y1)


class Box(np.ndarray):
    def __new__(
        cls,
        x: number = 0,
        y: number = 0,
        z: number = 0,
        width: number = 0,
        height: number = 0,
        depth: number = 0,
    ):
        return np.array([x, y, z, width, height, depth]).view(cls)

    x = Vector1Proxy(0)
    y = Vector1Proxy(1)
    z = Vector1Proxy(2)
    width = Vector1Proxy(3)
    height = Vector1Proxy(4)
    depth = Vector1Proxy(5)

    @property
    def xmin(self) -> float:
        return self[0]

    @property
    def ymin(self) -> float:
        return self[1]

    @property
    def zmin(self) -> float:
        return self[2]

    @property
    def xmax(self) -> float:
        return self[0] + self[3]

    @property
    def ymax(self) -> float:
        return self[1] + self[4]

    @property
    def zmax(self) -> float:
        return self[2] + self[5]

    @property
    def center(self) -> Vector3:
        return Vector3(
            self.x + self.width * 0.5,
            self.y + self.height * 0.5,
            self.z + self.depth * 0.5,
        )

    point = Vector3Proxy((0, 1, 2))
    box_size = Vector3Proxy((3, 4, 5))

    @property
    def xy(self) -> Rect:
        return Rect(self.xmin, self.ymin, self.width, self.height)

    @property
    def xz(self) -> Rect:
        return Rect(self.xmin, self.zmin, self.width, self.depth)

    @property
    def yz(self) -> Rect:
        return Rect(self.ymin, self.zmin, self.height, self.depth)

    @property
    def corners(self) -> list[Vector3]:
        return [
            Vector3(x, y, z)
            for x in [self.xmin, self.xmax]
            for y in [self.ymin, self.ymax]
            for z in [self.zmin, self.zmax]
        ]

    def extend(self, dx: number, dy: number, dz: number) -> 'Box':
        return Box.from_coords(
            self.xmin - dx,
            self.ymin - dy,
            self.zmin - dz,
            self.xmax + dx,
            self.ymax + dy,
            self.zmax + dz,
        )

    def __eq__(self, other: 'Box') -> bool:
        return np.array_equal(self, other)

    def __ne__(self, other: 'Box') -> bool:
        return not self == other

    def __str__(self) -> str:
        return f'Box(x={self.x}, y={self.y}, z={self.z}, width={self.width}, height={self.height}, depth={self.depth})'

    def contains(self, obj: 'Box | Vector3') -> bool:
        match obj:
            case Box():
                xmin, ymin, zmin, xmax, ymax, zmax = obj.xmin, obj.ymin, obj.zmin, obj.xmax, obj.ymax, obj.zmax
                return (self.xmin <= xmin and xmax <= self.xmax and
                        self.ymin <= ymin and ymax <= self.ymax and
                        self.zmin <= zmin and zmax <= self.zmax)
            case Vector3():
                return (
                    self.xmin >= obj[0] and self.xmax <= obj[0] and
                    self.ymin >= obj[1] and self.ymax <= obj[1] and
                    self.zmin >= obj[2] and self.zmax <= obj[2]
                )

    def intersect(self, box: 'Box') -> 'Box | None':
        x1, x2 = max(self.xmin, box.xmin), min(self.xmax, box.xmax)
        if x2 < x1:
            return None

        y1, y2 = max(self.ymin, box.ymin), min(self.ymax, box.ymax)
        if y2 < y1:
            return None

        z1, z2 = max(self.zmin, box.zmin), min(self.zmax, box.zmax)
        if z2 < z1:
            return None

        return Box.from_coords(x1, y1, z1, x2, y2, z2)

    def merge(self, box: 'Box') -> 'Box':
        return Box.from_coords(
            x1=min(self.xmin, box.xmin),
            y1=min(self.ymin, box.ymin),
            z1=min(self.zmin, box.zmin),
            x2=max(self.xmax, box.xmax),
            y2=max(self.ymax, box.ymax),
            z2=max(self.zmax, box.zmax),
        )

    @staticmethod
    def from_point_and_size(bottom_left: Vector3, size: Vector3) -> 'Box':
        return Box(bottom_left.x, bottom_left.y, bottom_left.z,
                   size.x, size.y, size.z)

    @staticmethod
    def from_center_and_size(center: Vector3, size: Vector3) -> 'Box':
        return Box(
            center.x - size.x * 0.5,
            center.y - size.y * 0.5,
            center.z - size.z * 0.5,
            size.x,
            size.y,
            size.z,
        )

    @staticmethod
    def from_coords(x1: number, y1: number, z1: number,
                    x2: number, y2: number, z2: number) -> 'Box':
        if x1 > x2:
            x1, x2 = x2, x1
        if y1 > y2:
            y1, y2 = y2, y1
        if z1 > z2:
            z1, z2 = z2, z1

        return Box(x1, y1, z1, x2 - x1, y2 - y1, z2 - z1)


__all__ = [
    'Vector2',
    'Vector3',
    'Vector4',
    'Quaternion',
    'Matrix44',
    'Rect',
    'Box',
]
