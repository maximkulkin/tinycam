from tinycam.ui.view_items.canvas.sdf_shape import SdfShape


class Rectangle(SdfShape):
    shape_code = '''
        float shape(vec2 p) {
            vec2 d = abs(p) - size * 0.5;
            return length(max(d, 0.0)) + min(max(d.x, d.y), 0.0);
        }
    '''
