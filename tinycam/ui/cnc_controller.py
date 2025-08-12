from typing import cast

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from qasync import asyncSlot
import serial.tools.list_ports

from tinycam.globals import GLOBALS
from tinycam import grbl
from tinycam.project import CncProject
from tinycam.properties import format_suffix
import tinycam.settings as s
from tinycam.types import Vector3
from tinycam.ui.window import CncWindow


BAUD_RATES = [
    9600,
    14400,
    19200,
    38400,
    57600,
    115200,
    128000,
    256000,
]

DEFAULT_BAUD_RATE = 115200


FIXED_SIZE_POLICY = QtWidgets.QSizePolicy(
    QtWidgets.QSizePolicy.Policy.Fixed,
    QtWidgets.QSizePolicy.Policy.Fixed,
)


class SerialPortSelector(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._populate_serial_ports()

    def showPopup(self):
        self._populate_serial_ports()
        super().showPopup()

    def _populate_serial_ports(self):
        currentText = self.currentText()

        self.clear()
        self.addItem('<Select serial port>')
        for port in serial.tools.list_ports.comports():
            self.addItem(port.device, userData=port)

        self.setCurrentIndex(max(0, self.findText(currentText)))


class CncConnectionToolbar(QtWidgets.QToolBar):

    def __init__(self):
        super().__init__()

        self.setObjectName('cnc_connection_toolbar')
        self.setWindowTitle('Connection Toolbar')

        self._connect_button = QtWidgets.QPushButton('Connect')
        self._connect_button.setEnabled(False)
        self._connect_button.clicked.connect(self._on_connect_clicked)

        self._unlock_button = QtWidgets.QPushButton('Unlock')
        self._unlock_button.setEnabled(False)
        self._unlock_button.clicked.connect(self._on_unlock_clicked)

        self._port_selector = SerialPortSelector()
        self._port_selector.currentIndexChanged.connect(self._on_port_changed)

        self._baud_selector = QtWidgets.QComboBox()
        self._baud_selector.setSizePolicy(FIXED_SIZE_POLICY)
        for baud in BAUD_RATES:
            self._baud_selector.addItem(str(baud), userData=baud)
        self._baud_selector.setCurrentIndex(
            self._baud_selector.findData(DEFAULT_BAUD_RATE)
        )

        self.addWidget(self._port_selector)
        self.addWidget(self._baud_selector)
        self.addWidget(self._connect_button)
        self.addWidget(self._unlock_button)

        self.controller.connected_changed.connect(self._on_connected_changed)

        self._connect_timeout_timer = QtCore.QTimer()
        self._connect_timeout_timer.setSingleShot(True)
        self._connect_timeout_timer.setInterval(10000)
        self._connect_timeout_timer.timeout.connect(self._on_connect_timeout)

    def _on_port_changed(self, _index: int):
        self._connect_button.setEnabled(self._port_selector.currentIndex() > 0)

    @asyncSlot()
    async def _on_connect_clicked(self):
        if self.controller.connected:
            self._connect_button.setText('Disconnecting...')
            self._connect_button.setEnabled(False)
            await self.controller.disconnect()
        else:
            port = self._port_selector.currentData()
            baud = self._baud_selector.currentData()

            if port is None or baud is None:
                return

            await self.controller.connect(port.device, baud)

            self._connect_button.setText('Connecting...')
            self._connect_button.setEnabled(False)
            self._port_selector.setEnabled(False)
            self._baud_selector.setEnabled(False)
            self._connect_timeout_timer.start()

    def _on_connect_timeout(self):
        self._connect_button.setText('Connect')
        self._connect_button.setEnabled(self._port_selector.currentIndex() > 0)
        self._port_selector.setEnabled(True)
        self._baud_selector.setEnabled(True)

    @property
    def controller(self) -> grbl.Controller:
        return GLOBALS.CNC_CONTROLLER

    @asyncSlot()
    async def _on_unlock_clicked(self):
        await self.controller.unlock()

    def _on_connected_changed(self, value: bool):
        if value:
            if self.controller.ready:
                self._on_ready_changed(True)
            else:
                self.controller.ready_changed.connect(self._on_ready_changed)
                self.controller.status_changed.connect(self._on_status_changed)
        else:
            self._connect_button.setText('Connect')
            self._connect_button.setEnabled(True)
            self._port_selector.setEnabled(True)
            self._baud_selector.setEnabled(True)

    def _on_ready_changed(self, value: bool):
        if value:
            self._connect_timeout_timer.stop()
            self._connect_button.setText('Disconnect')
            self._connect_button.setEnabled(True)
            self._port_selector.setEnabled(False)
            self._baud_selector.setEnabled(False)
            self._unlock_button.setEnabled(self.controller.status == grbl.Status.ALARM)
        else:
            self._connect_button.setText('Connecting...')
            self._connect_button.setEnabled(False)
            self._port_selector.setEnabled(False)
            self._baud_selector.setEnabled(False)
            self._unlock_button.setEnabled(False)

    def _on_status_changed(self, status: 'grbl.Status'):
        self._unlock_button.setEnabled(status == grbl.Status.ALARM)


class CncControllerConsoleWindow(CncWindow):
    MAX_COMMAND_HISTORY = 100

    class ArrowKeyFilter(QtCore.QObject):
        up_pressed = QtCore.Signal()
        down_pressed = QtCore.Signal()

        def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent):
            if event.type() == QtCore.QEvent.KeyPress:
                key_event = cast(QtGui.QKeyEvent, event)
                match key_event.key():
                    case Qt.Key_Up:
                        self.up_pressed.emit()
                        return True
                    case Qt.Key_Down:
                        self.down_pressed.emit()
                        return True

            return super().eventFilter(obj, event)

    def __init__(self, project, *args, **kwargs):
        super().__init__(project, *args, **kwargs)

        self.setObjectName("cnc_controller_console")
        self.setWindowTitle("CNC console")

        self.controller.connected_changed.connect(self._on_connected_changed)
        self.controller.line_sent.connect(self._on_line_sent)
        self.controller.line_received.connect(self._on_line_received)

        self._log_view = QtWidgets.QTextEdit()
        self._log_view.setReadOnly(True)

        self._command_history = []
        self._command_history_idx = 0

        self._command_edit = QtWidgets.QLineEdit()
        self._command_edit.textChanged.connect(self._on_command_changed)
        self._command_edit.textChanged.connect(self._on_command_changed)
        self._command_edit.returnPressed.connect(self._on_command_return_pressed)

        self._key_filter = self.ArrowKeyFilter()
        self._key_filter.up_pressed.connect(self._on_command_history_prev)
        self._key_filter.down_pressed.connect(self._on_command_history_next)
        self._command_edit.installEventFilter(self._key_filter)

        self._command_send_button = QtWidgets.QPushButton('Send')
        self._command_send_button.setEnabled(False)
        self._command_send_button.clicked.connect(self._on_command_send_button_clicked)

        command_entry_layout = QtWidgets.QHBoxLayout()
        command_entry_layout.addWidget(QtWidgets.QLabel('Command:'))
        command_entry_layout.addWidget(self._command_edit)
        command_entry_layout.addWidget(self._command_send_button)
        command_entry_layout.setContentsMargins(0, 0, 0, 0)

        self._command_entry_group = QtWidgets.QWidget()
        self._command_entry_group.setLayout(command_entry_layout)
        self._command_entry_group.setEnabled(False)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 0)
        layout.addWidget(self._log_view)
        layout.addWidget(self._command_entry_group)

        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(layout)
        self.setWidget(main_widget)

    @property
    def controller(self) -> grbl.Controller:
        return GLOBALS.CNC_CONTROLLER

    def _on_connected_changed(self, value: bool):
        self._command_entry_group.setEnabled(self.controller.connected)
        self._on_command_changed(self._command_edit.text())

    def _on_command_changed(self, text: str):
        self._command_send_button.setEnabled(text != '')

    def _on_line_sent(self, line: str):
        self._log_view.append(f'< {line}')

    def _on_line_received(self, line: str):
        self._log_view.append(f'> {line}')

    async def _send_command(self, command: str):
        if len(self._command_history) == 0 or self._command_history[-1] != command:
            self._command_history.append(command)
            if len(self._command_history) > self.MAX_COMMAND_HISTORY:
                self._command_history = self._command_history[-self.MAX_COMMAND_HISTORY:]
        self._command_history_idx = 0
        if command in ['?', '!', '~']:
            await self.controller.send(command.encode('utf-8'))
        else:
            await self.controller.send_command(command)

    @asyncSlot()
    async def _on_command_return_pressed(self):
        await self._send_command(self._command_edit.text())
        self._command_edit.clear()

    @asyncSlot()
    async def _on_command_send_button_clicked(self):
        await self._send_command(self._command_edit.text())
        self._command_edit.clear()

    def _on_command_history_prev(self):
        if self._command_history_idx >= len(self._command_history):
            return

        self._command_history_idx += 1
        self._command_edit.setText(self._command_history[-self._command_history_idx])

    def _on_command_history_next(self):
        if self._command_history_idx <= 0:
            return

        self._command_history_idx -= 1
        if self._command_history_idx == 0:
            self._command_edit.clear()
        else:
            self._command_edit.setText(self._command_history[-self._command_history_idx])


class CncCoordinateDisplay(QtWidgets.QWidget):
    def __init__(self, label: str):
        super().__init__()

        font = QtGui.QFont()
        font.setPointSize(24)

        self._label = QtWidgets.QLabel(label)
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._label.setFont(font)

        self._value_display = QtWidgets.QLabel('0')
        self._value_display.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._value_display.setStyleSheet("background-color: black; padding: 5; margin: 5;")
        self._value_display.setFont(font)

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._label)
        layout.addWidget(self._value_display)
        layout.setStretch(1, 1)

        self.setLayout(layout)

    def setValue(self, value: float):
        return self._value_display.setText(str(value))


class CncControllerStateDisplayWindow(CncWindow):
    def __init__(self, project: CncProject, controller: grbl.Controller, *args, **kwargs):
        super().__init__(project=project, *args, **kwargs)

        self.setObjectName("cnc_state")
        self.setWindowTitle("CNC State")

        controller.workspace_coordinates_changed.connect(
            self._on_workspace_coordinates_changed,
        )

        self._x_readout = CncCoordinateDisplay('X')
        self._y_readout = CncCoordinateDisplay('Y')
        self._z_readout = CncCoordinateDisplay('Z')

        font = QtGui.QFont()
        font.setPointSize(16)

        self._feedrate_label = QtWidgets.QLabel("Feedrate:  ")
        self._feedrate_label.setFont(font)
        self._feedrate_display = QtWidgets.QLabel("0")
        self._feedrate_display.setFont(font)
        self._spindle_label = QtWidgets.QLabel("Spindle:  ")
        self._spindle_label.setFont(font)
        self._spindle_display = QtWidgets.QLabel("0")
        self._spindle_display.setFont(font)

        additional_layout = QtWidgets.QGridLayout()
        additional_layout.setSpacing(5)
        additional_layout.addWidget(self._feedrate_label, 0, 0, Qt.AlignmentFlag.AlignRight)
        additional_layout.addWidget(self._feedrate_display, 0, 1, Qt.AlignmentFlag.AlignLeft)
        additional_layout.addWidget(self._spindle_label, 1, 0, Qt.AlignmentFlag.AlignRight)
        additional_layout.addWidget(self._spindle_display, 1, 1, Qt.AlignmentFlag.AlignLeft)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self._x_readout)
        layout.addWidget(self._y_readout)
        layout.addWidget(self._z_readout)
        layout.addLayout(additional_layout)
        layout.addStretch()

        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(layout)
        self.setWidget(main_widget)

    def _on_workspace_coordinates_changed(self, coords: Vector3):
        self._x_readout.setValue(coords.x)
        self._y_readout.setValue(coords.y)
        self._z_readout.setValue(coords.z)


class CncControllerJogControlsWindow(CncWindow):
    def __init__(self, project: CncProject, controller: grbl.Controller, *args, **kwargs):
        super().__init__(project=project, *args, **kwargs)

        self.setObjectName("cnc_jog_controls")
        self.setWindowTitle("CNC Jog Controls")

        self._controller = controller

        self._x_neg_button = QtWidgets.QPushButton("-X")
        self._x_neg_button.clicked.connect(self._on_x_neg_clicked)
        self._x_pos_button = QtWidgets.QPushButton("+X")
        self._x_pos_button.clicked.connect(self._on_x_pos_clicked)
        self._y_neg_button = QtWidgets.QPushButton("-Y")
        self._y_neg_button.clicked.connect(self._on_y_neg_clicked)
        self._y_pos_button = QtWidgets.QPushButton("+Y")
        self._y_pos_button.clicked.connect(self._on_y_pos_clicked)
        self._z_neg_button = QtWidgets.QPushButton("-Z")
        self._z_neg_button.clicked.connect(self._on_z_neg_clicked)
        self._z_pos_button = QtWidgets.QPushButton("+Z")
        self._z_pos_button.clicked.connect(self._on_z_pos_clicked)

        self._xy_step_edit = QtWidgets.QDoubleSpinBox()
        self._xy_step_edit.setMinimum(0.001)
        self._xy_step_edit.setMaximum(1000.0)
        self._xy_step_edit.setValue(1.0)

        self._z_step_edit = QtWidgets.QDoubleSpinBox()
        self._z_step_edit.setMinimum(0.001)
        self._z_step_edit.setMaximum(1000.0)
        self._z_step_edit.setValue(1.0)

        self._feedrate_edit = QtWidgets.QDoubleSpinBox()
        self._feedrate_edit.setMinimum(0.001)
        self._feedrate_edit.setMaximum(1000.0)
        self._feedrate_edit.setValue(100.0)

        movement_layout = QtWidgets.QGridLayout()
        movement_layout.addWidget(self._y_pos_button, 0, 1)
        movement_layout.addWidget(self._x_neg_button, 1, 0)
        movement_layout.addWidget(self._x_pos_button, 1, 2)
        movement_layout.addWidget(self._y_neg_button, 2, 1)

        movement_layout.addWidget(self._z_pos_button, 0, 2)
        movement_layout.addWidget(self._z_neg_button, 2, 2)

        settings_layout = QtWidgets.QGridLayout()
        settings_layout.addWidget(QtWidgets.QLabel('XY step:'), 0, 0, Qt.AlignmentFlag.AlignRight)
        settings_layout.addWidget(self._xy_step_edit, 0, 1)

        settings_layout.addWidget(QtWidgets.QLabel('Z step:'), 1, 0, Qt.AlignmentFlag.AlignRight)
        settings_layout.addWidget(self._z_step_edit, 1, 1)

        settings_layout.addWidget(QtWidgets.QLabel('Feedrate:'), 2, 0, Qt.AlignmentFlag.AlignRight)
        settings_layout.addWidget(self._feedrate_edit, 2, 1)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(movement_layout)
        layout.addLayout(settings_layout)
        layout.addStretch()

        self._main_widget = QtWidgets.QWidget(self)
        self._main_widget.setLayout(layout)
        self.setWidget(self._main_widget)

        s.SETTINGS['general/units'].changed.connect(self._on_units_changed)
        self._on_units_changed(s.SETTINGS.get('general/units'))

        self._controller.ready_changed.connect(self._on_ready_changed)
        self._on_ready_changed(self._controller.ready)

    @asyncSlot()
    async def _on_x_neg_clicked(self):
        await self._controller.jog(
            feedrate=self._feedrate_edit.value(),
            units=s.SETTINGS.get('general/units'),
            x=-self._xy_step_edit.value(),
        )

    @asyncSlot()
    async def _on_x_pos_clicked(self):
        await self._controller.jog(
            feedrate=self._feedrate_edit.value(),
            units=s.SETTINGS.get('general/units'),
            x=self._xy_step_edit.value(),
        )

    @asyncSlot()
    async def _on_y_neg_clicked(self):
        await self._controller.jog(
            feedrate=self._feedrate_edit.value(),
            units=s.SETTINGS.get('general/units'),
            y=-self._xy_step_edit.value(),
        )

    @asyncSlot()
    async def _on_y_pos_clicked(self):
        await self._controller.jog(
            feedrate=self._feedrate_edit.value(),
            units=s.SETTINGS.get('general/units'),
            y=self._xy_step_edit.value(),
        )

    @asyncSlot()
    async def _on_z_neg_clicked(self):
        await self._controller.jog(
            feedrate=self._feedrate_edit.value(),
            units=s.SETTINGS.get('general/units'),
            z=-self._z_step_edit.value(),
        )

    @asyncSlot()
    async def _on_z_pos_clicked(self):
        await self._controller.jog(
            feedrate=self._feedrate_edit.value(),
            units=s.SETTINGS.get('general/units'),
            z=self._z_step_edit.value(),
        )

    def _on_ready_changed(self, ready: bool):
        self._main_widget.setEnabled(ready)

    def _on_units_changed(self, _: s.Units):
        self._xy_step_edit.setSuffix(format_suffix('{units}'))
        self._z_step_edit.setSuffix(format_suffix('{units}'))
        self._feedrate_edit.setSuffix(format_suffix('{units}/min'))


class OverrideSlider(QtWidgets.QWidget):
    valueChanged = QtCore.Signal(int)

    def __init__(self):
        super().__init__()

        self._slider = QtWidgets.QSlider(Qt.Horizontal)
        self._slider.setMinimum(1)
        self._slider.setMaximum(200)
        self._slider.setValue(100)
        self._slider.setTickInterval(10)
        self._slider.setTickPosition(QtWidgets.QSlider.TickPosition.TicksBelow)
        self._slider.valueChanged.connect(self._on_slider_value_changed)

        self._value_edit = QtWidgets.QSpinBox()
        self._value_edit.setMinimum(1)
        self._value_edit.setMaximum(1000)
        self._value_edit.setValue(100)
        self._value_edit.setSuffix(' %')
        self._value_edit.editingFinished.connect(self._on_value_edit_changed)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._slider)
        layout.addWidget(self._value_edit)
        self.setLayout(layout)

    @property
    def value(self) -> int:
        return self._value_edit.value()

    @value.setter
    def value(self, new_value: int):
        self._slider.setValue(new_value)
        self._value_edit.setValue(new_value)

    def _on_slider_value_changed(self, value: int):
        self._value_edit.setValue(value)
        self.valueChanged.emit(value)

    def _on_value_edit_changed(self):
        value = self._value_edit.value()
        self._slider.setValue(value)
        self.valueChanged.emit(value)


class CncControllerControlsWindow(CncWindow):

    def __init__(self, project: CncProject, controller: grbl.Controller, *args, **kwargs):
        super().__init__(project, *args, **kwargs)

        self.setObjectName('cnc_controller_controls')
        self.setWindowTitle('CNC controls')

        self._controller = controller

        self._home_xy_button = QtWidgets.QPushButton('Home XY')
        self._home_xy_button.clicked.connect(self._on_home_xy_clicked)

        self._home_z_button = QtWidgets.QPushButton('Home Z')
        self._home_z_button.clicked.connect(self._on_home_z_clicked)

        self._zero_xy_button = QtWidgets.QPushButton('Zero XY')
        self._zero_xy_button.clicked.connect(self._on_zero_xy_clicked)

        self._zero_z_button = QtWidgets.QPushButton('Zero Z')
        self._zero_z_button.clicked.connect(self._on_zero_z_clicked)

        self._reset_button = QtWidgets.QPushButton('Reset')
        self._reset_button.clicked.connect(self._on_reset_clicked)

        self._unlock_button = QtWidgets.QPushButton('Unlock')
        self._unlock_button.clicked.connect(self._on_unlock_clicked)

        self._feedrate_override = OverrideSlider()
        self._feedrate_override.value = 100
        self._feedrate_override.valueChanged.connect(self._on_feedrate_override_changed)

        self._travel_override = OverrideSlider()
        self._travel_override.value = 100
        self._travel_override.valueChanged.connect(self._on_travel_override_changed)

        self._spindle_override = OverrideSlider()
        self._spindle_override.value = 100
        self._spindle_override.valueChanged.connect(self._on_spindle_override_changed)

        controls_layout = QtWidgets.QGridLayout()
        # controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addWidget(self._home_xy_button, 0, 0)
        controls_layout.addWidget(self._home_z_button, 0, 1)
        controls_layout.addWidget(self._zero_xy_button, 0, 2)
        controls_layout.addWidget(self._zero_z_button, 0, 3)
        controls_layout.addWidget(self._reset_button, 1, 2)
        controls_layout.addWidget(self._unlock_button, 1, 3)

        controls_widget = QtWidgets.QGroupBox('Controls')
        controls_widget.setLayout(controls_layout)

        overrides_layout = QtWidgets.QGridLayout()
        overrides_layout.setContentsMargins(10, 0, 0, 0)
        overrides_layout.setSpacing(0)
        overrides_layout.addWidget(QtWidgets.QLabel('Feed Rate:'), 0, 0)
        overrides_layout.addWidget(self._feedrate_override, 0, 1)
        overrides_layout.addWidget(QtWidgets.QLabel('Travel Speed:'), 1, 0)
        overrides_layout.addWidget(self._travel_override, 1, 1)
        overrides_layout.addWidget(QtWidgets.QLabel('Spindle Speed:'), 2, 0)
        overrides_layout.addWidget(self._spindle_override, 2, 1)

        overrides_widget = QtWidgets.QGroupBox('Overrides')
        overrides_widget.setLayout(overrides_layout)

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(20)
        layout.addWidget(controls_widget)
        layout.addWidget(overrides_widget)
        layout.addStretch()

        self._main_widget = QtWidgets.QWidget(self)
        self._main_widget.setLayout(layout)
        self.setWidget(self._main_widget)

        self._controller.ready_changed.connect(self._on_ready_changed)
        self._on_ready_changed(self._controller.ready)

    def _on_ready_changed(self, ready: bool):
        # self._main_widget.setEnabled(ready)
        self._main_widget.setEnabled(True)

    def _on_home_xy_clicked(self):
        pass

    def _on_home_z_clicked(self):
        pass

    def _on_zero_xy_clicked(self):
        pass

    def _on_zero_z_clicked(self):
        pass

    def _on_reset_clicked(self):
        pass

    def _on_unlock_clicked(self):
        pass

    def _on_feedrate_override_changed(self, value: int):
        pass

    def _on_travel_override_changed(self, value: int):
        pass

    def _on_spindle_override_changed(self, value: int):
        pass
