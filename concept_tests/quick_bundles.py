from braviz import _test_arrow

__author__ = 'Diego'

import dipy
import braviz
import numpy as np
reader = braviz.readAndFilter.BravizAutoReader()
subject = "093" if braviz.readAndFilter.PROJECT == "kmc40" else "119"
tracts = reader.get("FIBERS",subject)
tracts.GetNumberOfLines()
from braviz.readAndFilter.filter_fibers import extract_poly_data_subset

def line_to_array(line):
    n_pts = line.GetNumberOfPoints()
    pts = line.GetPoints()
    array = np.zeros((n_pts,3))
    for i in xrange(n_pts):
        array[i,:] = pts.GetPoint(i)
    return array

n_lines = tracts.GetNumberOfCells()
np_tracts = [line_to_array(tracts.GetCell(i)) for i in xrange(n_lines)]

import dipy.segment.quickbundles

#====================================================================
bundles = dipy.segment.quickbundles.QuickBundles(np_tracts,30,25)
#====================================================================
print bundles.total_clusters
partitions = bundles.partitions()
in_cluster = bundles.label2tracksids(0)
bundles.remove_small_clusters(5)

dat = tracts.GetPointData()
dat.RemoveArray(0)
import vtk
new_array = vtk.vtkIntArray()
new_array.SetNumberOfTuples(n_lines)
new_array.SetNumberOfComponents(1)
for i in xrange(n_lines):
    new_array.SetComponent(i,0,bundles.total_clusters+1)

permutation = np.random.permutation(bundles.total_clusters)

for i in xrange(bundles.total_clusters):
    label = permutation[i]
    for j in bundles.label2tracksids(i):
        new_array.SetComponent(j,0,label)

new_array.SetName("clusters")
tracts.GetCellData().SetScalars(new_array)
v = simpleVtkViewer()
ac = v.addPolyData(tracts)
mp = ac.GetMapper()
mp.SetScalarModeToUseCellData()
lut = vtk.vtkColorTransferFunction()
lut.SetColorSpaceToHSV()

lut.AdjustRange((0,bundles.total_clusters))
lut.HSVWrapOff()

lut.AddHSVSegment(0,        0.0,   1.0, 0.8,
  bundles.total_clusters//3,0.33 ,  1.0, 0.8)

lut.AddHSVSegment(bundles.total_clusters//3,        0.33,   1.0, 0.8,
  bundles.total_clusters//3*2                      ,0.66 ,  1.0, 0.8)

lut.AddHSVSegment(bundles.total_clusters//3*2,        0.66,   1.0, 0.8,
  bundles.total_clusters                             ,0.99 ,  1.0, 0.8)
c=[0,0,0]
# for i in xrange(bundles.total_clusters):
#     lut.GetColor(i,c)
#     print c
mp.SetLookupTable(lut)

context_img = reader.get("MRI",subject,format="vtk")
image_widget = v.addImg(context_img)
v.start()

for i in xrange(bundles.total_clusters):
    fibs2 = extract_poly_data_subset(tracts,bundles.label2tracksids(i))
    mp.SetInputData(fibs2)
    v.start()

