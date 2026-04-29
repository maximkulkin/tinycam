import numpy as np

from tinycam.math_types import Vector3, Matrix44
from tinycam.ui.view import RenderState
from tinycam.ui.view_items.core.node3d import Node3D


class Billboard(Node3D):
    """
    A node that always rotates towards camera
    so that it's XY plane is perpendicular to it.
    """
    def render(self, state: RenderState):
        camera = state.camera

        rotation = camera.rotation.conjugate
        y_axis = rotation * camera.UP
        z_axis = rotation * camera.BACKWARD
        x_axis = Vector3.cross(y_axis, z_axis)

        mat = Matrix44(np.array((
            (x_axis[0], y_axis[0], z_axis[0], 0.),
            (x_axis[1], y_axis[1], z_axis[1], 0.),
            (x_axis[2], y_axis[2], z_axis[2], 0.),
            (0, 0, 0, 1.),
        )))
        _, rotation, _ = mat.decompose()
        self.world_rotation = rotation.conjugate

        super().render(state)
