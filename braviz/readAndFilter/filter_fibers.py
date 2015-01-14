##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

from __future__ import division

import vtk

import braviz
import numpy as np
import logging


__author__ = 'Diego'


def iter_id_list(id_list):
    """
    Iterate over a vtkIdList

    Args:
        id_list (vtkIdList) : Id List

    Yields:
        Point ids
    """
    n = id_list.GetNumberOfIds()
    for i in xrange(n):
        id_i = id_list.GetId(i)
        yield id_i

def abstract_test_lines_in_polyline(fibers,predicate):
    """
    Extract lines where at least one point makes predicate True.

    Args:
        fibers (vtkPolyData) : Tractography
        predicate (function) : Should take point coordinates and return a boolean

    Returns:
        Set of cells where the predicate is True for at least one point
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
            if predicate(p):
                #inside=True
                return True
            #if not inside:
        return False

    for i in xrange(n):
        if test_polyline(i):
            valid_fibers.add(i)
    return valid_fibers



def extract_poly_data_subset(polydata,id_list):
    """
    Extracts polylines with given ids from polydata

    Args:
        polydata (vtkPolyData) : Full polydata
        id_list (list) : List of cell ids

    Returns:
        A vtkPolyData containing only the requested cells.
    """
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

class FilterBundleWithSphere(object):
    """
    A class to interactively filter a polydata with a moving sphere
    """
    def __init__(self):
        """
        A class to interactively filter a polydata with a moving sphere
        """
        self.__full_bundle = None
        self.__locator = None

    def set_bundle(self,bundle):
        """
        Set the base polydata

        Args:
            bundle (vtkPolyData) : base bundle
        """
        self.__full_bundle = bundle
        self.__locator = vtk.vtkKdTreePointLocator()
        self.__locator.SetDataSet(self.__full_bundle)
        self.__locator.BuildLocator()

    def filter_bundle_with_sphere(self,center,radius,get_ids = False):
        """
        Filter polydata to keep only the lines which have a point inside a sphere

        Args:
            center (tuple) : Sphere center (x,y,z)
            radius (float) : Sphere radius
            get_ids (bool) : get ids or filtered polydata

        Returns:
            If get_ids is True the ids of the satisfying cells are returned, otherwise a filtered vtkPolydata is
                returned
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

def filterPolylinesWithModel(fibers, model):
    """filters a polyline, keeps only the lines that cross a model

    Args:
        fibers (vtkPolyData) : Tractography
        model (vtkPolyData) : Structure model (closed surface)

    Returns:
        Set of polyline ids where the line goes through the model
    """
    selector = vtk.vtkSelectEnclosedPoints()
    selector.Initialize(model)
    def test_point_inside_model(p):
        if selector.IsInsideSurface(p):
            return True
        else:
            return False

    valid_fibers = abstract_test_lines_in_polyline(fibers,test_point_inside_model)
    selector.Complete()
    return valid_fibers



def filter_polylines_with_img_slow(polydata,img,label):
    """
    Slow version of :func:`filter_polylines_with_img`
    """
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


def filter_polylines_with_img(polydata,img,label):
    """
    Filter polydata based on labels found in an image.

    For each point in the polyline the function finds the corresponding label in the image. Only lines where at least
    one point has the requested label are left in the output set.

    Args:
        polydata (vtkPolyData) : Full tractography polydata
        img (nibabel.spatialimages.SpatialImage) : Label map, should be in same coordinate system as polydata
        label (int) : Label of interest

    Returns:
        Set of CellIds where at least one point gets the requested label
    """

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
        coords_i = np.round(coords).astype(np.int)
        #interpolates, too slow
        vals = data[coords_i[:,0],coords_i[:,1],coords_i[:,2]]
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

def filter_polylines_by_scalar(fibs,scalar):
    """
    Finds lines where at least one point has a scalar value in the range (scalar -0.5, scalar + 0.5)

    Args:
        fibs (vtkPolyData) : Full polydata with scalar data
        scalar (float) : scalar value to look for

    Returns:
        Cell ids where at least one point has a scalar in the range (scalar -0.5, scalar + 0.5)
    """
    selection = vtk.vtkSelection()
    selection_node = vtk.vtkSelectionNode()
    selection_node.GetProperties().Set(vtk.vtkSelectionNode.CONTENT_TYPE(), vtk.vtkSelectionNode.THRESHOLDS)
    selection_node.GetProperties().Set(vtk.vtkSelectionNode.FIELD_TYPE(), vtk.vtkSelectionNode.POINT)
    selection.AddNode(selection_node)

    array = vtk.vtkDoubleArray()
    array.SetNumberOfComponents(1)
    array.InsertNextValue(scalar-.5)
    array.InsertNextValue(scalar+.5)
    selection_node.SetSelectionList(array)
    extract_lines = vtk.vtkExtractSelection()
    extract_lines.SetInputData(1, selection)
    extract_lines.SetInputData(0, fibs)
    extract_lines.PreserveTopologyOff()
    extract_lines.Update()
    out = extract_lines.GetOutput()
    out_ids = out.GetPointData().GetScalars("vtkOriginalPointIds")

    valid_cell_ids = set()
    for i in xrange(out_ids.GetNumberOfTuples()):
        pt_id = int(out_ids.GetTuple(i)[0])
        id_list2 = vtk.vtkIdList()
        fibs.GetPointCells(pt_id,id_list2)
        valid_cell_ids.update(iter_id_list(id_list2))

    return valid_cell_ids

if __name__ == "__main__":
    reader = braviz.readAndFilter.BravizAutoReader()
    fibers = reader.get("fibers","093")
    r=20
    ctr = (32,-43,9)
    test_filter = FilterBundleWithSphere()
    test_filter.set_bundle(fibers)
    out = test_filter.filter_bundle_with_sphere(ctr,r)
    viewer = simpleVtkViewer()
    viewer.addPolyData(out)
    viewer.start()


def boundingBoxIntesection(box1, box2):
    """test if two bounding boxes intersect

    Args:
        box1 (list) : Bounding box [x0, x1, y0, y1, z0, z1]
        box2 (list) : Bounding box [x0, x1, y0, y1, z0, z1]

    Returns:
        ``True`` if the bounding boxes intersect, ``False`` otherwise

    """
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