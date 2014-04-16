from __future__ import division
__author__ = 'Diego'

import braviz
import vtk
import numpy as np
from scipy import ndimage

subj = "144"
image_type = "FA"
#image_type = "MD"
reader = braviz.readAndFilter.kmc40AutoReader()

base_fibers = reader.get("fibers",subj)
image_nii = reader.get(image_type,subj,space="world")
mri = reader.get("MRI",subj,space="world",format = "VTK")

affine = image_nii.get_affine()
iaffine = np.linalg.inv(affine)
data = image_nii.get_data()

#update scalars
#remove colors array
pd = base_fibers.GetPointData()
pd.RemoveArray(0)

npoints = base_fibers.GetNumberOfPoints()
new_array = vtk.vtkDoubleArray()
new_array.SetNumberOfTuples(npoints)
new_array.SetNumberOfComponents(1)

for i in xrange(npoints):
    coords = base_fibers.GetPoint(i) + (1,)
    coords = np.dot(iaffine,coords)
    coords = coords[:3]/coords[3]
    coords = coords.reshape(3, 1)
    image_val = ndimage.map_coordinates(data,coords,order=1)
    new_array.SetComponent(i,0,image_val)

if image_type == "FA":
    LUT = braviz.visualization.get_colorbrewer_lut(0.35,0.82,"BuGn",9,invert=False)
else:
    LUT = braviz.visualization.get_colorbrewer_lut(6e-10,11e-10,"PuBu",9,invert=False)
pd.SetScalars(new_array)
viewer = braviz.visualization.simpleVtkViewer()
ac = viewer.addPolyData(base_fibers,LUT)
#viewer.addImg(mri)
viewer.start()