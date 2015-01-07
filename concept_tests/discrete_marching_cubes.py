import vtk

import braviz
from braviz import _test_arrow


__author__ = 'Diego'


#load image
reader=braviz.readAndFilter.BravizAutoReader()
viewer= simpleVtkViewer()

aparc=reader.get('APARC','310',format='vtk')
aparc_lut=reader.get('APARC','310',lut=True)

img=viewer.addImg(aparc)
img.SetLookupTable(aparc_lut)
img.SetPlaneOrientationToZAxes()
img.SetResliceInterpolateToNearestNeighbour()
img.SetSliceIndex(102)
viewer.start()

close=vtk.vtkImageOpenClose3D()
close.SetKernelSize(9,9,9)
close.SetCloseValue(17)
close.SetOpenValue(10)
close.SetInputData(aparc)
close.Update()
aparc2=close.GetOutput()
img.SetInputData(aparc2)
viewer.start(0)
#img.Off()
#discrete marching cubes
discrete_cubes=vtk.vtkDiscreteMarchingCubes()
discrete_cubes.SetInputData(aparc2)
contours=range(11,21)
for i,c in enumerate(contours):
    discrete_cubes.SetValue(i,c)

discrete_cubes.Update()
#sync filter
out=discrete_cubes.GetOutput()
viewer.addPolyData(out,aparc_lut)
viewer.start(0)

viewer.clear_poly_data()
sync=True
if sync is True:
    smoother=vtk.vtkWindowedSincPolyDataFilter()
    smoother.SetInputConnection(discrete_cubes.GetOutputPort())

    smoother.NormalizeCoordinatesOn()
    smoother.SetNumberOfIterations(20)
    smoother.SetBoundarySmoothing(0)
    smoother.SetFeatureEdgeSmoothing(0)
    smoother.SetPassBand(0.001)
else:
    smoother = vtk.vtkSmoothPolyDataFilter()
    smoother.SetInputConnection(discrete_cubes.GetOutputPort())

    smoother.SetNumberOfIterations(200)
    smoother.SetBoundarySmoothing(0)
    smoother.SetFeatureEdgeSmoothing(0)
    smoother.SetConvergence(0.001)

smoother.Update()
out2=smoother.GetOutput()
viewer.addPolyData(out2,aparc_lut)
viewer.start(0)