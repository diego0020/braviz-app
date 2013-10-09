# Import and filter
from __future__ import division
import struct
import os
import random
import functools
import time
import copy

import nibabel as nib
import vtk
import numpy as np


def nibNii2vtk(nii):
    "Transform a nifti image read by nibabel into a vtkImageData"
    d = nii.get_data()
    return numpy2vtk_img(d)


def numpy2vtk_img(d):
    "Transform a 3d numpy array into a vtk image data object"
    data_type = d.dtype
    importer = vtk.vtkImageImport()
    dstring = d.flatten(order='F').tostring()
    importer.SetDataScalarTypeToShort()#default
    if data_type.type == np.float64:
        importer.SetDataScalarTypeToDouble()
    elif data_type.type == np.float32:
        importer.SetDataScalarTypeToFloat()
    elif data_type.type == np.int32:
        importer.SetDataScalarTypeToInt()
    elif data_type.type == np.int16:
        importer.SetDataScalarTypeToShort()
        #======================================
    if data_type.byteorder == '>':
        #Fix byte order
        dflat_l = d.flatten(order='F').tolist()
        format_string = '<%id' % len(dflat_l)
        dstring = struct.pack(format_string, *dflat_l)
        #importer.SetDataScalarTypeToInt()
    importer.SetNumberOfScalarComponents(1)
    importer.CopyImportVoidPointer(dstring, len(dstring))
    dshape = d.shape
    importer.SetDataExtent(0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
    importer.SetWholeExtent(0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
    importer.Update()
    imgData = importer.GetOutput()
    #return imgData
    out_img = vtk.vtkImageData()
    out_img.DeepCopy(imgData)
    return out_img


def applyTransform(img, transform, origin2=None, dimension2=None, spacing2=None, interpolate=True):
    """Apply a linear transform to a grid which afterwards resamples the image.
       Be sure to pass the inverse of the transform you would use to transform a point.
       Accepts linear and non linear transforms"""
    if isinstance(transform, (np.matrix, np.ndarray)):
        transform = numpy2vtkMatrix(transform)
    if isinstance(transform, vtk.vtkMatrix4x4):
        vtkTrans = vtk.vtkMatrixToHomogeneousTransform()
        vtkTrans.SetInput(transform)
        transform_i = transform.NewInstance()
        transform_i.DeepCopy(transform)
        transform_i.Invert()
        if origin2 is None:
            #TODO: Use a better strategy to find the new origin; this doesn't work with large rotations or reflections
            origin = img.GetOrigin()
            origin = list(origin) + [1]
            origin2 = transform_i.MultiplyDoublePoint(origin)[:-1]
        if spacing2 is None:
            def get_spacing(i):
                line = [transform_i.GetElement(i, 0), transform_i.GetElement(i, 1), transform_i.GetElement(i, 2)]
                return max(line, key=abs)

            spacing2 = [get_spacing(i) for i in range(3)]
    elif isinstance(transform, vtk.vtkAbstractTransform):
        vtkTrans = transform
        if None == spacing2 or None == origin2:
            print "spacing2 and origin2 are required when using a general transform"
            raise Exception("spacing2 and origin2 are required when using a general transform")
    else:
        print "Method not implemented for %s transform" % type(transform)
        raise Exception("Method not implemented for %s transform" % type(transform))
    if None == dimension2:
        dimension2 = img.GetDimensions()
        #=============================Finished parsing arguments==================================
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
    reslicer.Update()
    outImg = reslicer.GetOutput()
    #print dimension2
    return outImg


def readFlirtMatrix(file_name, src_img_file, ref_img_file, path=''):
    """read a matrix in fsl flirt format: 
    In order to apply this transformation information about 
    the source and ref images is also requierd. The function returns
    the effective transform that can be applied to point data."""
    file_name = os.path.join(path, file_name)
    src_img_file = os.path.join(path, src_img_file)
    ref_img_file = os.path.join(path, ref_img_file)
    mat_file = open(file_name)
    lines = mat_file.readlines()
    mat_file.close()
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


def numpy2vtkMatrix(M):
    "Transform a numpy array into vtk4x4 matrix"
    vtk_matrix = vtk.vtkMatrix4x4()
    for i in range(0, 4):
        for j in range(0, 4):
            vtk_matrix.SetElement(i, j, M[i, j])
    return vtk_matrix


def transformPolyData(poly_data, transform):
    "Kept for compatibility, it is an alias to transformGeneralData"
    output = transformGeneralData(poly_data, transform)
    return output


def transformGeneralData(data, transform):
    "Use a transform or a 4x4Matrix to transform vtkPointData or poly data"
    if isinstance(transform, (np.matrix, np.ndarray)):
        transform = numpy2vtkMatrix(transform)
    if isinstance(transform, vtk.vtkMatrix4x4):
        vtkTrans = vtk.vtkMatrixToLinearTransform()
        vtkTrans.SetInput(transform)
    elif isinstance(transform, vtk.vtkAbstractTransform):
        vtkTrans = transform
    else:
        print "Method not implemented for %s transform" % type(transform)
        raise Exception("Method not implemented for %s transform" % type(transform))
    if isinstance(data, vtk.vtkPolyData):
        transFilter = vtk.vtkTransformPolyDataFilter()
    elif isinstance(data,vtk.vtkDataSet):
        transFilter = vtk.vtkTransformFilter()
    else:
        return vtkTrans.TransformPoint(data)
    transFilter.SetTransform(vtkTrans)
    transFilter.SetInputData(data)
    transFilter.Update()
    output = transFilter.GetOutput()
    return output


def filterPolylinesWithModel(fibers, model, progress=None, do_remove=True):
    """filters a polyline, keeps only the lines that cross a model
    the progress variable is pudated (via its set method) to indicate progress in the filtering operation
    if do_remove is true, the filtered polydata object is returned, otherwise a list of the fibers that do cross the model is returned"""
    selector = vtk.vtkSelectEnclosedPoints()
    selector.Initialize(model)
    model_bb = model.GetBounds()
    valid_fibers = set()
    invalid_fibers = set()
    if progress:
        progress.set(10)
    n = fibers.GetNumberOfCells()
    l = fibers.GetNumberOfLines()
    if n != l:
        print "Input must be a polydata containing only lines"
        raise Exception("Input must be a polydata containing only lines")

    def test_Polyline(cellId):
        i = cellId
        c = fibers.GetCell(i)
        c_bb = c.GetBounds()
        if not boundingBoxIntesection(model_bb, c_bb):
            #fibers.DeleteCell(cellId)
            return False
        pts = c.GetPoints()
        npts = pts.GetNumberOfPoints()
        #inside=False
        pts_list = range(npts)
        random.shuffle(pts_list)
        for j in pts_list:
            p = pts.GetPoint(j)
            if selector.IsInsideSurface(p):
                #inside=True
                return True
            #if not inside:
        return False

    for i in xrange(n):
        if not test_Polyline(i):
            invalid_fibers.add(i)
        else:
            valid_fibers.add(i)
    selector.Complete()
    if do_remove:
        for i in invalid_fibers:
            fibers.DeleteCell(i)
        fibers.RemoveDeletedCells()
        return fibers
    else:
        return valid_fibers


def boundingBoxIntesection(box1, box2):
    "test if two bounding boxes intersect"
    #Test intersection in three axis
    for i in range(3):
        #      2----[1]------2------1                                   1-----[2]-----1------2
        if (box2[2 * i] <= box1[2 * i] <= box2[2 * i + 1]) or (
                    box1[2 * i] <= box2[2 * i] <= box1[2 * i + 1]):
        #      2----[1]-----1-------2                                   1-----[2]-----2-------1 
            pass
        else:
            #Must intersect in all axis
            return False
    return True


def readFreeSurferTransform(filename):
    "Reads a freeSurfer transform file and returns a numpy array"
    try:
        f = open(filename)
        lines = f.readlines()
        trans = lines[-3:]
        trans = [l.split() for l in trans]
        trans = [l[0:4] for l in trans]
        trans_f = [map(float, l) for l in trans]
        trans_f.append([0] * 3 + [1])
        np.array(trans_f)
        nar = np.array(trans_f)
        f.close()
    except IOError:
        print "couldn't open %s" % filename
        raise Exception("couldn't open %s" % filename)

    return nar


def cache_function(max_cache_size):
    "modified classic python @memo decorator to handle some special cases in braviz"

    def decorator(f):
        cache = f.cache = {}
        #print "max cache is %d"%max_cache_size
        #cache will store tuples (output,date)
        max_cache = f.max_cache = max_cache_size

        @functools.wraps(f)
        def cached_f(*args, **kw_args):
            #print "cache size=%d"%len(cache)
            key = str(args) + str(kw_args)
            key = key.upper()
            if key not in cache:
                output = f(*args, **kw_args)
                if output is not None:
                    if len(cache) >= max_cache:
                        oldest = min(cache.items(), key=lambda x: x[1][1])[0]
                        cache.pop(oldest)
                    cache[key] = (output, time.time())
            else:
                output, _ = cache[key]
                cache[key] = (output, time.time())
                #return a copy to keep integrity of objects in cache
            try:
                output_copy = output.NewInstance()
                output_copy.DeepCopy(output)
            except AttributeError:
                #not a vtk object
                try:
                    output_copy = copy.deepcopy(output)
                except:
                    output_copy = output
            return output_copy

        return cached_f

    return decorator


#Easy access to kmc readers
from kmc40 import kmc40Reader
from kmc40 import autoReader as kmc40AutoReader