__author__ = 'Diego'

import os

import nibabel as nib
import vtk
import numpy as np

import braviz

viewer= braviz.visualization.simpleVtkViewer()


os.chdir(r"C:\Users\Diego\Documents\kmc40-db\KAB-db\093\camino")
nimage=nib.load("rgb2.nii.gz")

data=nimage.get_data()

data2=np.rollaxis(data,3,0)
importer = vtk.vtkImageImport()

importer.SetDataScalarTypeToUnsignedChar()
importer.SetNumberOfScalarComponents(3)
dstring = data2.flatten(order='F').tostring()
importer.CopyImportVoidPointer(dstring, len(dstring))
dshape = data.shape
importer.SetDataExtent(0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
importer.SetWholeExtent(0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)

importer.Update()

img=importer.GetOutput()
img2=braviz.readAndFilter.applyTransform(img,np.linalg.inv(nimage.get_affine()))

reader=braviz.readAndFilter.BravizAutoReader()

img2=reader.get("DTI","093",format="VTK")

viewer= braviz.visualization.simpleVtkViewer()
nip=viewer.addImg(img2)
nip.GetColorMap().SetLookupTable(None)

viewer.start()



