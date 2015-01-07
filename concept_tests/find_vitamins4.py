from __future__ import division
import itertools
from braviz.readAndFilter.images import write_vtk_image

__author__ = 'Diego'

import os
import nibabel as nib
import numpy as np
from scipy import ndimage
import braviz
from skimage import morphology

os.chdir(r"C:\Users\Diego\Documents\prueba_free_surf_400")

skull = nib.load("skull.nii.gz")
data = skull.get_data()
#===============

def get_next_peak(array, shadow_shape):
    m0 = np.argmax(array)
    m0_coords = np.unravel_index(m0, array.shape)
    sx, sy, sz = map(lambda x: x // 2, shadow_shape)

    yield m0_coords
    i_array = array.copy()
    while True:
        #zero next part
        x, y, z = m0_coords
        i_array[x - sx:x + sx + 1, y - sy:y + sy + 1, z - sz:z + sz + 1] = np.zeros(shadow_shape)
        m0 = np.argmax(i_array)
        m0_coords = np.unravel_index(m0, array.shape)
        yield m0_coords


def draw_cross(array, coords):
    length = 5
    x, y, z = coords
    val = np.max(array)
    #x
    array[x - length:x + length + 1, y, z] = val
    #y
    array[x, y - length:y + length + 1, z] = val
    #z
    array[x, y, z - length:z + length + 1] = val
    return array


data2 = ndimage.median_filter(data, size=3)
data2 = data2.astype(np.float64)
max_val = np.max(data2)
model_radius = 5

model = morphology.ball(model_radius) - 0.5

s = model.shape

#data2[118:118 + s[0], 130:130 + s[1], 231:231 + s[2]] = max_val // 2 + model * (max_val // 2)

data2 = ndimage.filters.correlate(data2, model)

#=================
for c, i in itertools.izip(get_next_peak(data2, model.shape), xrange(5)):
    print c
    print data2[c]
    draw_cross(data, c)


viewer = braviz.visualization.simpleVtkViewer()
vtk_image = numpy2vtk_img(data)
plane_widget = viewer.addImg(vtk_image)
plane_widget.SetResliceInterpolateToNearestNeighbour()
plane_widget.set_orientation(0)
viewer.start()
plane_widget.set_orientation(1)
viewer.start()
plane_widget.set_orientation(2)
viewer.start()