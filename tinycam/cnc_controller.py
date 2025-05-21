from blinker import Signal

import serial_asyncio
from tinycam import grbl
from PySide6 import QtCore


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


class CncController:
    connected_changed = Signal('connected: bool')
    history_changed = Signal('line: str')

    def __init__(self):
        super().__init__()
        self._grbl = None
        self._history = []

    @property
    def connected(self) -> bool:
        return self._grbl is not None

    @property
    def grbl(self) -> grbl.Controller | None:
        return self._grbl

    @property
    def history(self) -> list[str]:
        return self._history

    async def connect(self, port: str, baud: int = 115200):
        try:
            r, w = await serial_asyncio.open_serial_connection(
                url=port,
                baudrate=baud,
                timeout=10,  # 10 second timeout
            )
            self._grbl = grbl.Controller(r, w)
            self._grbl.line_sent.connect(self._on_line_sent)
            self._grbl.line_received.connect(self._on_line_received)
        except Exception as e:
            print(f'Failed to connect: {e}')
            return

        self.connected_changed.send(True)

    async def disconnect(self):
        if self._grbl is None:
            return

        await self._grbl.shutdown()
        self._grbl = None
        self.connected_changed.send(False)

    def _on_line_sent(self, line: str):
        line = f'< {line}'
        self._history.append(line)
        self.history_changed.send(line)

    def _on_line_received(self, line: str):
        line = f'> {line}'
        self._history.append(line)
        self.history_changed.send(line)
