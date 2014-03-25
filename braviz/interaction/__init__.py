"""This module provides access to common operations on data and common interaction components"""

from __future__ import division
import vtk
import numpy as np


def compute_volume_and_area(struct):
    """Returns (volume,surface) of a polydata closed surface"""
    massProperty = vtk.vtkMassProperties()
    triangleFilter = vtk.vtkTriangleFilter()
    triangleFilter.SetInputData(struct)
    massProperty.SetInputConnection(triangleFilter.GetOutputPort())
    massProperty.Update()
    surface = massProperty.GetSurfaceArea()
    volume = massProperty.GetVolume()
    return volume, surface


def compute_fiber_lengths(fib):
    """Returns a dictionary mapping line ids to line lengths"""
    if not fib.GetNumberOfLines() == fib.GetNumberOfCells():
        print "Error, fib must contain only lines"
        raise Exception("Error, fib must contain only lines")
    lengths = {}

    def line_length(pl):
        """Calculates the length of a polyline"""
        npts = pl.GetNumberOfPoints()
        length = 0
        pts = pl.GetPoints()
        pt1 = pts.GetPoint(0)
        for i in xrange(1, npts):
            pt2 = pts.GetPoint(i)
            length += np.linalg.norm(np.subtract(pt1, pt2))
            pt1 = pt2
        return length

    for i in xrange(fib.GetNumberOfLines()):
        lengths[i] = line_length(fib.GetCell(i))
    return lengths


def get_fiber_bundle_descriptors(fib):
    """Returns ( number of fibers, mean length, max length, min length, standard deviation of length) """
    d = compute_fiber_lengths(fib).values()
    if len(d) == 0:
        d = [0]
    return len(d), np.mean(d), np.max(d), np.min(d), np.std(d)


def aggregate_fiber_scalar(fib, component=0, norm_factor=1.0 / 255):
    """Calculates descriptive statistics (n,mean,max,min,std) from the point scalars in a polydata"""
    scalars = fib.GetPointData().GetScalars()
    if scalars is None or scalars.GetNumberOfTuples() == 0:
        d = [float('nan')]
    else:
        d = []
        for i in xrange(scalars.GetNumberOfTuples()):
            d.append(scalars.GetTuple(i)[component])
        d = np.dot(d, norm_factor)
    return len(d), np.mean(d), np.max(d), np.min(d), np.std(d)

