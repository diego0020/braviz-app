__author__ = 'Diego'

import sys

import nibabel as nib
import numpy as np


if len(sys.argv)<3:
    print "usage: "+sys.argv[0]+" <camino_image> <out_img>"
    sys.exit(0)

#os.chdir(r"C:\Users\Diego\Documents\kmc40-db\KAB-db\093\camino")
#nimage=nib.load("rgb_dti.nii.gz")
nimage=nib.load(sys.argv[1])
out_image=sys.argv[2]

data = nimage.get_data()

#split in 3 components
data_r=data["R"]

data_g=data["G"]

data_b=data["B"]

dshape = data_r.shape
dshape2=dshape + (1,)

data_r=data_r.reshape(*dshape2)
data_g=data_g.reshape(*dshape2)
data_b=data_b.reshape(*dshape2)
data_3=np.concatenate((data_r,data_g,data_b),3)

h=nimage.get_header()
h2=h.copy()
h2.set_data_dtype(np.ubyte)
dshape3 = dshape + (3,)
h2.set_data_shape(dshape3)
img2=nib.Nifti1Image(data_3,nimage.get_affine(),h2)
#nib.save(img2,"rgb2.nii.gz")
nib.save(img2,out_image)

