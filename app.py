from functools import reduce
import math
import os.path
import sys

import shapely
from PySide6.QtCore import Qt, QSettings, Signal, QObject, QPointF, QRectF, \
    QMarginsF, QSizeF, QAbstractListModel, QModelIndex, QItemSelection, QItemSelectionModel
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QDockWidget, \
    QMenuBar, QToolBar, QStatusBar, QListView, QVBoxLayout, QFileDialog, \
    QAbstractItemView
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPen, QMouseEvent, \
    QPainterPath
from geometry import Geometry, BaseShape
from gerber_parser import parse_gerber


GEOMETRY = Geometry()


class GerberObject:
    def __init__(self, name, geometry):
        self.name = name
        self.geometry = geometry
        self._geometry_cache = None

    def draw(self, painter):
        if not self._geometry_cache:
            path = QPainterPath()

            exteriors = GEOMETRY.exteriors(self.geometry)
            if exteriors:
                path.addPolygon(
                    QPolygonF.fromList([
                        QPointF(x, y)
                        for x, y in GEOMETRY.points(exteriors[0])
                    ])
                )

                for exterior in exteriors[1:]:
                    p = QPainterPath()
                    p.addPolygon(
                        QPolygonF.fromList([
                            QPointF(x, y)
                            for x, y in GEOMETRY.points(exterior)
                        ])
                    )
                    path = path.united(p)

                for interior in GEOMETRY.interiors(self.geometry):
                    p = QPainterPath()
                    p.addPolygon(
                        QPolygonF.fromList([
                            QPointF(x, y)
                            for x, y in GEOMETRY.points(interior)
                        ])
                    )
                    path = path.subtracted(p)

            self._geometry_cache = path

        painter.drawPath(self._geometry_cache)


class CncJob:
    def __init__(self):
        self._geometry = None

    @property
    def geometry(self):
        return self._geometry

    def update(self):
        pass

    def draw(self, painter):
        pass


class CncIsolateJob(CncJob):
    def __init__(self, source_geometry, tool_diameter, cut_depth, feed_rate, spindle_speed):
        super().__init__()
        self._source_geometry = source_geometry
        self._tool_diameter = tool_diameter
        self._cut_depth = cut_depth
        self._feed_rate = feed_rate
        self._spindle_speed = spindle_speed

        self._geometry = None

    @property
    def geometry(self):
        return self._isolation_geometry

    @property
    def tool_diameter(self):
        return self._tool_diameter

    @tool_diameter.setter
    def tool_diameter(self, value):
        self._tool_diameter = value
        self.update()

    @property
    def feed_rate(self):
        return self._feed_rate

    @feed_rate.setter
    def feed_rate(self, value):
        self._feed_rate = value
        self.update()

    @property
    def spindle_speed(self):
        return self._spindle_speed

    @spindle_speed.setter
    def spindle_speed(self, value):
        self._spindle_speed = value
        self.update()

    def update(self):
        self._geometry = s


class Project(QObject):
    objects_changed = Signal()
    selection_changed = Signal()

    def __init__(self):
        super().__init__()
        self._objects = []
        self._selection = set()

        self._jobs = []

    @property
    def objects(self):
        return self._objects

    @property
    def jobs(self):
        return self._jobs

    def import_gerber(self, path):
        with open(path, 'rt') as f:
            geometry = parse_gerber(f.read(), geometry=GEOMETRY)
            name, ext = os.path.splitext(os.path.basename(path))
            obj = GerberObject(name, geometry)
            self._objects.append(obj)
            self.objects_changed.emit()
            return obj

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, value):
        if not isinstance(value, set):
            raise ValueError('Selection should be a set')

        self._selection = value
        self.selection_changed.emit()


def combine_bounds(b1, b2):
    return (min(b1[0], b2[0]), min(b1[1], b2[1]), max(b1[2], b2[2]), max(b1[3], b2[3]))

def total_bounds(shapes):
    coords = reduce(combine_bounds, [shape.bounds for shape in shapes])
    return QRectF(coords[0], coords[1], coords[2] - coords[0], coords[3] - coords[1])


class CncHandle:
    def __init__(self, position):
        self.position = position

    def draw(self, painter):
        pass

    def contains(self, point):
        return False


class CncBoxHandle(CncHandle):
    def draw(self, painter):
        painter.drawRect(self.position.x(), self.position.y(),
                         self.size.x(), self.size.y())

    def contains(self, point):
        return (
            abs(point.x() - self.position.x()) <= self.size.x() and
            abs(point.y() - self.position.y()) <= self.size.y()
        )


class CncTool:
    def __init__(self):
        pass

    def keyboardEvent(self, event):
        pass

    def mousePressEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def wheelEvent(self, event):
        pass

    def paint(self, painter):
        pass


class CncProjectView(QWidget):
    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project
        self.setMouseTracking(True)

        self._scale = 1.0
        self._offset = QPointF(0.0, 0.0)

        self._panning = False
        self._last_mouse_position = QPointF(0.0, 0.0)
        self._selected_geometries = []

        self._geometry_cache = {}
        self._handles = []

        self.project.selection_changed.connect(self.update)
    
    def _zoom(self, k, position=None):
        self._scale *= k
        self._offset = self._offset * k + position * (1 - k)
        self.repaint()

    def zoom_in(self):
        self._zoom(1.0 / 0.8, QPointF(self.width()/2, self.height()/2))

    def zoom_out(self):
        self._zoom(0.8, QPointF(self.width()/2, self.height()/2))

    def zoom_to_fit(self):
        bounds = reduce(combine_bounds, [obj.geometry.bounds for obj in self.project.objects])

        self._scale = min((self.width() - 20) / (bounds[2] - bounds[0]),
                          (self.height() - 20) / (bounds[3] - bounds[1]))
        w = (bounds[2] - bounds[0]) * self._scale
        h = (bounds[3] - bounds[1]) * self._scale
        self._offset = self._canvas_to_screen_point(
            self._screen_to_canvas_point(
                QPointF((self.width() - w) * 0.5, (self.height() - h) * 0.5)
            ) - QPointF(bounds[0], bounds[1])
        )
        self.repaint()

    def mousePressEvent(self, event):
        # print('mouse press: %s' % event)
        if event.buttons() == Qt.LeftButton:
            idx = self._find_geometry_at(
                self._screen_to_canvas_point(event.position())
            )
            if event.modifiers() & Qt.ShiftModifier:
                if idx != -1:
                    if idx in self.project.selection:
                        self.project.selection -= {idx}
                    else:
                        self.project.selection |= {idx}
            else:
                self.project.selection = set() if idx == -1 else {idx}
            self.repaint()
        elif event.buttons() == Qt.MiddleButton:
            self._panning = True
            self._last_mouse_position = event.position()
        event.accept()

    def mouseReleaseEvent(self, event):
        # print('mouse release: %s' % event)
        if self._panning and (event.button() == Qt.MiddleButton):
            self._panning = False
        event.accept()

    def mouseMoveEvent(self, event):
        # print('mouse move: %s' % event)
        if self._panning:
            self._offset += (event.position() - self._last_mouse_position)
            self.repaint()

        self._last_mouse_position = event.position()
        event.accept()

    def wheelEvent(self, event):
        dy = event.pixelDelta().y()
        if dy == 0:
            return

        self._zoom(0.9 if dy < 0 else 1.0 / 0.9, event.position())

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("white"))

        painter.translate(self._offset)
        painter.scale(self._scale, self._scale)

        self._draw_grid(painter)
        self._draw_axis(painter)

        pen = QPen()
        pen.setColor(QColor("black"))
        pen.setWidthF(2 / self._scale)
        painter.setPen(pen)

        brush = QBrush()
        brush.setColor(QColor("grey"))
        brush.setStyle(Qt.SolidPattern)
        painter.setBrush(brush)

        for idx, obj in enumerate(self.project.objects):
            if idx in self._selected_geometries:
                continue

            obj.draw(painter)

        if self.project.selection:
            selectedBrush = QBrush()
            selectedBrush.setColor(QColor("grey").lighter(120.0))
            selectedBrush.setStyle(Qt.SolidPattern)
            painter.setBrush(selectedBrush)

            selectedPen = QPen()
            selectedPen.setColor(QColor("black").lighter(120.0))
            selectedPen.setWidthF(2 / self._scale)
            painter.setPen(selectedPen)

            for idx in sorted(self.project.selection):
                if idx < 0 or idx >= len(self.project.objects):
                    print('selected index is out of bounds')
                    continue

                self.project.objects[idx].draw(painter)

            self._draw_selection_handles(
                painter, [self.project.objects[idx].geometry
                          for idx in self.project.selection])

    def _draw_axis(self, painter):
        pmin = self._screen_to_canvas_point((0, 0))
        pmax = self._screen_to_canvas_point((self.width(), self.height()))
        pen = QPen()
        pen.setWidthF(2 / self._scale)
        # pen.setColor(QColor(1.0, 0.0, 0.0, 0.5))
        pen.setColor(QColor("red"))
        painter.setPen(pen)
        painter.drawLine(QPointF(pmin.x(), 0), QPointF(pmax.x(), 0))

        # pen.setColor(QColor(0.0, 1.0, 0.0, 0.5))
        pen.setColor(QColor("green"))
        painter.setPen(pen)
        painter.drawLine(QPointF(0, pmin.y()), QPointF(0, pmax.y()))

    def _draw_grid_with_step(self, painter, step):
        pmin = self._screen_to_canvas_point((0, 0))
        pmax = self._screen_to_canvas_point((self.width(), self.height()))

        # draw horizontal lines
        y = pmin.y() - pmin.y() % step + step
        while y < pmax.y():
            painter.drawLine(QPointF(pmin.x(), y), QPointF(pmax.x(), y))
            y += step

        # draw vertical lines
        x = pmin.x() - pmin.x() % step + step
        while x < pmax.x():
            painter.drawLine(QPointF(x, pmin.y()), QPointF(x, pmax.y()))
            x += step

    def _draw_grid(self, painter):
        pen = QPen()
        pen.setColor(QColor("grey"))
        painter.setPen(pen)

        grid_step = 10 / (10 ** math.floor(math.log10(self._scale)))

        # draw minor lines
        pen.setWidthF(0.5 / self._scale)
        painter.setPen(pen)
        self._draw_grid_with_step(painter, grid_step)

        # draw major lines
        pen.setWidthF(1.5 / self._scale)
        painter.setPen(pen)
        self._draw_grid_with_step(painter, 10 * grid_step)

    def _draw_selection_handles(self, painter, geometries):
        margin = QMarginsF() + 10
        bounds = total_bounds(geometries).marginsAdded(margin / self._scale)

        self._draw_box_handle(painter, bounds.topLeft())
        self._draw_box_handle(painter, bounds.topRight())
        self._draw_box_handle(painter, bounds.bottomLeft())
        self._draw_box_handle(painter, bounds.bottomRight())

    def _draw_box_handle(self, painter, position, size=QSizeF(10, 10)):
        canvas_size = size / self._scale
        painter.drawRect(QRectF(position.x() - canvas_size.width()*0.5,
                                position.y() - canvas_size.height()*0.5,
                                canvas_size.width(), canvas_size.height()));

    def _screen_to_canvas_point(self, point):
        if not isinstance(point, QPointF):
            point = QPointF(point[0], point[1])
        return (point - self._offset) / self._scale

    def _canvas_to_screen_point(self, point):
        if not isinstance(point, QPointF):
            point = QPointF(point[0], point[1])
        return point * self._scale + self._offset

    def _find_geometry_at(self, point):
        for idx, obj in enumerate(self.project.objects):
            if GEOMETRY.contains(obj.geometry, (point.x(), point.y())):
                return idx

        return -1


class CncWindow(QDockWidget):
    visibilityChanged = Signal()

    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.project = project
        self.setMinimumSize(200, 200)

    def showEvent(self, event):
        self.visibilityChanged.emit()
        super().showEvent(event)

    def hideEvent(self, event):
        self.visibilityChanged.emit()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.hide()
        event.accept()


class ProjectModel(QAbstractListModel):
    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project = project
        self._project.objects_changed.connect(self._on_objects_changed)

    def rowCount(self, parent=QModelIndex()):
        return len(self._project.objects)

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None

        return self._project.objects[index.row()].name

    def _on_objects_changed(self):
        self.dataChanged.emit(self.createIndex(0, 0),
                              self.createIndex(len(self._project.objects), 1))


class CncObjectsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("objects_window")
        self.setWindowTitle("Obejcts")

        self._view = QListView()
        self._view.setModel(ProjectModel(self.project))
        self._view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._view.setSelectionBehavior(QAbstractItemView.SelectRows)

        self._view.selectionModel().selectionChanged.connect(self._on_view_selection_changed)
        self._updating_selection = False

        self.project.selection_changed.connect(self._on_project_selection_changed)

        self.setWidget(self._view)

    def _on_view_selection_changed(self, selected, deselected):
        if self._updating_selection:
            return

        self.project.selection = (self.project.selection | {idx.row() for idx in selected.indexes()}) - {idx.row() for idx in deselected.indexes()}

    def _on_project_selection_changed(self):
        selectionModel = self._view.selectionModel()
        self._updating_selection = True
        selectionModel.clear()
        for idx in self.project.selection:
            selectionModel.select(
                QItemSelection(self._view.model().createIndex(idx, 0),
                               self._view.model().createIndex(idx, 0)),
                QItemSelectionModel.Select
            )
        self._updating_selection = False


class CncJobsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("jobs_window")
        self.setWindowTitle("Jobs")


class CncToolOptionsWindow(CncWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("tool_options_window")
        self.setWindowTitle("Tool options")


class CncMainWindow(QMainWindow):
    def __init__(self, project, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(600, 400)

        self.project = project
        self.project_view = CncProjectView(self.project, self)
        self.setCentralWidget(self.project_view)

        self.menu = QMenuBar()
        self.file_menu = self.menu.addMenu("File")
        self.file_menu.addAction('Import Gerber', self._import_gerber,
                                 shortcut='Ctrl+o')

        self.view_menu = self.menu.addMenu("View")

        self.setMenuBar(self.menu)

        self.toolbar = QToolBar()
        self.toolbar.setObjectName('Toolbar')
        self.addToolBar(self.toolbar)
        self.toolbar.addAction('Import', self._import_gerber)
        self.toolbar.addAction('Zoom To Fit', self.project_view.zoom_to_fit)

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self._windows = []
        self._windows_menu = {}

        self._add_dock_window(
            CncObjectsWindow(self.project), Qt.LeftDockWidgetArea,
            shortcut='Ctrl+1',
        )
        self._add_dock_window(
            CncJobsWindow(self.project), Qt.LeftDockWidgetArea,
            shortcut='Ctrl+2',
        )
        self._add_dock_window(
            CncToolOptionsWindow(self.project), Qt.RightDockWidgetArea,
            shortcut='Ctrl+3',
        )

        self.view_menu.addSeparator()
        self.view_menu.addAction('Zoom In', self.project_view.zoom_in,
                                 shortcut='Ctrl++')
        self.view_menu.addAction('Zoom Out', self.project_view.zoom_out,
                                 shortcut='Ctrl+-')
        self.view_menu.addAction('Zoom To Fit', self.project_view.zoom_to_fit,
                                 shortcut='Ctrl+=')
        self.view_menu.addSeparator()

        self._load_settings()

    def _import_gerber(self):
        result = QFileDialog.getOpenFileName(
            parent=self, caption='Import Gerber',
            # filter='Gerber (*.gbr);Excellon (*.drl)'
        )
        if result[0] != '':
            self.project.import_gerber(result[0])

    def _add_dock_window(self, window, area, shortcut=''):
        self._windows.append(window)
        self.addDockWidget(area, window)
        action = self.view_menu.addAction(
            window.windowTitle(), lambda: self._toggle_window(window),
            shortcut=shortcut)
        action.setCheckable(True)
        self._windows_menu[window] = action

    def _toggle_window(self, window):
        if window.isVisible():
            window.hide()
        else:
            window.show()

        if window in self._windows_menu:
            self._windows_menu.get(window).setChecked(window.isVisible())

    def showEvent(self, event):
        super().showEvent(event)

        for window in self._windows:
            self._windows_menu[window].setChecked(window.isVisible())

        self.project_view.zoom_to_fit()

    def closeEvent(self, event):
        self._save_settings()
        super().closeEvent(event)

    def _save_settings(self):
        settings = QSettings()
        settings.beginGroup("main_window")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        settings.endGroup()

    def _load_settings(self):
        settings = QSettings()
        settings.beginGroup("main_window")
        self.restoreGeometry(settings.value("geometry"))
        self.restoreState(settings.value("windowState"))
        settings.endGroup()


PROJECT = Project()
PROJECT.import_gerber('sample.gbr')

app = QApplication(sys.argv)

main_window = CncMainWindow(PROJECT)
main_window.show()

app.exec()
