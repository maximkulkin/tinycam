import asyncio
import enum
from typing import Tuple

__all__ = [
    'Error',
    'ErrorType',
    'Positioning',
    'Plane',
    'Units',
    'Controller',
]


Coordinates = Tuple[float, float, float]


class Alarm(enum.Enum):
    HARD_LIMIT = 1
    SOFT_LIMIT = 2
    ABORT_DURING_CYCLE = 3
    PROBE_STATE = 4
    PROBE_MISS = 5
    HOMING_RESET = 6
    HOMING_DOOR = 7
    HOMING_PULLOFF = 8
    HOMING_MISS = 9


class ErrorType(enum.Enum):
    EXPECTED_COMMAND_LETTER = 1
    BAD_NUMBER_FORMAT = 2
    INVALID_SYSTEM_COMMAND = 3
    UNEXPECTED_NEGATIVE_VALUE = 4
    HOMING_NOT_ENABLED = 5
    STEP_PULSE_TOO_LOW = 6
    EEPROM_READ_FAILURE = 7
    SYSTEM_COMMAND_WHEN_NOT_IDLE = 8
    LOCKED = 9
    SOFT_LIMITS_WITHOUT_HOMING = 10
    LINE_OVERFLOW = 11
    STEP_RATE_TOO_HIGH = 12
    CHECK_DOOR = 13
    LINE_LENGTH_EXCEEDED = 14
    JOG_TRAVEL_EXCEEDED = 15
    INVALID_JOG_COMMAND = 16
    LASER_MODE_REQUIRES_PWM = 17
    UNSUPPORTED_COMMAND = 20
    MODAL_GROUP_VIOLATION = 21
    UNDEFINED_FEED_RATE = 22
    GCODE_COMMAND_REQUIRES_INTEGER = 23
    MULTIPLE_GCODE_COMMANDS_REQUIRE_AXES = 24
    REPEATED_GCODE_COMMANDS = 25
    NO_AXES_FOUND = 26
    INVALID_LINE_NUMBER = 27
    GCODE_COMMAND_REQUIRES_VALUE = 28
    UNSUPPORTED_COORDINATE_SYSTEM = 29
    G53_GCODE_COMMAND_REQUIRES_G0_OR_G1 = 30
    AXES_NOT_NEEDED = 31
    ARC_GCDODE_COMMAND_REQUIRES_INPLANE_AXIS = 32
    MOTION_COMMAND_TARGET_INVALID = 33
    INVALID_ARC_RADIUS = 34
    ARC_GCDODE_COMMAND_REQUIRES_INPLANE_OFFSET = 35
    UNUSED_VALUE_WORDS = 36
    DYNAMIC_TOOL_LENGTH_OFFSET_NO_AXIS = 37
    INVALID_TOOL_NUMBER = 38


class Error(Exception):
    def __init__(self, type: ErrorType):
        super().__init__()
        self.type = type


class Status(enum.Enum):
    IDLE = enum.auto()
    ALARM = enum.auto()
    RUN = enum.auto()
    HOMING = enum.auto()
    CYCLE = enum.auto()
    HOLD = enum.auto()
    JOG = enum.auto()
    SAFETY_DOOR = enum.auto()
    SLEEP = enum.auto()


def _setting(code):
    def fget(settings):
        return settings.get(code)

    def fset(settings, value):
        settings.set(code, value)

    return property(fget, fset)


class Settings:
    def __init__(self, controller):
        self._controller = controller
        self._cache = None

    def get(self, code):
        return self._controller.get_setting(code)

    def set(self, code, value):
        self._controller.set_setting(code, value)

    step_pulse_microseconds = _setting('0')
    stepper_idle_lock_time = _setting('1')
    step_invert_mask = _setting('2')
    direction_invert_mask = _setting('3')
    step_enable_invert = _setting('4')
    limit_pins_invert = _setting('5')
    probe_invert_mask = _setting('6')
    status_report_mask = _setting('10')
    junction_deviation = _setting('11')
    arc_tolerance = _setting('12')
    report_inches = _setting('13')
    soft_limits_enabled = _setting('20')
    hard_limits_enabled = _setting('21')
    homing_enabled = _setting('22')
    homing_dir_mask = _setting('23')
    homing_feed_rate = _setting('24')
    homing_seek_rate = _setting('25')
    homing_debounce_delay = _setting('26')
    homing_pulloff = _setting('27')
    max_spindle_speed = _setting('30')
    min_spindle_speed = _setting('31')
    laser_mode = _setting('32')
    steps_per_mm_x = _setting('100')
    steps_per_mm_y = _setting('101')
    steps_per_mm_z = _setting('102')
    max_rate_x = _setting('110')
    max_rate_y = _setting('111')
    max_rate_z = _setting('112')
    acceleration_x = _setting('120')
    acceleration_y = _setting('121')
    acceleration_z = _setting('122')
    max_travel_x = _setting('130')
    max_travel_y = _setting('131')
    max_travel_z = _setting('132')


class Positioning(enum.Enum):
    ABSOLUTE = 0
    RELATIVE = 1


class Plane(enum.Enum):
    XY = 0
    XZ = 1
    YZ = 2


class Units(enum.Enum):
    IN = 0
    MM = 1


class Controller:
    def __init__(self, reader, writer, on_line_send=None, on_line_receive=None):
        self._reader = reader
        self._writer = writer

        self._on_line_send = on_line_send
        self._on_line_receive = on_line_receive

        self.status_poll_interval = 1.0
        self.max_commands = 10

        self._ready = False
        self._locked = False

        self._commands = asyncio.Queue()
        self._command_results = asyncio.Queue(self.max_commands)
        self._command_response = []

        self._status = Status.ALARM
        self._modal_command = 'G0'
        self._positioning = Positioning.ABSOLUTE
        self._units = Units.IN
        self._plane = Plane.XY
        self._feedrate = 0
        self._spindle_speed = 0
        self._settings = {}

        self._ref_position1 = (0., 0., 0.)
        self._ref_position2 = (0., 0., 0.)
        self._workspace_offsets = [(0., 0., 0.) for _ in range(6)]
        self._current_workspace = 0
        self._machine_coordinates = (0., 0., 0.)
        self._workspace_coordinates = (0., 0., 0.)

        self._reader_task = asyncio.create_task(self._reader_run())
        self._command_sender_task = asyncio.create_task(self._command_sender_run())
        self._state_poller_task = asyncio.create_task(self._state_poller_run())

    async def shutdown(self) -> None:
        self._reader_task.cancel()
        self._command_sender_task.cancel()
        self._state_poller_task.cancel()

        try:
            await self._reader_task
        except asyncio.CancelledError:
            pass

        try:
            await self._command_sender_task
        except asyncio.CancelledError:
            pass

        try:
            await self._state_poller_task
        except asyncio.CancelledError:
            pass

        self._writer.close()
        await self._writer.wait_closed()

    async def _reader_run(self) -> None:
        while True:
            line = (await self._reader.readline()).decode('utf-8').replace('\r\n', '')
            await self._process_line(line)

    async def _state_poller_run(self) -> None:
        while True:
            if self.ready:
                await self.status_report()
            await asyncio.sleep(self.status_poll_interval)

    async def _command_sender_run(self) -> None:
        while True:
            command, future = await self._commands.get()

            if isinstance(command, str):
                command = command.encode('utf-8')

            await self._command_results.put(future)
            self.send_nowait(command + b'\n')

    def _parse_coordinates(self, s: str) -> Coordinates:
        return tuple(float(v) for v in s.split(','))

    async def _process_line(self, line):
        l = line.strip()
        print(f'Processing line "{l}"')
        if l.startswith('Grbl '):
            self._ready = True
            self.send_command('$$')
            self.send_command('$G')
            self.send_command('$#')
        elif l.startswith('[') and l.endswith(']'):
            l = l[1:-1]
            topic, l = l.split(':', 1)
            match topic:
                case 'MSG':
                    pass
                case 'GC':
                    l = l[3:]
                    for part in l.split():
                        match part:
                            case 'G0' | 'G1' | 'G2' | 'G3':
                                self._modal_command = part
                            case 'G17':
                                self._plane = Plane.XY
                            case 'G18':
                                self._plane = Plane.XZ
                            case 'G19':
                                self._plane = Plane.YZ
                            case 'G20':
                                self._units = Units.IN
                            case 'G21':
                                self._units = Units.MM
                            case 'G90':
                                self._positioning = Positioning.ABSOLUTE
                            case 'G91':
                                self._positioning = Positioning.RELATIVE
                case 'G54' | 'G55' | 'G56' | 'G57' | 'G58' | 'G59':
                    index = int(topic[1:]) - 54
                    self._workspace_offsets[index] = self._parse_coordinates(l)
                case 'G28':
                    self._ref_position1 = self._parse_coordinates(l)
                case 'G30':
                    self._ref_position2 = self._parse_coordinates(l)
                    pass
                case 'G92':
                    pass
                case 'TLO':
                    pass
                case 'PRB':
                    pass
        elif l.startswith('<') and l.endswith('>'):
            l = l[1:-1]
            parts = l.split('|')
            if parts:
                match parts[0]:
                    case 'Idle':
                        self._status = Status.IDLE
                    case 'Run':
                        self._status = Status.RUN
                    case 'JOG':
                        self._status = Status.JOG
                    case 'ALARM':
                        self._status = Status.ALARM
                    case 'HOLD':
                        self._status = Status.HOLD
                    case 'DOOR':
                        self._status = Status.DOOR
                    case _:
                        print(f'Unknown state: {parts[0]}')

                for part in parts[1:]:
                    pass
        elif l.startswith('$'):
            l = l[1:]
            if '=' in l:
                key, value = l.split('=', 1)
                self._settings[key] = value
        elif l == 'ok':
            if not self._command_results.empty():
                future = await self._command_results.get()
                future.set_result(self._command_response)
            self._command_response = []
        elif l.startswith('error:'):
            error_type = ErrorType(int(l[len('error:'):]))
            if not self._command_results.empty():
                future = await self._command_results.get()
                future.set_exception(Error(error_type))
            self._command_response = []
        else:
            if not self._command_results.empty():
                self._command_response.append(l)

        if self._on_line_receive:
            self._on_line_receive(line)

    def send_nowait(self, data: str | bytes, echo: bool = True):
        if isinstance(data, str):
            data = data.encode('utf-8')
        self._writer.write(data)
        if echo and self._on_line_send:
            self._on_line_send(data.decode('utf-8'))

    async def send(self, data: str | bytes, echo: bool = True):
        self.send_nowait(data, echo=echo)
        await self._writer.drain()

    def _send_command_internal(self, command):
        if isinstance(command, str):
            command = command.encode('utf-8')

        result_future = asyncio.get_running_loop().create_future()
        self._command_results.put_nowait(result_future)
        self.send_nowait(command + b'\n')

    def send_command(self, command: str | bytes) -> asyncio.Future[list[str]]:
        result_future = asyncio.get_running_loop().create_future()
        self._commands.put_nowait((command, result_future))
        return result_future

    async def soft_reset(self) -> None:
        await self.send(b'\x18', echo=False)
        self._ready = False

    async def status_report(self) -> None:
        await self.send(b'?', echo=False)

    async def start_resume(self) -> None:
        await self.send(b'~', echo=False)

    async def feed_hold(self) -> None:
        await self.send(b'!', echo=False)

    # Grbl 1.1 extended realtime commands
    async def safety_door(self) -> None:
        await self.send(b'\x84', echo=False)

    async def feed_override_reset(self) -> None:
        await self.send(b'\x90', echo=False)

    async def feed_override_increase_10(self) -> None:
        await self.send(b'\x91', echo=False)

    async def feed_override_decrease_10(self) -> None:
        await self.send(b'\x92', echo=False)

    async def feed_override_increase_1(self) -> None:
        await self.send(b'\x93', echo=False)

    async def feed_override_decrease_1(self) -> None:
        await self.send(b'\x94', echo=False)

    async def rapid_override_reset(self) -> None:
        await self.send(b'\x95', echo=False)

    async def rapid_override_half(self) -> None:
        await self.send(b'\x96', echo=False)

    async def rapid_override_quarter(self) -> None:
        await self.send(b'\x97', echo=False)

    async def spindle_override_reset(self) -> None:
        await self.send(b'\x99', echo=False)

    async def spindle_override_increase_10(self) -> None:
        await self.send(b'\x9A', echo=False)

    async def spindle_override_decrease_10(self) -> None:
        await self.send(b'\x9B', echo=False)

    async def spindle_override_increase_1(self) -> None:
        await self.send(b'\x9C', echo=False)

    async def spindle_override_decrease_1(self) -> None:
        await self.send(b'\x9D', echo=False)

    async def toggle_spindle_stop(self) -> None:
        await self.send(b'\x9E', echo=False)

    async def toggle_flood_coolant(self) -> None:
        await self.send(b'\xA0', echo=False)

    async def toggle_mist_coolant(self) -> None:
        await self.send(b'\xA1', echo=False)

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def locked(self) -> bool:
        return self._status == Status.ALARM

    async def unlock(self) -> None:
        await self.send_command('$X')

    async def run_homing_cycle(self) -> None:
        await self.send_command('$H')

    @property
    def positioning(self) -> Positioning:
        return self._positioning

    def set_positioning(self, value: Positioning) -> None:
        match value:
            case Positioning.ABSOLUTE:
                self.send_command('G90')
            case Positioning.RELATIVE:
                self.send_command('G91')
        self._positioning = value

    @property
    def plane(self) -> Plane:
        return self._plane

    def set_plane(self, value: Plane) -> None:
        match value:
            case Plane.XY:
                self.send_command('G17')
            case Plane.XZ:
                self.send_command('G18')
            case Plane.YX:
                self.send_command('G19')
        self._plane = value

    @property
    def units(self) -> Units:
        return self._units

    def set_units(self, value: Units) -> None:
        match value:
            case Units.IN:
                self.send_command('G20')
            case Units.MM:
                self.send_command('G21')

    @property
    def feedrate(self) -> float:
        return self._feedrate

    def set_feedrate(self, value: float) -> None:
        self.send_command(f'F{value}')
        self._feedrate = value

    @property
    def spindle_speed(self) -> float:
        return self._spindle_speed

    def set_spindle_speed(self, value: float) -> None:
        self.send_command(f'S{value}')
        self._spindle_speed = value

    @property
    def reference_position1(self) -> Coordinates:
        return self._ref_position1

    @property
    def reference_position2(self) -> Coordinates:
        return self._ref_position2

    @property
    def machine_coordinates(self) -> Coordinates:
        return self._machine_coordinates

    @property
    def coordinates(self) -> Coordinates:
        if self._current_workspace == 0:
            return self._machine_coordinates

        return self._machine_coordinates + self._workspace_offsets[self._current_workspace]

    def get_workspace_offset(self, idx: int) -> Coordinates:
        if idx < 1 or idx > len(self._workspace_offsets):
            raise ArgumentError('Invalid work coordinates index')
        return self._workspace_offsets[idx]

    async def jog(
        self,
        feedrate: float | None = None,
        positioning: Positioning = Positioning.RELATIVE,
        units: Units = Units.MM,
        x: float | None = None,
        y: float | None = None,
        z: float | None = None
    ):

        command = f'$J=G{90 + positioning.value}G{20 + units.value}'
        if self._modal_command != 'G0':
            command += 'G0'
        command += f'F{feedrate}'
        if x is not None:
            command += f'X{x}'
        if y is not None:
            command += f'Y{y}'
        if z is not None:
            command += f'Z{z}'
        await self.send_command(command)

    async def jog_cancel(self):
        await self.send(b'\x85', echo=False)
