import typing
from typing import Protocol, Self, overload, runtime_checkable


@runtime_checkable
class Lerpable(Protocol):
    def __add__(self, other: Self) -> Self:
        ...

    def __sub__(self, other: Self) -> Self:
        ...

    def __mul__(self, other: float) -> Self:
        ...


@overload
def lerp(a: int, b: int, t: float) -> float: ...  # noqa: E704
@overload
def lerp(a: float, b: float, t: float) -> float: ...  # noqa: E704
@overload
def lerp[T: Lerpable](a: T, b: T, t: float) -> T: ...  # noqa: E704


def lerp(a, b, t):
    return a + (b - a) * t


def index_if(items, predicate, missing=-1):
    for index, item in enumerate(items):
        if predicate(item):
            return index

    return missing


def find_if(items, predicate, missing=None):
    for item in items:
        if predicate(item):
            return item

    return missing


def get_property_type(prop: object) -> type:
    if hasattr(prop, 'fget'):
        prop_type = typing.get_type_hints(prop.fget)['return']
    else:
        prop_type = typing.get_type_hints(prop.__get__)['return']

    if isinstance(prop_type, typing.TypeVar):
        if (hasattr(prop, '__orig_class__') and
                hasattr(prop.__orig_class__, '__args__')):
            idx = prop.__parameters__.index(prop_type)
            prop_type = prop.__orig_class__.__args__[idx]
        else:
            for base in prop.__orig_bases__:
                origin = typing.get_origin(base)
                args = typing.get_args(base)
                if origin is not None and hasattr(origin, '__parameters__'):
                    tvar_map = dict(zip(origin.__parameters__, args))
                    prop_type = tvar_map.get(prop_type, prop_type)
                    break

    return prop_type
