from typing import cast, Sequence

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QMouseEvent, QKeyEvent, QCursor
from PySide6.QtWidgets import QWidget

from tinycam.geometry import MultiLineString
from tinycam.globals import GLOBALS
from tinycam.project import GeometryItem
from tinycam.math_types import Vector2, Vector3, Vector4
from tinycam.ui.commands import CreatePolylineCommand, EditPolylineCommand
from tinycam.ui.tools import CncTool
from tinycam.ui.utils import vector2
from tinycam.ui.view import SnapFlags, SnapResult
from tinycam.ui.view_items.core import Line2D, Node3D
from tinycam.ui.view_items.core.canvas import Canvas, CanvasItem, Circle, VerticalCross, DiagonalCross


class PolylineTool(CncTool):
    SNAP_THRESHOLD = 10   # pixels — point proximity for snap / pick
    SEGMENT_THRESHOLD = 8 # pixels — segment proximity for point insertion

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Shared canvas overlay
        self._canvas = None
        self._marker = None
        self._snap_marker = None

        # Create mode state
        self._drawing = False
        self._points: list[Vector2] = []
        self._last_point = Vector2()
        self._polyline = None
        self._point_controls: list[Circle] = []

        # Edit mode state
        self._edit_mode = False
        self._edit_item: GeometryItem | None = None
        self._edit_original_geometry = None
        # One entry per sub-shape: (points, is_closed).
        # Single Line/Ring → one entry; MultiLineString → one per sub-line.
        self._edit_shapes: list[tuple[list[Vector2], bool]] = []
        # Parallel to _edit_shapes: 'line' | 'ring' | 'polygon_ext' | 'polygon_hole'
        self._edit_shape_kinds: list[str] = []
        # Parallel to _edit_shapes: integer that groups a 'polygon_ext' with its
        # 'polygon_hole' entries; None for 'line' and 'ring' entries.
        self._edit_polygon_group: list[int | None] = []
        # How to wrap rebuilt shapes back into the item's geometry.
        # 'single' | 'multi_line' | 'group'
        self._edit_wrapper: str = 'single'
        # Non-polyline, non-polygon sub-shapes from a Group, preserved unchanged.
        self._edit_other_shapes: list = []
        self._drag_idx: int | None = None          # flat index across all sub-shapes
        self._hovered_point_idx: int | None = None # flat index
        self._hovered_segment: tuple[int, int] | None = None  # (shape_idx, local_seg_idx)
        self._segment_insert_pos: Vector2 | None = None
        self._segment_marker: Circle | None = None

    # ------------------------------------------------------------------
    # Tool lifecycle
    # ------------------------------------------------------------------

    def activate(self):
        super().activate()

        if self._canvas is None:
            self._canvas = Canvas(self.view.ctx)
            self._canvas.priority = 5
        self.view.add_item(self._canvas)

        if self._marker is None:
            self._marker = self._make_marker()
            self._canvas.add_item(self._marker)

        if self._snap_marker is None:
            self._snap_marker = self._make_snap_marker()
            self._canvas.add_item(self._snap_marker)

        self._marker.position = vector2(self.view.mapFromGlobal(QCursor.pos()))
        self._marker.visible = True
        self._snap_marker.visible = False

        # Enter edit mode when exactly one editable line/ring is selected
        selection = list(GLOBALS.APP.project.selection)
        if len(selection) == 1 and self._is_edit_candidate(selection[0]):
            self._enter_edit_mode(selection[0])

        self.view.update()

    def deactivate(self):
        if self._edit_mode:
            self.commit()   # preserve edits when switching tools
        else:
            self.cancel()
        assert self._canvas is not None
        self.view.remove_item(self._canvas)
        super().deactivate()

    def commit(self, closed: bool = False):
        if self._edit_mode:
            assert self._edit_item is not None
            new_geom = self._edit_item.geometry
            if new_geom is not self._edit_original_geometry:
                GLOBALS.APP.undo_stack.push(
                    EditPolylineCommand(
                        self._edit_item,
                        self._edit_original_geometry,
                        new_geom,
                    )
                )
            self._exit_edit_mode()
            self.view.update()
            return

        if self._polyline:
            if closed:
                self._create_polyline(self._points[:-2], closed=True)
            else:
                self._create_polyline(self._points[:-1], closed=False)

            self.view.remove_item(self._polyline)
            self._polyline = None

        self._drawing = False

    def cancel(self):
        if self._edit_mode:
            if self._edit_item is not None and self._edit_original_geometry is not None:
                self._edit_item.geometry = self._edit_original_geometry
            self._exit_edit_mode()
            self.view.update()
            return

        if self._polyline:
            self.view.remove_item(self._polyline)
            self._polyline = None

        if self._point_controls:
            assert self._canvas is not None
            for control in self._point_controls:
                self._canvas.remove_item(control)
            self._point_controls = []

        self._points = []
        self._drawing = False

    def eventFilter(self, widget: QWidget, event: QEvent) -> bool:
        if self._edit_mode:
            return self._edit_event_filter(widget, event)
        return self._create_event_filter(widget, event)

    # ------------------------------------------------------------------
    # Edit mode — entry / exit
    # ------------------------------------------------------------------

    def _is_edit_candidate(self, item) -> bool:
        return isinstance(item, GeometryItem)

    def _enter_edit_mode(self, item: GeometryItem):
        G = GLOBALS.GEOMETRY
        geom = item.geometry

        self._edit_item = item
        self._edit_original_geometry = geom
        self._edit_shapes = []
        self._edit_shape_kinds = []
        self._edit_polygon_group = []
        self._edit_other_shapes = []

        if G.is_ring(geom):
            pts = list(G.points(geom))[:-1]
            self._edit_shapes = [(pts, True)]
            self._edit_shape_kinds = ['ring']
            self._edit_polygon_group = [None]
            self._edit_wrapper = 'single'
        elif G.is_line(geom):
            self._edit_shapes = [(list(G.points(geom)), False)]
            self._edit_shape_kinds = ['line']
            self._edit_polygon_group = [None]
            self._edit_wrapper = 'single'
        elif isinstance(geom, MultiLineString):
            for sub in G.lines(geom):
                self._edit_shapes.append((list(G.points(sub)), False))
                self._edit_shape_kinds.append('line')
                self._edit_polygon_group.append(None)
            self._edit_wrapper = 'multi_line'
        else:
            # Group/GeometryCollection: extract editable shapes, preserve the rest
            poly_group = 0
            for sub in G.shapes(geom):
                if G.is_ring(sub):
                    pts = list(G.points(sub))[:-1]
                    self._edit_shapes.append((pts, True))
                    self._edit_shape_kinds.append('ring')
                    self._edit_polygon_group.append(None)
                elif G.is_line(sub):
                    self._edit_shapes.append((list(G.points(sub)), False))
                    self._edit_shape_kinds.append('line')
                    self._edit_polygon_group.append(None)
                elif G.is_polygon(sub):
                    # Exterior
                    pts = [Vector2(c[0], c[1]) for c in sub.exterior.coords][:-1]
                    self._edit_shapes.append((pts, True))
                    self._edit_shape_kinds.append('polygon_ext')
                    self._edit_polygon_group.append(poly_group)
                    # Holes
                    for interior in sub.interiors:
                        hole_pts = [Vector2(c[0], c[1]) for c in interior.coords][:-1]
                        self._edit_shapes.append((hole_pts, True))
                        self._edit_shape_kinds.append('polygon_hole')
                        self._edit_polygon_group.append(poly_group)
                    poly_group += 1
                else:
                    self._edit_other_shapes.append(sub)
            self._edit_wrapper = 'group'

        self._drag_idx = None
        self._hovered_point_idx = None
        self._hovered_segment = None
        self._segment_insert_pos = None
        self._segment_marker = None
        self._edit_mode = True

        self._update_edit_controls()

    def _exit_edit_mode(self):
        assert self._canvas is not None
        for ctrl in self._point_controls:
            self._canvas.remove_item(ctrl)
        self._point_controls = []

        if self._segment_marker is not None:
            self._canvas.remove_item(self._segment_marker)
            self._segment_marker = None

        self._edit_mode = False
        self._edit_item = None
        self._edit_original_geometry = None
        self._edit_shapes = []
        self._edit_shape_kinds = []
        self._edit_polygon_group = []
        self._edit_wrapper = 'single'
        self._edit_other_shapes = []
        self._drag_idx = None
        self._hovered_point_idx = None
        self._hovered_segment = None
        self._segment_insert_pos = None
        self.view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    # ------------------------------------------------------------------
    # Edit mode — geometry helpers
    # ------------------------------------------------------------------

    def _flat_edit_points(self) -> list[Vector2]:
        return [pt for pts, _ in self._edit_shapes for pt in pts]

    def _shape_and_local_idx(self, flat_idx: int) -> tuple[int, int]:
        offset = 0
        for shape_idx, (pts, _) in enumerate(self._edit_shapes):
            if flat_idx < offset + len(pts):
                return shape_idx, flat_idx - offset
            offset += len(pts)
        raise IndexError(flat_idx)

    def _flat_offset(self, shape_idx: int) -> int:
        return sum(len(pts) for pts, _ in self._edit_shapes[:shape_idx])

    def _apply_edit_geometry(self):
        """Rebuild the item's live geometry from the current edit shapes."""
        assert self._edit_item is not None
        G = GLOBALS.GEOMETRY

        built = []
        # polygon_group_idx -> {'ext': pts | None, 'holes': [pts, ...]}
        poly_groups: dict[int, dict] = {}

        for (pts, closed), kind, group in zip(
            self._edit_shapes, self._edit_shape_kinds, self._edit_polygon_group
        ):
            min_pts = 3 if closed else 2
            match kind:
                case 'line' | 'ring':
                    if len(pts) >= min_pts:
                        built.append(G.line(pts, closed=closed))
                case 'polygon_ext':
                    poly_groups.setdefault(group, {'ext': None, 'holes': []})
                    if len(pts) >= 3:
                        poly_groups[group]['ext'] = pts
                case 'polygon_hole':
                    poly_groups.setdefault(group, {'ext': None, 'holes': []})
                    if len(pts) >= 3:
                        poly_groups[group]['holes'].append(pts)

        for g_idx in sorted(poly_groups):
            data = poly_groups[g_idx]
            if data['ext'] is not None:
                built.append(G.polygon(data['ext'], holes=data['holes'] or None))

        if not built:
            return
        match self._edit_wrapper:
            case 'single':
                self._edit_item.geometry = built[0]
            case 'multi_line':
                self._edit_item.geometry = G.multi_line(built)
            case 'group':
                self._edit_item.geometry = G.group(*(built + self._edit_other_shapes))

    def _find_near_edit_point(self, world_pos: Vector2, screen_pos: Vector2) -> int | None:
        """Return the flat index of the nearest vertex within SNAP_THRESHOLD pixels, or None."""
        p0 = self.view.camera.screen_to_world_point(Vector2(0, 0))
        p1 = self.view.camera.screen_to_world_point(Vector2(1, 0))
        threshold_sq = float((p0 - p1).squared_length) * self.SNAP_THRESHOLD ** 2

        best_idx = None
        best_sq = float('inf')
        for i, pt in enumerate(self._flat_edit_points()):
            diff = pt - world_pos
            sq = float(diff[0] ** 2 + diff[1] ** 2)
            if sq < threshold_sq and sq < best_sq:
                best_sq = sq
                best_idx = i
        return best_idx

    def _find_near_edit_segment(
        self, world_pos: Vector2, screen_pos: Vector2,
    ) -> tuple[int | None, int | None, Vector2 | None]:
        """Return (shape_idx, local_seg_idx, insert_world_pos) for the nearest segment.

        Segments never cross sub-shape boundaries.
        """
        best_dist = float(self.SEGMENT_THRESHOLD)
        best_shape: int | None = None
        best_seg: int | None = None
        best_pos: Vector2 | None = None

        for shape_idx, (pts, closed) in enumerate(self._edit_shapes):
            n = len(pts)
            if n < 2:
                continue
            seg_range = range(n) if closed else range(n - 1)
            for i in seg_range:
                a = pts[i]
                b = pts[(i + 1) % n]
                a_s = self.view.camera.world_to_screen_point(Vector3.from_vector2(a))
                b_s = self.view.camera.world_to_screen_point(Vector3.from_vector2(b))
                dist, t = self._point_segment_dist(screen_pos, a_s, b_s)
                if dist < best_dist:
                    best_dist = dist
                    best_shape = shape_idx
                    best_seg = i
                    best_pos = a + (b - a) * t

        return best_shape, best_seg, best_pos

    @staticmethod
    def _point_segment_dist(p: Vector2, a: Vector2, b: Vector2) -> tuple[float, float]:
        """Return (distance, t∈[0,1]) from point p to segment a–b (all in same space)."""
        ab = b - a
        len_sq = float(ab[0] ** 2 + ab[1] ** 2)
        if len_sq < 1e-10:
            d = p - a
            return float((d[0] ** 2 + d[1] ** 2) ** 0.5), 0.0
        ap = p - a
        t = max(0.0, min(1.0, float(ap[0] * ab[0] + ap[1] * ab[1]) / len_sq))
        closest = a + ab * t
        d = p - closest
        return float((d[0] ** 2 + d[1] ** 2) ** 0.5), t

    # ------------------------------------------------------------------
    # Edit mode — visuals
    # ------------------------------------------------------------------

    def _update_edit_controls(self):
        """Rebuild vertex circles and the segment-insert preview dot."""
        assert self._canvas is not None

        for ctrl in self._point_controls:
            self._canvas.remove_item(ctrl)
        self._point_controls = []

        if self._segment_marker is not None:
            self._canvas.remove_item(self._segment_marker)
            self._segment_marker = None

        for i, pt in enumerate(self._flat_edit_points()):
            color = Vector4(1, 1, 0, 1) if i == self._hovered_point_idx else Vector4(1, 0, 0, 1)
            ctrl = Circle(
                self.view.ctx,
                radius=8,
                position=pt,
                screen_space_size=True,
                fill_color=color,
                edge_color=color,
            )
            self._point_controls.append(ctrl)
            self._canvas.add_item(ctrl)

        if self._hovered_segment is not None and self._segment_insert_pos is not None:
            self._segment_marker = Circle(
                self.view.ctx,
                radius=6,
                position=self._segment_insert_pos,
                screen_space_size=True,
                fill_color=Vector4(0, 1, 0.5, 1),
                edge_color=Vector4(0, 1, 0.5, 1),
            )
            self._canvas.add_item(self._segment_marker)

    def _fast_update_edit_positions(self):
        """Cheap path: just move existing circles without rebuilding (used while dragging)."""
        for ctrl, pt in zip(self._point_controls, self._flat_edit_points()):
            ctrl.position = pt

    # ------------------------------------------------------------------
    # Edit mode — event filter
    # ------------------------------------------------------------------

    def _edit_event_filter(self, widget: QWidget, event: QEvent) -> bool:
        mouse_event = cast(QMouseEvent, event)

        # Double-click dissolves a vertex
        if event.type() == QEvent.Type.MouseButtonDblClick:
            if mouse_event.button() & Qt.MouseButton.LeftButton:
                screen_pos = vector2(mouse_event.position())
                world_pos = self.view.camera.screen_to_world_point(screen_pos).xy
                near_idx = self._find_near_edit_point(world_pos, screen_pos)
                if near_idx is not None:
                    self._dissolve_point(near_idx)
                return True

        elif (event.type() == QEvent.Type.MouseButtonPress and
              mouse_event.button() & Qt.MouseButton.LeftButton):
            screen_pos = vector2(mouse_event.position())
            if not (mouse_event.modifiers() & Qt.KeyboardModifier.AltModifier):
                snap = self.view.snap_point(screen_pos, SnapFlags.GRID_EDGES | SnapFlags.GRID_CORNERS)
                screen_pos = snap.point
            world_pos = self.view.camera.screen_to_world_point(screen_pos).xy

            near_idx = self._find_near_edit_point(world_pos, screen_pos)
            if near_idx is not None:
                self._drag_idx = near_idx
            else:
                shape_idx, seg_idx, insert_pos = self._find_near_edit_segment(world_pos, screen_pos)
                if shape_idx is not None and seg_idx is not None and insert_pos is not None:
                    self._edit_shapes[shape_idx][0].insert(seg_idx + 1, insert_pos)
                    self._drag_idx = self._flat_offset(shape_idx) + seg_idx + 1
                    self._hovered_point_idx = None
                    self._hovered_segment = None
                    self._segment_insert_pos = None
                    self._apply_edit_geometry()
                    self._update_edit_controls()

            self.view.update()
            return True

        elif (event.type() == QEvent.Type.MouseButtonRelease and
              mouse_event.button() & Qt.MouseButton.LeftButton):
            self._drag_idx = None
            self.view.update()
            return True

        elif (event.type() == QEvent.Type.MouseButtonPress and
              mouse_event.button() & Qt.MouseButton.RightButton):
            self.commit()
            return True

        elif event.type() == QEvent.Type.MouseMove:
            screen_pos = vector2(mouse_event.position())
            if not (mouse_event.modifiers() & Qt.KeyboardModifier.AltModifier):
                snap = self.view.snap_point(screen_pos, SnapFlags.GRID_EDGES | SnapFlags.GRID_CORNERS)
                screen_pos = snap.point
                self._marker.visible = not snap.snapped
                self._snap_marker.visible = snap.snapped
            else:
                self._marker.visible = True
                self._snap_marker.visible = False

            world_pos = self.view.camera.screen_to_world_point(screen_pos).xy
            self._marker.position = world_pos
            self._snap_marker.position = world_pos

            if self._drag_idx is not None:
                shape_idx, local_idx = self._shape_and_local_idx(self._drag_idx)
                self._edit_shapes[shape_idx][0][local_idx] = world_pos
                self._apply_edit_geometry()
                self._fast_update_edit_positions()
            else:
                old_hpt = self._hovered_point_idx
                old_hseg = self._hovered_segment

                self._hovered_point_idx = self._find_near_edit_point(world_pos, screen_pos)
                if self._hovered_point_idx is not None:
                    self._hovered_segment = None
                    self._segment_insert_pos = None
                    self.view.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
                else:
                    shape_idx, seg_idx, insert_pos = self._find_near_edit_segment(world_pos, screen_pos)
                    self._hovered_segment = (shape_idx, seg_idx) if shape_idx is not None else None
                    self._segment_insert_pos = insert_pos
                    if shape_idx is not None:
                        self.view.setCursor(QCursor(Qt.CursorShape.CrossCursor))
                    else:
                        self.view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

                if old_hpt != self._hovered_point_idx or old_hseg != self._hovered_segment:
                    self._update_edit_controls()

            self.view.coordinateChanged.emit(world_pos)
            self.view.update()
            return True

        elif event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            if key_event.key() == Qt.Key.Key_Escape:
                self.cancel()
                return True
            elif key_event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
                self.commit()
                return True
            elif key_event.key() in [Qt.Key.Key_Delete, Qt.Key.Key_Backspace]:
                if self._hovered_point_idx is not None:
                    self._dissolve_point(self._hovered_point_idx)
                return True

        return False

    def _dissolve_point(self, flat_idx: int):
        """Remove vertex at flat_idx if the resulting sub-shape would remain valid."""
        shape_idx, local_idx = self._shape_and_local_idx(flat_idx)
        pts, closed = self._edit_shapes[shape_idx]
        if len(pts) <= (3 if closed else 2):
            return
        del pts[local_idx]
        self._drag_idx = None
        self._hovered_point_idx = None
        self._apply_edit_geometry()
        self._update_edit_controls()
        self.view.update()

    # ------------------------------------------------------------------
    # Create mode — event filter (original behaviour, unchanged)
    # ------------------------------------------------------------------

    def _create_event_filter(self, widget: QWidget, event: QEvent) -> bool:
        mouse_event = cast(QMouseEvent, event)

        if (event.type() == QEvent.Type.MouseButtonPress and
                mouse_event.button() & Qt.MouseButton.LeftButton):
            screen_point = self._snap_point(vector2(mouse_event.position())).point

            if not self._drawing:
                world_point = self.view.camera.screen_to_world_point(screen_point).xy
                self._points.append(world_point)
                self._points.append(world_point)
                self._last_point = screen_point

                self._polyline = self._make_polyline()
                self.view.add_item(self._polyline)

                self._point_controls = [self._make_point_control(world_point)]
                assert self._canvas is not None
                self._canvas.add_item(self._point_controls[-1])

                self._drawing = True
            else:
                if mouse_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                    d = screen_point - self._last_point
                    if abs(d.x) > abs(d.y):
                        screen_point = Vector2(screen_point.x, self._last_point.y)
                    else:
                        screen_point = Vector2(self._last_point.x, screen_point.y)

                world_point = self.view.camera.screen_to_world_point(screen_point).xy

                self._points[-1] = world_point
                self._point_controls.append(
                    self._make_point_control(world_point)
                )
                assert self._canvas is not None
                self._canvas.add_item(self._point_controls[-1])
                self._points.append(world_point)
                self._last_point = screen_point

                if (self._points[-1] - self._points[0]).length < 0.001:
                    self.commit(closed=True)

            self.view.update()
            return True

        elif (event.type() == QEvent.Type.MouseButtonPress and
                mouse_event.button() & Qt.MouseButton.RightButton):
            self.commit()
            return True

        elif event.type() == QEvent.Type.MouseMove:
            assert self._marker is not None
            assert self._snap_marker is not None

            screen_point = vector2(mouse_event.position())
            if not self._drawing:
                p1 = self.view.camera.screen_to_world_point(Vector2(0, 0))
                p2 = self.view.camera.screen_to_world_point(Vector2(1, 0))
                squared_trigger_distance = (p1 - p2).squared_length * 100

                world_point = self.view.camera.screen_to_world_point(screen_point).xy
                for point in self._points:
                    if (point - world_point).squared_length < squared_trigger_distance:
                        self.view.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
                        break
                else:
                    self.view.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

            if mouse_event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                d = screen_point - self._last_point
                if abs(d.x) > abs(d.y):
                    screen_point = Vector2(screen_point.x, self._last_point.y)
                else:
                    screen_point = Vector2(self._last_point.x, screen_point.y)

            if not (mouse_event.modifiers() & Qt.KeyboardModifier.AltModifier):
                snap_result = self._snap_point(screen_point)
                screen_point = snap_result.point

                self._marker.visible = not snap_result.snapped
                self._snap_marker.visible = snap_result.snapped

            world_point = self.view.camera.screen_to_world_point(screen_point).xy

            self._marker.position = world_point
            self._snap_marker.position = world_point

            if self._drawing:
                self._points[-1] = world_point

                if self._polyline:
                    self.view.remove_item(self._polyline)

                self._polyline = self._make_polyline()
                self.view.add_item(self._polyline)

            self.view.coordinateChanged.emit(world_point)
            self.view.update()
            return True

        elif event.type() == QEvent.Type.KeyPress:
            key_event = cast(QKeyEvent, event)
            if key_event.key() == Qt.Key.Key_Escape:
                if self._drawing:
                    self.cancel()
                else:
                    self.deactivate()
                return True
            elif key_event.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
                self.commit()
                return True
            elif key_event.key() == Qt.Key.Key_Backspace and self._drawing:
                if len(self._points) <= 2:
                    self.cancel()
                else:
                    del self._points[-2]
                    point_control = self._point_controls[-1]
                    assert self._canvas is not None
                    self._canvas.remove_item(point_control)
                    del self._point_controls[-1]

                    if self._polyline:
                        self.view.remove_item(self._polyline)

                    self._polyline = self._make_polyline()
                    self.view.add_item(self._polyline)

                    self.view.update()

            if key_event.modifiers() & Qt.KeyboardModifier.AltModifier:
                if self._marker is not None:
                    self._marker.visible = True
                if self._snap_marker is not None:
                    self._snap_marker.visible = False

        return False

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _snap_point(self, point: Vector2) -> SnapResult:
        if self._points:
            world_point = self.view.camera.screen_to_world_point(point).xy
            world_closest = min(self._points[:-1], key=lambda p: float((p - world_point).length))
            screen_closest = self.view.camera.world_to_screen_point(Vector3.from_vector2(world_closest))
            if (screen_closest - point).length < self.SNAP_THRESHOLD:
                return SnapResult(screen_closest, snapped=True)

        return self.view.snap_point(point, SnapFlags.GRID_EDGES | SnapFlags.GRID_CORNERS)

    def _make_polyline(self) -> Node3D:
        assert self.view.ctx is not None
        line = Line2D(context=self.view.ctx, points=self._points, closed=False)
        line.priority = 1
        return line

    def _make_marker(self) -> CanvasItem:
        marker = VerticalCross(
            self.view.ctx,
            size=Vector2(40, 40),
            screen_space_size=True,
            screen_space_edge_width=True,
            fill_color=Vector4(1, 1, 1, 1),
            edge_color=Vector4(1, 1, 1, 1),
            edge_width=2,
        )
        marker.priority = 10
        return marker

    def _make_snap_marker(self) -> CanvasItem:
        marker = DiagonalCross(
            self.view.ctx,
            size=Vector2(30, 30),
            screen_space_size=True,
            screen_space_edge_width=True,
            fill_color=Vector4(1, 1, 1, 1),
            edge_width=2,
        )
        marker.priority = 10
        return marker

    def _make_point_control(self, point: Vector2) -> Circle:
        return Circle(
            self.view.ctx,
            radius=8,
            position=point,
            screen_space_size=True,
            fill_color=Vector4(1, 0, 0, 1),
            edge_color=Vector4(1, 0, 0, 1),
        )

    def _create_polyline(self, points: Sequence[Vector2], closed: bool = False):
        GLOBALS.APP.undo_stack.push(CreatePolylineCommand(points=points, closed=closed))
