from tinycam.project import CncProjectItem, CncDrillJob, ExcellonItem
from tinycam.ui.commands.create_item import CreateItemCommandBase


class CreateDrillJobCommand(CreateItemCommandBase):
    def __init__(self, item: ExcellonItem):
        super().__init__('Create Drill Job')
        self._source_item: ExcellonItem = item
        self._item = None

    @property
    def source_item(self) -> ExcellonItem:
        return self._source_item

    @property
    def item(self) -> CncProjectItem | None:
        if self._item is None:
            self._item = CncDrillJob(self.source_item)

        return self._item
