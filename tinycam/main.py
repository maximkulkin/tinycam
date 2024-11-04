import sys

from PySide6 import QtGui

from tinycam.globals import GLOBALS
from tinycam.application import CncApplication
from tinycam.ui.main_window import CncMainWindow
# from tinycam.project import GerberItem, ExcellonItem

GLOBALS.APP = CncApplication(sys.argv)
# GLOBALS.APP.project.items.append(GerberItem.from_file('sample.gbr'))
# GLOBALS.APP.project.items.append(ExcellonItem.from_file('sample.drl'))

fmt = QtGui.QSurfaceFormat()
fmt.setVersion(4, 1)
fmt.setProfile(QtGui.QSurfaceFormat.CoreProfile)
fmt.setDepthBufferSize(24)
QtGui.QSurfaceFormat.setDefaultFormat(fmt)

main_window = CncMainWindow()
main_window.show()

GLOBALS.APP.exec()
