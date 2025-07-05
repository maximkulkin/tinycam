from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from qasync import asyncSlot
import serial.tools.list_ports

from tinycam.globals import GLOBALS
from tinycam import grbl
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
    def __init__(self, project, *args, **kwargs):
        super().__init__(project, *args, **kwargs)

        self.setObjectName("cnc_controller_console")
        self.setWindowTitle("CNC console")

        self.controller.connected_changed.connect(self._on_connected_changed)
        self.controller.line_sent.connect(self._on_line_sent)
        self.controller.line_received.connect(self._on_line_received)

        self._log_view = QtWidgets.QTextEdit()
        self._log_view.setReadOnly(True)

        self._command_edit = QtWidgets.QLineEdit()
        self._command_edit.textChanged.connect(self._on_command_changed)
        self._command_edit.textChanged.connect(self._on_command_changed)

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
    async def _on_command_send_button_clicked(self):
        await self._send_command(self._command_edit.text())
        self._command_edit.clear()


class CncCoordinateDisplay(QtWidgets.QWidget):
    def __init__(self, label: str):
        super().__init__()

        font = QtGui.QFont()
        font.setPointSize(48)

        self._label = QtWidgets.QLabel(label)
        self._label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._label.setFont(font)

        self._value = QtWidgets.QLabel('0')
        self._value.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._value.setFont(font)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self._label)
        layout.addWidget(self._value)

        self.setLayout(layout)


class CncControllerWindow(CncWindow):
    def __init__(self, project, *args, **kwargs):
        super().__init__(project, *args, **kwargs)

        self.setObjectName("cnc_controller")
        self.setWindowTitle("CNC controller")

        self._x_readout = CncCoordinateDisplay('X')
        self._y_readout = CncCoordinateDisplay('Y')
        self._z_readout = CncCoordinateDisplay('Z')

        layout = QtWidgets.QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(self._x_readout)
        layout.addWidget(self._y_readout)
        layout.addWidget(self._z_readout)
        layout.addStretch()

        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(layout)
        self.setWidget(main_widget)
