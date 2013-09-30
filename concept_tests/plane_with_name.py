import vtk

import braviz


r=braviz.readAndFilter.kmc40AutoReader()

mri=r.get('mri','093',format='vtk')
aparc=r.get('aparc','093',format='vtk')
lut=r.get('aparc','093',lut=1)
pw=braviz.visualization.persistentImagePlane()
pw.SetInputData(mri)
pw.addLabels(aparc)
pw.setLabelsLut(lut)

ren=vtk.vtkRenderer()
renWin=vtk.vtkRenderWindow()
iren=vtk.vtkRenderWindowInteractor()

renWin.AddRenderer(ren)
renWin.SetSize(600,400)

ren.SetBackground(0.5, 0.5, 0.5)

iren.SetRenderWindow(renWin)
iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

pw.SetInteractor(iren)
pw.On()

renWin.Render()
iren.Initialize()

cam1 = ren.GetActiveCamera()
cam1.Elevation(0)
cam1.Azimuth(80)
cam1.SetViewUp(0, 0, 1)
cam1.Pitch(0)
iren.Start()