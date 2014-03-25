__author__ = 'Diego'

import os

import nibabel as nib
import numpy as np

import braviz


os.chdir(r"C:\Users\Diego\Documents\kmc40-db\KAB-db\093\camino")
nimage=nib.load("MD.nii.gz")

data = nimage.get_data()
data = data * 1e12
vimg = braviz.readAndFilter.numpy2vtk_img(data)
t=nimage.get_affine()
it = np.linalg.inv(t)


vimg2=braviz.readAndFilter.applyTransform(vimg,it)

viewer= braviz.visualization.simpleVtkViewer()

ip=viewer.addImg(vimg2)
ip.SetSliceIndex(120)
