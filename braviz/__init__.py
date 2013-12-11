"""Braviz is a library for facilitating integrated visual analysis of brain data
The readAndFilter module contains several functions for reading different brain data formats and tabular data
The visualization module contains functions for displaying physical structures and charts of scalar values in the screen
The interaction module contains functions for performing common interactions with the data"""
print 'braviz v0.05'

import vtk
vtk_mayor=int(vtk.VTK_VERSION.split('.')[0])
if not vtk_mayor >= 6:
    print "WARNING: This package requires VTK version 6 or greater, please update your VTK install"
    raise UserWarning("This package requires VTK version 6 or greater, please update your VTK install")
#keep space clean
__vtk__output_window=vtk.vtkOutputWindow()
if isinstance(__vtk__output_window,vtk.vtkWin32OutputWindow):
    import os
    __fow=vtk.vtkFileOutputWindow()
    __fow.SetInstance(__fow)
    #__fow.GlobalWarningDisplayOff()
    __error_file=os.path.join(os.path.dirname(os.path.realpath(__file__)),'vtkError.log')
    __fow.SetFileName(__error_file)
    #__fow.AppendOn()
    __fow.FlushOn();
    print "vtk errors going to %s"%os.path.realpath(__error_file)
del vtk_mayor
del vtk
import readAndFilter
import visualization
import interaction