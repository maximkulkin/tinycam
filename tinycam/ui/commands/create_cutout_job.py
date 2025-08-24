from tinycam.project import CncProjectItem, CncCutoutJob
from tinycam.ui.commands.create_item import CreateItemCommandBase


class CreateCutoutJobCommand(CreateItemCommandBase):
    def __init__(self, item: CncProjectItem):
        super().__init__('Create Cutout Job')
        self._source_item = item
        self._item = None

    @property
    def source_item(self) -> CncProjectItem:
        return self._source_item

    @property
    def item(self) -> CncProjectItem | None:
        if self._item is None:
            self._item = CncCutoutJob(self.source_item)

        return self._item
