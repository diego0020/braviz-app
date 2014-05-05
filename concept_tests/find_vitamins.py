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

#data2 = np.ma.masked_greater(data,100)

#data2 = ndimage.gaussian_laplace(data,3)
#min_lap = np.min(data2)
#print min_lap
data2_x = ndimage.morphological_gradient(data,size=(5,0,0))
data2_x = ndimage.grey_closing(data2_x,size=(11,0,0))

data2_y = ndimage.morphological_gradient(data,size=(0,5,0))
data2_y = ndimage.grey_closing(data2_y,size=(0,11,0))

data2_z = ndimage.morphological_gradient(data,size=(0,0,5))
data2_z = ndimage.grey_closing(data2_z,size=(0,0,11))

data_l = ndimage.laplace(data)


data2 = data2_x + data2_y + data2_z + data_l

#data2 = np.ma.masked_less(data2,min_lap*0.8)
#data2 = ndimage.binary_closing(data2)
#data2=data2.astype(np.uint8)


#data2=ndimage.filters.gaussian_gradient_magnitude(data,1)

#=================
viewer = braviz.visualization.simpleVtkViewer()
vtk_image = braviz.readAndFilter.numpy2vtk_img(data2)
viewer.addImg(vtk_image)
viewer.start()
