from enum import Enum
import math
import pyparsing as pp
import pyparsing.exceptions
from tinycam.geometry import Geometry


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

unsigned_integer = pp.Regex(r'[0-9]+').set_parse_action(lambda result: int(result[0]))
positive_integer = pp.Regex(r'[1-9][0-9]*').set_parse_action(lambda result: int(result[0]))
integer = pp.Regex(r'[+-]?[0-9]+').set_parse_action(lambda result: int(result[0]))

unsigned_decimal = pp.Regex(r'([0-9]+(\.[0-9]*)?)|(\.[0-9]+)').set_parse_action(lambda result: float(result[0]))
decimal = pp.Regex(r'[+-]?(([0-9]+(\.[0-9]*)?)|(\.[0-9]+))').set_parse_action(lambda result: float(result[0]))

string = pp.Regex(r'[^%*]*')

field = pp.Regex(r'[^%*,]+')

name = pp.Regex(r'[._A-Za-z][._A-Za-z0-9]{0,126}')
standard_name = pp.Regex(r'\.[._A-Za-z][._A-Za-z0-9]{0,125}')
user_defined_name = pp.Regex(r'[_A-Za-z][._A-Za-z0-9]{0,126}')

units_mode = ('%MO' + (L('MM') | L('IN'))('units') + '*%').set_parse_action(
    make_node('units_mode')
)
coordinate_digits = (pp.Char('123456')('integer_digits') + pp.Char('56')('decimal_digits')).set_parse_action(lambda result: {'integer': int(result[0]), 'decimal': int(result[1])})
format_specification = (
    '%FSLA' +
    'X' + coordinate_digits('x_format') +
    'Y' + coordinate_digits('y_format') +
    '*%'
).set_parse_action(make_node('format_specification'))

plot_command = (
    pp.Optional('X' + integer('x')) +
    pp.Optional('Y' + integer('y')) +
    pp.Optional('I' + integer('i') + 'J' + integer('j')) +
    'D01*'
).set_parse_action(make_node('plot'))
move_command = (
    pp.Optional('X' + integer('x')) +
    pp.Optional('Y' + integer('y')) +
    'D02*'
).set_parse_action(make_node('move'))
flash_command = (
    pp.Optional('X' + integer('x')) +
    pp.Optional('Y' + integer('y')) +
    'D03*'
).set_parse_action(make_node('flash'))

linear_mode = L('G01*').set_parse_action(make_node('linear_mode'))
cw_circular_mode = L('G02*').set_parse_action(make_node('cw_circular_mode'))
ccw_circular_mode = L('G03*').set_parse_action(make_node('ccw_circular_mode'))
# left for compatibility with older versions of Gerber
prepare_circular_mode = L('G75*').set_parse_action(make_node('prepare_circular_mode'))

comment = ('G04' + string('comment') + '*').set_parse_action(make_node('comment'))

end_command = L('M02*').set_parse_action(make_node('end'))

load_polarity = ('%LP' + (L('C') | L('D'))('polarity') + '*%').set_parse_action(make_node('polarity'))
load_mirror   = ('%LM' + (L('N') | L('XY') | L('X') | L('Y'))('axis') + '*%').set_parse_action(make_node('mirror'))
load_rotation = ('%LR' + decimal('angle') + '*%').set_parse_action(make_node('rotate'))
load_scale    = ('%LS' + decimal('factor') + '*%').set_parse_action(make_node('scale'))

aperture_identifier = pp.Regex(r'D0*[1-9][0-9]+')

set_current_aperture = ('D' + unsigned_integer('identifier').set_parse_action(lambda result: 'D' + result['identifier']) + '*').set_parse_action(make_node('set_current_aperture'))

circle_aperture_definition = (
    'C,' +
    decimal('diameter') +
    pp.Optional('X' + decimal('hole_diameter'))
).set_parse_action(make_node('circle_aperture'))
rectangle_aperture_definition = (
    'R,' +
    decimal('x_size') + 'X' +
    decimal('y_size') +
    pp.Optional('X' + decimal('hole_diameter'))
).set_parse_action(make_node('rectangle_aperture'))
obround_aperture_definition = (
    'O,' +
    decimal('x_size') + 'X' +
    decimal('y_size') +
    pp.Optional('X' + decimal('hole_diameter'))
).set_parse_action(make_node('obround_aperture'))
polygon_aperture_definition = (
    'P,' +
    decimal('outer_diameter') + 'X' +
    integer('vertices') + 'X' +
    decimal('rotation') +
    pp.Optional('X' + decimal('hole_diameter'))
).set_parse_action(make_node('polygon_aperture'))
custom_aperture_definition = (
    name('name') +
    pp.Optional(pp.Suppress(',') + decimal + pp.ZeroOrMore(pp.Suppress('X') + decimal).set_parse_action(list))('parameters').set_parse_action(lambda result: result)
).set_parse_action(make_node('custom_aperture'))
aperture_template = (
      circle_aperture_definition
    | rectangle_aperture_definition
    | obround_aperture_definition
    | polygon_aperture_definition
    | custom_aperture_definition
).set_parse_action(lambda result: result[0])
aperture_definition = (
    '%AD' + aperture_identifier('identifier') + aperture_template('template') + '*%'
).set_parse_action(make_node('aperture_definition'))

expression = pp.Forward()

exposure = pp.Char('01')('exposure')

comment_primitive = ('0 ' + string('text')).set_parse_action(make_node('comment_primitive'))
circle_primitive = (
    '1,' +
    exposure + ',' +
    expression('diameter') + ',' +
    expression('x') + ',' +
    expression('y') +
    pp.Optional(',' + expression('rotation'))
).set_parse_action(make_node('circle'))
vector_line_primitive = (
    '20,' +
    exposure + ',' +
    expression('width') + ',' +
    expression('start_x') + ',' +
    expression('start_y') + ',' +
    expression('end_x') + ',' +
    expression('end_y') + ',' +
    expression('rotation')
).set_parse_action(make_node('vector_line'))
center_line_primitive = (
    '21,' +
    exposure + ',' +
    expression('width') + ',' +
    expression('height') + ',' +
    expression('center_x') + ',' +
    expression('center_y') + ',' +
    expression('rotation')
).set_parse_action(make_node('center_line'))
outline_primitive = (
    '4,' +
    exposure + ',' +
    expression('vertex_count') + ',' +
    expression('start_x') + ',' +
    expression('start_y') + ',' +
    ((expression('x') + pp.Suppress(',') + expression('y') + pp.Suppress(',')).set_parse_action(lambda result: (result[0], result[1])))[2, ...]('points') +
    expression('rotation')
).set_parse_action(make_node('outline'))
polygon_primitive = (
    '5,' +
    exposure +
    expression('vertex_count') + ',' +
    expression('center_x') + ',' +
    expression('center_y') + ',' +
    expression('diameter') + ',' +
    expression('rotation')
).set_parse_action(make_node('polygon'))
thermal_primitive = (
    '7,' +
    expression('center_x') + ',' +
    expression('center_y') + ',' +
    expression('outer_diameter') + ',' +
    expression('inner_diameter') + ',' +
    expression('gap_thickness') + ',' +
    expression('rotation')
).set_parse_action(make_node('thermal'))

primitive = (
      comment_primitive
    | circle_primitive
    | vector_line_primitive
    | center_line_primitive
    | outline_primitive
    | polygon_primitive
    | thermal_primitive
) + pp.Suppress('*')

macro_variable = pp.Combine('$' + positive_integer)

term = pp.Forward()

factor = (
      ('(' + expression + ')').set_parse_action(lambda result: result[1])
    | macro_variable('name').set_parse_action(make_node('variable'))
    | unsigned_decimal('value')
)
term <<= (factor('a') + pp.Char('x/') + term('b')).set_parse_action(make_node('factor')) | factor

expression <<= (
      (pp.Char('+-')('operator') + term('value')).set_parse_action(make_node('unary'))
    | (term('a') + pp.Char('+-')('operator') + expression('b')).set_parse_action(make_node('term'))
    | term
)

variable_definition = (
    macro_variable('name') + '=' + expression('expression') + '*'
).set_parse_action(make_node('variable_definition'))

aperture_macro = (
    '%AM' +
    name('name') + '*' +
    pp.OneOrMore(primitive | variable_definition)('body') +
    '%'
).set_parse_action(make_node('aperture_macro'))

file_attribute     = (
    '%TF' + field('name') +
    pp.ZeroOrMore(',' + field('value')) +
    '*%'
).set_parse_action(make_node('file_attribute'))
aperture_attribute = (
    '%TA' + field('name') +
    pp.ZeroOrMore(',' + field('value')) +
    '*%'
).set_parse_action(make_node('aperture_attribute'))
object_attribute   = (
    '%TO' + field('name') +
    pp.ZeroOrMore(',' + field('value')) +
    '*%'
).set_parse_action(make_node('object_attribute'))
delete_attribute   = (
    '%TD' + pp.Optional(field('name')) + '*%'
).set_parse_action(make_node('delete_attribute'))

region_definition = (
    'G36*' +
    pp.OneOrMore(
        (
            move_command +
            pp.ZeroOrMore(
                  plot_command
                | linear_mode
                | cw_circular_mode
                | ccw_circular_mode
            )
        ).set_parse_action(lambda location, result: Node('contour', location=location, data={'commands': list(result)}))
    )('contours') +
    'G37*'
).set_parse_action(make_node('region'))

block_aperture = pp.Forward()
block_aperture << (
    '%AB' + aperture_identifier('identifier') + '*%' +
    pp.ZeroOrMore(
          move_command
        | plot_command
        | flash_command
        | linear_mode
        | cw_circular_mode
        | ccw_circular_mode
        | prepare_circular_mode
        | set_current_aperture
        | comment
        | object_attribute
        | delete_attribute
        | aperture_attribute
        | file_attribute
        | aperture_definition
        | aperture_macro
        | load_polarity
        | load_mirror
        | load_rotation
        | load_scale
        | region_definition
        | block_aperture
    )('body') +
    '%AB*%'
).set_parse_action(make_node('step_and_repeat'))

step_and_repeat_block = (
    '%SR' +
    'X' + integer('x_repeats') + 'Y' + integer('y_repeats') +
    'I' + decimal('x_step') + 'J' + decimal('y_step') + '*%' +
    pp.ZeroOrMore(
          move_command
        | plot_command
        | flash_command
        | linear_mode
        | cw_circular_mode
        | ccw_circular_mode
        | prepare_circular_mode
        | set_current_aperture
        | comment
        | object_attribute
        | delete_attribute
        | aperture_attribute
        | file_attribute
        | aperture_definition
        | aperture_macro
        | load_polarity
        | load_mirror
        | load_rotation
        | load_scale
        | region_definition
        | block_aperture
    )('body') +
    '%SR*%'
).set_parse_action(make_node('step_and_repeat'))

unknown_command = (
    pp.Regex(r'[^*]*') + '*'
).set_parse_action(
    lambda location, result: Node(
        'unknown_command', location=location, data={'text': str(result)},
    )
)
unknown_macro = ('%' + pp.Regex(r'[^%]*') + '%').set_parse_action(
    lambda location, result: Node(
        'unknown_macro', location=location, data={'text': str(result)},
    )
)

gerber_file = pp.ZeroOrMore(
      units_mode
    | format_specification
    | comment
    | aperture_definition
    | aperture_macro
    | set_current_aperture
    | plot_command
    | move_command
    | flash_command
    | linear_mode
    | cw_circular_mode
    | ccw_circular_mode
    | load_polarity
    | load_mirror
    | load_rotation
    | load_scale
    | file_attribute
    | aperture_attribute
    | object_attribute
    | delete_attribute
    | region_definition
    | block_aperture
    | step_and_repeat_block
    | unknown_macro
    | unknown_command,
    stop_on=end_command,
) + end_command


class GerberError(Exception):
    def __init__(self, location, message):
        super().__init__('Error at %s: %s' % (location, message))
        self.location = location


class PlotMode(Enum):
    LINEAR = 1
    CIRCULAR_CW = 2
    CIRCULAR_CCW = 3


class GerberParser:
    def __init__(self, geometry=Geometry()):
        self._geometry = geometry
        self._reset()

    def _reset(self):
        self._units = None
        self._units_scale = 1.0
        self._fixed_width_x_multiplier = 1.0
        self._fixed_width_y_multiplier = 1.0

        self._apertures = {}
        self._aperture_macros = {}
        self._current_aperture = None

        self._polarity = False
        self._mirror = (1.0, 1.0)
        self._rotate = 0
        self._scale = 1.0
        self._plot_mode = PlotMode.LINEAR
        self._current_position = (0.0, 0.0)

        self._shapes = None

    def parse_string(self, s):
        self._reset()

        try:
            nodes = gerber_file.parse_string(s)
        except pyparsing.exceptions.ParseException as e:
            raise GerberError(None, 'Error parsing gerber: %s' % e)

        for node in nodes:
            self._process_node(node)

        return self._shapes

    def _process_node(self, node):
        method_name = '_process_%s' % node.type
        if not hasattr(self, method_name):
            print('Got unexpected command: %s' % node.type)
            return

        getattr(self, method_name)(node)

    def _eval_point(self, point, x, y):
        if x is not None:
            x *= self._fixed_width_x_multiplier * self._units_scale
        else:
            x = self._current_position[0]

        if y is not None:
            y *= self._fixed_width_y_multiplier * self._units_scale
        else:
            y = self._current_position[1]

        return (x, y)

    def _eval_expression(self, expression, variables):
        if isinstance(expression, (int, float)):
            return expression

        match expression.type:
            case 'decimal':
                return expression.value
            case 'variable':
                return variables[expression.name]
            case 'unary':
                a = self._eval_expression(expression.value, variables)
                if expression.operator == '-':
                    a = -a
                return a
            case 'term':
                a = self._eval_expression(expression.a, variables)
                b = self._eval_expression(expression.b, variables)
                match expression.operator:
                    case '+':
                        return a + b
                    case '-':
                        return a - b
            case 'factor':
                a = self._eval_expression(expression.a, variables)
                b = self._eval_expression(expression.b, variables)
                match expression.operator:
                    case 'x':
                        return a * b
                    case '/':
                        return a / b

    def _process_comment(self, node):
        pass

    def _process_units_mode(self, node):
        self._units = node.units
        match node.units:
            case 'MM':
                self._units_scale = 1.0
            case 'IN':
                self._units_scale = 25.4
            case _:
                raise GerberError(node.location, 'Unknown units: %s' % node.units)

    def _process_format_specification(self, node):
        self._fixed_width_x_multiplier = 0.1**node.x_format['decimal']
        self._fixed_width_y_multiplier = 0.1**node.y_format['decimal']

    def _process_aperture_definition(self, node):
        match node.template.type:
            case 'circle_aperture':
                aperture = {
                    'type': 'circle',
                    'diameter': node.template.diameter,
                    'shape': self._geometry.circle(node.template.diameter),
                }

            case 'rectangle_aperture':
                hw, hh = node.template.x_size/2, node.template.y_size/2
                aperture = {
                    'type': 'rectangle',
                    'shape': self._geometry.box((-hw, -hh), (hw, hh)),
                }

            case 'obround_aperture':
                w, h = node.template.x_size, node.template.y_size
                d2 = abs(w - h)/2
                if w < h:
                    shape = self._geometry.line([(0, -d2), (0, d2)], width=w)
                else:
                    shape = self._geometry.line([(-d2, 0), (d2, 0)], width=h)
                aperture = {
                    'type': 'obround',
                    'shape': shape,
                }

            case 'polygon_aperture':
                points = []
                r = node.template.outer_diameter
                for i in range(node.template.vertices):
                    angle = math.radians(
                        360*i/node.template.vertices + node.template.rotation
                    )
                    points.append((math.cos(angle)*r, math.sin(angle)*r))

                aperture = {
                    'type': 'polygon',
                    'shape': self._geometry.polygon(points),
                }

            case 'custom_aperture':
                aperture = {
                    'type': 'macro',
                    'shape': self._eval_macro_aperture(node.template),
                }
            case _:
                raise GerberError(
                    node.location, 'Unknown aperture type: %s' % node.template.type,
                )

        if hasattr(node, 'hole_diameter'):
            aperture['shape'] = self._geometry.difference(
                aperture['shape'],
                self._geometry.circle(node.hole_diameter),
            )

        self._apertures[node.identifier] = aperture

    def _eval_macro_aperture(self, template):
        if template.name not in self._aperture_macros:
            raise GerberError(
                node.location, 'Unknown aperture macro: %s' % template.name,
            )

        macro_body = self._aperture_macros[template.name]
        variables = {
            '$' + str(i): param
            for i, param in enumerate(template.parameters, 1)
        }

        def eval_expression(expr):
            return self._eval_expression(expr, variables)

        shape = None

        for statement in macro_body:
            polarity = True
            shape1 = None
            match statement.type:
                case 'comment_primitive':
                    pass

                case 'variable_definition':
                    variables[statement.name] = eval_expression(statement.expression)

                case 'circle':
                    d = eval_expression(statement.diameter)
                    cx = eval_expression(statement.x)
                    cy = eval_expression(statement.y)

                    shape1 = self._geometry.circle(d, (cx, cy))

                case 'vector_line':
                    w = eval_expression(statement.width)
                    sx = eval_expression(statement.start_x)
                    sy = eval_expression(statement.start_y)
                    ex = eval_expression(statement.end_x)
                    ey = eval_expression(statement.end_y)

                    v = (ex - sx, ey - sy)
                    l = w / 2 / math.sqrt(v[0]**2 + v[1]**2)
                    n = (-v[1] * l, v[0] * l)

                    shape1 = self._geometry.polygon([
                        (sx + n[0], sy + n[1]),
                        (ex + n[0], ey + n[1]),
                        (ex - n[0], ey - n[1]),
                        (sx - n[0], sy - n[1]),
                    ])

                case 'center_line':
                    w = eval_expression(statement.width)
                    h = eval_expression(statement.height)
                    cx = eval_expression(statement.center_x)
                    cy = eval_expression(statement.center_y)

                    shape1 = self._geometry.box(
                        (cx - w*0.5, cy - h*0.5),
                        (cx + w*0.5, cy + h*0.5),
                    )

                case 'outline':
                    n = eval_expression(statement.vertex_count)
                    points = [(eval_expression(statement.start_x),
                               eval_expression(statement.start_y))]
                    if len(statement.points) != n:
                        raise GerberError(
                            node.location,
                            'Invalid number of outline points: '
                            'expected %d found %d' % (
                                n+1, len(statement.points)
                            )
                        )
                    for p in statement.points:
                        points.append((eval_expression(p[0]),
                                       eval_expression(p[1])))

                    shape1 = self._geometry.polygon(points)

                case 'polygon':
                    n = eval_expression(statement.vertex_count)
                    cx = eval_expression(statement.center_x)
                    cy = eval_expression(statement.center_y)
                    d = eval_expression(statement.diameter)

                    shape1 = self._geometry.polygon([
                        (cx + math.cos(angle)*d*0.5,
                         cy + math.sin(angle)*d*0.5)
                        for i in range(n)
                        for angle in [math.pi*i/n]
                    ])

                case 'thermal':
                    cx = eval_expression(statement.center_x)
                    cy = eval_expression(statement.center_y)
                    od = eval_expression(statement.outer_diameter)
                    id = eval_expression(statement.inner_diameter)
                    g = eval_expression(statement.gap_thickness)

                    shape1 = self._geometry.difference(
                        self._geometry.circle(od),
                        self._geometry.circle(id),
                        self._geometry.box((-g*0.5, -od), (g*0.5, od)),
                        self._geometry.box((-od, -g*0.5), (od, g*0.5)),
                    )

            if shape1 is not None and hasattr(statement, 'rotation'):
                shape1 = self._geometry.rotate(
                    shape1,
                    eval_expression(statement.rotation),
                )

            if shape1 is not None:
                if statement.exposure == '1' or statement.type == 'thermal':
                    shape = self._geometry.union(shape, shape1)
                else:
                    shape = self._geometry.difference(shape, shape1)

        return shape

    def _process_aperture_macro(self, node):
        self._aperture_macros[node.name] = node.body

    def _process_file_attribute(self, node):
        # TODO:
        pass

    def _process_aperture_attribute(self, node):
        # TODO:
        pass

    def _process_object_attribute(self, node):
        # TODO:
        pass

    def _process_delete_attribute(self, node):
        # TODO:
        pass

    def _process_polarity(self, node):
        self._polarity = node.polarity == 'D'

    def _process_mirror(self, node):
        match node.axis:
            case 'N':
                self._mirror = (1.0, 1.0)
            case 'X':
                self._mirror = (-1.0, 1.0)
            case 'Y':
                self._mirror = (1.0, -1.0)
            case 'XY':
                self._mirror = (-1.0, -1.0)

    def _process_rotate(self, node):
        self._rotate = node.angle

    def _process_scale(self, node):
        self._scale = node.factor

    def _process_set_current_aperture(self, node):
        if node.identifier not in self._apertures:
            raise GerberError(
                node.location, 'Unknown aperture ID: %s' % node.identifier,
            )
        self._current_aperture = node.identifier

    def _process_linear_mode(self, node):
        self._plot_mode = PlotMode.LINEAR

    def _process_cw_circular_mode(self, node):
        self._plot_mode = PlotMode.CIRCULAR_CW

    def _process_ccw_circular_mode(self, node):
        self._plot_mode = PlotMode.CIRCULAR_CCW

    def _process_plot(self, node):
        if self._current_aperture is None:
            raise GerberError(node.location, 'Plot with no aperture selected')

        aperture = self._apertures[self._current_aperture]
        if aperture['type'] != 'circle':
            raise GerberError(node.location, 'Plot aperture is not circle')

        point = self._eval_point(
            self._current_position,
            node.get('x'),
            node.get('y'),
        )
        bounds = self._apertures[self._current_aperture]['shape'].bounds
        width = (bounds[2] - bounds[0]) * self._scale
        shape = None
        match self._plot_mode:
            case PlotMode.LINEAR:
                shape = self._geometry.line(
                    [self._current_position, point],
                    width=width,
                )

            case PlotMode.CIRCULAR_CW:
                offset = self._eval_point(
                    (0.0, 0.0),
                    node.get('i'),
                    node.get('j'),
                )
                center = (self._current_position[0] + offset[0],
                          self._current_position[1] + offset[1])
                radius = math.sqrt(offset[0]**2 + offset[1]**2)
                start_angle = math.atan2(-offset[1], -offset[0])
                end_angle = math.atan2(point[1] - center[1], point[0] - center[0])

                shape = self._geometry.arc(
                    center, radius, start_angle, end_angle,
                    angle_step=0.1, width=width,
                )

            case PlotMode.CIRCULAR_CCW:
                offset = self._eval_point(
                    (0.0, 0.0),
                    node.get('i'),
                    node.get('j'),
                )
                center = self._current_position + offset
                radius = math.sqrt(offset[0]**2 + offset[1]**2)
                start_angle = math.atan2(-offset[1], -offset[0])
                end_angle = math.atan2(point[1] - center[1], point[0] - center[0])

                shape = self._geometry.arc(
                    center, radius, start_angle, end_angle,
                    angle_step=-0.1, width=width,
                )

        if shape is not None:
            if self._polarity:
                self._shapes = self._geometry.union(self._shapes, shape)
            else:
                self._shapes = self._geometry.intersection(self._shapes, shape)

        self._current_position = point

    def _process_move(self, node):
        self._current_position = self._eval_point(
            self._current_position,
            node.get('x'),
            node.get('y')
        )

    def _process_flash(self, node):
        if self._current_aperture is None:
            raise GerberError(node.location, 'Flash with no aperture selected')

        aperture = self._apertures[self._current_aperture]
        if aperture['type'] == 'block':
            for block_node in aperture['body']:
                self._process_node(block_node)
            return

        point = self._eval_point(
            self._current_position,
            node.get('x'),
            node.get('y')
        )

        shape = self._geometry.translate(
            self._geometry.rotate(
                self._geometry.scale(
                    self._geometry.scale(aperture['shape'], self._mirror),
                    self._scale
                ),
                self._rotate
            ),
            point
        )
        self._shapes = self._geometry.union(self._shapes, shape)

        self._current_position = point

    def _process_region(self, node):
        plot_mode = self._plot_mode  # initialize local plot mode with global one
        for contour in node.contours:
            points = []
            last_point = (0, 0)
            for command in contour.commands:
                match command.type:
                    case 'move':
                        if points:
                            shape = self._geometry.polygon(points)
                            self._shapes = self._geometry.union(self._shapes, shape)

                            points = []

                        last_point = self._eval_point(
                            last_point,
                            command.get('x'),
                            command.get('y')
                        )
                        points.append(last_point)
                    case 'plot':
                        point = self._eval_point(
                            last_point,
                            command.get('x'),
                            command.get('y')
                        )
                        match plot_mode:
                            case PlotMode.LINEAR:
                                points.append(point)

                            case PlotMode.CIRCULAR_CW:
                                offset = self._eval_point(
                                    (0.0, 0.0),
                                    node.get('i'),
                                    node.get('j'),
                                )
                                center = (self._current_position[0] + offset[0],
                                          self._current_position[1] + offset[1])
                                radius = math.sqrt(offset[0]**2 + offset[1]**2)
                                start_angle = math.atan2(-offset[1], -offset[0])
                                end_angle = math.atan2(point[1] - center[1],
                                                       point[0] - center[0])

                                points.extend(self._geometry.arc(
                                    center, radius, start_angle, end_angle,
                                    angle_step=0.1, width=0,
                                ).points)
                                points[-1] = point

                            case PlotMode.CIRCULAR_CCW:
                                offset = self._eval_point(
                                    (0.0, 0.0),
                                    node.get('i'),
                                    node.get('j'),
                                )
                                center = self._current_position + offset
                                radius = math.sqrt(offset[0]**2 + offset[1]**2)
                                start_angle = math.atan2(-offset[1], -offset[0])
                                end_angle = math.atan2(point[1] - center[1],
                                                       point[0] - center[0])

                                points.extend(self._geometry.arc(
                                    center, radius, start_angle, end_angle,
                                    angle_step=-0.1, width=0,
                                ).points)
                                points[-1] = point

                        last_point = point

                    case 'linear_mode':
                        plot_mode = PlotMode.LINEAR

                    case 'cw_circular_mode':
                        plot_mode = PlotMode.CIRCULAR_CW

                    case 'ccw_circular_mode':
                        plot_mode = PlotMode.CIRCULAR_CCW

            shape = self._geometry.polygon(points)
            self._shapes = self._geometry.union(self._shapes, shape)

    def _process_block_aperture(self, node):
        self._apertures[node.identifier] = {
            'type': 'block',
            'body': node.body,
        }

    def _process_step_and_repeat(self, node):
        for i in range(node.x_repeats):
            for j in range(node.y_repeats):
                for block_node in node.body:
                    self._process_node(block_node)

                self._current_position = (self._current_position[0],
                                          self._current_position[1] + node.y_step)

            self._current_position = (self._current_position[0] + node.x_step,
                                      self._current_position[1])

        self._current_position = None

    def _process_end(self, node):
        pass


def parse_gerber(content, geometry=Geometry()):
    parser = GerberParser(geometry=geometry)
    return parser.parse_string(content)


if __name__ == '__main__':
    # with open('sample.gbr', 'rt') as f:
    with open('bbb.gbr', 'rt') as f:
        nodes = gerber_file.parse_string(f.read())
        print('\n'.join([str(node) for node in nodes if node.type not in ('unknown_command', 'unknown_macro')]))
        # print('\n'.join([str(node) for node in nodes if node.type not in ('unknown_command', 'unknown_macro')]))
