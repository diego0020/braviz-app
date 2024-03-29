import os

import vtk
import nibabel as nib
from numpy.linalg import inv

import braviz
from braviz import _test_arrow
from braviz.readAndFilter.images import write_vtk_image
from braviz.readAndFilter.transforms import applyTransform, transformGeneralData

subject='144'

v= simpleVtkViewer()

#os.chdir(r'C:\Users\da.angulo39\Documents\Kanguro\093\camino')
reader=braviz.readAndFilter.BravizAutoReader()
data_root=reader.get_data_root()
os.chdir(os.path.join(data_root,subject,'camino'))

img=nib.load('FA_mri_masked.nii.gz')
img2=nib.load('FA.nii.gz')

img_vtk= nibNii2vtk(img)
img_w= applyTransform(img_vtk,inv(img.get_affine()))

img2_vtk= nibNii2vtk(img2)
img2_w= applyTransform(img2_vtk,inv(img2.get_affine()))

reader=braviz.readAndFilter.BravizAutoReader()
img3_w=reader.get('MRI',subject,format='vtk')
models=reader.get('MODEL',subject,index='')
cc=[m for m in models if 'CC' in m]
vtkModels=[reader.get('MODEL',subject,name=m) for m in cc]
for m in vtkModels:
    v.addPolyData(m)

track_reader=vtk.vtkPolyDataReader()
track_reader.SetFileName('streams.vtk')
track_reader.Update()
streams=track_reader.GetOutput()
#matrix=braviz.readAndFilter.readMatrix('surf2diff.mat')
matrix= readFlirtMatrix('diff2surf.mat','FA.nii.gz','orig.nii.gz')
streams_mri= transformPolyData(streams,matrix)
#streams_mri

v.addImg(img3_w)
v.addPolyData(streams_mri)
v.start()