import collections
import enum
from typing import Any, override
from tinycam.types import Vector2
from PySide6 import QtCore


def humanize(s: str) -> str:
    parts = s.split('_')
    parts[0] = parts[0].capitalize()
    return ' '.join(parts)


class CncSetting(QtCore.QObject):
    changed: QtCore.Signal = QtCore.Signal(object)

    def __init__(
        self,
        path: str,
        label: str | None = None,
        description: str | None = None,
        default: object | None = None,
    ):
        super().__init__()
        self._path: str = path
        self._value: object = None
        self._label: str | None = label
        self._description: str | None = description
        self._default: object = default

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
    def value(self) -> object:
        if self._value is None:
            return self.default
        return self._value

    @value.setter
    def value(self, value: object):
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
    def default(self) -> object | None:
        return self._default

    def save(self) -> str:
        return str(self.value)

    def load(self, _data: str) -> None:
        raise NotImplementedError()

    def validate(self, _data: object) -> str | None:
        raise NotImplementedError()


class CncStringSetting(CncSetting):
    @override
    def load(self, value: str):
        self._value: object = value

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, str) else 'Value is not a string'

    @override
    def __str__(self):
        return 'STRING'


class CncIntegerSetting(CncSetting):
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
    def load(self, data: str):
        value = int(data)
        if self.minimum is not None and self.minimum > value:
            value = self.minimum
        if self.maximum is not None and value > self.maximum:
            value = self.maximum
        self._value = value

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


class CncFloatSetting(CncSetting):
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
    def load(self, data: str):
        value = float(data)
        if self.minimum is not None and self.minimum > value:
            value = self.minimum
        if self.maximum is not None and value > self.maximum:
            value = self.maximum
        self._value = value

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


class CncBooleanSetting(CncSetting):
    @override
    def save(self) -> str:
        data = 'true' if bool(self.value) else 'false'
        return data

    @override
    def load(self, data: str):
        self._value = data == 'true'

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, bool) else 'Value is not a boolean'

    @override
    def __str__(self):
        return 'BOOLEAN'


class CncVector2Setting(CncSetting):
    @override
    def save(self) -> str:
        return f'{self.value[0]},{self.value[1]}'  # pyright: ignore

    @override
    def load(self, data: str) -> object:
        self._value = Vector2((float(x) for x in data.split(',', 1)))  # pyright: ignore

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, Vector2) else 'Value is not a Vector2'

    @override
    def __str__(self):
        return 'VECTOR2'


class CncEnumSetting(CncSetting):
    def __init__(self, *args, enum_type: type[enum.Enum] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        if enum_type is None:
            raise ValueError('Enum type is not specified')
        self._enum_type = enum_type

    @property
    def enum_type(self) -> type[enum.Enum]:
        return self._enum_type

    @override
    def save(self) -> str:
        return str(self.value.value)  # pyright: ignore

    @override
    def load(self, data: str) -> object:
        self._value = self._enum_type(int(data))

    @override
    def validate(self, data: object) -> str | None:
        return None if isinstance(data, self._enum_type) else f'Value is not a {self.enum_type}'

    @override
    def __str__(self):
        return f'{self.enum_type}'


class CncListSetting[T](CncSetting):
    def __init__(self, item_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_type = item_type

    __match_args__ = ('item_type',)

    @override
    def load(self, data: str) -> object:
        raise NotImplementedError()

    @override
    def save(self, data: object) -> str:
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

    def register(self, path: str, type: type[CncSetting], *args, **kwargs):
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

    def register(
        self,
        path: str,
        setting_type: type[CncSetting],
        *args,
        label: str | None = None,
        description: str | None = None,
        default: object | None = None,
        **kwargs
    ):
        if path in self._settings:
            raise CncSettingAlreadyExistsError(path)

        parts = path.split('/')
        if len(parts) < 2:
            raise CncInvalidSettingPathError(path)

        if label is None:
            label = humanize(parts[-1])

        self._settings[path] = setting_type(
            path, *args, label=label, description=description,
            default=default, **kwargs
        )

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


SETTINGS.register('general/units', CncEnumSetting, enum_type=Units, default=Units.MM)
SETTINGS.register('general/control_type', CncEnumSetting, enum_type=ControlType,
                  default=ControlType.MOUSE)
SETTINGS.register('general/invert_zoom', CncBooleanSetting, default=False)
