
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


if image_type == "FA":
    LUT = braviz.visualization.get_colorbrewer_lut(0.35,0.82,"BuGn",9,invert=False)
else:
    LUT = braviz.visualization.get_colorbrewer_lut(6e-10,11e-10,"PuBu",9,invert=False)

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


if(False):
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


    pd.SetScalars(new_array)

#cell data
if(False):
    cd = base_fibers.GetCellData()
    ncells = base_fibers.GetNumberOfCells()
    new_array = vtk.vtkDoubleArray()
    new_array.SetNumberOfTuples(ncells)
    new_array.SetNumberOfComponents(1)
    for i in xrange(ncells):
        c = base_fibers.GetCell(i)
        npts = c.GetNumberOfPoints()

        point_values = np.zeros(npts)
        for j in xrange(npts):
            p_id = c.GetPointId(j)
            coords = base_fibers.GetPoint(p_id) + (1,)
            coords = np.dot(iaffine,coords)
            coords = coords[:3]/coords[3]
            coords = coords.reshape(3, 1)
            image_val = ndimage.map_coordinates(data,coords,order=1)
            point_values[j]=image_val

        value = point_values.mean()
        new_array.SetComponent(i,0,value)

    cd.SetScalars(new_array)

#length
if(True):

    ncells = base_fibers.GetNumberOfCells()
    lengths= np.zeros(ncells-1)
    new_array = vtk.vtkDoubleArray()
    new_array.SetNumberOfTuples(ncells)
    new_array.SetNumberOfComponents(1)
    for i in xrange(ncells):
        c = base_fibers.GetCell(i)
        npts = c.GetNumberOfPoints()

        length = 0
        last_point = None
        for j in xrange(1,npts):
            p_id = c.GetPointId(j)
            coords = np.array(base_fibers.GetPoint(p_id))
            if last_point is not None:
                step = np.linalg.norm(coords-last_point)
                length += step

            last_point = coords

        value = length
        lengths[i-1]=length
        new_array.SetComponent(i,0,value)
    LUT = braviz.visualization.get_colorbrewer_lut(41,125,"YlOrBr",9,invert=False)
    cd = base_fibers.GetCellData()
    cd.SetScalars(new_array)




viewer = braviz.visualization.simpleVtkViewer()
ac = viewer.addPolyData(base_fibers,LUT)
#viewer.addImg(mri)
viewer.start()