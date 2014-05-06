from __future__ import division

__author__ = 'Diego'

import os
import nibabel as nib
from scipy import ndimage
import braviz

os.chdir(r"C:\Users\Diego\Documents\prueba_free_surf_400")

skull = nib.load("skull.nii.gz")
data = skull.get_data()
#===============

#data2 = data

data2 = ndimage.gaussian_filter(data,3)
data2 = ndimage
#=================
viewer = braviz.visualization.simpleVtkViewer()
vtk_image = braviz.readAndFilter.numpy2vtk_img(data2)
plane_widget = viewer.addImg(vtk_image)
plane_widget.SetResliceInterpolateToNearestNeighbour()
plane_widget.set_orientation(0)
viewer.start()
plane_widget.set_orientation(1)
viewer.start()
plane_widget.set_orientation(2)
viewer.start()