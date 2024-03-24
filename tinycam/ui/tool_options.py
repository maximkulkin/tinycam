from PySide6 import QtCore, QtWidgets

from tinycam.globals import CncGlobals
from tinycam.ui.window import CncWindow
from tinycam.ui.options import CncProjectItemOptionsView, CncIsolateJobOptionsView


class CncToolOptionsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("tool_options_window")
        self.setWindowTitle("Tool options")

        self._options_views = []
        self._options_views.append(CncIsolateJobOptionsView(self))
        self._options_views.append(CncProjectItemOptionsView(self))

        layout = QtWidgets.QVBoxLayout()
        for view in self._options_views:
            layout.addWidget(view)
        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(layout)
        self.setWidget(main_widget)

        self._current_view = None
        self._items = []
        CncGlobals.APP.project.selection.changed.connect(self._on_project_selection_changed)

    def _on_project_selection_changed(self):
        if len(self._items) != 0:
            self._deactivate_view()

        self._items = CncGlobals.APP.project.selectedItems
        if len(self._items) != 0:
            for view in self._options_views:
                if view.matches(self._items):
                    self._activate_view(view)
                    break

    def _activate_view(self, view):
        if self._current_view is view:
            return

        if self._current_view is not None:
            self._current_view.deactivate()

        self._current_view = view
        self._current_view.activate()

    def _deactivate_view(self):
        if self._current_view is None:
            return

        self._current_view.deactivate()
        self._current_view = None
