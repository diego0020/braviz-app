'''
Created on 22/08/2013

@author: da.angulo39
'''
import vtk
import braviz

#test='sphere'
#test='measure'
test='measure'

v=braviz.visualization.simpleVtkViewer()
r=braviz.readAndFilter.kmc40AutoReader()
struct=r.get('Model','093',name='Left-Caudate')
v.addPolyData(struct)


if test=='measure':
    dw=vtk.vtkDistanceWidget()
    dwr=vtk.vtkDistanceRepresentation3D()
    dw.SetInteractor(v.iren)
    dw.SetRepresentation(dwr)
    dw.PickingManagedOn()
    dwr.SetHandleSize(0.5)

if test=='sphere':   
    sw=vtk.vtkSphereWidget2()
    swr=vtk.vtkSphereRepresentation()
    sw.SetInteractor(v.iren)
    sw.SetRepresentation(swr)
    sw.PickingManagedOn()
    swr.PlaceWidget((0,0,0),(0,0,0))
    sw.ScalingEnabledOff()
    swr.HandleVisibilityOff() 
    swr.SetRepresentationToSurface()
    swr.SetRadius(5)
    prop=swr.GetSphereProperty()
    prop.SetColor(0.2,0.8,0.8)
    prop=swr.GetSelectedSphereProperty()
    prop.SetColor(0.9,0.1,0.1)
    sw.On()

if test=='plane':
    pw=vtk.vtkPlaneWidget()
    pw.SetInteractor(v.iren)
    pw.SetCenter(0, 0, 0)
    pw.SetPoint1(20,0,0)
    pw.SetPoint2(0,20,0)
    pw.PickingManagedOn()
    pw.SetRepresentationToSurface()
    prop=pw.GetPlaneProperty()
    prop.SetColor(0.5,0.5,0.5)
    pw.PlaceWidget()
    
    pw.On()
    
    

v.start()

if test=='measure':
    x=[0,0,0]
    dwr.GetPoint1WorldPosition(x)
    pts=vtk.vtkPoints()
    pts.SetNumberOfPoints(1)
    pts.SetPoint(0,x)
    pd=vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd2=r.transformPointsToSpace(pd,'talairach','093')
    pd2.GetPoint(0)
