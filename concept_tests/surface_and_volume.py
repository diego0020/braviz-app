'''
Created on 27/08/2013

@author: da.angulo39
'''
import vtk

import braviz
from braviz import _test_arrow


r=braviz.readAndFilter.BravizAutoReader()
struct=r.get('Model','093',name='Left-Caudate')

massProperty=vtk.vtkMassProperties()
triangleFilter=vtk.vtkTriangleFilter()
triangleFilter.SetInputData(struct)
massProperty.SetInputConnection(triangleFilter.GetOutputPort())
massProperty.Update()
surface=massProperty.GetSurfaceArea()
volume=massProperty.GetVolume()

print volume
print surface

v= simpleVtkViewer()
actor=v.addPolyData(struct)
balloon=vtk.vtkBalloonWidget()
balloon_rep=vtk.vtkBalloonRepresentation()
balloon.SetRepresentation(balloon_rep)
balloon.SetInteractor(v.iren)
balloon.On()
balloon.AddBalloon(actor,"Volume = %.2f mm3 \nSurface Area = %.2f mm2 "%(volume,surface))
v.start()