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


"""Braviz is a library for facilitating integrated visual analysis of brain data
The readAndFilter module contains several functions for reading different brain data formats
and tabular data
The visualization module contains functions for displaying physical structures and charts of
scalar values in the screen
The interaction module contains functions for performing common interactions with the data
and creating graphical interfaces"""
#'braviz v2.01'

from __future__ import print_function
import platform
import logging


import vtk


vtk_mayor = int(vtk.VTK_VERSION.split('.')[0])
if not vtk_mayor >= 6:
    print("WARNING: This package requires VTK version 6 or greater, please update your VTK install")
    raise UserWarning(
        "This package requires VTK version 6 or greater, please update your VTK install")
# keep space clean

if platform.system() == 'Windows':
    import os
    __vtk__output_window = vtk.vtkOutputWindow()
    if isinstance(__vtk__output_window, vtk.vtkWin32OutputWindow):
        __fow = vtk.vtkFileOutputWindow()
        __fow.SetInstance(__fow)
        #__fow.GlobalWarningDisplayOff()
        __error_file = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "logs", 'vtkError.log')
        __fow.SetFileName(__error_file)
        #__fow.AppendOn()
        __fow.FlushOn()
        log = logging.getLogger(__name__)
        log.info("vtk errors going to %s", os.path.realpath(__error_file))


if __name__ == "__main__":
    import os
    from braviz.utilities import configure_logger_from_conf
    from braviz import readAndFilter, interaction, visualization
    from braviz.visualization.simple_vtk import SimpleVtkViewer
    from braviz.readAndFilter.config_file import get_apps_config
    configure_logger_from_conf(__name__)
    viewer = SimpleVtkViewer()
    reader = readAndFilter.BravizAutoReader()
    get_conf = get_apps_config()
