from PySide6 import QtGui
from itertools import chain
from tinycam.types import Vector2, Vector3, Vector4, Matrix44
from tinycam.ui.camera import Camera
from typing import cast


def qcolor_to_vec4(color: QtGui.QColor) -> Vector4:
    return Vector4(color.redF(), color.greenF(), color.blueF(), color.alphaF())


def project(point: Vector3, camera: Camera) -> Vector2:
    sp = camera.projection_matrix * camera.view_matrix * Vector4.from_vector3(point, 1.0)
    return camera.ndc_to_screen_point(sp)


def unproject(point: tuple[float, float], camera: Camera) -> Vector3:
    vp = cast(Matrix44, camera.projection_matrix * camera.view_matrix)
    ivp = vp.inverse

    ndc = camera.screen_to_ndc_point(Vector2(point))

    p = Vector4(ndc[0], ndc[1], ndc[2], 1)
    v: Vector4 = cast(Vector4, ivp * p)
    if v.w != 0.0:
        v /= v.w

    r = v.xyz
    r -= r.z * (camera.position - r) / (camera.position.z - r.z)
    return r


def point_inside_polygon(p: Vector2, polygon: list[Vector2]) -> bool:
    count = 0
    for (p1, p2) in zip(polygon, chain(polygon[1:], [polygon[0]])):
        if (p.y < p1.y) == (p.y < p2.y):
            continue

        if ((p1.y == p2.y) or p.x < p1.x + (p.y - p1.y) / (p2.y - p1.y) * (p2.x - p1.x)):
            count += 1
    return count % 2 == 1


def clear_layout(layout):
    while layout.count() > 0:
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())
