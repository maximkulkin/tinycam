import collections
import enum
import struct
from typing import Any, Type, override, get_args

from tinycam.types import Vector2, Vector3
import tinycam.properties as p
from tinycam.utils import find_if, get_property_type
from PySide6 import QtCore


def humanize(s: str) -> str:
    parts = s.split('_')
    parts[0] = parts[0].capitalize()
    return ' '.join(parts)


class BufferReader:
    def __init__(self, data: bytes):
        self._data = data
        self._offset = 0

    @property
    def size(self) -> int:
        return len(self._data)

    @property
    def offset(self) -> int:
        return self._offset

    @property
    def remaining(self) -> int:
        return len(self._data) - self._offset

    def peek(self, size: int) -> bytes:
        return self._data[self._offset:self._offset + size]

    def read(self, size: int) -> bytes:
        data = self._data[self._offset:self._offset + size]
        self._offset += size
        return data

    def read_i8(self) -> int:
        return int.from_bytes(self.read(1), signed=True)

    def read_u8(self) -> int:
        return int.from_bytes(self.read(1), signed=False)

    def read_i16(self) -> int:
        return int.from_bytes(self.read(2), signed=True)

    def read_u16(self) -> int:
        return int.from_bytes(self.read(2), signed=False)

    def read_i32(self) -> int:
        return int.from_bytes(self.read(4), signed=True)

    def read_u32(self) -> int:
        return int.from_bytes(self.read(4), signed=False)

    def read_i64(self) -> int:
        return int.from_bytes(self.read(8), signed=True)

    def read_u64(self) -> int:
        return int.from_bytes(self.read(8), signed=False)

    def read_ixx(self) -> int:
        l = self.read_u8()
        if l < 128:
            return l
        return int.from_bytes(self.read(l), signed=True)

    def read_uxx(self) -> int:
        l = self.read_u8()
        if l < 128:
            return l
        return int.from_bytes(self.read(l), signed=False)

    def read_bool(self) -> bool:
        return struct.unpack('?', self.read(1))[0]

    def read_float(self) -> float:
        return struct.unpack('>f', self.read(4))[0]

    def read_str(self) -> str:
        l = self.read_uxx()
        return self.read(l).decode()

    def seek(self, position: int):
        self._offset = position


class BufferWriter:
    def __init__(self):
        self._data = bytearray()

    @property
    def size(self) -> int:
        return len(self._data)

    @property
    def data(self) -> bytes:
        return self._data

    def write(self, data: bytes):
        self._data += data

    def write_i8(self, value: int):
        self._data += value.to_bytes(1, signed=True)

    def write_u8(self, value: int):
        self._data += value.to_bytes(1, signed=False)

    def write_i16(self, value: int):
        self._data += value.to_bytes(2, signed=True)

    def write_u16(self, value: int):
        self._data += value.to_bytes(2, signed=False)

    def write_i32(self, value: int):
        self._data += value.to_bytes(4, signed=True)

    def write_u32(self, value: int):
        self._data += value.to_bytes(4, signed=False)

    def write_i64(self, value: int):
        self._data += value.to_bytes(8, signed=True)

    def write_u64(self, value: int):
        self._data += value.to_bytes(8, signed=False)

    def write_ixx(self, value: int):
        if value > 0 and value < 128:
            self._data += value.to_bytes(1, signed=True)
        else:
            l = (value.bit_length() + 7) // 8 or 1
            if l > 8:
                raise ValueError('Integer is too big')
            self._data += (l + 128).to_bytes(1, signed=False)
            self._data += value.to_bytes(l, signed=True)

    def write_uxx(self, value: int):
        if value > 0 and value < 128:
            self._data += value.to_bytes(1, signed=True)
        else:
            l = (value.bit_length() + 7) // 8 or 1
            if l > 8:
                raise ValueError('Integer is too big')
            self._data += (l + 128).to_bytes(1, signed=False)
            self._data += value.to_bytes(l, signed=False)

    def write_bool(self, value: bool):
        self._data += struct.pack('?', value)

    def write_float(self, value: float):
        self._data += struct.pack('>f', value)

    def write_str(self, value: str):
        data = value.encode()
        self.write_uxx(len(data))
        return self.write(data)


class Serializer[T]:
    type: Type[T]

    def __init__(self, t: Type[T]):
        self.type = t

    def serialize(self, value: T, writer: BufferWriter):
        return NotImplementedError()

    def deserialize(self, reader: BufferReader) -> T:
        raise NotImplementedError()

    _all_serializers = []

    @classmethod
    def all_serializers(cls):
        return cls._all_serializers

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._all_serializers.append(cls)


class StringSerializer(Serializer[str]):
    type = str

    @override
    def serialize(self, value: str, writer: BufferWriter):
        writer.write_str(value)

    @override
    def deserialize(self, reader: BufferReader) -> str:
        return reader.read_str()


class IntegerSerializer(Serializer[int]):
    type = int

    @override
    def serialize(self, value: int, writer: BufferWriter):
        writer.write_ixx(value)

    @override
    def deserialize(self, reader: BufferReader) -> int:
        return reader.read_ixx()


class FloatSerializer(Serializer[float]):
    type = float

    @override
    def serialize(self, value: float, writer: BufferWriter):
        writer.write_float(value)

    @override
    def deserialize(self, reader: BufferReader) -> float:
        return reader.read_float()


class BoolSerializer(Serializer[bool]):
    type = bool

    @override
    def serialize(self, value: bool, writer: BufferWriter):
        writer.write_bool(value)

    @override
    def deserialize(self, reader: BufferReader) -> bool:
        return reader.read_bool()


class Vector2Serializer(Serializer[Vector2]):
    type = Vector2

    @override
    def serialize(self, value: Vector2, writer: BufferWriter):
        writer.write_float(value.x)
        writer.write_float(value.y)

    @override
    def deserialize(self, reader: BufferReader) -> Vector2:
        x = reader.read_float()
        y = reader.read_float()
        return Vector2(x, y)


class Vector3Serializer(Serializer[Vector3]):
    type = Vector3

    @override
    def serialize(self, value: Vector3, writer: BufferWriter):
        writer.write_float(value.x)
        writer.write_float(value.y)
        writer.write_float(value.z)

    @override
    def deserialize(self, reader: BufferReader) -> Vector3:
        x = reader.read_float()
        y = reader.read_float()
        z = reader.read_float()
        return Vector3(x, y, z)


class EnumSerializer[E: enum.Enum](Serializer[E]):
    type = enum.Enum

    @override
    def serialize(self, value: E, writer: BufferWriter):
        writer.write_uxx(value.value)

    @override
    def deserialize(self, reader: BufferReader) -> E:
        return self.type(reader.read_uxx())


class ListSerializer[T](Serializer[list[T]]):
    type = list[T]

    def __init__(self, t: Type[list[T]]):
        super().__init__(t)
        item_type = get_args(t)[0]
        self._item_serializer = get_serializer(item_type)
        if self._item_serializer is None:
            raise TypeError('List item type {item_type} is not serializable')

    @override
    def serialize(self, value: list[T], writer: BufferWriter):
        writer.write_uxx(len(value))
        for item in value:
            self._item_serializer.serialize(item, writer)

    @override
    def deserialize(self, reader: BufferReader) -> list[T]:
        count = reader.read_uxx()

        result = []
        for i in range(count):
            result.append(self._item_serializer.deserialize(reader))
        return result


class ObjectSerializer(Serializer[object]):
    type = object

    @override
    def serialize(self, value: object, writer: BufferWriter):
        attrs = []
        value_type = type(value)
        for attr in p.get_all(value_type):
            prop = getattr(value_type, attr, None)
            prop_type = get_property_type(prop)
            serializer = get_serializer(prop_type)
            if serializer is None:
                continue

            value = getattr(value, attr, None)
            if value is None:
                continue

            attrs.append((attr, serializer, value))

        writer.write_uxx(len(attrs))

        for attr, serializer, value in attrs:
            writer.write_str(attr)
            serializer.serialize(value, writer)

    @override
    def deserialize(self, reader: BufferReader) -> object:
        count = reader.read_uxx()

        result = self.type()
        for _ in range(count):
            attr = reader.read_str()

            prop = getattr(self.type, attr, None)
            prop_type = get_property_type(prop)

            serializer = get_serializer(prop_type)
            if serializer is None:
                continue

            value = serializer.deserialize(reader)
            setattr(result, attr, value)

        return result


def get_serializer[T](t: Type[T]) -> Serializer[T] | None:
    if t is None:
        raise ValueError('t is None')

    serializer = find_if(Serializer.all_serializers(), lambda s: s.type == t)
    if serializer is None:
        if getattr(t, '__origin__', None) == list:
            return ListSerializer[t.__args__[0]](t)

        if issubclass(t, enum.Enum):
            return EnumSerializer[t](t)

        return None

    return serializer(t)


class CncSetting[T](QtCore.QObject):
    changed: QtCore.Signal = QtCore.Signal(object)

    def __init__(
        self,
        path: str,
        label: str | None = None,
        description: str | None = None,
        default: T | None = None,
    ):
        super().__init__()
        self._path: str = path
        self._value: T | None = None
        self._label: str | None = label
        self._description: str | None = description
        self._default: T | None = default

    @property
    def type(self) -> type:
        return get_args(self.__orig_bases__[0])[0]

    @property
    def path(self) -> str:
        return self._path

    @property
    def label(self) -> str | None:
        return self._label

    @property
    def description(self) -> str | None:
        return self._description

    @property
    def value(self) -> T | None:
        if self._value is None:
            return self.default
        return self._value

    @value.setter
    def value(self, value: T):
        if self._value == value:
            return

        error = self.validate(value)
        if error is not None:
            raise CncInvalidSettingValueError(self._path, error)
        self._value = value
        self.changed.emit(self._value)

    def reset(self):
        self._value = None

    @property
    def default(self) -> T | None:
        return self._default

    def validate(self, _data: object) -> str | None:
        raise NotImplementedError()


class CncStringSetting(CncSetting[str]):
    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, str) else 'Value is not a string'

    @override
    def __str__(self):
        return 'STRING'


class CncIntegerSetting(CncSetting[int]):
    def __init__(
        self,
        *args,
        minimum: int | None = None,
        maximum: int | None = None,
        suffix: str | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._minimum: int | None = minimum
        self._maximum: int | None = maximum
        self._suffix: str | None = suffix

    @property
    def minimum(self) -> int | None:
        return self._minimum

    @property
    def maximum(self) -> int | None:
        return self._maximum

    @property
    def suffix(self) -> str | None:
        return self._suffix

    @override
    def validate(self, value: object) -> str | None:
        if not isinstance(value, int):
            return 'Value is not an integer'
        if self.minimum is not None and value < self.minimum:
            return f'Value should not be less than {self.minimum}'
        if self.maximum is not None and value > self.maximum:
            return f'Value should not be greater than {self.minimum}'
        return None

    @override
    def __str__(self):
        return 'INTEGER'


class CncFloatSetting(CncSetting[float]):
    def __init__(
        self,
        *args,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._minimum: float | None = minimum
        self._maximum: float | None = maximum
        self._suffix: str | None = suffix

    @property
    def minimum(self) -> float | None:
        return self._minimum

    @property
    def maximum(self) -> float | None:
        return self._maximum

    @property
    def suffix(self) -> str | None:
        return self._suffix

    @override
    def validate(self, value: object) -> str | None:
        if not isinstance(value, float):
            return 'Value is not a float'
        if self.minimum is not None and value < self.minimum:
            return f'Value should not be less than {self.minimum}'
        if self.maximum is not None and value > self.maximum:
            return f'Value should not be greater than {self.minimum}'
        return None

    @override
    def __str__(self):
        return 'FLOAT'


class CncBooleanSetting(CncSetting[bool]):
    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, bool) else 'Value is not a boolean'

    @override
    def __str__(self):
        return 'BOOLEAN'


class CncVector2Setting(CncSetting[Vector2]):
    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, Vector2) else 'Value is not a Vector2'

    @override
    def __str__(self):
        return 'VECTOR2'


class CncEnumSetting[E: enum.Enum](CncSetting[E]):
    @override
    @property
    def type(self) -> type:
        return get_args(self.__orig_class__)[0]

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, self.type) else f'Value is not a {self.type}'

    @override
    def __str__(self):
        return f'{self.type}'


class CncListSetting[I](CncSetting[list[I]]):
    @override
    @property
    def type(self) -> type:
        return list[get_args(self.__orig_class__)[0]]

    @override
    def validate(self, data: object) -> str | None:
        if not isinstance(data, list):
            return 'Value is not a list'
        return None

    @override
    def __str__(self):
        return f'LIST[{self.type}]'


class CncSettingError(Exception):
    pass


class CncSettingAlreadyExistsError(CncSettingError):
    def __init__(self, path: str):
        super().__init__(f'Setting {path} already exists')
        self.path: str = path


class CncUnknownSettingError(CncSettingError):
    def __init__(self, path: str):
        super().__init__(f'Unknown setting {path}')
        self.path: str = path


class CncInvalidSettingPathError(CncSettingError):
    def __init__(self, path: str):
        super().__init__(f'Setting path should have at least on "/": {path}')
        self.path: str = path


class CncInvalidSettingValueError(CncSettingError):
    def __init__(self, path: str, error: str):
        super().__init__(f'Value for {path} is invalid: {error}')
        self.path: str = path
        self.error: str = error


class CncSectionSettings:
    def __init__(self, settings: 'CncSettings', path: str):
        self._settings: CncSettings = settings
        self._path: str = path
        if self._path.endswith('/'):
            self._path = self._path[:-1]

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        pass

    def _make_path(self, path: str) -> str:
        return f'{self._path}/{path}'

    def register[S: CncSetting](
        self,
        path: str,
        type: type[S],
        *args,
        **kwargs
    ) -> S:
        return self._settings.register(self._make_path(path), type, *args, **kwargs)

    def __getitem__(self, path: str) -> CncSetting:
        return self._settings[self._make_path(path)]

    def __contains__(self, path: str | CncSetting):
        return path in self._settings

    def get(self, path: str | CncSetting) -> Any:
        if isinstance(path, str):
            path = self._make_path(path)
        return self._settings.get(path)

    def set(self, path: str | CncSetting, value: Any):
        if isinstance(path, str):
            path = self._make_path(path)
        self._settings.set(path, value)

    def reset(self, path: str | CncSetting):
        if isinstance(path, str):
            path = self._make_path(path)
        self._settings.reset(path)

    def is_default(self, path: str | CncSetting) -> bool:
        if isinstance(path, str):
            path = self._make_path(path)
        return self._settings.is_default(path)

    def validate(self, path: str | CncSetting, value: Any):
        if isinstance(path, str):
            path = self._make_path(path)
        self._settings.validate(path, value)

    def __iter__(self):
        prefix = f'{self._path}/'
        for v in self._settings:
            if v.path.startswith(prefix):
                yield v


class CncSettings(QtCore.QObject):
    changed = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self._settings = collections.OrderedDict[str, CncSetting]()
        self._values = {}

    def section(self, path: str) -> CncSectionSettings:
        return CncSectionSettings(self, path)

    def register[S: CncSetting](
        self,
        path: str,
        setting_type: type[S],
        *args,
        label: str | None = None,
        description: str | None = None,
        default: object | None = None,
        **kwargs
    ) -> S:
        if path in self._settings:
            raise CncSettingAlreadyExistsError(path)

        parts = path.split('/')
        if len(parts) < 2:
            raise CncInvalidSettingPathError(path)

        if label is None:
            label = humanize(parts[-1])

        setting = setting_type(
            path, *args, label=label, description=description,
            default=default, **kwargs
        )
        self._settings[path] = setting
        return setting

    def __getitem__(self, path: str) -> CncSetting:
        return self._settings[path]

    def __contains__(self, path: str | CncSetting):
        if isinstance(path, CncSetting):
            path = path.path

        return path in self._settings

    def get(self, path: str | CncSetting) -> Any:
        if isinstance(path, CncSetting):
            path = path.path

        setting = self._settings.get(path, None)
        if setting is None:
            raise CncUnknownSettingError(path)

        return setting.value if setting.value is not None else setting.default

    def set(self, path: str | CncSetting, value: Any):
        if isinstance(path, CncSetting):
            path = path.path

        setting = self._settings.get(path, None)
        if setting is None:
            raise CncSettingAlreadyExistsError(path)

        error = setting.validate(value)
        if error is not None:
            raise CncInvalidSettingValueError(path, error)

        setting.value = value

    def reset(self, path: str | CncSetting):
        if isinstance(path, CncSetting):
            path = path.path

        setting = self._settings.get(path, None)
        if setting is None:
            raise CncSettingAlreadyExistsError(path)
        setting.reset()

    def is_default(self, path: str | CncSetting) -> bool:
        if isinstance(path, CncSetting):
            path = path.path

        if path not in self._settings:
            raise CncUnknownSettingError(path)

        setting = self._settings[path]
        return setting.value == setting.default

    def validate(self, path: str | CncSetting, value: Any):
        if isinstance(path, CncSetting):
            path = path.path

        setting = self._settings.get(path, None)
        if setting is None:
            raise CncUnknownSettingError(path)

        return setting.validate(value)

    def __iter__(self):
        yield from self._settings.values()


# Settings
SETTINGS = CncSettings()
SETTINGS.register('general/dev_mode', CncBooleanSetting, default=True)


class Units(enum.Enum):
    IN = 1
    MM = 2

    def __str__(self) -> str:
        match self:
            case Units.IN: return 'Inches'
            case Units.MM: return 'Millimeters'


class ControlType(enum.Enum):
    MOUSE = 1
    TOUCHPAD = 2

    def __str__(self) -> str:
        match self:
            case ControlType.MOUSE: return 'Mouse'
            case ControlType.TOUCHPAD: return 'Touchpad'


SETTINGS.register('general/units', CncEnumSetting[Units], default=Units.MM)
SETTINGS.register('general/control_type', CncEnumSetting[ControlType], default=ControlType.MOUSE)
SETTINGS.register('general/invert_zoom', CncBooleanSetting, default=False)
