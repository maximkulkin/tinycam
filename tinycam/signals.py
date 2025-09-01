import inspect
from typing import Any, Callable, cast, overload
import weakref


_MISSING = object()


class Connection[T]:
    @overload
    def __init__(self, signal: 'SignalInstance[None]', callback: Callable[[], None]):
            ...

    @overload
    def __init__(self, signal: 'SignalInstance[T]', callback: Callable[[T], None]):
            ...

    def __init__(self, signal, callback):
        self.owner = signal
        self.callback = callback

        if inspect.ismethod(callback):
            self._ref = weakref.WeakMethod(callback, self.disconnect)
        else:
            self._ref = weakref.ref(callback, self.disconnect)

    @overload
    def __call__(self: 'Connection[None]') -> None:
        ...

    @overload
    def __call__(self: 'Connection[T]', value: T) -> None:
        ...

    def __call__(self, value: object = _MISSING):
        if value is _MISSING:
            self.callback()
        else:
            self.callback(value)

    def disconnect(self, _) -> None:
        self.owner.disconnect(self)


class SignalInstance[T]:
    def __init__(self):
        self._connections: list[Connection[T]] = []

    @overload
    def connect(self: 'SignalInstance[None]', callback: Callable[[], None]) -> Connection[T]:
        ...

    @overload
    def connect(self: 'SignalInstance[T]', callback: Callable[[T], None]) -> Connection[T]:
        ...

    def connect(self, callback: Callable[..., None]) -> Connection[T]:
        connection = Connection(self, callback)
        self._connections.append(connection)
        return connection

    @overload
    def disconnect(self: 'SignalInstance[None]', subject: Callable[[], None]) -> bool:
        ...

    @overload
    def disconnect(self: 'SignalInstance[T]', subject: Callable[[T], None]) -> bool:
        ...

    @overload
    def disconnect(self, subject: Connection[T]) -> bool:
        ...

    def disconnect(self, subject) -> bool:
        if isinstance(subject, Connection):
            if subject not in self._connections:
                return False
            connection = cast(Connection[T], subject)
            self._connections.remove(connection)
            return True
        elif isinstance(subject, Callable):
            new_connections = [
                connection
                for connection in self._connections
                if connection.callback != subject
            ]
            success = len(new_connections) != len(self._connections)
            self._connections = new_connections
            return success
        else:
            raise ValueError('Unknown slot to disconnect')

    @overload
    def emit(self: 'SignalInstance[None]') -> None:
        ...

    @overload
    def emit(self: 'SignalInstance[T]', value: T) -> None:
        ...

    def emit(self, value: object = _MISSING):
        if value is _MISSING:
            for connection in self._connections:
                connection.callback()
        else:
            for connection in self._connections:
                connection.callback(value)


class Signal[T = None]:
    def __init__(self):
        self._name = None

    def __set_name__(self, objtype: type, name: str):
        self._name = name

    @overload
    def __get__(self, instance: None, owner: Any) -> 'Signal[T]':
        ...

    @overload
    def __get__(self, instance: object, owner: Any) -> SignalInstance[T]:
        ...

    def __get__(self, instance, owner):
        if instance is None:
            return self

        signal_instance = SignalInstance[T]()
        assert self._name is not None
        setattr(instance, self._name, signal_instance)
        return signal_instance
