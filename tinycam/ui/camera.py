from tinycam.types import Vector3, Quaternion, Matrix44


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
        return self._world_matrix

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


class OrthographicCamera(Camera):
    def __init__(
        self,
        left: float = -10.0,
        right: float = 10.0,
        top: float = 10.0,
        bottom: float = -10.0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self._left = left
        self._right = right
        self._top = top
        self._bottom = bottom

    @property
    def left(self) -> float:
        return self._left

    @left.setter
    def left(self, value: float) -> None:
        self._left = value
        self._invalidate_projection_matrix()

    @property
    def right(self) -> float:
        return self._right

    @right.setter
    def right(self, value: float) -> None:
        self._right = value
        self._invalidate_projection_matrix()

    @property
    def top(self) -> float:
        return self._top

    @top.setter
    def top(self, value: float) -> None:
        self._top = value
        self._invalidate_projection_matrix()

    @property
    def bottom(self) -> float:
        return self._bottom

    @bottom.setter
    def bottom(self, value: float) -> None:
        self._bottom = value
        self._invalidate_projection_matrix()

    def _calculate_projection_matrix(self) -> Matrix44:
        return Matrix44.orthogonal_projection(
            left=self.left, right=self.right,
            top=self.top, bottom=self.bottom,
            near=self.near, far=self.far,
        )
