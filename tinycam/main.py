import sys

from tinycam.globals import CncGlobals
from tinycam.application import CncApplication
from tinycam.ui.main_window import CncMainWindow
# from tinycam.project import GerberItem, ExcellonItem

CncGlobals.APP = CncApplication(sys.argv)
# tinycam.globals.APP.project.items.append(GerberItem.from_file('sample.gbr'))
# tinycam.globals.APP.project.items.append(ExcellonItem.from_file('sample.drl'))

main_window = CncMainWindow()
main_window.show()

CncGlobals.APP.exec()
