from __future__ import division

import vtk

import braviz
from braviz.readAndFilter import iter_id_list,extract_poly_data_subset


__author__ = 'Diego'

class FilterBundleWithSphere:
    def __init__(self):
        self.__full_bundle = None
        self.__locator = None

    def set_bundle(self,bundle):
        self.__full_bundle = bundle
        self.__locator = vtk.vtkKdTreePointLocator()
        self.__locator.SetDataSet(self.__full_bundle)
        self.__locator.BuildLocator()

    def filter_bundle_with_sphere(self,center,radius):
        """
        Filter a polydata to keep only the lines which have a point inside a sphere
        """
        if self.__full_bundle is None:
            raise Exception("Set a bundle first")
            return None
        id_list = vtk.vtkIdList()
        self.__locator.FindPointsWithinRadius(radius,center,id_list)
        npts = id_list.GetNumberOfIds()
        valid_cell_ids = set()
        for pt_id in iter_id_list(id_list):
            id_list2 = vtk.vtkIdList()
            self.__full_bundle.GetPointCells(pt_id,id_list2)
            valid_cell_ids.update(iter_id_list(id_list2))

        out_pd = extract_poly_data_subset(self.__full_bundle,valid_cell_ids)
        return out_pd



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
