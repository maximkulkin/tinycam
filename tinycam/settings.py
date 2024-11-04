import collections
import dataclasses
from typing import Any, Optional, Union, TypeVar


def humanize(s: str) -> str:
    parts = s.split('_')
    parts[0] = parts[0].capitalize()
    return ' '.join(parts)


T = TypeVar('T')

class CncSettingType:
    def serialize(self, data: T) -> str:
        raise NotImplemented()

    def deserialize(self, data: str) -> T:
        raise NotImplemented()

    def validate(self, data: T) -> Union[None, str]:
        raise NotImplemented()

    def default(self) -> T:
        raise NotImplemented()



class CncStringSettingType(CncSettingType):
    def serialize(self, data: str) -> str:
        return str(data)

    def deserialize(self, data: str) -> str:
        return str(data)

    def validate(self, data: str) -> Union[None, str]:
        return None if isinstance(data, str) else 'Value is not a string'

    def __str__(self):
        return 'STRING'


class CncIntegerSettingType(CncSettingType):
    def serialize(self, data: int) -> str:
        return str(data)

    def deserialize(self, data: str) -> int:
        return int(data)

    def validate(self, data: int) -> Union[None, str]:
        return None if isinstance(data, int) else 'Value is not an int'

    def __str__(self):
        return 'INTEGER'


class CncFloatSettingType(CncSettingType):
    def serialize(self, data: float) -> str:
        return str(data)

    def deserialize(self, data: str) -> float:
        return float(data)

    def validate(self, data: float) -> Union[None, str]:
        return None if isinstance(data, float) else 'Value is not a float'

    def __str__(self):
        return 'FLOAT'


class CncBooleanSettingType(CncSettingType):
    def serialize(self, data: bool) -> str:
        return 'true' if bool(data) else 'false'

    def deserialize(self, data: str) -> bool:
        return True if data == 'true' else False

    def validate(self, data: bool) -> Union[None, str]:
        return None if isinstance(data, bool) else 'Value is not a boolean'

    def __str__(self):
        return 'BOOLEAN'


class CncSettingError(Exception):
    pass


class CncSettingAlreadyExists(CncSettingError):
    def __init__(self, path):
        super().__init__(f'Setting {path} already exists')
        self.path = path


class CncUnknownSettingError(CncSettingError):
    def __init__(self, path):
        super().__init__(f'Unknown setting {path}')
        self.path = path


class CncInvalidSettingValueError(CncSettingError):
    def __init__(self, path, error):
        super().__init__(f'Value for {path} is invalid: {error}')
        self.path = path
        self.error = error


@dataclasses.dataclass(order=True)
class CncSetting:
    path: str
    type: CncSettingType
    label: str
    description: Optional[str]
    default: Any


class CncSettings:

    def __init__(self):
        self._metadata = collections.OrderedDict()
        self._values = {}

    def register(self, path: str, type: CncSettingType, label: str = None,
                 description: Optional[str] = None,
                 default: Any = None):
        if path in self._metadata:
            raise CncSettingAlreadyExists(path)

        if label is None:
            parts = path.split('/')
            label = humanize(parts[-1])

        self._metadata[path] = CncSetting(
            path=path, type=type, label=label, description=description,
            default=default,
        )

    def get(self, path: str) -> Any:
        metadata = self._metadata.get(path, None)
        if metadata is None:
            raise CncUnknownSettingError(path)

        return self._values.get(path, metadata.default)

    def set(self, path: str, value: Any):
        metadata = self._metadata.get(path, None)
        if metadata is None:
            raise CncSettingAlreadyExists(path)

        error = metadata.type.validate(value)
        if error is not None:
            raise CncInvalidSettingValueError(path, error)

        self._values[path] = value

    def reset(self, path: str):
        if path not in self._values:
            return
        del self._values[path]

    def is_default(self, path: str) -> bool:
        if path not in self._metadata:
            raise CncUnknownSettingError(path)

    def validate(self, path: str, value: Any):
        metadata = self._metadata.get(path, None)
        if metadata is None:
            raise CncUnknownSettingError(path)

        return metadata.validate(value)

    def __iter__(self):
        yield from self._metadata.values()


STRING = CncStringSettingType()
INTEGER = CncIntegerSettingType()
FLOAT = CncFloatSettingType()
BOOLEAN = CncBooleanSettingType()


SETTINGS = CncSettings()
SETTINGS.register('dev_mode', BOOLEAN, default=True)
SETTINGS.register('foo/bar', STRING, default='')
SETTINGS.register('foo/baz', INTEGER, default=0)
SETTINGS.register('foo/bam/quux', INTEGER, default=0)
SETTINGS.register('foo/bam/quux2', INTEGER, default=0)
SETTINGS.register('bar/boom', FLOAT, default=0.0)
SETTINGS.register('bar/hello', BOOLEAN, default=False)
SETTINGS.register('bar/hello/yes', BOOLEAN, default=False)
