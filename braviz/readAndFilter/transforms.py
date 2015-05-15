##############################################################################
# Braviz, Brain Data interactive visualization                            #
# Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

from __future__ import division
import logging
import os
import nibabel as nib
import numpy as np
import vtk
from braviz.readAndFilter.cache import memo_ten

__author__ = 'diego'


def applyTransform(img, transform, origin2=None, dimension2=None, spacing2=None, interpolate=True):
    """Apply a linear transform to a grid which afterwards resamples the image.

       Be sure to pass the inverse of the transform you would use to transform a point.
       Accepts linear and non linear transforms

       Args:
            img (vtkImageData) : Image
            transform (vtkTransform) : Linear or nonlinear transform
            origin2 (tuple) : If not None, the origin for the output image
            dimension2 (tuple) : If not None, the dimension for the output image
            spacing2 (tuple) : If not None, the spacing for the output image
            interpolate (bool) : If True voxel values are interpolated, if ``False`` the nearest neighbour value is
                used. This is important for label maps.

       Returns:
            Resampled vtkImageData
       """
    if isinstance(transform, (np.matrix, np.ndarray)):
        transform = numpy2vtkMatrix(transform)
    if isinstance(transform, vtk.vtkMatrix4x4):
        vtkTrans = vtk.vtkMatrixToHomogeneousTransform()
        vtkTrans.SetInput(transform)
        if spacing2 is None or origin2 is None:
            transform_i = transform.NewInstance()
            transform_i.DeepCopy(transform)
            transform_i.Invert()
            if spacing2 is None:
                org = np.array(transform_i.MultiplyDoublePoint((0,0,0,1)))
                next_pt = np.array(transform_i.MultiplyDoublePoint((1,1,1,1)))
                delta = (org[0:3]/org[3]) - (next_pt[0:3]/next_pt[3])
                spacing2 = delta
                #spacing2 = [transform_i.GetElement(0, 0), transform_i.GetElement(1, 1), transform_i.GetElement(2, 2)]
            if origin2 is None or spacing2 is None:

                if origin2 is None:
                    # TODO: Use a better strategy to find the new origin; this doesn't
                    # work with large rotations or reflections
                    x_min, x_max, y_min, y_max, z_min, z_max = img.GetBounds()
                    corners = [(x_min, y_min, z_min), (x_min, y_min, z_max), (x_min, y_max, z_min),
                               (x_min, y_max, z_max),
                               (x_max, y_min, z_min), (x_max, y_min, z_max), (x_max, y_max, z_min),
                               (x_max, y_max, z_max)]

                    corners2 = []
                    for c in corners:
                        ch = c + (1,)
                        corners2.append(transform_i.MultiplyDoublePoint(ch))
                    x2_min, y2_min, z2_min, _ = np.min(corners2, axis=0)
                    x2_max, y2_max, z2_max, _ = np.max(corners2, axis=0)
                    origin2 = [0, 0, 0]
                    origin2[0] = x2_min if spacing2[0] >= 0 else x2_max
                    origin2[1] = y2_min if spacing2[1] >= 0 else y2_max
                    origin2[2] = z2_min if spacing2[2] >= 0 else z2_max

                    if dimension2 is None:
                        dimension2 = [0, 0, 0]
                        dimension2[0] = int(np.ceil(np.abs((x2_min - x2_max) / spacing2[0])))
                        dimension2[1] = int(np.ceil(np.abs((y2_min - y2_max) / spacing2[1])))
                        dimension2[2] = int(np.ceil(np.abs((z2_min - z2_max) / spacing2[2])))


    elif isinstance(transform, vtk.vtkAbstractTransform):
        vtkTrans = transform
        if None == spacing2 or None == origin2:
            log = logging.getLogger(__name__)
            log.error(
                "spacing2 and origin2 are required when using a general transform")
            raise Exception(
                "spacing2 and origin2 are required when using a general transform")
    else:
        log = logging.getLogger(__name__)
        log.error("Method not implemented for %s transform" % type(transform))
        raise Exception(
            "Method not implemented for %s transform" % type(transform))
    if None == dimension2:
        dimension2 = img.GetDimensions()
        #=============================Finished parsing arguments===============
    reslicer = vtk.vtkImageReslice()

    reslicer.SetResliceTransform(vtkTrans)
    reslicer.SetInputData(img)
    outData = vtk.vtkImageData()
    outData.SetOrigin(origin2)
    outData.SetDimensions(dimension2)
    outData.SetSpacing(spacing2)
    reslicer.SetInformationInput(outData)
    if interpolate is False:
        reslicer.SetInterpolationModeToNearestNeighbor()
    else:
        reslicer.SetInterpolationModeToCubic()
    reslicer.Update()
    outImg = reslicer.GetOutput()
    # print dimension2
    return outImg


def numpy2vtkMatrix(M):
    """
    Transform a 4x4 numpy array into vtk4x4 matrix

    Args:
        M (numpy.ndarray) : Numpy 4x4 array

    Returns
        vtk4x4Matrix
    """
    vtk_matrix = vtk.vtkMatrix4x4()
    for i in range(0, 4):
        for j in range(0, 4):
            vtk_matrix.SetElement(i, j, M[i, j])
    return vtk_matrix


def transformGeneralData(data, transform):
    """
    Use a transform or a 4x4Matrix to transform vtkPointData or poly data

    Args:
        data : Data to apply the transform to
        transform (vtkTransform) : Transform to be applied

    Returns:
        Transformed data
    """
    if isinstance(transform, (np.matrix, np.ndarray)):
        transform = numpy2vtkMatrix(transform)
    if isinstance(transform, vtk.vtkMatrix4x4):
        vtkTrans = vtk.vtkMatrixToLinearTransform()
        vtkTrans.SetInput(transform)
    elif isinstance(transform, vtk.vtkAbstractTransform):
        vtkTrans = transform
        if isinstance(vtkTrans, vtk.vtkGridTransform):
            vtkTrans.SetInterpolationModeToCubic()
    else:
        log = logging.getLogger(__name__)
        log.error("Method not implemented for %s transform" % type(transform))
        raise Exception(
            "Method not implemented for %s transform" % type(transform))
    if isinstance(data, vtk.vtkPolyData):
        transFilter = vtk.vtkTransformPolyDataFilter()
    elif isinstance(data, vtk.vtkDataSet):
        transFilter = vtk.vtkTransformFilter()
    else:
        return vtkTrans.TransformPoint(data)
    transFilter.SetTransform(vtkTrans)
    transFilter.SetInputData(data)
    transFilter.Update()
    output = transFilter.GetOutput()
    return output


def transformPolyData(poly_data, transform):
    """
    Kept for compatibility, it is an alias to :func:`transformGeneralData`

    .. deprecated :: 3.0b
        Use :func:`transformGeneralData`
    """
    output = transformGeneralData(poly_data, transform)
    return output


def readFreeSurferTransform(filename):
    """
    Reads a freeSurfer transform file and returns a numpy array

    Args:
        filename (str) : Path to freesurfer transform

    Returns:
        4x4 numpy array
    """
    try:
        with open(filename) as f:
            lines = f.readlines()
            trans = lines[-3:]
            trans = [l.split() for l in trans]
            trans = [l[0:4] for l in trans]
            # possible semicolomg in the last term
            trans[2][3] = trans[2][3].rstrip(";")
            trans_f = [map(float, l) for l in trans]
            trans_f.append([0] * 3 + [1])
            np.array(trans_f)
            nar = np.array(trans_f)
    except IOError:
        log = logging.getLogger(__name__)
        log.error("couldn't open %s" % filename)
        raise Exception("couldn't open %s" % filename)

    return nar


@memo_ten
def readFlirtMatrix(file_name, src_img_file, ref_img_file, path=''):
    """
    read a matrix in fsl flirt format

    In order to apply this transformation information about
    the source and ref images is also requierd. The function returns
    the effective transform that can be applied to point data.

    Args:
        file_name (str) : Path to fsl transform
        src_img_file (str) : Path to the image specifying the source image for the transform
        ref_img_file (str) : Path to the image specifying the destination image for the transform
        path (str) : Common path to all files, it is prepended to the other arguments

    Returns:
        Numpy 4x4 matrix
    """
    file_name = os.path.join(path, file_name)
    src_img_file = os.path.join(path, src_img_file)
    ref_img_file = os.path.join(path, ref_img_file)
    with open(file_name) as mat_file:
        lines = mat_file.readlines()

    lines_s = [l.split() for l in lines]
    lines_f = [[float(n) for n in l3] for l3 in lines_s]
    M2 = np.matrix(lines_f)
    src_img = nib.load(src_img_file)
    M1 = np.matrix(src_img.get_affine())
    ref_img = nib.load(ref_img_file)
    M3 = np.matrix(ref_img.get_affine())
    M1i = M1 ** (-1)
    scale_vec = np.diag(M1)
    Ms = abs(np.matrix(np.diag(scale_vec)))
    T = M3 * M2 * Ms * M1i
    return T
