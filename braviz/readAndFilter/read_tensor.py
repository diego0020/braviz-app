from __future__ import division
import itertools
import os
import logging
from itertools import izip

import vtk
import nibabel as nib
import numpy as np

from braviz.readAndFilter.transforms import numpy2vtkMatrix


def tensorFromImgData(img_data):
    "Returns a function which generates tensors for each coordinate in img_data"
    #print img_data.shape
    def get_tensor(i,j,k):
            "Returns the tensor located at coordinates i,j,k"
            Dxx=img_data[i,j,k,0,0]
            Dxy=img_data[i,j,k,0,1]
            Dxz=img_data[i,j,k,0,2]
            Dyy=img_data[i,j,k,0,3]
            Dyz=img_data[i,j,k,0,4]
            Dzz=img_data[i,j,k,0,5]
            return (Dxx, Dxy, Dxz,
                    Dxy, Dyy, Dyz,
                    Dxz, Dyz, Dzz)
    return get_tensor

def get_color(tens,i=-1):
    "Returns a color for a tensor based on the direction of the principal eigenvector"
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

def readTensorImage(tensor_file,fa_file=None, min_fa=0.3):
    """Read data from a nifti tensor image and return a vtk unstructured grid. 
    If a fa_file is provided the tensors are scaled according to it"""
    
    if fa_file:
        fa_img=nib.load(fa_file)
        fa_data=fa_img.get_data()
    img=nib.load(tensor_file)
    shape=img.get_shape()
    points=[(i,j,k) for i,j,k in itertools.product(range(shape[0]),range(shape[1]),range(shape[2]))]
    #print "points = %d"%len(points)
    img_data=img.get_data()
    get_tensor=tensorFromImgData(img_data)
    tensors=[get_tensor(i,j,k) for (i,j,k) in points ]
    #print "tensors = %d"%len(tensors)
    #Scale to make them closer to 1
    if fa_file:
        tensors=[np.dot(t,2e9*fa_data[p]) for t,p in izip(tensors,points)]
    else:
        tensors=[np.dot(t,2e9) for t,p in izip(tensors,points)]
    vtk_points=vtk.vtkPoints()
    farray=vtk.vtkFloatArray()
    farray.SetNumberOfComponents(9)
    if fa_file:
        def filtro(pt):
            p,t = pt
            x=fa_data[p]
            return x>min_fa
    else:
        filtro=lambda x:0
    for i,(p,t) in enumerate(itertools.ifilter(filtro,izip(points,tensors))):
    #for i,(p,t) in enumerate(izip(points,tensors)):
        vtk_points.InsertPoint(i,p)
        farray.InsertTuple(i,t)
        #if i%1000 ==0:
            #print "i=%d"%i
    #print farray    
    
    colors=vtk.vtkUnsignedIntArray()
    colors.SetNumberOfComponents(1)
    colors.SetName('Encoded RGB_scalars')
    colors.SetNumberOfTuples(farray.GetNumberOfTuples())
    for i in xrange(farray.GetNumberOfTuples()):
        color=get_color(farray.GetTuple(i),i)
        colors.SetTupleValue(i,[encode_chars(color),])
    
    ugrid=vtk.vtkUnstructuredGrid()
    ugrid.SetPoints(vtk_points)
    pointData=ugrid.GetPointData()
    pointData.SetScalars(colors)
    pointData.SetTensors(farray)
    
    matrix=fa_img.get_affine()
    vtk_matrix=numpy2vtkMatrix(matrix)
    vtkTrans=vtk.vtkMatrixToLinearTransform()
    vtkTrans.SetInput(vtk_matrix)
    transFilter=vtk.vtkTransformFilter()
    transFilter.SetTransform(vtkTrans)
    transFilter.SetInputData(ugrid)
    transFilter.Update()
    
    
    return transFilter.GetOutput()

def cached_readTensorImage(tensor_file,fa_file=None, min_fa=0.3):
    "cached version of readTensorImage"     
        #============CACHE READ==================
    cache_file=tensor_file[0:-7]
    if fa_file:
        cache_file += '_%f' % min_fa
    cache_file += '.vtk'
    vtkFile=cache_file
    log = logging.getLogger(__name__)
    if os.path.isfile(vtkFile):
        log.info('reading from vtk-file')
        vtkreader=vtk.vtkUnstructuredGridReader()
        vtkreader.SetFileName(cache_file)
        vtkreader.Update()
        return vtkreader.GetOutput()
    #=============END CACHE READ=====================
    out=readTensorImage(tensor_file,fa_file, min_fa)
    log.info('attempting to write cache to: %s'%cache_file)
    try:
        vtkWriter=vtk.vtkUnstructuredGridWriter()
        vtkWriter.SetInputData(out)
        vtkWriter.SetFileName(cache_file)
        vtkWriter.SetFileTypeToBinary()
        vtkWriter.Update()
        if vtkWriter.GetErrorCode() != 0:
            log.warning('cache write failed')
    except Exception:
        log.warning('cache write failed')
    return out
    