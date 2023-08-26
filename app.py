import sys

import shapely
from PySide6.QtCore import Qt, QSettings, Signal, QPointF
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QDockWidget, \
    QMenuBar, QToolBar, QStatusBar
from PySide6.QtGui import QPainter, QColor, QPolygonF, QBrush, QPen, QMouseEvent


class Project:
    def __init__(self):
        self._geometry = [
            shapely.box(10, 10, 100, 50),
            shapely.box(200, 30, 100, 20),
        ]

    @property
    def geometry(self):
        return self._geometry


PROJECT = Project()


class CncProjectView(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)

        self._scale = 1.0
        self._offset = QPointF(0.0, 0.0)

        self._selecting = False
        self._moving = False
        self._last_mouse_position = QPointF(0.0, 0.0)
        self._selected_geometries = []

    def mousePressEvent(self, event):
        # print('mouse press: %s' % event)
        if event.buttons() == Qt.LeftButton:
            idx = self._find_geometry_at(
                self._screen_to_canvas_point(event.position())
            )
            if event.modifiers() & Qt.ShiftModifier:
                if idx != -1:
                    if idx in self._selected_geometries:
                        self._selected_geometries.remove(idx)
                    else:
                        self._selected_geometries.append(idx)
                        self._selected_geometries.sort()
            else:
                self._selected_geometries = [] if idx == -1 else [idx]
            self.repaint()
        elif event.buttons() == Qt.MiddleButton:
            self._moving = True
            self._last_mouse_position = event.position()
        event.accept()

    def mouseReleaseEvent(self, event):
        # print('mouse release: %s' % event)
        if self._moving and (event.button() == Qt.MiddleButton):
            self._moving = False
        event.accept()

    def mouseMoveEvent(self, event):
        # print('mouse move: %s' % event)
        if self._moving:
            self._offset += (event.position() - self._last_mouse_position)
            self.repaint()

        self._last_mouse_position = event.position()
        event.accept()

    def wheelEvent(self, event):
        if event.pixelDelta().y() == 0:
            return

        event_pos = event.position()
        canvas_pos = (event_pos - self._offset) / self._scale

        if event.pixelDelta().y() < 0:
            self._scale *= 0.9
        elif event.pixelDelta().y() > 0:
            self._scale /= 0.9
        self._offset = event_pos - canvas_pos * self._scale
        self.repaint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("white"))

        painter.translate(self._offset)
        painter.scale(self._scale, self._scale)

        painter.setBrush(QColor("grey"))
        painter.setPen(QColor("black"))

        for idx, geometry in enumerate(PROJECT.geometry):
            if idx in self._selected_geometries:
                continue

            self._draw_geometry(painter, geometry)

        painter.setPen(QColor("yellow"))
        for idx in self._selected_geometries:
            self._draw_geometry(painter, PROJECT.geometry[idx])

    def _draw_geometry(self, painter, geometry):
        painter.drawPolygon(
            QPolygonF.fromList([
                QPointF(x, y)
                for x, y in geometry.exterior.coords
            ]),
        )

    def _screen_to_canvas_point(self, point):
        return (point - self._offset) / self._scale

    def _canvas_to_screen_point(self, point):
        return point * self._scale + self._offset

    def _find_geometry_at(self, point):
        for idx, geometry in enumerate(PROJECT.geometry):
            if shapely.contains_xy(geometry, point.x(), point.y()):
                return idx

        return -1


class CncWindow(QDockWidget):
    visibilityChanged = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.resize(600, 400)

        self.project_view = CncProjectView(self)
        self.setCentralWidget(self.project_view)

        self.menu = QMenuBar()
        self.windows_menu = self.menu.addMenu("Windows")

        self.setMenuBar(self.menu)

        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self._windows = []
        self._windows_menu = {}

        self._add_dock_window(CncJobsWindow(), Qt.LeftDockWidgetArea)
        self._add_dock_window(CncToolOptionsWindow(), Qt.RightDockWidgetArea)

        self._load_settings()

    def _add_dock_window(self, window, area):
        self._windows.append(window)
        self.addDockWidget(area, window)
        action = self.windows_menu.addAction(
            window.windowTitle(), lambda: self._toggle_window(window))
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


app = QApplication(sys.argv)

main_window = CncMainWindow()
main_window.show()

app.exec()
