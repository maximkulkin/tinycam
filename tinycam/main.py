import sys

from PySide6 import QtGui
import PySide6.QtAsyncio as QtAsyncio

from tinycam.globals import GLOBALS
from tinycam.application import CncApplication
from tinycam.ui.main_window import CncMainWindow
# from tinycam.project import GerberItem, ExcellonItem

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

async_loop = QtAsyncio.QAsyncioEventLoop(GLOBALS.APP)
async_loop.run_forever()  # internally calls app.exec()
