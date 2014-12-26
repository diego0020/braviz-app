from __future__ import division
import os
import itertools

import vtk
import nibabel as nib
import numpy as np

import braviz


kmc_40_reader=braviz.readAndFilter.BravizAutoReader()
root_path=kmc_40_reader.get_data_root()
image_path=os.path.join(root_path,'911','camino','camino_dt.nii.gz')
output_path=os.path.join(root_path,'911','camino','camino_dt.vtk')
img=nib.load(image_path)
img_data=img.get_data()

fa_image_path=os.path.join(root_path,'911','camino','FA-masked.nii.gz')
fa_img_nii=nib.load(fa_image_path)
fa_img=braviz.readAndFilter.nibNii2vtk(fa_img_nii)
#fa_img_w=braviz.readAndFilter.applyTransform(fa_img, fa_img_nii.get_affine())
fa_img.SetSpacing( 1.02, 1.02, 4.0)

tensor_field=vtk.vtkImageData()
tensor_field.DeepCopy(fa_img)

seed=(136,121,13*4)

#add tensors to the data
def get_tensor(i,j,k):
    Dxx=img_data[i,j,k,0,0]
    Dxy=img_data[i,j,k,0,1]
    Dxz=img_data[i,j,k,0,2]
    Dyy=img_data[i,j,k,0,3]
    Dyz=img_data[i,j,k,0,4]
    Dzz=img_data[i,j,k,0,5]
    return (Dxx, Dxy, Dxz,
            Dxy, Dyy, Dyz,
            Dxz, Dyz, Dzz)

tensors_array=vtk.vtkFloatArray()
tensors_array.SetNumberOfComponents(9)
i_max, j_max, k_max=fa_img.GetDimensions()
tensors_array.SetNumberOfTuples(i_max*j_max*k_max)
for (i,j,k) in itertools.product(range(i_max),range(j_max),range(k_max)):
    t=get_tensor(i,j,k)
    t=np.dot(t,2e9)
    flat_index=tensor_field.ComputePointId((i,j,k))
    tensors_array.SetTupleValue(flat_index, t)

tensor_field.GetPointData().SetTensors(tensors_array)
#tensor_field=reader.get('TENSORS', '093')

#writer=vtk.vtkDataSetWriter()
#writer.SetFileName(output_path)
#writer.SetInputData(tensor_field)
#writer.Update()

hiperFilter=vtk.vtkHyperStreamline()
hiperFilter.SetStartPosition(*seed)
hiperFilter.SetInputData(tensor_field)
#hiperFilter.IntegrateMajorEigenvector()
hiperFilter.IntegrateMinorEigenvector()
#hiperFilter.IntegrateMediumEigenvector
hiperFilter.SetMaximumPropagationDistance(100)
hiperFilter.SetStepLength(0.00001)
hiperFilter.SetIntegrationStepLength(0.00001)
hiperFilter.SetRadius(0.5)
hiperFilter.SetNumberOfSides(10)
hiperFilter.SetIntegrationDirectionToIntegrateBothDirections()
hiperFilter.Update()

lut = vtk.vtkLogLookupTable()
lut.SetHueRange(.6667, 0.0)

s1Mapper = vtk.vtkPolyDataMapper()
s1Mapper.SetInputConnection(hiperFilter.GetOutputPort())
s1Mapper.SetScalarRange(fa_img.GetScalarRange())

s1Actor = vtk.vtkActor()
s1Actor.SetMapper(s1Mapper)
s1Mapper.SetLookupTable(lut )

v=braviz.visualization.simpleVtkViewer()
v.ren.AddActor(s1Actor)
v.addImg(fa_img)

seed_sphere=vtk.vtkSphereSource()
seed_sphere.SetRadius(1)
seed_sphere.SetCenter(*seed)

sphere_mapper=vtk.vtkPolyDataMapper()
sphere_mapper.SetInputConnection(seed_sphere.GetOutputPort())

sphere_actor=vtk.vtkActor()
sphere_actor.SetMapper(sphere_mapper)
v.ren.AddActor(sphere_actor)

v.start()