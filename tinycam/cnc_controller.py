import tinycam.grbl
import serial_asyncio


class CncController:
    def __init__(self):
        self._grbl = None
        self._r = None
        self._w = None

    @property
    def status(self):
        if self._grbl is None:
            return 'Disconnected'

        return self._grbl.status

    async def connect(self, port, baud=115200):
        self._r, self._w = await serial_asyncio.open_serial_connection(
            url=self._port,
            baudrate=self._baud,
        )
        self._grbl = tinycam.grbl.Controller(self._r, self._w)

    def disconnect(self):
        if self._grbl is None:
            return

        self._grbl.shutdown()
        self._grbl = None
