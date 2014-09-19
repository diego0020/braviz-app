from __future__ import division
import braviz
import vtk


__author__ = 'Diego'

reader = braviz.readAndFilter.BravizAutoReader()

img1_p = reader.get("MRI",119,format="vtk")
img2_p = reader.get("FA",119,format="vtk")


cast1 = vtk.vtkImageCast()
cast1.SetInputData(img1_p)
cast1.SetOutputScalarTypeToFloat()
cast1.Update()

img1 = cast1.GetOutput()

stats1 = vtk.vtkImageHistogramStatistics()
stats1.SetInputData(img1)
stats1.SetAutoRangePercentiles(5,95)
stats1.Update()
range1 = stats1.GetAutoRange()

cast = vtk.vtkImageCast()
cast.SetInputData(img2_p)
cast.SetOutputScalarTypeToFloat()
cast.Update()

img2_p1 = cast.GetOutput()



reslice = vtk.vtkImageReslice()
reslice.SetInterpolationModeToCubic()
reslice.SetOutputSpacing(img1.GetSpacing())
reslice.SetOutputOrigin(img1.GetOrigin())
reslice.SetOutputExtent(img1.GetExtent())
reslice.SetInputData(img2_p1)

reslice.Update()

img2_p2 = reslice.GetOutput()

stats2 = vtk.vtkImageHistogramStatistics()
stats2.SetInputData(img2_p2)
stats2.SetAutoRangePercentiles(5,99)
stats2.Update()
range2 = stats2.GetAutoRange()
range2 = (stats2.GetMinimum(),stats2.GetMaximum())

scale = (range1[1]-range1[0])/(range2[1]-range2[0])
offset = range1[0]/scale - range2[0]

shift = vtk.vtkImageShiftScale()
shift.SetInputData(img2_p2)
shift.SetShift(offset)
shift.SetScale(scale)
shift.Update()
img2 = shift.GetOutput()

stats3 = vtk.vtkImageHistogramStatistics()
stats3.SetInputData(img2)
stats3.SetAutoRangePercentiles(5,99)
stats3.Update()
range3 = stats3.GetAutoRange()

check = vtk.vtkImageCheckerboard()

check.SetInput1Data(img1)
check.SetInput2Data(img2)
check.SetNumberOfDivisions(1,5,5)

check.Update()
out = check.GetOutput()

viewer = braviz.visualization.simpleVtkViewer()
viewer.addImg(out)
#viewer.addImg(img2)


viewer.start()