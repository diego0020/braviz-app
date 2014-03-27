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

import readAndFilter
import visualization
import interaction

if __name__ == "__main__":
    viewer = visualization.simpleVtkViewer()
    reader = readAndFilter.kmc40AutoReader()
    get_conf = interaction.get_config()