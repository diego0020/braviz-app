'''
Created on 11/09/2013

@author: da.angulo39
'''
import braviz
import nibabel as nib
import os
import numpy as np
import vtk
import itertools

os.chdir(r'K:\JohanaForero\KAB-db\144\spm\POWERGRIP')
n_bT1=nib.load('T1.nii.gz')
bT1=braviz.readAndFilter.nibNii2vtk(n_bT1)
T=n_bT1.get_affine()
Ti=np.linalg.inv(T)
v_T1=braviz.readAndFilter.applyTransform(bT1,Ti)


#os.chdir(r'../T1')
n_T1=nib.load('../T1/T1.nii.gz')
T2=n_T1.get_affine()
T2i=np.linalg.inv(T2)
T3=np.dot(T,T2i)

T1_b=braviz.readAndFilter.applyTransform(v_T1,T3)

v=braviz.visualization.simpleVtkViewer()
v.addImg(T1_b)
v.start()

#Warp

print "importing dartel warp field... this will take a while"
img=nib.load('../y_seg_inv.nii')
data=img.get_data()
#matrix=img.get_affine()
matrix=np.identity(4)
#Voxel space
origin=(0,0,0)
spacing=(1,1,1)

dimensions=img.get_shape()[0:3]
field=vtk.vtkImageData()
field.SetOrigin(origin)
field.SetSpacing(spacing)
field.SetDimensions(dimensions)
field.AllocateScalars(vtk.VTK_FLOAT,3)
def get_displacement(index):
    index_h=index+(1,)
    original_position=np.dot(matrix,index_h)[0:3] #find mm coordinates in yback space
    warped_position=data[index+(0,)] #component is in the 5th dimension, 4th is always zero
    difference=warped_position-original_position
    index_val=[index+(i,v) for i,v in enumerate(difference)]
    return index_val
indexes=map(xrange,dimensions)
# This loop takes 233s to run -> almost 4 minutes... must be cached or improved in performance
for index in itertools.product(*indexes):
    index_val=get_displacement(index)
    for iv in index_val:
        field.SetScalarComponentFromDouble(*iv)

transform=vtk.vtkGridTransform()
transform.SetDisplacementGridData(field)
transform.Update()

#convert matlab indexes to python indexes


#coord to voxel transform
affine=img.get_affine()
aff_vtk=braviz.readAndFilter.numpy2vtkMatrix(affine)
aff_vtk.Invert()

vtkTrans=vtk.vtkMatrixToLinearTransform()
vtkTrans.SetInput(aff_vtk)

#combine transforms
concatenated=vtk.vtkGeneralTransform()
concatenated.Identity()
concatenated.Concatenate(transform)
concatenated.Concatenate(vtkTrans)

p0=[9.8,35.9,51.2]
p1=[0]*3
concatenated.TransformPoint(p0,p1)
print p1


#Paint functional over anatomic
n_bT1=nib.load('T1.nii')
T1_T=n_T1.get_affine()
#print T
T1_Ti=np.linalg.inv(T)
bT1=braviz.readAndFilter.nibNii2vtk(n_bT1)
v_T1=braviz.readAndFilter.applyTransform(bT1,T1_Ti)




t_map_file='spmT_0001.hdr'
t_img=nib.load(t_map_file)

t_vtk=braviz.readAndFilter.nibNii2vtk(t_img)
aff2=t_img.get_affine()
aff2=np.linalg.inv(aff2)
t_vtk=braviz.readAndFilter.applyTransform(t_vtk,aff2)

reslicer=vtk.vtkImageReslice()
reslicer.SetInputData(t_vtk)
reslicer.SetResliceTransform(concatenated)
reslicer.SetOutputOrigin(v_T1.GetOrigin())
reslicer.SetOutputSpacing(v_T1.GetSpacing())
reslicer.SetOutputExtent(v_T1.GetExtent())
reslicer.Update()



v=braviz.visualization.simpleVtkViewer()
v.addImg(reslicer.GetOutput())
v.addImg(v_T1)
v.start()

trans=concatenated
#cache test

g1=trans.GetConcatenatedTransform(1)
gg=g1.GetDisplacementGrid()

m0=trans.GetConcatenatedTransform(0)
matrix=m0.GetMatrix()

array=vtk.vtkDoubleArray()
array.SetNumberOfValues(16)
for i in range(16):
    row=i//4
    column=i%4
    element=matrix.GetElement(row,column)
    array.SetValue(i, element)
array.SetName('matrix')

cache_name='test.vtk'
gg.GetFieldData().AddArray(array)


writer=vtk.vtkDataSetWriter()
writer.SetFileTypeToBinary()
writer.SetFileName(cache_name)
writer.SetInputData(gg)
writer.Update()

#Read from cache
reader=vtk.vtkDataSetReader()
reader.SetFileName(cache_name)
reader.Update()

readed_trans=reader.GetOutput()
#recreate transform
#GetMatrix
array=readed_trans.GetFieldData().GetArray(0)
readed_matrix=vtk.vtkMatrix4x4()
for i in range(16):
    row=i//4
    column=i%4
    element=array.GetValue(i)
    readed_matrix.SetElement(row,column,element)

array=readed_trans.GetFieldData().RemoveArray('matrix')
r_vtkTrans=vtk.vtkMatrixToHomogeneousTransform()
r_vtkTrans.SetInput(readed_matrix)    


#recover trans

r_trans=vtk.vtkGridTransform()
r_trans.SetDisplacementGridData(readed_trans)


# join
r_concatenated=vtk.vtkGeneralTransform()
r_concatenated.Identity()
r_concatenated.Concatenate(r_trans)
r_concatenated.Concatenate(r_vtkTrans)

r_concatenated.Update()

#========
import braviz
r=braviz.readAndFilter.kmc40AutoReader()
func=r.get('fMRI','144',name='POWERGRIP',space='world',format='vtk')
v=braviz.visualization.simpleVtkViewer()
v.addImg(func)
v.start()
