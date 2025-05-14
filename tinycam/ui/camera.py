from typing import cast

from tinycam.types import Vector2, Vector3, Vector4, Quaternion, Matrix44


class Camera:
    UP = Vector3(0, 1, 0)
    DOWN = Vector3(0, -1, 0)
    FORWARD = Vector3(0, 0, -1)
    BACKWARD = Vector3(0, 0, 1)
    RIGHT = Vector3(1, 0, 0)
    LEFT = Vector3(-1, 0, 0)

    def __init__(
        self,
        position: Vector3 | None = None,
        rotation: Quaternion | None = None,
        near: float = 0.1,
        far: float = 1000.0,
    ):
        self._position = position or Vector3()
        self._rotation = rotation or Quaternion()
        self._near = near
        self._far = far

        self._world_matrix = None
        self._view_matrix = None
        self._projection_matrix = None
        self._pixel_size = Vector2()
        self._device_pixel_ratio = 1.0

    @property
    def position(self) -> Vector3:
        return self._position

    @position.setter
    def position(self, value: Vector3) -> None:
        self._position = value
        self._invalidate_matrixes()

    @property
    def rotation(self) -> Quaternion:
        return self._rotation

    @rotation.setter
    def rotation(self, value: Quaternion) -> None:
        self._rotation = value
        self._invalidate_matrixes()

    @property
    def pixel_size(self) -> Vector2:
        return self._pixel_size

    @pixel_size.setter
    def pixel_size(self, value: Vector2):
        self._pixel_size = value

    @property
    def pixel_center(self) -> Vector2:
        return self._pixel_size * 0.5

    @property
    def pixel_width(self) -> float:
        return float(self.pixel_size.x)

    @property
    def pixel_height(self) -> float:
        return float(self.pixel_size.y)

    view_size = pixel_size
    view_center = pixel_center
    view_width = pixel_width
    view_height = pixel_height

    @property
    def device_pixel_ratio(self) -> float:
        return self._device_pixel_ratio

    @device_pixel_ratio.setter
    def device_pixel_ratio(self, value: float):
        self._device_pixel_ratio = value

    @property
    def near(self) -> float:
        return self._near

    @near.setter
    def near(self, value: float):
        self._near = value
        self._invalidate_projection_matrix

    @property
    def far(self) -> float:
        return self._far

    @far.setter
    def far(self, value: float):
        self._far = value
        self._invalidate_projection_matrix()

    def _invalidate_matrixes(self) -> None:
        self._world_matrix = None
        self._view_matrix = None

    def _invalidate_projection_matrix(self) -> None:
        self._projection_matrix = None

    def _calculate_projection_matrix(self) -> Matrix44:
        raise NotImplementedError()

    @property
    def world_matrix(self) -> Matrix44:
        if self._world_matrix is None:
            self._world_matrix = (
                Matrix44.from_translation(self.position) *
                Matrix44.from_quaternion(self.rotation)
            )
        return cast(Matrix44, self._world_matrix)

    @property
    def view_matrix(self) -> Matrix44:
        if self._view_matrix is None:
            self._view_matrix = self.world_matrix.inverse
        return self._view_matrix

    @property
    def projection_matrix(self):
        if self._projection_matrix is None:
            self._projection_matrix = self._calculate_projection_matrix()
        return self._projection_matrix

    def screen_to_ndc_point(self, screen_point: Vector2, z: float = 0.0) -> Vector3:
        return Vector3(
            2. * screen_point.x / self.pixel_width - 1.,
            1. - 2. * screen_point.y / self.pixel_height,
            z
        )

    def ndc_to_screen_point(self, ndc_point: Vector3) -> Vector2:
        return Vector2(
            (ndc_point.x + 1.) * 0.5 * self.pixel_width,
            (1. - ndc_point.y) * 0.5 * self.pixel_height,
        )

    def screen_to_world_point(self, screen_point: Vector2, z: float = 0.0) -> Vector3:
        ndc = self.screen_to_ndc_point(screen_point, z=z)

        v = (self.projection_matrix * self.view_matrix).inverse * Vector4.from_vector3(ndc)
        return v.dehomogenize().xyz

    def world_to_screen_point(self, world_point: Vector3) -> Vector2:
        return self.ndc_to_screen_point(
            (self.projection_matrix * self.view_matrix *
                Vector4.from_vector3(world_point, w=1.0)).dehomogenize().xyz
        )

    project = world_to_screen_point
    unproject = screen_to_world_point


class PerspectiveCamera(Camera):
    def __init__(
        self,
        fov: float = 45.0,
        aspect: float = 1.0,
        **kwargs
    ):
        super().__init__(**kwargs)

        self._fov = fov
        self._aspect = aspect

    @property
    def fov(self) -> float:
        return self._fov

    @fov.setter
    def fov(self, value: float) -> None:
        self._fov = value
        self._invalidate_projection_matrix()

    @property
    def aspect(self) -> float:
        return self._aspect

    @aspect.setter
    def aspect(self, value: float) -> None:
        self._aspect = value
        self._invalidate_projection_matrix()

    @property
    def pixel_size(self) -> Vector2:
        return super().pixel_size

    @pixel_size.setter
    def pixel_size(self, value: Vector2):
        Camera.pixel_size.fset(self, value)  # pyright: ignore
        self.aspect = float(value.x / value.y if value.x > 0 else 1.0)

    def look_at(
        self,
        target: Vector3,
        up: Vector3 = Vector3(0, 1, 0),
    ) -> None:
        _, r, _ = (
            Matrix44.look_at(self.position, target, up).decompose()
        )
        self.rotation = r.conjugate

    def _calculate_projection_matrix(self):
        return Matrix44.perspective_projection(
            self._fov, self._aspect, self._near, self._far,
        )

    def unproject(self, screen_point: Vector2) -> Vector3:
        point = super().unproject(screen_point)
        point -= point.z * (self.position - point) / (self.position.z - point.z)

        return point


class OrthographicCamera(Camera):
    def __init__(
        self,
        width: float = 20.0,
        height: float = 20.0,
        zoom: float = 1.0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._width = width
        self._height = height
        self._zoom = zoom

    @property
    def width(self) -> float:
        return self._width

    @width.setter
    def width(self, value: float):
        self._width = value
        self._invalidate_projection_matrix()

    @property
    def height(self) -> float:
        return self._height

    @height.setter
    def height(self, value: float):
        self._height = value
        self._invalidate_projection_matrix()

    @property
    def zoom(self) -> float:
        return self._zoom

    @zoom.setter
    def zoom(self, value: float):
        self._zoom = value
        self._invalidate_projection_matrix()

    def resize(self, width: float, height: float, keep_aspect: bool = True):
        if keep_aspect:
            aspect = self.width / self.height
            width = height * aspect
        self._width = width
        self._height = height
        self._invalidate_projection_matrix()

    def _calculate_projection_matrix(self) -> Matrix44:
        w = self.width * 0.5 / self.zoom
        h = self.height * 0.5 / self.zoom
        return Matrix44.orthogonal_projection(
            left=-w, right=w,
            bottom=-h, top=h,
            near=self.near, far=self.far,
        )
