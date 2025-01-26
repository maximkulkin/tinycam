from collections.abc import Callable


class Property:
    def __init__(self, *,
                 label: str | None = None,
                 on_update: Callable[[object], None] | None = None):
        self._name: str | None = None
        self._label: str | None = label
        self._on_update: Callable[[object], None] | None = on_update

    @property
    def name(self) -> str:
        return self._name or ''

    @property
    def label(self) -> str:
        return self._label or ''

    def __set_name__(self, objtype, name):
        self._name = name
        self._variable_name = f'_{name}'
        if self._label is None:
            self._label = name.replace('_', ' ').capitalize()

    def __get__(self, instance: object, objtype: type = None):
        if instance is None:
            return self
        return instance.__dict__.get(self._variable_name)

    def __set__(self, instance: object, value: object):
        instance.__dict__[self._variable_name] = value
        if self._on_update is not None:
            self._on_update(instance)


class StringProperty(Property):
    pass


class BoolProperty(Property):
    pass


class IntProperty(Property):
    def __init__(self, *,
                 min_value: int | None = None,
                 max_value: int | None = None,
                 suffix: str | None = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.min_value: int | None = min_value
        self.max_value: int | None = max_value
        self.suffix: str | None = suffix


class FloatProperty(Property):
    def __init__(self, *,
                 min_value: float | None = None,
                 max_value: float | None = None,
                 suffix: str | None = None,
                 **kwargs):
        super().__init__(**kwargs)
        self.min_value: float | None = min_value
        self.max_value: float | None = max_value
        self.suffix: str | None = suffix


class Vector2Property(Property):
    pass


class Vector3Property(Property):
    pass
