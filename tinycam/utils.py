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
