from collections.abc import Callable
from dataclasses import dataclass
import weakref
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Qt
from tinycam.globals import GLOBALS
from typing import Optional


class TaskManager(QtCore.QObject):
    @dataclass
    class TaskInfo:
        progress: int = 0

    def __init__(self):
        super().__init__()
        self._tasks = {}
        self._statusbar = None

        self._task_label = QtWidgets.QLabel('Idle')
        self._task_label.setFixedWidth(100)
        self._task_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft |
            Qt.AlignmentFlag.AlignVCenter
        )

        self._progressbar = QtWidgets.QProgressBar()
        self._progressbar.setFixedWidth(100)
        self._progressbar.setStyleSheet(
            'QProgressBar::chunk { background-color: transparent; }'
        )

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(10, 0, 10, 0)
        layout.addWidget(self._task_label)
        layout.addWidget(self._progressbar)

        self._widget = QtWidgets.QFrame()
        self._widget.setFrameStyle(QtWidgets.QFrame.Panel)
        self._widget.setLayout(layout)
        self._widget.setSizePolicy(
            QtWidgets.QSizePolicy.Fixed,
            QtWidgets.QSizePolicy.Expanding,
        )

    @property
    def statusbar(self) -> Optional[QtWidgets.QStatusBar]:
        return self._statusbar

    @statusbar.setter
    def statusbar(self, statusbar: QtWidgets.QStatusBar):
        if self._statusbar is not None:
            self._statusbar.removeWidget(self._widget)
        self._statusbar = statusbar
        if self._statusbar is not None:
            self._statusbar.addPermanentWidget(self._widget)

    def register_task(self, task: 'Task'):
        if task in self._tasks:
            return

        task_ref = weakref.ref(task)
        task.finished.connect(lambda: self._task_finished(task_ref))
        task.progress.connect(lambda progress: self._task_progress(task_ref, progress))
        self._tasks[task] = self.TaskInfo()

    def unregister_task(self, task: 'Task'):
        if task not in self._tasks:
            return
        del self._tasks[task]
        if not self._tasks:
            self._progressbar.reset()

    def _task_finished(self, task_ref: weakref.ReferenceType):
        task = task_ref()
        if task is None:
            return
        if self._task_label.text() == task.name:
            self._task_label.setText('Idle')
        self.unregister_task(task)

    def _task_progress(self, task_ref: weakref.ReferenceType, progress: int):
        task = task_ref()
        if task is None or task not in self._tasks:
            return
        self._tasks[task].progress = progress
        if len(self._tasks) == 1:
            self._task_label.setText(task.name)
            self._progressbar.setValue(progress)


class TaskStatus:
    def __init__(self, signal):
        self._signal = signal
        self._min_value = 0
        self._max_value = 100
        self._value = 0

    @property
    def min_value(self) -> int:
        return self._min_value

    @min_value.setter
    def min_value(self, value: int):
        self._min_value = value

    @property
    def max_value(self) -> int:
        return self._max_value

    @max_value.setter
    def max_value(self, value: int):
        self._max_value = value

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, x: int):
        self._value = x
        progress = (x - self._min_value) * 100 / (self._max_value - self._min_value)
        self._signal.emit(progress)


class Task(QtCore.QThread):
    progress = QtCore.Signal(int)

    def __init__(self, name: str, f: Callable[[TaskStatus], None]):
        super().__init__()
        self._name = name
        self._f = f
        self._status = TaskStatus(self.progress)
        self.setTerminationEnabled(True)

    @property
    def name(self):
        return self._name

    @property
    def status(self):
        return self._status

    def run(self):
        self._f(self._status)


def run_task(name: str, callback: Callable[[], None] | None = None):
    def wrapper(f):
        task = Task(name, f)
        if callback is not None:
            task.finished.connect(callback)
        GLOBALS.APP.task_manager.register_task(task)
        task.start()
    return wrapper
