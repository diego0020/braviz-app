import vtk

ren_win = vtk.vtkRenderWindow()
ren = vtk.vtkRenderer()
ren_win.AddRenderer(ren)
iact = vtk.vtkRenderWindowInteractor()
iact.SetRenderWindow(ren_win)

prop1 = vtk.vtkPropAssembly()
ren.AddViewProp(prop1)
prop2 = vtk.vtkPropAssembly()
prop1.AddPart(prop2)

sphere_source = vtk.vtkSphereSource()
sphere_map = vtk.vtkPolyDataMapper()
sphere_map.SetInputConnection(sphere_source.GetOutputPort())
ac = vtk.vtkActor()
ac.SetMapper(sphere_map)
prop2.AddPart(ac)

iact.Initialize()
iact.Start()
