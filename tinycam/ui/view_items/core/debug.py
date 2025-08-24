from tinycam.ui.view import Context, RenderState
from tinycam.ui.view_items.core import Node3D


class Debug(Node3D):
    def __init__(
        self,
        context: Context,
        debug: bool = True,
    ):
        super().__init__(context)
        self._debug = debug

    @property
    def debug(self) -> bool:
        return self._debug

    @debug.setter
    def debug(self, value: bool):
        self._debug = value

    def render(self, state: RenderState):
        with self.context.scope(wireframe=self._debug):
            super().render(state)
