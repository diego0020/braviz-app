"""Braviz is a library for facilitating integrated visual analysis of brain data
The readAndFilter module contains several functions for reading different brain data formats and tabular data
The visualization module contains functions for displaying physical structures and charts of scalar values in the screen
The interaction module contains functions for performing common interactions with the data"""
#'braviz v2.01'

import platform
import logging

import vtk


vtk_mayor=int(vtk.VTK_VERSION.split('.')[0])
if not vtk_mayor >= 6:
    print "WARNING: This package requires VTK version 6 or greater, please update your VTK install"
    raise UserWarning("This package requires VTK version 6 or greater, please update your VTK install")
#keep space clean

if platform.system() == 'Windows':
    import os
    __vtk__output_window=vtk.vtkOutputWindow()
    if isinstance(__vtk__output_window,vtk.vtkWin32OutputWindow):
        __fow=vtk.vtkFileOutputWindow()
        __fow.SetInstance(__fow)
        #__fow.GlobalWarningDisplayOff()
        __error_file=os.path.join(os.path.dirname(os.path.realpath(__file__)),"logs",'vtkError.log')
        __fow.SetFileName(__error_file)
        #__fow.AppendOn()
        __fow.FlushOn();
        log = logging.getLogger(__name__)
        log.info("vtk errors going to %s"%os.path.realpath(__error_file))



import readAndFilter
import visualization
import interaction

if __name__ == "__main__":
    viewer = visualization.simpleVtkViewer()
    reader = readAndFilter.kmc40AutoReader()
    get_conf = interaction.get_config()