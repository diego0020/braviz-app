import vtk

renWin = vtk.vtkRenderWindow()
iren = vtk.vtkRenderWindowInteractor()
ren = vtk.vtkRenderer()

iren.SetRenderWindow(renWin)
renWin.AddRenderer(ren)
iren.Initialize()
iren.Start()
