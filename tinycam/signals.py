import inspect
from typing import Any, Callable, overload
import weakref


class Connection[Ts]:
    def __init__(self, signal: 'SignalInstance[Ts]', callback: Callable[Ts, None]):
        self.owner = signal
        self.callback = callback

        if inspect.ismethod(callback):
            self._ref = weakref.WeakMethod(callback, self.disconnect)
        else:
            self._ref = weakref.ref(callback, self.disconnect)

    def __call__(self, *args: Ts):
        self.callback(*args)

    def disconnect(self):
        self.owner.disconnect(self)


class SignalInstance[Ts]:
    def __init__(self):
        self._connections: list[Connection[Ts]] = []

    def connect(self, callback: Callable[Ts, None]) -> Connection[Ts]:
        connection = Connection(self, callback)
        self._connections.append(connection)
        return connection

    @overload
    def disconnect(self, callback: Callable[Ts, None]) -> bool:
        ...

    @overload
    def disconnect(self, connection: Connection[Ts]):
        ...

    def disconnect(self, subject):
        if isinstance(subject, Connection):
            if subject not in self._connections:
                return False
            self._connections.remove(subject)
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

    def emit(self, *args: Ts):
        for connection in self._connections:
            connection.callback(*args)


class Signal[*Ts]:
    def __init__(self, *args: *Ts):
        self._name = None

    def __set_name__(self, objtype: type, name: str):
        self._name = name

    @overload
    def __get__(self, instance: object, owner: Any | None) -> SignalInstance[Ts]:
        ...

    @overload
    def __get__(self, instance: None, owner: Any | None) -> 'Signal[*Ts]':
        ...

    def __get__(self, instance, owner):
        if instance is None:
            return self

        signal_instance = SignalInstance[Ts]()
        setattr(instance, self._name, signal_instance)
        return signal_instance
