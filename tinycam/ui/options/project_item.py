from tinycam.project import CncProjectItem
from tinycam.ui.options_base import CncOptionsView


class CncProjectItemOptionsView(CncOptionsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._scale_edit = self._add_vector_edit("Scale")
        self._offset_edit = self._add_vector_edit("Offset")

    def matches(self, items):
        return all(isinstance(item, CncProjectItem) for item in items)
