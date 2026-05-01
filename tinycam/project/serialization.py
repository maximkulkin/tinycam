import json

from tinycam.project.item import CncProjectItem
from tinycam.project.gerber_item import GerberItem
from tinycam.project.excellon_item import ExcellonItem
from tinycam.project.svg_item import SvgItem
from tinycam.project.geometry import GeometryItem
from tinycam.project.rectangle import RectangleItem
from tinycam.project.jobs.cutout_job import CncCutoutJob
from tinycam.project.jobs.isolate_job import CncIsolateJob
from tinycam.project.jobs.drill_job import CncDrillJob


_TYPE_REGISTRY: dict[str, type[CncProjectItem]] = {
    'gerber': GerberItem,
    'excellon': ExcellonItem,
    'svg': SvgItem,
    'geometry_item': GeometryItem,
    'rectangle': RectangleItem,
    'cutout_job': CncCutoutJob,
    'isolate_job': CncIsolateJob,
    'drill_job': CncDrillJob,
}

_TYPE_NAMES: dict[type[CncProjectItem], str] = {v: k for k, v in _TYPE_REGISTRY.items()}


def save_project(items: list[CncProjectItem], path: str) -> None:
    items_data = []
    for item in items:
        data = item.save()
        data['id'] = item.id
        data['type'] = _TYPE_NAMES[type(item)]
        items_data.append(data)

    doc = {'version': 1, 'items': items_data}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2)


def load_project(path: str) -> list[CncProjectItem]:
    with open(path, 'r', encoding='utf-8') as f:
        doc = json.load(f)

    items: list[CncProjectItem] = []
    items_by_id: dict[str, CncProjectItem] = {}

    for item_data in doc.get('items', []):
        type_name = item_data.get('type')
        cls = _TYPE_REGISTRY.get(type_name)
        if cls is None:
            raise ValueError(f'Unknown item type: {type_name!r}')

        item = cls()
        item.load(item_data)
        items_by_id[item.id] = item
        items.append(item)

    for item in items:
        item.resolve_references(items_by_id)

    return items
