from collections.abc import Sequence
import dataclasses
from typing import List

from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt

import tinycam.settings as s
from tinycam.utils import find_if


@dataclasses.dataclass
class TreeItem:
    name: str
    row: int
    id: int
    parent_id: int = 0
    children: List['TreeItem'] = dataclasses.field(default_factory=list)
    settings: List[s.CncSetting] = dataclasses.field(default_factory=list)


class CncSettingsModel(QtCore.QAbstractItemModel):

    def __init__(self, settings: s.CncSettings):
        super().__init__()
        self._settings = settings
        self._root = TreeItem('root', row=-1, id=0)
        self._items_by_id = {self._root.id: self._root}

        next_id = 1
        for setting in self._settings:
            parts = setting.path.split('/')

            root = self._root
            for part in parts[:-1]:
                child = find_if(root.children, lambda c: c.name == part)
                if child is None:
                    child = TreeItem(part, len(root.children), next_id, parent_id=root.id)
                    root.children.append(child)

                    self._items_by_id[child.id] = child

                    next_id += 1

                root = child

            root.settings.append(setting)

    def get_item_by_index(self, index: QtCore.QModelIndex = QtCore.QModelIndex()):
        return self._items_by_id.get(index.internalId())

    def data(self, index, role):
        item = self.get_item_by_index(index)
        if item is None:
            return None

        if role != Qt.DisplayRole:
            return None

        if index.column() == 0:
            return s.humanize(item.name)
        return None

    def index(self, row, column, parent_index: QtCore.QModelIndex = QtCore.QModelIndex()):
        parent = self.get_item_by_index(parent_index)
        if parent is None:
            return QtCore.QModelIndex()

        if row < 0 or row >= len(parent.children):
            return QtCore.QModelIndex()

        item = parent.children[row]

        return self.createIndex(item.row, column, id=item.id)

    def parent(self, index: QtCore.QModelIndex):
        item = self.get_item_by_index(index)
        if item is None:
            return QtCore.QModelIndex()

        parent = self._items_by_id.get(item.parent_id)
        if parent is None:
            return QtCore.QModelIndex()

        return self.createIndex(parent.row, index.column(), id=parent.id)

    def rowCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()):
        item = self.get_item_by_index(parent)
        return len(item.children)

    def columnCount(self, parent: QtCore.QModelIndex = QtCore.QModelIndex()):
        return 1


class CncSettingsDialog(QtWidgets.QDialog):
    def __init__(self, settings: s.CncSettings, parent=None):
        super().__init__(parent=parent)

        self.resize(800, 600)

        self.settings = settings

        self._tree_model = CncSettingsModel(self.settings)
        self._tree_view = QtWidgets.QTreeView(self)
        self._tree_view.setMinimumSize(QtCore.QSize(300, 300))
        self._tree_view.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.MinimumExpanding,
        )
        self._tree_view.setModel(self._tree_model)
        self._tree_view.setHeaderHidden(True)
        self._tree_view.setItemsExpandable(True)
        # self._tree_view.setExpandsOnDoubleClick(True)
        self._tree_view.setIndentation(20)
        self._tree_view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self._tree_view.expandAll()
        self._tree_view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self._tree_view.selectionModel().currentRowChanged.connect(self._on_selection_row_changed)

        self._main_panel_layout = QtWidgets.QGridLayout()

        main_panel_layout = QtWidgets.QVBoxLayout()
        main_panel_layout.addLayout(self._main_panel_layout)
        main_panel_layout.addStretch()

        self._main_panel = QtWidgets.QWidget(self)
        self._main_panel.setLayout(main_panel_layout)

        main_area_layout = QtWidgets.QHBoxLayout()
        main_area_layout.addWidget(self._tree_view)
        main_area_layout.addWidget(self._main_panel)

        close_button = QtWidgets.QPushButton('Close', self)
        close_button.clicked.connect(self.accept)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setAlignment(Qt.AlignHCenter)
        buttons_layout.addWidget(close_button)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(main_area_layout)
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

    def _on_selection_row_changed(self, current: QtCore.QModelIndex, previous: QtCore.QModelIndex):
        item = self._tree_model.get_item_by_index(current)
        if item is None:
            return

        self._populate_view(item.settings)

    def _populate_view(self, settings: Sequence[s.CncSetting]):
        layout = self._main_panel_layout
        while layout.count() > 0:
            item = layout.takeAt(0)
            item.widget().setParent(None)

        for i, setting in enumerate(settings):
            widget = self._make_setting_widget(setting)
            layout.addWidget(QtWidgets.QLabel(setting.label), i, 0)
            layout.addWidget(widget, i, 1)

    def _make_setting_widget(self, setting: s.CncSetting) -> QtWidgets.QWidget:
        match setting:
            case s.CncStringSetting():
                widget = QtWidgets.QLineEdit()
                widget.setText(self.settings.get(setting) or '')
                widget.editingFinished.connect(
                    lambda: self.settings.set(setting, widget.text())
                )
                return widget
            case s.CncIntegerSetting():
                widget = QtWidgets.QSpinBox()
                if setting.minimum is not None:
                    widget.setMinimum(setting.minimum)
                if setting.maximum is not None:
                    widget.setMaximum(setting.maximum)
                if setting.suffix is not None:
                    widget.setSuffix(self._format_suffix(setting.suffix))
                widget.setValue(self.settings.get(setting) or 0)
                widget.valueChanged.connect(
                    lambda: self.settings.set(setting, widget.value())
                )
                return widget
            case s.CncFloatSetting():
                widget = QtWidgets.QDoubleSpinBox()
                if setting.minimum is not None:
                    widget.setMinimum(setting.minimum)
                if setting.maximum is not None:
                    widget.setMaximum(setting.maximum)
                if setting.suffix is not None:
                    widget.setSuffix(self._format_suffix(setting.suffix))
                widget.setValue(self.settings.get(setting) or 0.0)
                widget.valueChanged.connect(
                    lambda: self.settings.set(setting, widget.value())
                )
                return widget
            case s.CncBooleanSetting():
                widget = QtWidgets.QCheckBox()
                widget.setCheckState(Qt.Checked if self.settings.get(setting) else Qt.Unchecked)
                widget.checkStateChanged.connect(
                    lambda state: self.settings.set(setting, state == Qt.Checked)
                )
                return widget
            case s.CncEnumSetting():
                widget = QtWidgets.QComboBox()
                for value in setting.enum_type:
                    label = str(value)
                    widget.addItem(label, value)
                widget.setCurrentIndex(widget.findData(self.settings.get(setting)))
                widget.currentIndexChanged.connect(
                    lambda idx: self.settings.set(setting, widget.itemData(idx))
                )
                return widget
            case _:
                print(f'Unknown setting type: {setting.type}')
                return None

    def _format_suffix(self, suffix: str) -> str:
        units = 'mm'
        match s.SETTINGS.get('general/units'):
            case s.Units.MM:
                units = 'mm'
            case s.Units.IN:
                units = 'in'

        return ' ' + suffix.format(units=units)
