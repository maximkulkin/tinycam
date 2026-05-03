import os.path

from PIL import Image
from PySide6 import QtGui

from tinycam.project.item import CncProjectItem
from tinycam.math_types import Rect, Vector2


class ImageItem(CncProjectItem):
    def __init__(self):
        super().__init__()
        self.name = 'Image'
        self.color = QtGui.QColor(255, 255, 255, 255)
        self._path = ''
        self._image: Image.Image | None = None
        self._rect = Rect(0.0, 0.0, 0.0, 0.0)

    @property
    def path(self) -> str:
        return self._path

    @property
    def image(self) -> Image.Image | None:
        return self._image

    @property
    def bounds(self) -> Rect:
        return self._rect

    @staticmethod
    def from_file(path: str) -> 'ImageItem':
        image = Image.open(path).convert('RGBA')
        w, h = image.size
        item = ImageItem()
        item.name = os.path.basename(path)
        item._path = path
        item._image = image
        item._rect = Rect(-w / 2.0, -h / 2.0, float(w), float(h))
        return item

    def translate(self, offset: Vector2):
        self._rect = self._rect.translated(offset)
        self._signal_changed()

    def scale(self, scale: Vector2, origin: Vector2 = Vector2()):
        self._rect = self._rect.scaled(scale, origin)
        self._signal_changed()

    def save(self) -> dict:
        data = super().save()
        data['path'] = self._path
        data['rect'] = [float(self._rect.x), float(self._rect.y),
                        float(self._rect.width), float(self._rect.height)]
        return data

    def load(self, data: dict) -> None:
        with self:
            super().load(data)
            if 'path' in data:
                path = data['path']
                try:
                    image = Image.open(path).convert('RGBA')
                    self._path = path
                    self._image = image
                except Exception:
                    pass
            if 'rect' in data:
                r = data['rect']
                self._rect = Rect(r[0], r[1], r[2], r[3])
