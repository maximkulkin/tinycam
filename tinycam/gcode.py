from tinycam import commands


class GcodeBuilder:
    def __init__(self):
        self.commands = []
        self._last_unit_mode = None
        self._last_feed_rate = None
        self._last_spindle_speed = None
        self._last_command = None
        self._last_positioning_mode = None
        self._last_coordinate_system = None

    def command(self, s, *args, **kwargs):
        self.commands.append(s.format(*args, **kwargs))

    def rapid_move(self, x=None, y=None, z=None, feed_rate=None):
        words = []
        if self._last_command != 'G00':
            words.append('G00')
            self._last_command = 'G00'

        if x is not None:
            words.append(f'X{x:g}')

        if y is not None:
            words.append(f'Y{y:g}')

        if z is not None:
            words.append(f'Z{z:g}')

        if feed_rate is not None and feed_rate != self._last_feed_rate:
            words.append(f'F{feed_rate:d}')
            self._last_feed_rate = feed_rate

        self.command(''.join(words))

    def move(self, x=None, y=None, z=None, feed_rate=None, spindle_speed=None):
        words = []
        if self._last_command != 'G01':
            words.append('G01')
            self._last_command = 'G01'

        if x is not None:
            words.append(f'X{x:g}')

        if y is not None:
            words.append(f'Y{y:g}')

        if z is not None:
            words.append(f'Z{z:g}')

        if feed_rate is not None and feed_rate != self._last_feed_rate:
            words.append(f'F{feed_rate:d}')
            self._last_feed_rate = feed_rate

        if spindle_speed is not None and spindle_speed != self._last_spindle_speed:
            words.append(f'S{spindle_speed:d}')
            self._last_spindle_speed = spindle_speed

        self.command(''.join(words))

    def _set_units_mode(self, mode):
        if self._last_unit_mode == mode:
            return

        self.command(mode)
        self._last_unit_mode = mode

    def set_inch_units(self):
        self._set_units_mode('G20')

    def set_millimeter_units(self):
        self._set_units_mode('G21')

    def _set_positioning_mode(self, mode):
        if self._last_positioning_mode == mode:
            return

        self.command(mode)
        self._last_positioning_mode = mode

    def set_absolute_positioning(self):
        self._set_positioning_mode('G90')

    def set_relative_positioning(self):
        self._set_positioning_mode('G91')

    def select_machine_coordinates(self):
        if self._last_coordinate_system == 'G53':
            return
        self.command('G53')
        self._last_coordinate_system = 'G53'

    def select_work_offset(self, offset_idx):
        if offset_idx < 1 or offset_idx > 6:
            raise ValueEror('Work offset index is out of range')

        offset_idx += 53
        command = 'G{offset_idx:02d}'
        if command == self._last_coordinate_system:
            return

        self.command(command)
        self._last_coordinate_system = command

    def set_work_offset(self, offset_idx, x=None, y=None, z=None):
        if offset_idx < 1 or offset_idx > 6:
            raise ValueError('Work offset index is out of range')

        words = ['G10', 'P{offset_idx}']
        if x is not None:
            words.append('X{x:g}')
        if y is not None:
            words.append('Y{y:g}')
        if z is not None:
            words.append('Z{z:g}')
        self.command(''.join(words))

    def build(self):
        return '\n'.join(self.commands)


class GcodeRenderer:
    def __init__(self):
        pass

    def render(self, cnc_commands):
        g = GcodeBuilder()

        move_speed = 0
        spindle_speed = 0

        g.set_millimeter_units()
        g.set_absolute_positioning()
        for command in cnc_commands:
            match type(command):
                case commands.CncTravelCommand:
                    g.rapid_move(x=command.x, y=command.y, z=command.z)
                case commands.CncCutCommand:
                    g.move(x=command.x, y=command.y, z=command.z,
                           feed_rate=move_speed, spindle_speed=spindle_speed)
                case commands.CncSetCutSpeed:
                    move_speed = command.speed
                case commands.CncSetSpindleSpeed:
                    spindle_speed = command.speed
                case _:
                    print(f'Unknown CNC command: {command}')

        return g.build()

