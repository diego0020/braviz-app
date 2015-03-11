##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


__author__ = 'Diego'

from __future__ import print_function
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

            subprocess.Popen(
                ["pyrcc4", "-o", "resources_rc.py", "resources.qrc"])
    except OSError:
        print("couldn't generate resources")

if __name__ == "__main__":
    update_guis()
