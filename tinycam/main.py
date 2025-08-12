import sys

import asyncio
from PySide6 import QtGui
from qasync import QEventLoop

import tinycam.icons_rc
from tinycam.application import CncApplication
from tinycam.globals import GLOBALS
from tinycam.project import GerberItem, ExcellonItem
from tinycam.ui.main_window import CncMainWindow


GLOBALS.APP = CncApplication(sys.argv)
# GLOBALS.APP.project.items.append(GerberItem.from_file('sample.gbr'))
# GLOBALS.APP.project.items.append(ExcellonItem.from_file('sample.drl'))

fmt = QtGui.QSurfaceFormat()
fmt.setVersion(4, 1)
fmt.setProfile(QtGui.QSurfaceFormat.OpenGLContextProfile.CoreProfile)
fmt.setDepthBufferSize(24)
QtGui.QSurfaceFormat.setDefaultFormat(fmt)

main_window = CncMainWindow()
main_window.show()

loop = QEventLoop(GLOBALS.APP)
asyncio.set_event_loop(loop)

with loop:
    loop.run_forever()
