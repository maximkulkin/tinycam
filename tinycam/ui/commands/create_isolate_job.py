from tinycam.project import CncProjectItem, CncIsolateJob
from tinycam.ui.commands.create_item import CreateItemCommandBase


class CreateIsolateJobCommand(CreateItemCommandBase):
    def __init__(self, item: CncProjectItem):
        super().__init__('Create Isolate Job')
        self._source_item = item
        self._item = None

    @property
    def source_item(self) -> CncProjectItem:
        return self._source_item

    @property
    def item(self) -> CncProjectItem | None:
        if self._item is None:
            self._item = CncIsolateJob()
            self._item.source_item = self.source_item
        return self._item
