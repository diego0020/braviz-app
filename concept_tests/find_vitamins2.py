from __future__ import division

__author__ = 'Diego'

import os
import nibabel as nib
from scipy import ndimage
import braviz
import numpy as np

os.chdir(r"C:\Users\Diego\Documents\prueba_free_surf_400")

skull = nib.load("skull.nii.gz")
data = skull.get_data()
#===============

#data2 = data

data2 = ndimage.gaussian_filter(data,3)
data2 = data2.astype(np.float64)

datax = ndimage.sobel(data2,0)
kernel = np.ones((11,1,1))
kernel[6:,0,0]=-1*kernel[6:,0,0]
datax = ndimage.convolve(datax,kernel)

datay = ndimage.sobel(data2,1)
kernel = np.ones((1,11,1))
kernel[0,6:,0]=-1*kernel[0,6:,0]
datay = ndimage.convolve(datay,kernel)

dataz = ndimage.sobel(data2,2)
kernel = np.ones((1,1,11))
kernel[0,0,6:]=-1*kernel[0,0,6:]
dataz = ndimage.convolve(dataz,kernel)


data2 = np.maximum(np.maximum(datax,datay),dataz)
data2 = -1*data2
#data2 = dataz

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