from __future__ import division
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

#data2 = data

# data2_x = np.abs(ndimage.sobel(data,axis=0,mode="constant"))
# data2_x = ndimage.grey_closing(data2_x,size=(11,0,0))
#
# data2_y = np.abs(ndimage.sobel(data,axis=1,mode="constant"))
# data2_y = ndimage.grey_closing(data2_y,size=(0,11,0))
# #
# data2_z = np.abs(ndimage.sobel(data,axis=2,mode="constant"))
# data2_z = ndimage.grey_closing(data2_z,size=(0,0,11))
#
#
# data2 = data2_x + data2_y + data2_z
#
#
# data2 = (data2>2200).astype(np.int)
#
# kernel = np.ones((5,5,5))
# data2 = ndimage.binary_opening(data2,structure=kernel)
#
# data2 = data2.astype(np.uint8)
#

data2 = ndimage.median_filter(data,size=3)
data2 = data2 > 50
data3 = ndimage.binary_erosion(data2,np.ones((3,3,3)))
edges = data2-data3
edges = edges.astype(np.float64)
#kernel = np.ones((5,5,5))

#hough_res = hough_circle(edges,radii)
#data2 = ndimage.grey_opening(data2,structure=kernel)
data2 = edges
kernel_size = 9
ans = np.zeros(edges.shape,dtype=np.float64)
radii = np.arange(2,7)
for ir,radius in enumerate(radii):
    for ia,aura in enumerate(xrange(2,4)):
        giant_ball = morphology.ball(radius+aura)
        shape = giant_ball.shape
        big_ball = morphology.ball(radius+aura-1)
        big_ball_pad=np.zeros(shape)
        dif = shape[0]-big_ball.shape[0]
        big_ball_pad[dif//2:-dif//2,dif//2:-dif//2,dif//2:-dif//2]=big_ball
        big_ball=big_ball_pad

        med_ball = morphology.ball(radius)
        med_ball_pad=np.zeros(shape)
        dif = shape[0]-med_ball.shape[0]
        med_ball_pad[dif//2:-dif//2,dif//2:-dif//2,dif//2:-dif//2]=med_ball
        med_ball=med_ball_pad

        small_ball = morphology.ball(radius-1)
        small_ball_pad=np.zeros(shape)
        dif = shape[0]-small_ball.shape[0]
        small_ball_pad[dif//2:-dif//2,dif//2:-dif//2,dif//2:-dif//2]=small_ball
        small_ball=small_ball_pad


        hit_or_miss_background = giant_ball-big_ball+small_ball
        hit_or_miss_foreground = med_ball-small_ball

        c=shape[0]//2
        #hit_or_miss_background[c,c,c]=100
        #ans_p = ndimage.binary_hit_or_miss(edges,hit_or_miss_foreground,hit_or_miss_background)

        #print hit_or_miss_background
        #print "=============="
        #print hit_or_miss_foreground

        conv_kernel = hit_or_miss_foreground - hit_or_miss_background
        ans_p = ndimage.convolve(edges,conv_kernel,mode="constant")
        ans = np.add(ans,np.power(ans_p,2))
        z0=shape[0]
        y0=(ia+1)*shape[0]
        x0=(ir+1)*20
        edges[x0:x0+z0,y0:y0+z0,0:z0]=conv_kernel+1
    print radius

data2 = np.power(ans,0.5)
data2 = ndimage.grey_dilation(data2,size=10)

data2 = (500*edges+data2)
#data2=ndimage.filters.gaussian_gradient_magnitude(data,1)

#=================
viewer = braviz.visualization.simpleVtkViewer()
vtk_image = numpy2vtk_img(data2)
plane_widget = viewer.addImg(vtk_image)
plane_widget.SetResliceInterpolateToNearestNeighbour()
viewer.start()
