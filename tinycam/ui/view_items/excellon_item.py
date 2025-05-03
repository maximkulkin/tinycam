from tinycam.types import Matrix44
from tinycam.ui.view_items.project_item import CncProjectItemView


class ExcellonItemView(CncProjectItemView):

    def _model_matrix(self):
        return (
            Matrix44.from_translation((self.model.offset[0], self.model.offset[1], 0.0)) *
            Matrix44.from_scale((self.model.scale[0], self.model.scale[1], 1.0))
        )

