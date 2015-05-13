

import braviz

import nibabel as nib
from braviz.readAndFilter import images, transforms
from braviz.visualization.simple_vtk import SimpleVtkViewer
import numpy as np


p=r"Z:\nii\144\eT2WTSEPEBCLEAR.nii.gz"

img=nib.load(p)

vd=images.nibNii2vtk(img)

ti = np.linalg.inv(img.get_affine())

vd2 = transforms.applyTransform(vd,ti)

v=SimpleVtkViewer()

v.addImg(vd2)

v.start()