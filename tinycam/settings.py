import collections
import dataclasses
import enum
from typing import Any, TypeVar, Generic, override, get_type_hints
from tinycam.types import Vector2


def humanize(s: str) -> str:
    parts = s.split('_')
    parts[0] = parts[0].capitalize()
    return ' '.join(parts)


class CncSettingType:
    def __init__(self):
        pass

    def serialize(self, _data: object) -> str:
        raise NotImplementedError()

    def deserialize(self, _data: str) -> object:
        raise NotImplementedError()

    def validate(self, _data: object) -> str | None:
        raise NotImplementedError()

    def default(self) -> object:
        raise NotImplementedError()


class CncStringSettingType(CncSettingType):
    @override
    def serialize(self, data: object) -> str:
        return str(data)

    @override
    def deserialize(self, data: str) -> object:
        return str(data)

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, str) else 'Value is not a string'

    @override
    def __str__(self):
        return 'STRING'


class CncIntegerSettingType(CncSettingType):
    def __init__(
        self,
        minimum: int | None = None,
        maximum: int | None = None,
        suffix: str | None = None,
    ):
        super().__init__()
        self.minimum: int | None = minimum
        self.maximum: int | None = maximum
        self.suffix: str | None = suffix

    @override
    def serialize(self, data: object) -> str:
        return str(data)

    @override
    def deserialize(self, data: str) -> object:
        return int(data)

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, int) else 'Value is not an integer'

    @override
    def __str__(self):
        return 'INTEGER'


class CncFloatSettingType(CncSettingType):
    def __init__(
        self,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
    ):
        super().__init__()
        self.minimum: float | None = minimum
        self.maximum: float | None = maximum
        self.suffix: str | None = suffix

    @override
    def serialize(self, data: object) -> str:
        return str(data)

    @override
    def deserialize(self, data: str) -> object:
        return float(data)

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, float) else 'Value is not a float'

    @override
    def __str__(self):
        return 'FLOAT'


class CncBooleanSettingType(CncSettingType):
    @override
    def serialize(self, data: object) -> str:
        return 'true' if bool(data) else 'false'

    @override
    def deserialize(self, data: str) -> object:
        return True if data == 'true' else False

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, bool) else 'Value is not a boolean'

    @override
    def __str__(self):
        return 'BOOLEAN'


class CncVector2SettingType(CncSettingType):
    @override
    def serialize(self, data: object) -> str:
        return f'{data[0]},{data[1]}'

    @override
    def deserialize(self, data: str) -> object:
        return Vector2((float(x) for x in data.split(',', 1)))

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, Vector2) else 'Value is not a Vector2'

    @override
    def __str__(self):
        return 'VECTOR2'


class CncEnumSettingType(CncSettingType):
    def __init__(self, enum_type):
        super().__init__()
        self.enum_type = enum_type

    __match_args__ = ('enum_type',)

    @override
    def serialize(self, data: object) -> str:
        raise NotImplementedError()

    @override
    def deserialize(self, data: str) -> object:
        raise NotImplementedError()

    @override
    def validate(self, data: object) -> str | None:
        raise NotImplementedError()

    @override
    def __str__(self):
        return f'{self.enum_type}'


class CncListSettingType[T](CncSettingType):
    @override
    def serialize(self, data: object) -> str:
        raise NotImplementedError()

    @override
    def deserialize(self, data: str) -> object:
        raise NotImplementedError()

    @override
    def validate(self, data: object) -> str | None:
        raise NotImplementedError()

    @override
    def __str__(self):
        return f'LIST[{T}]'


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
    def __init__(self, path: str, error: Exception):
        super().__init__(f'Value for {path} is invalid: {error}')
        self.path: str = path
        self.error: Exception = error


@dataclasses.dataclass(order=True)
class CncSetting:
    path: str
    type: CncSettingType
    label: str
    description: str | None
    default: object


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

    def register(self, path: str, type: CncSettingType, **kwargs):
        return self._settings.register(self._make_path(path), type, **kwargs)

    def __getitem__(self, path: str | CncSetting) -> Any:
        return self.get(path)

    def __setitem__(self, path: str | CncSetting, value: Any):
        self.set(path, value)

    def get(self, path: str) -> Any:
        return self._settings.get(self._make_path(path))

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
        return self._settings.is_default(self._make_path(path))

    def validate(self, path: str | CncSetting, value: Any):
        if isinstance(path, str):
            path = self._make_path(path)
        self._settings.validate(self._make_path(path), value)

    def __iter__(self):
        prefix = f'{self._path}/'
        for v in self._settings:
            if v.path.startswith(prefix):
                yield v


class CncSettings:

    def __init__(self):
        self._metadata = collections.OrderedDict[str, CncSetting]()
        self._values = {}

    def section(self, path: str) -> CncSectionSettings:
        return CncSectionSettings(self, path)

    def register(self, path: str, type: CncSettingType, *, label: str = None,
                 description: str | None = None,
                 default: Any = None):
        if path in self._metadata:
            raise CncSettingAlreadyExistsError(path)

        parts = path.split('/')
        if len(parts) < 2:
            raise CncInvalidSettingPathError(path)

        if label is None:
            label = humanize(parts[-1])

        self._metadata[path] = CncSetting(
            path=path, type=type, label=label, description=description,
            default=default,
        )

    def __getitem__(self, path: str | CncSetting) -> Any:
        return self.get(path)

    def __setitem__(self, path: str | CncSetting, value: Any):
        self.set(path, value)

    def get(self, path: str | CncSetting) -> Any:
        if isinstance(path, CncSetting):
            path = path.path

        metadata = self._metadata.get(path, None)
        if metadata is None:
            raise CncUnknownSettingError(path)

        return self._values.get(path, metadata.default)

    def set(self, path: str | CncSetting, value: Any):
        if isinstance(path, CncSetting):
            path = path.path

        metadata = self._metadata.get(path, None)
        if metadata is None:
            raise CncSettingAlreadyExistsError(path)

        error = metadata.type.validate(value)
        if error is not None:
            raise CncInvalidSettingValueError(path, error)

        self._values[path] = value

    def reset(self, path: str | CncSetting):
        if isinstance(path, CncSetting):
            path = path.path

        if path not in self._values:
            return
        del self._values[path]

    def is_default(self, path: str | CncSetting) -> bool:
        if isinstance(path, CncSetting):
            path = path.path

        if path not in self._metadata:
            raise CncUnknownSettingError(path)

        metadata = self._metadata[path]
        return path not in self._values or self._values[path] == metadata.default

    def validate(self, path: str | CncSetting, value: Any):
        if isinstance(path, CncSetting):
            path = path.path

        metadata = self._metadata.get(path, None)
        if metadata is None:
            raise CncUnknownSettingError(path)

        return metadata.validate(value)

    def __iter__(self):
        yield from self._metadata.values()


# Common types
STRING = CncStringSettingType()
INTEGER = CncIntegerSettingType()
FLOAT = CncFloatSettingType()
BOOLEAN = CncBooleanSettingType()
VECTOR2 = CncVector2SettingType()

# Settings
SETTINGS = CncSettings()
SETTINGS.register('general/dev_mode', BOOLEAN, default=True)


class ControlType(enum.Enum):
    MOUSE = (1, 'Mouse')
    TOUCHPAD = (2, 'Touchpad')

    def __init__(self, value: int, label: str):
        self.label = label


SETTINGS.register('general/control_type', CncEnumSettingType(ControlType), default=ControlType.MOUSE)
