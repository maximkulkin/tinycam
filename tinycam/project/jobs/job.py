from tinycam.project.item import CncProjectItem


class CncJob(CncProjectItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._geometry = None

    @property
    def geometry(self):
        return self._geometry

    def generate_commands(self):
        raise NotImplemented()

