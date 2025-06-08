from tinycam.globals import GLOBALS
from tinycam.ui.window import CncWindow
from tinycam.ui.property_editor import PropertyEditor


class CncToolOptionsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("tool_options_window")
        self.setWindowTitle("Tool options")

        self._property_editor = PropertyEditor()
        self.setWidget(self._property_editor)

        GLOBALS.APP.project.selection.changed.connect(self._on_project_selection_changed)

    def _on_project_selection_changed(self):
        items = list(GLOBALS.APP.project.selection)
        if items:
            self._property_editor.target = items[0]
        else:
            self._property_editor.target = None
