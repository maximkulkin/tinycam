import numpy as np
import enum
import math
from typing import cast, Callable, Union

from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from PySide6.QtWidgets import QWidget

from tinycam.settings import SETTINGS, ControlType
from tinycam.types import Vector2, Vector3, Quaternion, Matrix44
from tinycam.utils import lerp
from tinycam.ui.camera import Camera, OrthographicCamera
from tinycam.ui.utils import vector2


class Axis(enum.Enum):
    X = enum.auto()
    Y = enum.auto()
    Z = enum.auto()

    def make_rotation(self) -> Callable[[float], Quaternion]:
        match self:
            case Axis.X: return Quaternion.from_x_rotation
            case Axis.Y: return Quaternion.from_y_rotation
            case Axis.Z: return Quaternion.from_z_rotation


class CameraOrbitAnimation(QtCore.QAbstractAnimation):
    def __init__(
        self,
        controller: 'OrbitController',
        pitch: float,
        yaw: float,
        duration: float,
    ):
        super().__init__()

        self._controller = controller

        self._start_pitch = self._controller.pitch
        self._start_yaw = self._controller.yaw
        self._target_pitch = pitch
        self._target_yaw = yaw

        self._duration_ms = int(duration * 1000)

    def duration(self) -> int:
        return self._duration_ms

    def updateCurrentTime(self, currentTime: int):
        t = currentTime / self.duration()
        # TODO: implement slerp instead of lerp
        pitch = self._start_pitch + t * (self._target_pitch - self._start_pitch)
        yaw = self._start_yaw + t * (self._target_yaw - self._start_yaw)
        self._controller.rotate(pitch, yaw)


class OrbitController(QtCore.QObject):
    def __init__(
        self,
        camera: Camera,
        mouse_sensitivity: Union[float, tuple[float, float]] = 0.01,
    ):
        super().__init__()
        self._widget: QWidget | None = None

        SETTINGS['general/control_type'].changed.connect(self._on_control_type_changed)
        self._on_control_type_changed(SETTINGS.get('general/control_type'))

        self._camera = camera
        _, self._pitch, self._yaw = self._camera.rotation.to_eulers()

        sens = mouse_sensitivity
        self._mouse_sensitivity: Vector2 = (
            Vector2(sens, sens) if isinstance(sens, float) else Vector2(sens)
        )

        self._orbit_point = Vector3(0, 0, 0)
        self._last_position = None
        self._animation = None

    @property
    def pitch(self) -> float:
        return self._pitch

    @property
    def yaw(self) -> float:
        return self._yaw

    def rotate(self, pitch: float, yaw: float, duration: float | None = None):
        if duration is not None:
            if self._animation is not None:
                self._animation.stop()
            self._animation = CameraOrbitAnimation(self, pitch, yaw, duration)
            self._animation.finished.connect(self._on_animation_finished)
            self._animation.start()
            return

        two_pi = 2. * math.pi
        self._pitch = (pitch + two_pi) % (two_pi * 2.) - two_pi
        self._yaw = (yaw + two_pi) % (two_pi * 2.0) - two_pi

        v = self._camera.rotation.conjugate * Camera.FORWARD
        d = v | Vector3(0, 0, -1)
        if d != 0.0:
            self._orbit_point = self._camera.position + v * (self._camera.position.z / d)

        distance = (self._camera.position - self._orbit_point).length

        self._camera.rotation = Quaternion.from_x_rotation(self._pitch) * Quaternion.from_z_rotation(self._yaw)
        self._camera.position = self._orbit_point - self._camera.rotation.conjugate * Camera.FORWARD * distance
        if self._widget is not None:
            self._widget.update()

    def _on_animation_finished(self):
        self._animation = None

    def _on_control_type_changed(self, value: ControlType):
        match value:
            case ControlType.MOUSE:
                self._orbit_button = Qt.MouseButton.MiddleButton
            case ControlType.TOUCHPAD:
                self._orbit_button = Qt.MouseButton.LeftButton

    def eventFilter(self, widget: QWidget, event: QtCore.QEvent) -> bool:
        if widget != self._widget:
            self._widget = widget

        e = cast(QMouseEvent, event)

        if (event.type() == QEvent.Type.MouseButtonPress
                and e.button() == self._orbit_button
                and e.modifiers() & Qt.KeyboardModifier.AltModifier):
            self._last_position = e.position()
            widget.setCursor(QtGui.QCursor(Qt.CursorShape.SizeAllCursor))
            return True
        elif (event.type() == QEvent.Type.MouseButtonRelease
                and e.button() == self._orbit_button
                and self._last_position is not None):
            self._last_position = None
            widget.setCursor(QtGui.QCursor(Qt.CursorShape.ArrowCursor))
            return True
        elif event.type() == QEvent.Type.MouseMove and self._last_position is not None:
            delta = e.position() - self._last_position

            self._last_position = e.position()

            self.rotate(
                yaw=self._yaw + delta.x() * self._mouse_sensitivity[1],
                pitch=self._pitch + delta.y() * self._mouse_sensitivity[0],
            )

        return False


class CameraPanAndZoomAnimation(QtCore.QAbstractAnimation):
    def __init__(
        self,
        camera: OrthographicCamera,
        *,
        duration: float,
        position: Vector3 | None = None,
        zoom: float | None = None,
        on_update: Callable[[], None] = lambda: None,
    ):
        super().__init__()

        self._camera = camera

        self._start_position = Vector3(self._camera.position)

        self._start_zoom = self._camera.zoom

        self._target_position = position if position is not None else self._start_position
        self._target_zoom = zoom if zoom is not None else self._start_zoom
        self._last_t = 0.0
        self._log_start_zoom = math.log(self._start_zoom)
        self._log_target_zoom = math.log(self._target_zoom)

        screen_point = self._camera.project(self._target_position)
        self._position_delta = Vector3.from_vector2(self._camera.pixel_size * 0.5 - screen_point) / self._target_zoom * Vector3(-1, 1, 0)

        self._duration_ms = int(duration * 1000)
        self._on_update = on_update

    def duration(self) -> int:
        return self._duration_ms

    def updateCurrentTime(self, currentTime: int):
        t = currentTime / self.duration()

        delta = (t - self._last_t) * self._position_delta

        screen_point = self._camera.project(self._target_position)
        p0 = self._camera.unproject(screen_point)

        self._camera.zoom = math.exp(lerp(self._log_start_zoom, self._log_target_zoom, t))

        p1 = self._camera.unproject(screen_point)
        v1 = (p0 - p1) * Vector3(1, 1, 0)

        self._camera.position += v1 + delta
        self._on_update()

        self._last_t = t


class PanAndZoomController(QtCore.QObject):
    def __init__(
        self,
        camera: Camera,
    ):
        super().__init__()
        self._widget: QWidget | None = None

        self._camera = camera
        self._start_position = None
        self._last_position = None
        self._pan_button = Qt.MouseButton.MiddleButton
        self._pan_modifiers = Qt.KeyboardModifier.NoModifier
        self._zoom_inverter = 1.0

        self._panning = False

        SETTINGS['general/control_type'].changed.connect(self._on_control_type_changed)
        self._on_control_type_changed(SETTINGS.get('general/control_type'))

        SETTINGS['general/invert_zoom'].changed.connect(self._on_invert_zoom_changed)
        self._on_invert_zoom_changed(SETTINGS.get('general/invert_zoom'))

    def _on_control_type_changed(self, value: ControlType):
        match value:
            case ControlType.MOUSE:
                self._pan_button = Qt.MouseButton.MiddleButton
                self._pan_modifiers = Qt.KeyboardModifier.NoModifier
            case ControlType.TOUCHPAD:
                self._pan_button = Qt.MouseButton.RightButton
                self._pan_modifiers = Qt.KeyboardModifier.MetaModifier

    def _on_invert_zoom_changed(self, value: bool):
        self._zoom_inverter = -1.0 if value else 1.0

    def eventFilter(self, widget: QWidget, event: QtCore.QEvent) -> bool:
        if widget != self._widget:
            self._widget = widget

        if event.type() == QEvent.Type.MouseButtonPress:
            mouse_event = cast(QMouseEvent, event)
            if (mouse_event.button() == self._pan_button and
                    mouse_event.modifiers() == self._pan_modifiers):
                self._start_position = mouse_event.position()
                return False
        elif (event.type() == QEvent.Type.MouseButtonRelease):
            mouse_event = cast(QMouseEvent, event)
            if (mouse_event.button() == self._pan_button and self._panning):
                self._start_position = None
                self._last_position = None
                self._panning = False
                widget.setCursor(QtGui.QCursor(Qt.CursorShape.ArrowCursor))
                return True
        elif (event.type() == QEvent.Type.MouseMove
              and (self._panning or self._start_position is not None)):

            mouse_event = cast(QMouseEvent, event)

            position = mouse_event.position()
            if not self._panning:
                assert self._start_position is not None
                if (self._start_position - position).manhattanLength() > 20:
                    self._panning = True
                    self._last_position = self._start_position
                    return True

                return False

            if (mouse_event.buttons() != self._pan_button or
                    mouse_event.modifiers() != self._pan_modifiers):
                self._panning = False
                self._start_position = None
                return False

            assert self._last_position is not None

            p0 = self._camera.unproject(vector2(self._last_position))
            p1 = self._camera.unproject(vector2(position))
            self._camera.position += (p0 - p1) * Vector3(1, 1, 0)

            widget.setCursor(QtGui.QCursor(Qt.CursorShape.ClosedHandCursor))

            self._last_position = position
            widget.update()
            return True
        elif event.type() == QEvent.Type.Wheel:
            wheel_event = cast(QWheelEvent, event)

            screen_point = wheel_event.position()
            p0 = self._camera.unproject(vector2(screen_point))

            scale = 0.9 ** (wheel_event.angleDelta().y() / 120.0 * self._zoom_inverter)

            if isinstance(self._camera, OrthographicCamera):
                c = cast(OrthographicCamera, self._camera)
                c.zoom /= scale
            else:
                self._camera.position *= Vector3(1, 1, scale)

            p1 = self._camera.unproject(vector2(screen_point))
            self._camera.position += (p0 - p1) * Vector3(1, 1, 0)

            widget.update()

        return False


class FreeMoveController(QtCore.QObject):
    class Direction(enum.IntFlag):
        LEFT = enum.auto()
        RIGHT = enum.auto()
        UP = enum.auto()
        DOWN = enum.auto()
        FORWARD = enum.auto()
        BACKWARD = enum.auto()

    def __init__(
        self,
        camera: Camera,
        move_speed: float = 10,
        mouse_sensitivity: Union[float, tuple[float, float]] = 0.01,
        pitch_axis: Axis = Axis.X,
        yaw_axis: Axis = Axis.Z,
    ):
        super().__init__()
        self._widget = None

        self._camera = camera
        self._pitch_axis = pitch_axis
        self._yaw_axis = yaw_axis

        self._move_speed = move_speed
        self._turbo = False

        sens = mouse_sensitivity
        self._mouse_sensitivity: Vector2 = (
            Vector2(sens, sens) if isinstance(sens, float)
            else Vector2(cast(tuple[float, float], sens))
        )

        self._pitch = 0.0
        self._yaw = 0.0
        self._last_position = None

        make_pitch = pitch_axis.make_rotation()
        make_yaw = yaw_axis.make_rotation()

        self._make_rotation = lambda: (
            make_pitch(self._pitch) * make_yaw(self._yaw)
        )

        self._directions = 0
        self._movement = Vector3()

        self._move_timer = QtCore.QTimer(parent=self)
        self._move_timer.setSingleShot(False)
        self._move_timer.setInterval(16)
        self._move_timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._move_timer.timeout.connect(self._move_timer_timeout)

    def _move_timer_timeout(self):
        current_time = QtCore.QTime.currentTime()
        time_delta = self._last_time.msecsTo(current_time) / 1000.0
        self._last_time = current_time

        self._camera.position += self._camera.rotation.conjugate * self._movement * time_delta
        if self._widget:
            self._widget.update()

    def _update_movement(self):
        v = Vector3()
        if self._directions & self.Direction.LEFT != 0:
            v = v + Vector3(-1, 0, 0)
        if self._directions & self.Direction.RIGHT != 0:
            v = v + Vector3(1, 0, 0)
        if self._directions & self.Direction.UP != 0:
            v = v + Vector3(0, 1, 0)
        if self._directions & self.Direction.DOWN != 0:
            v = v + Vector3(0, -1, 0)
        if self._directions & self.Direction.FORWARD != 0:
            v = v + Vector3(0, 0, -1)
        if self._directions & self.Direction.BACKWARD != 0:
            v = v + Vector3(0, 0, 1)

        self._movement = v * (self._move_speed * 3 if self._turbo else self._move_speed)

        if self._directions != 0:
            if not self._move_timer.isActive():
                self._last_time = QtCore.QTime.currentTime()
                self._move_timer.start()
        else:
            if self._move_timer.isActive():
                self._move_timer.stop()

    def look_at(
        self,
        target: Vector3,
        up: Vector3 = Vector3(0, 1, 0),
    ) -> None:
        _, r, _ = (
            Matrix44.look_at(self._camera.position, target, up).decompose()
        )
        eulers = r.to_eulers()
        match self._pitch_axis:
            case Axis.X:
                self._pitch = eulers.x
            case Axis.Y:
                self._pitch = eulers.y
            case Axis.Z:
                self._pitch = eulers.z

        match self._yaw_axis:
            case Axis.X:
                self._yaw = eulers.x
            case Axis.Y:
                self._yaw = eulers.y
            case Axis.Z:
                self._yaw = eulers.z

    def eventFilter(self, widget: QWidget, event: QEvent) -> bool:
        if widget != self._widget:
            self._widget = widget

        if event.type() == QEvent.Type.KeyPress:
            match cast(QKeyEvent, event).key():
                case Qt.Key.Key_W:
                    self._directions |= self.Direction.FORWARD
                    self._update_movement()
                    return True
                case Qt.Key.Key_S:
                    self._directions |= self.Direction.BACKWARD
                    self._update_movement()
                    return True
                case Qt.Key.Key_A:
                    self._directions |= self.Direction.LEFT
                    self._update_movement()
                    return True
                case Qt.Key.Key_D:
                    self._directions |= self.Direction.RIGHT
                    self._update_movement()
                    return True
                case Qt.Key.Key_Q:
                    self._directions |= self.Direction.DOWN
                    self._update_movement()
                    return True
                case Qt.Key.Key_E:
                    self._directions |= self.Direction.UP
                    self._update_movement()
                    return True
                case Qt.Key.Key_Shift:
                    self._turbo = True
                    self._update_movement()
                    return True
        elif event.type() == QEvent.Type.KeyRelease:
            match cast(QtGui.QKeyEvent, event).key():
                case Qt.Key.Key_W:
                    self._directions &= ~self.Direction.FORWARD
                    self._update_movement()
                    return True
                case Qt.Key.Key_S:
                    self._directions &= ~self.Direction.BACKWARD
                    self._update_movement()
                    return True
                case Qt.Key.Key_A:
                    self._directions &= ~self.Direction.LEFT
                    self._update_movement()
                    return True
                case Qt.Key.Key_D:
                    self._directions &= ~self.Direction.RIGHT
                    self._update_movement()
                    return True
                case Qt.Key.Key_Q:
                    self._directions &= ~self.Direction.DOWN
                    self._update_movement()
                    return True
                case Qt.Key.Key_E:
                    self._directions &= ~self.Direction.UP
                    self._update_movement()
                    return True
                case Qt.Key.Key_Shift:
                    self._turbo = False
                    self._update_movement()
                    return True
        elif (event.type() == QEvent.Type.MouseButtonPress
                and cast(QMouseEvent, event).button() == Qt.MouseButton.LeftButton):
            self._last_position = cast(QMouseEvent, event).position()
            return True
        elif (event.type() == QEvent.Type.MouseButtonRelease
                and cast(QMouseEvent, event).button() == Qt.MouseButton.LeftButton
                and self._last_position is not None):
            self._last_position = None
            self._directions = 0
            self._update_movement()
            return True
        elif event.type() == QEvent.Type.MouseMove and self._last_position is not None:
            position = cast(QMouseEvent, event).position()
            dx = position.x() - self._last_position.x()
            dy = position.y() - self._last_position.y()
            self._pitch += dy * self._mouse_sensitivity[1]
            self._yaw += dx * self._mouse_sensitivity[0]
            self._camera.rotation = self._make_rotation()
            self._last_position = position
            if not self._move_timer.isActive():
                widget.update()
            return True

        return False
