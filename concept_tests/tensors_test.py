from __future__ import division
import itertools
import random
import os
from itertools import izip

import vtk
import nibabel as nib
import numpy as np

import braviz

#==========test data===============


#data_file=r'C:\Users\da.angulo39\Documents\VTK\VTKData\Data\tensors.vtk'
#reader=vtk.vtkDataSetReader()
#reader.SetFileName(data_file)
#reader.Update()

#==============fabricated data================

# points2=[ (0,0,0) , (1,1,1) , (0,1,1) ]
# tensores2=[ (1,0,0,0,1,0,0,0,1),
#            (2,0,0,0,1,0,0,0,2),
#            
#            (-2.7061348e-10,
#  -5.1998277e-11,
#  -1.1320061e-10,
#  -5.1998277e-11,
#  1.9747431e-10,
#  1.3192596e-10,
#  -1.1320061e-10,
#  1.3192596e-10,
#  3.8300815e-10)]
# 
# vtk_points2=vtk.vtkPoints()
# for i,p in enumerate(points2):
#     vtk_points2.InsertPoint(i,p)
# 
# farray2=vtk.vtkFloatArray()
# farray2.SetNumberOfComponents(9)
# for i,t in enumerate(tensores2):
#     farray2.InsertTuple(i,t)
# 
# ugrid2=vtk.vtkUnstructuredGrid()
# ugrid2.SetPoints(vtk_points2)
# 
# pointData2=ugrid2.GetPointData()
# pointData2.SetTensors(farray2)


#===================real data===================
from braviz.readAndFilter.images import write_vtk_image
from braviz.readAndFilter.transforms import applyTransform, numpy2vtkMatrix

kmc_40_reader=braviz.readAndFilter.BravizAutoReader()
root_path=kmc_40_reader.get_data_root()


image_path=os.path.join(root_path,'911','camino','camino_dt.nii.gz')
#r'C:\Users\da.angulo39\Documents\Kanguro\911\camino\camino_dt.nii.gz'

fa_image_path=os.path.join(root_path,'911','camino','FA_masked.nii.gz')
#r'C:\Users\da.angulo39\Documents\Kanguro\911\camino\FA-masked.nii.gz'
img=nib.load(image_path)
shape=img.get_shape()
points=[(i,j,k) for i,j,k in itertools.product(range(shape[0]),range(shape[1]),range(shape[2]))]

fa_img=nib.load(fa_image_path)
fa_data=fa_img.get_data()
#TODO: transform points with affine matrix

img_data=img.get_data()
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
tensors=[get_tensor(i,j,k) for (i,j,k) in points ]
tensors=[np.dot(t,2e9*fa_data[p]) for t,p in izip(tensors,points)]

vtk_points=vtk.vtkPoints()
farray=vtk.vtkFloatArray()
farray.SetNumberOfComponents(9)


def filtro(pt):
    p,t = pt
    #x=sum([abs(y) for y in t])
    x=fa_data[p]
    return x>0.6 and random.random()<0.5
for i,(p,t) in enumerate(itertools.ifilter(filtro,izip(points,tensors))):
    vtk_points.InsertPoint(i,p)
    farray.InsertTuple(i,t)

ugrid=vtk.vtkUnstructuredGrid()
ugrid.SetPoints(vtk_points)

pointData=ugrid.GetPointData()

def get_color(tens,i=-1):
    #return(0,255,255)
    t=np.array(tens)
    t=t.reshape(3,3)
    evals,evecs=np.linalg.eig(t)
    maxi=abs(evals).argmax()
    v0=evecs[:,maxi]
    v0p=abs(v0)*255 #*fa_data[points[i]]
    return v0p.tolist()

def encode_chars(chars_tuple):
    "Encode a tuple of three chars into a long ing"
    chars_tuple=map(int,chars_tuple)
    r,g,b = chars_tuple
    #g=b=0
    #g=random.randint(0,255)
    return r*(256**2)+g*256+b
def decode_chars(long_int):
    "transform a long int into a tuple of three chars"
    x=int(long_int)
    b=x%256
    x //= 256
    g=x%256
    x //= 256
    r=x%256
    return r,g,b

colors=vtk.vtkUnsignedIntArray()
colors.SetNumberOfComponents(1)
colors.SetName('RGB_scalars')
colors.SetNumberOfTuples(farray.GetNumberOfTuples())
for i in xrange(farray.GetNumberOfTuples()):
    color=get_color(farray.GetTuple(i),i)
    colors.SetTupleValue(i,[encode_chars(color),])

pointData.SetScalars(colors)
pointData.SetTensors(farray)

matrix=fa_img.get_affine()
vtk_matrix= numpy2vtkMatrix(matrix)
vtkTrans=vtk.vtkMatrixToLinearTransform()
vtkTrans.SetInput(vtk_matrix)
transFilter=vtk.vtkTransformFilter()
transFilter.SetTransform(vtkTrans)
transFilter.SetInputData(ugrid)

#=====================visualization=============
#sourcePort=reader.GetOutputPort()
#sourcePort=ugrid2.GetProducerPort()
sourcePort=transFilter.GetOutputPort()
#sourcePort=ugrid.GetProducerPort()

sg = vtk.vtkSphereSource()
sg.SetRadius(0.5)
sg.SetCenter(0.0, 0.0, 0.0)
sg.SetPhiResolution(10)
sg.SetThetaResolution(10)

g  = vtk.vtkTensorGlyph()
g.SetInputConnection(sourcePort)
g.SetSourceConnection(sg.GetOutputPort())

g.ClampScalingOn()
g.ColorGlyphsOn()
#g.SetColorModeToEigenvalues()
g.SetColorModeToScalars()

g.Update()
#decodificar los escalares
out_poly=g.GetOutput()
out_pointData=out_poly.GetPointData()
out_scalars=out_pointData.GetScalars()
new_scalars=vtk.vtkUnsignedCharArray()
new_scalars.SetNumberOfComponents(3)
new_scalars.Allocate(out_scalars.GetNumberOfTuples()*3)

for i in xrange(out_scalars.GetNumberOfTuples()):
    x=out_scalars.GetTuple(i)[0]
    new_scalars.SetTupleValue(i,decode_chars(x))

out_pointData.SetScalars(new_scalars)
#out_poly.Update()
del out_scalars
normals = vtk.vtkPolyDataNormals()
normals.SetInputData(out_poly)

mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(normals.GetOutputPort())

act = vtk.vtkActor()
act.SetMapper(mapper)




#s = g.GetOutput().GetPointData().GetScalars()
#if s:
#    map.SetScalarRange(s.GetRange())

of = vtk.vtkOutlineFilter()
of.SetInputConnection(sourcePort)

out_map = vtk.vtkPolyDataMapper()
out_map.SetInputConnection(of.GetOutputPort())

out_act = vtk.vtkActor()
out_act.SetMapper(out_map)


ren = vtk.vtkRenderer()
ren.AddActor(act)
ren.AddActor(out_act)
ren.ResetCamera()

cam = ren.GetActiveCamera()
cam.Azimuth(-20)
cam.Elevation(20)
cam.Zoom(1.5)

ren.SetBackground(0.5, 0.5, 0.5)

renWin = vtk.vtkRenderWindow()
renWin.AddRenderer(ren)


iren=vtk.vtkRenderWindowInteractor()
iren.SetRenderWindow(renWin)
iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())

#context
vtk_fa= nibNii2vtk(fa_img)
vtk_faw= applyTransform(vtk_fa,fa_img.get_affine())

planeWidget=vtk.vtkImagePlaneWidget()
planeWidget.SetInputData(vtk_faw)
planeWidget.SetPlaneOrientationToXAxes()
planeWidget.SetSliceIndex(138)
planeWidget.UpdatePlacement()
planeWidget.DisplayTextOn()
planeWidget.SetInteractor(renWin.GetInteractor())
planeWidget.On()

iren.Initialize()
iren.Start()

gli=g.GetOutput()
print gli.GetPointData().GetScalars().GetTuple(1)