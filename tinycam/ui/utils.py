import math
from itertools import chain
from tinycam.types import Vector2, Vector3, Vector4, Quaternion
from tinycam.ui.camera import Camera
from typing import Tuple


def quaternion_to_eulers(q: Quaternion) -> Vector3:
    t0 = 2.0 * (q.w * q.x + q.y * q.z)
    t1 = 1.0 - 2.0 * (q.x * q.x + q.y * q.y)
    roll = math.atan2(t0, t1)

    pitch = max(-1.0, min(1.0, 2.0 * (q.w * q.y - q.z * q.x)))

    t3 = 2.0 * (q.w * q.z + q.x * q.y)
    t4 = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    yaw = math.atan2(t3, t4)

    return roll, pitch, yaw


def project(point: Vector3, camera: Camera) -> Vector2:
    sp = camera.projection_matrix * camera.view_matrix * Vector4(*point, 1.0)
    return camera.ndc_to_screen_point(sp)


def unproject(point: Tuple[float, float], camera: Camera) -> Vector3:
    vp = camera.projection_matrix * camera.view_matrix
    ivp = vp.inverse

    ndc = camera.screen_to_ndc_point(Vector2(point))

    p = Vector4(*ndc, 1)
    v = ivp * p
    if v.w != 0.0:
        v /= v.w

    r = v.xyz
    r -= r.z * (camera.position - r) / (camera.position.z - r.z)
    return r


def clear_layout(layout):
    while layout.count() > 0:
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()
        elif item.layout() is not None:
            clear_layout(item.layout())
