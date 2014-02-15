__author__ = 'Diego'

import PyQt4.uic
import os

this_dir=os.path.dirname(__file__)
qt_gui_dir=os.path.join(this_dir,'qt_guis')

PyQt4.uic.compileUiDir(qt_gui_dir)
