from __future__ import division

import vtk

import braviz
import numpy as np
import logging
from scipy import ndimage

__author__ = 'Diego'


def iter_id_list(id_list):
    n = id_list.GetNumberOfIds()
    for i in xrange(n):
        id_i = id_list.GetId(i)
        yield id_i

def abstract_test_lines_in_polyline(fibers,test_point_fun):
    """
    return a list of line_ids where at least one of the points passes the condition test_point_fun(p) == True
    """
    valid_fibers = set()
    n = fibers.GetNumberOfCells()
    l = fibers.GetNumberOfLines()
    if n != l:
        log = logging.getLogger(__name__)
        log.error("Input must be a polydata containing only lines")
        raise Exception("Input must be a polydata containing only lines")
    def test_polyline(cellId):
        i = cellId
        c = fibers.GetCell(i)
        pts = c.GetPoints()
        npts = pts.GetNumberOfPoints()
        #inside=False
        for j in xrange(npts):
            p = pts.GetPoint(j)
            if test_point_fun(p):
                #inside=True
                return True
            #if not inside:
        return False

    for i in xrange(n):
        if test_polyline(i):
            valid_fibers.add(i)
    return valid_fibers



def extract_poly_data_subset(polydata,id_list):
    extract_lines = vtk.vtkExtractSelectedPolyDataIds()
    cleaner = vtk.vtkCleanPolyData()
    if isinstance(id_list,vtk.vtkIdTypeArray):
        id_array=id_list
    else:
        id_array = vtk.vtkIdTypeArray()
        id_array.SetNumberOfTuples(len(id_list))
        for i, cell_id in enumerate(id_list):
            id_array.SetTuple1(i, cell_id)
    selection = vtk.vtkSelection()
    selection_node = vtk.vtkSelectionNode()
    selection_node.GetProperties().Set(vtk.vtkSelectionNode.CONTENT_TYPE(), vtk.vtkSelectionNode.INDICES)
    selection_node.GetProperties().Set(vtk.vtkSelectionNode.FIELD_TYPE(), vtk.vtkSelectionNode.CELL)
    selection.AddNode(selection_node)
    selection_node.SetSelectionList(id_array)
    extract_lines.SetInputData(1, selection)
    extract_lines.SetInputData(0, polydata)
    #extract_lines.Update()
    cleaner.SetInputConnection(extract_lines.GetOutputPort())
    cleaner.PointMergingOff()
    cleaner.Update()
    fib2 = cleaner.GetOutput()
    return fib2

class FilterBundleWithSphere:
    def __init__(self):
        self.__full_bundle = None
        self.__locator = None

    def set_bundle(self,bundle):
        self.__full_bundle = bundle
        self.__locator = vtk.vtkKdTreePointLocator()
        self.__locator.SetDataSet(self.__full_bundle)
        self.__locator.BuildLocator()

    def filter_bundle_with_sphere(self,center,radius,get_ids = False):
        """
        Filter a polydata to keep only the lines which have a point inside a sphere
        """
        if self.__full_bundle is None:
            raise Exception("Set a bundle first")
            return None
        id_list = vtk.vtkIdList()
        self.__locator.FindPointsWithinRadius(radius,center,id_list)
        valid_cell_ids = set()
        for pt_id in iter_id_list(id_list):
            id_list2 = vtk.vtkIdList()
            self.__full_bundle.GetPointCells(pt_id,id_list2)
            valid_cell_ids.update(iter_id_list(id_list2))

        if get_ids is True:
            return valid_cell_ids
        out_pd = extract_poly_data_subset(self.__full_bundle,valid_cell_ids)
        return out_pd

def filterPolylinesWithModel(fibers, model, progress=None, do_remove=True):
    """filters a polyline, keeps only the lines that cross a model
    the progress variable is pudated (via its set method) to indicate progress in the filtering operation
    if do_remove is true, the filtered polydata object is returned,
     otherwise a list of the fibers that do cross the model is returned"""
    selector = vtk.vtkSelectEnclosedPoints()
    selector.Initialize(model)
    if progress:
        log = logging.getLogger(__name__)
        log.warning("use of this progress argument is deprecated")
        progress.set(0)
    def test_point_inside_model(p):
        if selector.IsInsideSurface(p):
            return True
        else:
            return False

    valid_fibers = abstract_test_lines_in_polyline(fibers,test_point_inside_model)
    selector.Complete()
    if do_remove is False:
        return valid_fibers
    else:
        raise Exception("Deprecated, you may use extract_poly_data_subset")


def filter_polylines_with_img(polydata,img,label,do_remove=False):
    """
    img should be in the nibabel format
    """
    #TODO, do it all with numpy arrays, only one for
    if do_remove is True:
        raise NotImplementedError
    affine = img.get_affine()
    i_affine = np.linalg.inv(affine)
    data = img.get_data()
    label = data.dtype.type(label)
    def test_point_in_img(p):
        n_p = np.ones(4)
        n_p[:3] = p
        coords_h = i_affine.dot(n_p)
        coords = coords_h[:3]/coords_h[3]
        coords_i = np.round(coords)
        try:
            v = data[tuple(coords_i)]
        except IndexError:
            v = None
        return v == label
    valid_fibers = abstract_test_lines_in_polyline(polydata,test_point_in_img)
    return valid_fibers


def filter_polylines_with_img_numpy_slow(polydata,img,label,do_remove=False):
    """
    img should be in the nibabel format
    """
    if do_remove is True:
        raise NotImplementedError
    affine = img.get_affine()
    i_affine = np.linalg.inv(affine)
    data = img.get_data()
    label = data.dtype.type(label)
    def test_poly_line(cell):
        pts = cell.GetPoints()
        n_pts = pts.GetNumberOfPoints()
        points_array = np.ones((n_pts,4))
        for i in xrange(n_pts):
            points_array[i,:3]=pts.GetPoint(i)
        coords_h = i_affine.dot(points_array.T).T
        coords = coords_h[:,:3]
        divisors = np.repeat(coords_h[:,3:],3,axis=1)
        coords = coords/divisors
        coords_i = np.round(coords)
        vals = ndimage.map_coordinates(data,coords_i.T)
        if np.any(vals==label):
            return True
        else:
            return False
    n = polydata.GetNumberOfCells()
    l = polydata.GetNumberOfLines()
    if n != l:
        log = logging.getLogger(__name__)
        log.error("Input must be a polydata containing only lines")
        raise Exception("Input must be a polydata containing only lines")
    valid_fibers = set(i for i in xrange(n) if test_poly_line(polydata.GetCell(i)))
    return valid_fibers

def filter_polylines_with_img_vtk(fibs,img,scalar):
    #paint fibs with image
    #threshold polydata
    #extract cells

    pass

if __name__ == "__main__":
    reader = braviz.readAndFilter.BravizAutoReader()
    fibers = reader.get("fibers","093")
    r=20
    ctr = (32,-43,9)
    test_filter = FilterBundleWithSphere()
    test_filter.set_bundle(fibers)
    out = test_filter.filter_bundle_with_sphere(ctr,r)
    viewer = braviz.visualization.simpleVtkViewer()
    viewer.addPolyData(out)
    viewer.start()
