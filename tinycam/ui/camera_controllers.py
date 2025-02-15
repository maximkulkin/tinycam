import enum
from PySide6 import QtCore, QtGui
from PySide6.QtCore import Qt
from tinycam.settings import SETTINGS, ControlType
from tinycam.types import Vector3, Quaternion, Matrix44
from tinycam.ui.camera import Camera
from tinycam.ui.utils import quaternion_to_eulers, unproject
from typing import Callable, Tuple, Union


class Axis(enum.Enum):
    X = enum.auto()
    Y = enum.auto()
    Z = enum.auto()

    def make_rotation(self) -> Callable[[float], Quaternion]:
        match self:
            case Axis.X: return Quaternion.from_x_rotation
            case Axis.Y: return Quaternion.from_y_rotation
            case Axis.Z: return Quaternion.from_z_rotation

        raise ValueError('Invalid axis')


class CameraOrbitAnimation(QtCore.QObject):
    finished = QtCore.Signal()

    def __init__(self, controller: 'OrbitController', pitch: float, yaw: float, duration: float):
        super().__init__()

        self._controller = controller

        self._start_pitch = self._controller.pitch
        self._start_yaw = self._controller.yaw
        self._target_pitch = pitch
        self._target_yaw = yaw

        self._duration_ms = int(duration * 1000)

        self._timer = QtCore.QTimer()
        self._timer.setInterval(20)
        self._timer.setTimerType(Qt.CoarseTimer)
        self._timer.timeout.connect(self._on_timeout)

    def start(self):
        self._start_time = QtCore.QTime.currentTime()
        self._timer.start()

    def stop(self):
        self._timer.stop()

    @property
    def is_active(self):
        return self._timer.isActive()

    def _on_timeout(self):
        delta_time_ms = self._start_time.msecsTo(QtCore.QTime.currentTime())
        if delta_time_ms > self._duration_ms:
            self._controller.rotate(self._target_pitch, self._target_yaw)
            self._timer.stop()
            self.finished.emit()
            return

        t = delta_time_ms / self._duration_ms
        # TODO: implement slerp instead of lerp
        pitch = self._start_pitch + t * (self._target_pitch - self._start_pitch)
        yaw = self._start_yaw + t * (self._target_yaw - self._start_yaw)
        self._controller.rotate(pitch, yaw)

        self._timer.start()


class OrbitController(QtCore.QObject):
    def __init__(
        self,
        camera: Camera,
        mouse_sensitivity: Union[float, Tuple[float, float]] = 0.01,
    ):
        super().__init__()
        self._widget = None

        SETTINGS['general/control_type'].changed.connect(self._on_control_type_changed)
        self._on_control_type_changed(SETTINGS.get('general/control_type'))

        self._camera = camera
        _, self._pitch, self._yaw = quaternion_to_eulers(self._camera.rotation)

        sens = mouse_sensitivity
        self._mouse_sensitivity = (sens, sens) if isinstance(sens, float) else sens

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

        self._pitch = pitch
        self._yaw = yaw

        v = self._camera.rotation.conjugate * Camera.FORWARD
        orbit_point = self._camera.position + v * (self._camera.position.z / (v | Vector3(0, 0, -1)))

        distance = (self._camera.position - orbit_point).length

        self._camera.rotation = Quaternion.from_x_rotation(self._pitch) * Quaternion.from_z_rotation(self._yaw)
        self._camera.position = orbit_point - self._camera.rotation.conjugate * Camera.FORWARD * distance
        self._widget.update()

    def _on_animation_finished(self):
        self._animation = None

    def _on_control_type_changed(self, value: ControlType):
        match value:
            case ControlType.MOUSE:
                self._orbit_button = Qt.MiddleButton
            case ControlType.TOUCHPAD:
                self._orbit_button = Qt.LeftButton

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if widget != self._widget:
            self._widget = widget

        if (event.type() == QtCore.QEvent.MouseButtonPress
                and event.button() == self._orbit_button
                and event.modifiers() & Qt.AltModifier):
            self._last_position = event.position()
            widget.grabKeyboard()
            widget.grabMouse()
            widget.setCursor(QtGui.QCursor(Qt.SizeAllCursor))
            return True
        elif (event.type() == QtCore.QEvent.MouseButtonRelease
                and event.button() == self._orbit_button
                and self._last_position is not None):
            self._last_position = None
            widget.releaseKeyboard()
            widget.releaseMouse()
            widget.setCursor(QtGui.QCursor(Qt.ArrowCursor))
            return True
        elif event.type() == QtCore.QEvent.MouseMove and self._last_position is not None:
            delta = event.position() - self._last_position

            self._last_position = event.position()

            self.rotate(
                yaw=self._yaw + delta.x() * self._mouse_sensitivity[1],
                pitch=self._pitch + delta.y() * self._mouse_sensitivity[0],
            )

        return False


class PanAndZoomController(QtCore.QObject):
    def __init__(
        self,
        camera: Camera,
    ):
        super().__init__()
        self._widget = None

        self._camera = camera
        self._last_position = None

        SETTINGS['general/control_type'].changed.connect(self._on_control_type_changed)
        self._on_control_type_changed(SETTINGS.get('general/control_type'))

    def _on_control_type_changed(self, value: ControlType):
        match value:
            case ControlType.MOUSE:
                self._pan_button = Qt.MiddleButton
            case ControlType.TOUCHPAD:
                self._pan_button = Qt.LeftButton

    def _unproject(self, p: QtCore.QPointF) -> Vector3:
        return unproject((p.x(), p.y()), self._camera)

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if widget != self._widget:
            self._widget = widget

        if (event.type() == QtCore.QEvent.MouseButtonPress
                and event.button() == self._pan_button):
            self._last_position = event.position()
            widget.grabKeyboard()
            widget.grabMouse()
            widget.setCursor(QtGui.QCursor(Qt.ClosedHandCursor))
            return True
        elif (event.type() == QtCore.QEvent.MouseButtonRelease
                and event.button() == self._pan_button
                and self._last_position is not None):
            self._last_position = None
            widget.releaseKeyboard()
            widget.releaseMouse()
            widget.setCursor(QtGui.QCursor(Qt.ArrowCursor))
            return True
        elif event.type() == QtCore.QEvent.MouseMove and self._last_position is not None:
            position = self._widget.mapFromGlobal(QtGui.QCursor.pos())
            p0 = self._unproject(self._last_position)
            p1 = self._unproject(position)
            d = p0 - p1

            self._camera.position += Vector3(d.x, d.y, 0)
            self._last_position = position
            widget.update()
            return True
        elif event.type() == QtCore.QEvent.Wheel:
            screen_point = self._widget.mapFromGlobal(QtGui.QCursor.pos())
            p0 = self._unproject(screen_point)

            scale = 0.9 ** (event.angleDelta().y() / 120.0)
            self._camera.position *= Vector3(1, 1, scale)

            p1 = self._unproject(screen_point)
            d = p0 - p1

            self._camera.position += Vector3(d.x, d.y, 0)
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
        mouse_sensitivity: Union[float, Tuple[float, float]] = 0.01,
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
        self._mouse_sensitivity = (sens, sens) if isinstance(sens, float) else sens

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
        self._move_timer.setTimerType(Qt.PreciseTimer)
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
            Matrix44.look_at(self.position, target, up).decompose()
        )
        eulers = quaternion_to_eulers(r)
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

    def eventFilter(self, widget: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if widget != self._widget:
            self._widget = widget

        if event.type() == QtCore.QEvent.KeyPress:
            match event.key():
                case Qt.Key_W:
                    self._directions |= self.Direction.FORWARD
                    self._update_movement()
                    return True
                case Qt.Key_S:
                    self._directions |= self.Direction.BACKWARD
                    self._update_movement()
                    return True
                case Qt.Key_A:
                    self._directions |= self.Direction.LEFT
                    self._update_movement()
                    return True
                case Qt.Key_D:
                    self._directions |= self.Direction.RIGHT
                    self._update_movement()
                    return True
                case Qt.Key_Q:
                    self._directions |= self.Direction.DOWN
                    self._update_movement()
                    return True
                case Qt.Key_E:
                    self._directions |= self.Direction.UP
                    self._update_movement()
                    return True
                case Qt.Key_Shift:
                    self._turbo = True
                    self._update_movement()
                    return True
        elif event.type() == QtCore.QEvent.KeyRelease:
            match event.key():
                case Qt.Key_W:
                    self._directions &= ~self.Direction.FORWARD
                    self._update_movement()
                    return True
                case Qt.Key_S:
                    self._directions &= ~self.Direction.BACKWARD
                    self._update_movement()
                    return True
                case Qt.Key_A:
                    self._directions &= ~self.Direction.LEFT
                    self._update_movement()
                    return True
                case Qt.Key_D:
                    self._directions &= ~self.Direction.RIGHT
                    self._update_movement()
                    return True
                case Qt.Key_Q:
                    self._directions &= ~self.Direction.DOWN
                    self._update_movement()
                    return True
                case Qt.Key_E:
                    self._directions &= ~self.Direction.UP
                    self._update_movement()
                    return True
                case Qt.Key_Shift:
                    self._turbo = False
                    self._update_movement()
                    return True
        elif (event.type() == QtCore.QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton):
            self._last_position = event.position()
            widget.grabKeyboard()
            widget.grabMouse()
            return True
        elif (event.type() == QtCore.QEvent.MouseButtonRelease
                and event.button() == Qt.LeftButton
                and self._last_position is not None):
            self._last_position = None
            widget.releaseKeyboard()
            widget.releaseMouse()
            self._directions = 0
            self._update_movement()
            return True
        elif event.type() == QtCore.QEvent.MouseMove and self._last_position is not None:
            dx = event.x() - self._last_position.x()
            dy = event.y() - self._last_position.y()
            self._pitch += dy * self._mouse_sensitivity[1]
            self._yaw += dx * self._mouse_sensitivity[0]
            self._camera.rotation = self._make_rotation()
            self._last_position = event.pos()
            if not self._move_timer.isActive():
                widget.update()
            return True

        return False
