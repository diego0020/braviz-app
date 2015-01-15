
__author__ = 'Diego'

import os
import subprocess

import PyQt4.uic

import braviz.utilities


def update_guis():
    """
    Updates python gui files in the ``braviz.interaction.qt_guis`` directory

    This function generates python files from .ui files in the mentioned folder, as well as
    the ``resources_rc.py`` file from ``resources.qrc`` qt resources file.
    """
    this_dir = os.path.dirname(__file__)
    qt_gui_dir = os.path.join(this_dir, 'qt_guis')

    PyQt4.uic.compileUiDir(qt_gui_dir)

    # pyrcc4 should be in the path


    try:
        with braviz.utilities.working_directory(os.path.join(os.path.dirname(__file__), "qt_guis")):

                subprocess.Popen(["pyrcc4", "-o", "resources_rc.py", "resources.qrc"])
    except OSError:
        print "couldn't generate resources"

if __name__ == "__main__":
    update_guis()