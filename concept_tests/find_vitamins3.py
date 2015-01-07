from __future__ import division
from braviz.readAndFilter.images import write_vtk_image

__author__ = 'Diego'

import os
import nibabel as nib
from scipy import ndimage
import braviz
import numpy as np
from skimage import data, filter, color
from skimage.transform import hough_circle
from skimage.feature import peak_local_max
from skimage.draw import circle_perimeter
from skimage.util import img_as_float
#matplotlib.use("Qt4Agg")
import matplotlib.pyplot as plt

os.chdir(r"C:\Users\Diego\Documents\prueba_free_surf_400")

skull = nib.load("skull.nii.gz")
data = skull.get_data()
#===============

#data2 = data

data2 = ndimage.median_filter(data,size=3)
#data2 = data2 > 50
slices = np.arange(130,165)

data2 = data2[:,slices,:]

data2 = data2 - np.min(data2)
data2 = data2/np.max(data2)



tot_scores = []
for s in xrange(data2.shape[1]):
    print s
    ax = plt.gca()
    ax.clear()
    slice = data2[:,s,:].squeeze()
    image = img_as_float(slice)
    edges = filter.canny(image)
#    ax.imshow(edges, cmap=plt.cm.gray)
#    plt.show()
    hough_radii = np.arange(4, 15, 1,dtype=np.intp)
    hough_res = hough_circle(edges, hough_radii)

    centers = []
    accums = []
    radii = []
    score = []
    for radius, h in zip(hough_radii, hough_res):
        # For each radius, extract two circles
        peaks = peak_local_max(h, num_peaks=2)
        centers.extend(peaks)
        accums.extend(h[peaks[:, 0], peaks[:, 1]])
        radii.extend([radius, radius])
        coords_scores = [h[tuple(p)] for p in peaks]
        score.extend(coords_scores)


    # Draw the most prominent 5 circles
    #image[image==0]=200
    image = color.gray2rgb(image)
    for idx in np.argsort(accums)[::-1][:2]:
        center_x, center_y = centers[idx]
        radius = radii[idx]
        cx, cy = circle_perimeter(center_y, center_x, radius)
        image[cy, cx] = (20, 100, 20)
    ax.imshow(image, cmap=plt.cm.gray)
    plt.show()
    tot_scores.extend(score)


#=================


viewer = braviz.visualization.simpleVtkViewer()
vtk_image = numpy2vtk_img(data2)
plane_widget = viewer.addImg(vtk_image)
plane_widget.SetResliceInterpolateToNearestNeighbour()
plane_widget.set_orientation(0)
viewer.start()
plane_widget.set_orientation(1)
viewer.start()
plane_widget.set_orientation(2)
viewer.start()