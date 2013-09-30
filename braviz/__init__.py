print 'braviz v0.05'

import vtk
vtk_mayor=int(vtk.VTK_VERSION.split('.')[0])
if not vtk_mayor >= 6:
    print "WARNING: This package requires VTK version 6 or greater, please update your VTK install"
    raise UserWarning("This package requires VTK version 6 or greater, please update your VTK install")
#keep space clean
del vtk_mayor
del vtk
import readAndFilter
import visualization
import interaction