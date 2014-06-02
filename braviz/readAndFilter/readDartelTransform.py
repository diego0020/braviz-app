from __future__ import division
import itertools
import os
import logging

import vtk
import nibabel as nib
import numpy as np

from braviz.readAndFilter import numpy2vtkMatrix


def dartel2GridTransform(y_file,assume_bad_matrix=False):
    """reads a dartel nifti file from disk and returns a vtkTransform, this function is very slow"""
    log = logging.getLogger(__name__)
    log.info("importing dartel warp field... this will take a while")
    img=nib.load(y_file)
    data=img.get_data()
    matrix=img.get_affine()
    good_matrix=False
    if not assume_bad_matrix and check_matrix(matrix):
        good_matrix=True
        origin=matrix[0:3,3]
        spacing=np.diag(matrix)[0:3]
    else:
        origin=(0,0,0)
        spacing=(1,1,1)
        matrix=np.identity(4)
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
    
    if good_matrix:
        return transform
    
    affine=img.get_affine()
    aff_vtk=numpy2vtkMatrix(affine)
    aff_vtk.Invert()
    
    vtkTrans=vtk.vtkMatrixToLinearTransform()
    vtkTrans.SetInput(aff_vtk)
    
    #combine transforms
    concatenated=vtk.vtkGeneralTransform()
    concatenated.Identity()
    concatenated.Concatenate(transform)
    concatenated.Concatenate(vtkTrans) 
    
    return concatenated
   
def check_matrix(m):
    "check that the affine matrix contains only spacing and translation"
    log = logging.getLogger(__name__)
    for i in range(4):
        for j in range(3): # don't look at last column
            if i!=j: # don't look at diagonal
                if abs(m[i,j]>0.0001):
                    log.warning("WARNING: Matrix contains rotations or shears, this is not tested")
                    return False
    return True
def dartel2GridTransform_cached(y_file,assume_bad_matrix=False,cache_file_name=None):
    "Cached version of dartel2GridTransform"
    log = logging.getLogger(__name__)
    if cache_file_name is None:
        if y_file[-2:]=='gz':
            base_name=y_file[:-7] # remove .nii.gz
        else:
            base_name=y_file[:-4] # remove .nii
        cache_name=base_name+'.vtk'
    else:
        cache_name = cache_file_name
    cache=os.path.isfile(cache_name)
    if not cache:
        log.info("importing dartel warp field... this will take a while")
        trans=dartel2GridTransform(y_file,assume_bad_matrix)
        if isinstance(trans, vtk.vtkGridTransform):
            g=trans.GetDisplacementGrid()
        elif isinstance(trans, vtk.vtkGeneralTransform):
            #"We are dealing with a composed transform"
            grid=trans.GetConcatenatedTransform(1)
            g=grid.GetDisplacementGrid()
            m0=trans.GetConcatenatedTransform(0)
            matrix=m0.GetMatrix()
            matrix_array=vtk.vtkDoubleArray()
            matrix_array.SetNumberOfValues(16)
            for i in range(16):
                row=i//4
                column=i%4
                element=matrix.GetElement(row,column)
                matrix_array.SetValue(i, element)
            matrix_array.SetName('matrix')
            #Encode matrix in field data of grid
            g.GetFieldData().AddArray(matrix_array)
        else:
            log.error('Unknown transform type')
            raise Exception('Unknown transform type')
        writer=vtk.vtkDataSetWriter()
        writer.SetFileTypeToBinary()
        writer.SetFileName(cache_name)
        writer.SetInputData(g)
        try:
            writer.Update()
            if writer.GetErrorCode()!=0:
                log.warning('cache write failed')
        except Exception:
            log.warning("Cache write failed")
        return trans
    else:
        reader=vtk.vtkDataSetReader()
        reader.SetFileName(cache_name)
        reader.Update()
        g=reader.GetOutput()
        matrix_array=g.GetFieldData().GetArray('matrix')
        if matrix_array is not None:
            #"we are dealing with a composed transform"
            readed_matrix=vtk.vtkMatrix4x4()
            for i in range(16):
                row=i//4
                column=i%4
                element=matrix_array.GetValue(i)
                readed_matrix.SetElement(row,column,element)
            
            g.GetFieldData().RemoveArray('matrix')
            r_vtkTrans=vtk.vtkMatrixToHomogeneousTransform()
            r_vtkTrans.SetInput(readed_matrix)    
            #recover trans
            r_trans=vtk.vtkGridTransform()
            r_trans.SetDisplacementGridData(g)
            # join
            r_concatenated=vtk.vtkGeneralTransform()
            r_concatenated.Identity()
            r_concatenated.Concatenate(r_trans)
            r_concatenated.Concatenate(r_vtkTrans)
            r_concatenated.Update()
            trans=r_concatenated
        else:
            trans=vtk.vtkGridTransform()
            trans.SetDisplacementGridData(g)
            trans.Update()
        return trans
    
    