from tinycam.globals import GLOBALS
from tinycam.project import CncIsolateJob
from tinycam.ui.options_base import CncOptionsView
from tinycam.ui.commands import UpdateItemsCommand


class CncIsolateJobOptionsView(CncOptionsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._add_label('Isolation Job')

        self._tool_diameter_edit = self._add_float_edit("Tool Diameter")
        self._tool_diameter_edit.setSingleStep(0.05)
        self._tool_diameter_edit.value_changed.connect(self._on_tool_diameter_changed)

        self._cut_depth_edit = self._add_float_edit("Cut Depth")
        self._cut_depth_edit.setSingleStep(0.05)
        self._cut_depth_edit.value_changed.connect(self._on_cut_depth_changed)

        self._pass_count_edit = self._add_int_edit("Pass Count")
        self._pass_count_edit.setMinimum(1)
        self._pass_count_edit.setMaximum(10)
        self._pass_count_edit.value_changed.connect(self._on_pass_count_changed)

        self._pass_overlap_edit = self._add_int_edit("Pass Overlap")
        self._pass_overlap_edit.setRange(0, 100)
        self._pass_overlap_edit.setSingleStep(5)
        self._pass_overlap_edit.value_changed.connect(self._on_pass_overlap_changed)

        self._cut_speed_edit = self._add_int_edit("Feed Rate")
        self._cut_speed_edit.setRange(10, 10000)
        self._cut_speed_edit.value_changed.connect(self._on_cut_speed_changed)

        self._spindle_speed_edit = self._add_int_edit("Spindle Speed")
        self._spindle_speed_edit.setRange(10, 100000)
        self._spindle_speed_edit.setSingleStep(25)
        self._spindle_speed_edit.value_changed.connect(self._on_spindle_speed_changed)

        self._travel_height_edit = self._add_float_edit("Travel Height")
        self._travel_height_edit.setSingleStep(1)
        self._travel_height_edit.value_changed.connect(self._on_travel_height_changed)

    def matches(self, items):
        return all(isinstance(item, CncIsolateJob) for item in items)

    @property
    def _item(self):
        return GLOBALS.APP.project.selectedItems[0]

    def update(self):
        self._tool_diameter_edit.setValue(self._item.tool_diameter)
        self._cut_depth_edit.setValue(self._item.cut_depth)
        self._pass_count_edit.setValue(self._item.pass_count)
        self._pass_overlap_edit.setValue(self._item.pass_overlap)
        self._cut_speed_edit.setValue(self._item.cut_speed)
        self._spindle_speed_edit.setValue(self._item.spindle_speed)
        self._travel_height_edit.setValue(self._item.travel_height)

    def _on_tool_diameter_changed(self):
        GLOBALS.APP.undo_stack.push(
            UpdateItemsCommand([self._item], {
                'tool_diameter': self._tool_diameter_edit.value(),
            })
        )

    def _on_cut_depth_changed(self):
        GLOBALS.APP.undo_stack.push(
            UpdateItemsCommand([self._item], {
                'cut_depth': self._cut_depth_edit.value(),
            })
        )

    def _on_pass_count_changed(self):
        GLOBALS.APP.undo_stack.push(
            UpdateItemsCommand([self._item], {
                'pass_count': self._pass_count_edit.value(),
            })
        )
        self._pass_overlap_edit.enabled = (self._item.pass_count > 1)

    def _on_pass_overlap_changed(self):
        GLOBALS.APP.undo_stack.push(
            UpdateItemsCommand([self._item], {
                'pass_overlap': self._pass_overlap_edit.value(),
            })
        )

    def _on_cut_speed_changed(self):
        GLOBALS.APP.undo_stack.push(
            UpdateItemsCommand([self._item], {
                'cut_speed': self._cut_speed_edit.value(),
            })
        )

    def _on_spindle_speed_changed(self):
        GLOBALS.APP.undo_stack.push(
            UpdateItemsCommand([self._item], {
                'spindle_speed': self._spindle_speed_edit.value(),
            })
        )

    def _on_travel_height_changed(self):
        GLOBALS.APP.undo_stack.push(
            UpdateItemsCommand([self._item], {
                'travel_height': self._travel_height_edit.value(),
            })
        )
