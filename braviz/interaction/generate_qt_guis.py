__author__ = 'Diego'

import os
import subprocess

import PyQt4.uic

import braviz.utilities


this_dir=os.path.dirname(__file__)
qt_gui_dir=os.path.join(this_dir,'qt_guis')

PyQt4.uic.compileUiDir(qt_gui_dir)

pyrcc4=r"C:\Users\Diego\Programas\vtk\PyQt4-install\pyrcc4.exe"

try:
    with braviz.utilities.working_directory(os.path.dirname(__file__)):
        subprocess.call(' '.join([pyrcc4,"-o resources_rc.py","resources.qrc"]))
except OSError:
    print "couldn't generate resources"
