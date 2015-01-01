# Import and filter
from __future__ import division
import struct
import os
import functools
import itertools
import time
import copy
from collections import OrderedDict
import logging

import nibabel as nib
import vtk
import numpy as np
import psutil

from braviz.readAndFilter.config_file import get_apps_config as __get_config



def memo_ten(f):
    f.vals = {}

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in f.vals:
            val = f(*args, **kwargs)
            if len(f.vals) > 10:
                f.vals.clear()
            f.vals[key] = val
            return val
        else:
            return f.vals[key]

    return wrapped


def nibNii2vtk(nii):
    """Transform a nifti image read by nibabel into a vtkImageData"""
    d = nii.get_data()
    return numpy2vtk_img(d)


def numpy2vtk_img(d, data_type=None):
    """Transform a 3d numpy array into a vtk image data object"""
    data_type = d.dtype
    importer = vtk.vtkImageImport()
    assert isinstance(d, np.ndarray)
    importer.SetDataScalarTypeToShort() # default
    if data_type is None:
        data_type = data_type.type
    if data_type == np.float64:
        importer.SetDataScalarTypeToDouble()
    elif data_type == np.float32:
        importer.SetDataScalarTypeToFloat()
    elif data_type == np.int32:
        importer.SetDataScalarTypeToInt()
    elif data_type == np.int16:
        importer.SetDataScalarTypeToShort()
    elif data_type == np.uint8:
        importer.SetDataScalarTypeToUnsignedChar()
    else:
        log = logging.getLogger(__name__)
        log.warning("casting to float64")
        importer.SetDataScalarTypeToDouble()
        d = d.astype(np.float64)
        #======================================
    dstring = d.flatten(order='F').tostring()
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


def nifti_rgb2vtk(nifti_rgb):
    data = nifti_rgb.get_data()
    data2 = np.rollaxis(data, 3, 0)
    importer = vtk.vtkImageImport()

    importer.SetDataScalarTypeToUnsignedChar()
    importer.SetNumberOfScalarComponents(3)
    dstring = data2.flatten(order='F').tostring()
    importer.CopyImportVoidPointer(dstring, len(dstring))
    dshape = data.shape
    importer.SetDataExtent(0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)
    importer.SetWholeExtent(0, dshape[0] - 1, 0, dshape[1] - 1, 0, dshape[2] - 1)

    importer.Update()
    img = importer.GetOutput()

    out_img = vtk.vtkImageData()
    out_img.DeepCopy(img)
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
        if origin2 is None or spacing2 is None:
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
            log = logging.getLogger(__name__)
            log.error("spacing2 and origin2 are required when using a general transform")
            raise Exception("spacing2 and origin2 are required when using a general transform")
    else:
        log = logging.getLogger(__name__)
        log.error("Method not implemented for %s transform" % type(transform))
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
    else:
        reslicer.SetInterpolationModeToCubic()
    reslicer.Update()
    outImg = reslicer.GetOutput()
    #print dimension2
    return outImg


@memo_ten
def readFlirtMatrix(file_name, src_img_file, ref_img_file, path=''):
    """read a matrix in fsl flirt format: 
    In order to apply this transformation information about 
    the source and ref images is also requierd. The function returns
    the effective transform that can be applied to point data."""
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
        if isinstance(vtkTrans, vtk.vtkGridTransform):
            vtkTrans.SetInterpolationModeToCubic()
    else:
        log = logging.getLogger(__name__)
        log.error("Method not implemented for %s transform" % type(transform))
        raise Exception("Method not implemented for %s transform" % type(transform))
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
        with open(filename) as f:
            lines = f.readlines()
            trans = lines[-3:]
            trans = [l.split() for l in trans]
            trans = [l[0:4] for l in trans]
            #possible semicolomg in the last term
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


class LastUpdatedOrderedDict(OrderedDict):
    'Store items in the order the keys were last added'

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)


class CacheContainer(object):
    def __init__(self, max_cache=500):
        self.__cache = LastUpdatedOrderedDict()
        self.__max_cache = max_cache

    @property
    def max_cache(self):
        return self.__max_cache

    @max_cache.setter
    def max_cache(self, val):
        self.__max_cache = val

    @property
    def cache(self):
        return self.__cache

    def clear(self):
        self.__cache.clear()


def cache_function(cache_container):
    "modified classic python @memo decorator to handle some special cases in braviz"

    def decorator(f):
        f.cache_container = cache_container
        f.cache = f.cache_container.cache
        #print "max cache is %d"%max_cache_size
        #cache will store tuples (output,date)

        @functools.wraps(f)
        def cached_f(*args, **kw_args):
            #print "cache size=%d"%len(cache)
            key = str(args) + str(kw_args)
            key = key.upper()
            if key not in f.cache:
                output = f(*args, **kw_args)
                if output is not None:
                    #new method to test memory in cache
                    process_id = psutil.Process(os.getpid())
                    mem = process_id.get_memory_info()[0] / (2 ** 20)
                    if mem >= f.cache_container.max_cache:
                        log = logging.getLogger(__name__)
                        log.info("freeing cache")
                        try:
                            while mem > 0.9 * f.cache_container.max_cache:
                                for i in xrange(len(f.cache) // 10 + 1):
                                    rem_key, val = f.cache.popitem(last=False)
                                    #print "removing %s with access time= %s"%(rem_key,val[1])
                                mem = process_id.get_memory_info()[0] / (2 ** 20)
                        except KeyError:
                            log = logging.getLogger(__name__)
                            log.warning("Cache is empty and memory still too high! check your program for memory leaks")
                    f.cache[key] = (output, time.time())
            else:
                output, _ = f.cache[key]
                #update access time
                f.cache[key] = (output, time.time())
                #return a copy to keep integrity of objects in cache
            try:
                output_copy = output.NewInstance()
                output_copy.DeepCopy(output)
            except AttributeError:
                #not a vtk object
                try:
                    output_copy = copy.deepcopy(output)
                except Exception:
                    output_copy = output
            return output_copy

        return cached_f

    return decorator


def write_vtk_image(image_data, out_file):
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
    nib_img = nib.Nifti1Image(data, affine=affine)
    nib_img.to_filename(out_file)
    print out_file
    return


from filter_fibers import filter_polylines_with_img, filterPolylinesWithModel, extract_poly_data_subset, \
    filter_polylines_by_scalar

#Easy access to kmc readers

#read configuration file and decide which project to expose
__config = __get_config()
PROJECT = __config.get_project_name()


def get_reader_class(project):
    import importlib
    import inspect
    from braviz.readAndFilter.base_reader import BaseReader
    #todo filter by being instance of base_reader
    module = importlib.import_module('braviz.readAndFilter.%s' % project)
    pred = lambda c: inspect.isclass(c) and issubclass(c, BaseReader)
    candidate_classes = [c for c in inspect.getmembers(module, pred)]
    project_upper = project.upper()
    candidate_classes2 = sorted([c for c in candidate_classes if c[0].upper().startswith(project_upper)],
                                key=lambda x: x[0])

    return candidate_classes2[0][1]


project_reader = get_reader_class(PROJECT)

BravizAutoReader = project_reader.get_auto_reader
braviz_auto_data_root = project_reader.get_auto_data_root
braviz_auto_dynamic_data_root = project_reader.get_auto_dyn_data_root

if __name__ == "__main__":
    __root = braviz_auto_data_root()
    __reader = BravizAutoReader()
    print __root
