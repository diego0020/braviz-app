

from __future__ import division, print_function

from braviz.utilities import configure_logger_from_conf
import braviz
from braviz.readAndFilter import BravizAutoReader, config_file

import vtk

win = vtk.vtkRenderWindow()
iren = vtk.vtkRenderWindowInteractor()
ren = vtk.vtkRenderer()

win.AddRenderer(ren)
iren.SetRenderWindow(win)

iren.Initialize()

sphere_w = vtk.vtkSphereWidget2()
sphere_w.SetInteractor(iren)
sphere_w.CreateDefaultRepresentation()

iren.Start()