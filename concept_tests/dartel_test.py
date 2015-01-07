from __future__ import division
import os
import itertools

import vtk
import nibabel as nib
import numpy as np

import braviz
from braviz.readAndFilter.images import write_vtk_image
from braviz.visualization.simple_vtk import _test_arrow

reader=braviz.readAndFilter.BravizAutoReader()
data_root=reader.get_data_root()
os.chdir(os.path.join(data_root,'Dartel'))

patient='911'
template_file='Template_6.nii.gz'
orig_img=reader.get('MRI',patient)
orig_vtk=reader.get('MRI',patient,format='vtk')
template_img=nib.load(template_file)
yback_file='y_%s-back.nii.gz'%patient
yforw_file='y_%s-forw.nii.gz'%patient
yback_img=nib.load(yback_file)
yback_data=yback_img.get_data()
yforw_img=nib.load(yforw_file)
yforw_data=yforw_img.get_data()
template_vtk= nibNii2vtk(template_img)
#template_vtk=braviz.readAndFilter.applyTransform(template_vtk, template_img.get_affine())
template_vtk.SetOrigin(template_img.get_affine()[0:3,3])
template_vtk.SetSpacing(np.diag(template_img.get_affine())[0:3])


#construct backward transform (for warping images)
back_field=vtk.vtkImageData()
back_field.CopyStructure(template_vtk)
back_field.AllocateScalars(vtk.VTK_FLOAT,3)

def get_displacement(index):
    index_h=index+(1,)
    original_position=np.dot(yback_img.get_affine(),index_h)[0:3] #find mm coordinates in yback space
    warped_position=yback_data[index+(0,)] #component is in the 5th dimension, 4th is always zero
    difference=warped_position-original_position
    index_val=[index+(i,v) for i,v in enumerate(difference)]
    return index_val

dimensions=back_field.GetDimensions()
indexes=map(xrange,dimensions)
for index in itertools.product(*indexes):
    index_val=get_displacement(index)
    for iv in index_val:
        back_field.SetScalarComponentFromDouble(*iv)
# The above loop takes 233s to run -> almost 4 minutes... must be cached or improved in performance

back_transform=vtk.vtkGridTransform()
back_transform.SetDisplacementGridData(back_field)
back_transform.Update()

reslicer=vtk.vtkImageReslice()
reslicer.SetResliceTransform(back_transform)
reslicer.SetInputData(orig_vtk)
reslicer.SetInformationInput(template_vtk)
reslicer.Update()
orig_warped=reslicer.GetOutput()

v= simpleVtkViewer()
v.addImg(template_vtk)
v.start()

v.addImg(orig_vtk)
v.start()

v.addImg(orig_warped)
v.start()


#Calculate forward transform: To map points
v2= simpleVtkViewer()
v2.addImg(orig_warped)
v2.addImg(template_vtk)

forw_field=vtk.vtkImageData()
forw_field.CopyStructure(orig_vtk)
forw_field.AllocateScalars(vtk.VTK_FLOAT,3)

def get_displacement_f(index):
    index_h=index+(1,)
    original_position=np.dot(yforw_img.get_affine(),index_h)[0:3] #find mm coordinates in yforw space
    warped_position=yforw_data[index+(0,)] #component is in the 5th dimension, 4th is always zero
    difference=warped_position-original_position
    index_val=[index+(i,v) for i,v in enumerate(difference)]
    return index_val

dimensions=forw_field.GetDimensions()
indexes=map(xrange,dimensions)
for index in itertools.product(*indexes):
    index_val=get_displacement_f(index)
    for iv in index_val:
        forw_field.SetScalarComponentFromDouble(*iv)


forw_transform=vtk.vtkGridTransform()
forw_transform.SetDisplacementGridData(forw_field)
forw_transform.Update()

#test with some fibers
fibers=reader.get('FIBERS',patient,space='World')
trans_filter=vtk.vtkTransformFilter()
trans_filter.SetTransform(forw_transform)
trans_filter.SetInputData(fibers)
trans_filter.Update()
out_fibers=trans_filter.GetOutput()
v2.addPolyData(out_fibers)
v2.start()
