##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
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


import itertools
import logging
import struct
import nibabel as nib
import numpy as np
import vtk

__author__ = 'diego'


def write_vtk_image(image_data, out_file):
    """
    Write a vtkImage to disk as a nifti file

    Args:
        image_data (vtkImageData) : Image to write
        out_file (str) : Path to output nifti file

    """
    dx, dy, dz = image_data.GetDimensions()
    data = np.zeros((dx, dy, dz), np.uint8)
    for i, j, k in itertools.product(xrange(dx), xrange(dy), xrange(dz)):
        v = image_data.GetScalarComponentAsDouble(i, j, k, 0)
        data[i, j, k] = v
    sx, sy, sz = image_data.GetSpacing()
    ox, oy, oz = image_data.GetOrigin()
    af = np.eye(4)
    af[0, 0], af[1, 1], af[2, 2] = sx, sy, sz
    af[0, 3], af[1, 3], af[2, 3] = ox, oy, oz
    nib_img = nib.Nifti1Image(data, affine=af)
    nib_img.to_filename(out_file)

    return


def write_nib_image(data, affine, out_file):
    """
    Writes nifti image to disk

    Args:
        data (numpy.ndarray) : Voxel data
        affine (numpy.ndarray) : Image transformation
        out_file (str) : Path to output file
    """
    nib_img = nib.Nifti1Image(data, affine=affine)
    nib_img.to_filename(out_file)
    log=logging.getLogger(__name__)
    log.info("%s written",out_file)
    return


def numpy2vtk_img(d, data_type=None):
    """
    Transform a 3d numpy array into a vtk image data object

    Args:
        d (numpy.ndarray) : Voxel data
        data_type (str) : Data type of voxel data, if None attempts to read from the array

    Returns:
        vtkImageData
    """
    array_data_type = d.dtype

    if data_type is not None:
        assert array_data_type == data_type

    importer = vtk.vtkImageImport()
    assert isinstance(d, np.ndarray)
    importer.SetDataScalarTypeToShort()  # default
    if array_data_type is None:
        array_data_type = d.type
    if array_data_type == np.float64:
        importer.SetDataScalarTypeToDouble()
    elif array_data_type == np.float32:
        importer.SetDataScalarTypeToFloat()
    elif array_data_type == np.int32:
        importer.SetDataScalarTypeToInt()
    elif array_data_type == np.int16:
        importer.SetDataScalarTypeToShort()
    elif array_data_type == np.uint8:
        importer.SetDataScalarTypeToUnsignedChar()
    else:
        log = logging.getLogger(__name__)
        log.warning("casting to float64")
        importer.SetDataScalarTypeToDouble()
        d = d.astype(np.float64)
        #======================================
    dstring = d.flatten(order='F').tostring()
    if array_data_type.byteorder == '>':
        # Fix byte order
        dflat_l = d.flatten(order='F').tolist()
        format_string = '<%id' % len(dflat_l)
        dstring = struct.pack(format_string, *dflat_l)
        # importer.SetDataScalarTypeToInt()
    importer.SetNumberOfScalarComponents(1)
    importer.CopyImportVoidPointer(dstring, len(dstring))
    dshape = d.shape
    importer.SetDataExtent(
        0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
    importer.SetWholeExtent(
        0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
    importer.Update()
    imgData = importer.GetOutput()
    # return imgData
    out_img = vtk.vtkImageData()
    out_img.DeepCopy(imgData)
    return out_img


def nifti_rgb2vtk(nifti_rgb):
    """
    Reads 4D rgb nifti images

    Args:
        nifti_rgb (nibabel.spatialimages.SpatialImage) : 4D Nifti image object

    Returns:
        vtkImageData with rgb scalars
    """
    data = nifti_rgb.get_data()
    data2 = np.rollaxis(data, 3, 0)
    importer = vtk.vtkImageImport()

    importer.SetDataScalarTypeToUnsignedChar()
    importer.SetNumberOfScalarComponents(3)
    dstring = data2.flatten(order='F').tostring()
    importer.CopyImportVoidPointer(dstring, len(dstring))
    dshape = data.shape
    importer.SetDataExtent(
        0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
    importer.SetWholeExtent(
        0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)

    importer.Update()
    img = importer.GetOutput()

    out_img = vtk.vtkImageData()
    out_img.DeepCopy(img)
    return out_img


def nibNii2vtk(nii):
    """
    Transform a nifti image read by nibabel into a vtkImageData ignoring transformations

    Args:
        nii (nibabel.spatialimages.SpatialImage) : Nifti image object

    Returns:
        vtkImageData, transformations are ignored, you should apply them afterwards
        see :func:`~braviz.readAndFilter.transforms.applyTransform`
    """
    d = nii.get_data()
    return numpy2vtk_img(d)


def vtk2numpy(vtk_image):
    """
    Transform a vtk image into a numpy array

    Args:
        vtk_image (vtkImageData) : vtk image

    Returns:
        A numpy array of the same shape as the image
    """
    return np.array(vtk_image.GetPointData()["ImageScalars"].reshape(vtk_image.GetDimensions(), order="F"))
