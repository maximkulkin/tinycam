from enum import Enum
from functools import reduce
import math
import pyparsing as pp
import shapely
import shapely.affinity
from geometry import Geometry


class Node:
    def __init__(self, type, location, data=None):
        self.type = type
        self._location = location
        self._data = data or {}

    @property
    def location(self):
        return self._location

    def __getattr__(self, name):
        if name not in self._data:
            raise AttributeError('Attribute {name} not found in {data}'.format(name=name, data=self._data))
        return self._data[name]

    def __hasattr__(self, name):
        return name in self._data

    def get(self, name, default=None):
        return self._data.get(name, default)

    def __repr__(self):
        extras = ''
        for k, v in self._data.items():
            if isinstance(v, list) and len(v) > 0 and isinstance(v[0], Node):
                extras += (
                    ' {k}=[\n'.format(k=k) +
                    '\n'.join(
                        '\n'.join('  ' + line for line in str(item).split('\n'))
                        for item in v
                    ) +
                    '\n]'
                )
            else:
                extras += ' {k}={v}'.format(k=k, v=v)
        return '<{type}{extras}>'.format(type=self.type, extras=extras)


def make_node(type):
    def make(location, result):
        return Node(type, location=location, data=result.as_dict())
    return make


L = pp.Literal

unsigned_decimal = pp.Regex(r'([0-9]+(\.[0-9]*)?)|(\.[0-9]+)').set_parse_action(lambda result: float(result[0]))
decimal = pp.Regex(r'[+-]?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))').set_parse_action(lambda result: float(result[0]))

header_start = pp.Suppress(L('M48'))

unit_mode = (
      L('METRIC')('units')
    | L('INCH')('units')
).set_parse_action(make_node('unit_mode'))

tool_definition = (
    L('T') + pp.Regex(r'[0-9]+')('id') +
    L('C') + unsigned_decimal('diameter')
).set_parse_action(make_node('tool_definition'))

header_end = pp.Suppress(L('%') | L('M95'))

header = (
    header_start +
    pp.ZeroOrMore(
          unit_mode
        | tool_definition,
        stop_on=header_end
    ) +
    header_end
)

select_tool_command = (
    L('T') + pp.Regex(r'[0-9]+')('id')
).set_parse_action(make_node('select_tool'))

drill_command = (
    L('X') + decimal('x') +
    L('Y') + decimal('y')
).set_parse_action(make_node('drill'))

move_command = (
    L('G00') +
    L('X') + decimal('x') +
    L('Y') + decimal('y')
).set_parse_action(make_node('move'))

mill_command = (
    L('G01') +
    L('X') + decimal('x') +
    L('Y') + decimal('y')
).set_parse_action(make_node('mill'))

absolute_positioning = L('G90').set_parse_action(make_node('absolute_positioning'))
relative_positioning = L('G91').set_parse_action(make_node('relative_positioning'))

g05 = pp.Suppress(L('G05'))
m15 = pp.Suppress(L('M15'))
m16 = pp.Suppress(L('M16'))
body_end = pp.Suppress(L('M30'))

body = (
    pp.ZeroOrMore(
          select_tool_command
        | absolute_positioning
        | relative_positioning
        | drill_command
        | move_command
        | mill_command
        | g05
        | m15
        | m16,
        stop_on=body_end
    ) +
    body_end
)

excellon_file = (
    pp.Optional(header('header')) +
    body('body')
).set_parse_action(make_node('excellon'))


class ExcellonError(Exception):
    def __init__(self, location, message):
        super().__init__('Error at %s: %s' % (location, message))
        self.location = location


class ExcellonParser:
    def __init__(self, geometry=Geometry()):
        self._geometry = geometry
        self._reset()

    def _reset(self):
        self._units = None
        self._units_scale = 1.0
        self._relative_positioning = False

        self._tool_diameters = {'0': 0.0}
        self._current_tool = None
        self._current_position = (0.0, 0.0)

        self._shapes = None

    def parse_string(self, s):
        self._reset()

        nodes = excellon_file.parse_string(s)
        for node in nodes:
            self._process_node(node)

        return self._shapes

    def _eval_position(self, p):
        if self._relative_positioning:
            return (p[0] + self._current_position[0],
                    p[1] + self._current_position[1])
        return p

    def _process_node(self, node):
        method_name = '_process_%s' % node.type
        if not hasattr(self, method_name):
            print('Got unexpected command: %s' % node.type)
            return

        getattr(self, method_name)(node)

    def _process_excellon(self, node):
        for header_node in node.header:
            self._process_node(header_node)

        for body_node in node.body:
            self._process_node(body_node)

    def _process_unit_mode(self, node):
        match node.units:
            case 'METRIC':
                self._units = 'mm'
                self._units_scale = 1.0
            case 'INCH':
                self._units = 'in'
                self._units_scale = 25.4
            case _:
                raise ExcellonError(node.location, 'Unknown units %s' % node.units)

    def _process_absolute_positioning(self, node):
        self._relative_positioning = False

    def _process_relative_positioning(self, node):
        self._relative_positioning = True

    def _process_tool_definition(self, node):
        self._tool_diameters[node.id] = node.diameter * self._units_scale

    def _process_select_tool(self, node):
        if node.id not in self._tool_diameters:
            raise ExcellonError(node.location, 'Unknown tool %s' % node.id)
        self._current_tool = node.id

    def _process_drill(self, node):
        if self._current_tool is None:
            raise ExcellonError(node.location, 'Drill command without tool selected')

        position = self._eval_position((node.x, node.y))

        self._shapes = self._geometry.union(
            self._shapes,
            self._geometry.circle(
                diameter=self._tool_diameters[self._current_tool],
                center=position,
            ),
        )
        self._current_position = position

    def _process_move(self, node):
        self._current_position = self._eval_position((node.x, node.y))

    def _process_mill(self, node):
        if self._current_position is None:
            raise ExcellonError(
                node.location, 'Mill command without moving into position',
            )

        if self._current_tool is None:
            raise ExcellonError(node.location, 'Mill command without tool selected')

        position = self._eval_position((node.x, node.y))
        self._shapes = self._geometry.union(
            self._shapes,
            self._geometry.line(
                [self._current_position, position],
                width=self._tool_diameters[self._current_tool],
            ),
        )
        self._current_position = position


def parse_excellon(content, geometry=Geometry()):
    parser = ExcellonParser(geometry=geometry)
    return parser.parse_string(content)


if __name__ == '__main__':
    with open('sample.drl', 'rt') as f:
        nodes = excellon_file.parse_string(f.read())
        print('\n'.join([str(node) for node in nodes]))
