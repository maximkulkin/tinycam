import asyncio
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt
import serial.tools.list_ports

from tinycam.globals import GLOBALS
from tinycam.ui.window import CncWindow
from tinycam.ui.widgets import PushButton


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


class CncControllerWindow(CncWindow):
    def __init__(self, project, *args, **kwargs):
        super().__init__(project, *args, **kwargs)

        self.setObjectName("cnc_controller")
        self.setWindowTitle("CNC controller")

        self.port_select = QtWidgets.QComboBox()
        self.port_select.setPlaceholderText('Device Port')

        self.baud_select = QtWidgets.QComboBox()
        for baud in BAUD_RATES:
            self.baud_select.addItem(str(baud))
        self.baud_select.setCurrentIndex(
            self.baud_select.findText(str(DEFAULT_BAUD_RATE))
        )

        self.connect_button = PushButton('Connect')
        self.connect_button.clicked.connect(self._connect)

        layout = QtWidgets.QHBoxLayout()
        layout.setAlignment(Qt.AlignJustify | Qt.AlignTop)
        layout.addWidget(self.port_select)
        layout.addWidget(self.baud_select)
        layout.addWidget(self.connect_button)

        main_widget = QtWidgets.QWidget(self)
        main_widget.setLayout(layout)
        self.setWidget(main_widget)

        self._populate_ports()

    def _populate_ports(self):
        self.port_select.clear()
        for port in serial.tools.list_ports.comports():
            self.port_select.addItem(port.device)
        self.port_select.setCurrentIndex(-1)

    def _connect(self):
        asyncio.ensure_future(
            GLOBALS.CNC_CONTROLLER.connect(self.port_select.currentText(), int(self.baud_select.currentText()))
        )
