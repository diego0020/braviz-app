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


from __future__ import division
import random
import math

import vtk
import numpy as np
from scipy import ndimage


def color_by_z(pt):
    """
    Color a point based on its 'z' coordinate

    Args:
        pt (tuple) : Point coordinates

    Returns:
        (r,g,b)
    """
    z = pt[2]
    z_norm = (z + 60) / (60 + 75)
    z_col = int(255 * z_norm)
    z_col = np.clip(z_col, 0, 255)
    color = (0, z_col, 0)
    return color


def color_by_fa(pt, fa_img):
    """
    Calculates color based on an FA img

    .. deprecated:: 3.0
        Use scalars instead

    Args:
        pt (tuple) : points coordinates
        fa_img (vtkImageData) : FA image

    Returns:
        (r,g,b)
    """
    org = fa_img.GetOrigin()
    delta = fa_img.GetSpacing()
    v_pt = np.subtract(pt, org)
    v_pt = v_pt / delta

    r_pt = map(round, v_pt)
    r_pt = r_pt + [0]
    r_pt = map(int, r_pt)
    fa = fa_img.GetScalarComponentAsDouble(*r_pt)
    fa = np.clip(fa, 0, 1)
    red = int(fa * 255)
    color = (red, 0, 0)
    return color


def color_fibers_pts(fibers, color_function, *args, **kw):
    """
    Apply a function to assign color for each point in a tractography

    Args:
        fibers (vtkPolyData) : Tractography
        color_function (function) : Function that takes point coordinates and returns a color tuple
        *args : extra positional arguments passed to ``color_function``
        **kwargs : extra keyword arguments passed to ``color_function``

    """
    n_pts = fibers.GetNumberOfPoints()
    pts = fibers.GetPoints()
    scalars = fibers.GetPointData().GetScalars()
    for i in xrange(n_pts):
        point = pts.GetPoint(i)
        color = color_function(point, *args, **kw)
        scalars.SetTupleValue(i, color)


def color_fibers_lines(fibers, polyline_color_function, *args, **kw):
    """
    Applies a function to each line in a tractography to assign it a color

    Args:
        fibers (vtkPolyData) : Tractography
        polyline_color_function (function) : Function that takes a vtkCell and returns a dict mapping point ids
            to colors
        *args : extra positional arguments passed to ``polyline_color_function``
        **kwargs : extra keyword arguments passed to ``polyline_color_function``
    """

    nlines = fibers.GetNumberOfLines()
    ncells = fibers.GetNumberOfCells()
    if nlines != ncells:
        raise Exception('fibers must have only polylines')
    scalars = fibers.GetPointData().GetScalars()
    for i in xrange(nlines):
        l = fibers.GetCell(i)
        color_dict = polyline_color_function(l, *args, **kw)
        for pt, c in color_dict.iteritems():
            scalars.SetTupleValue(pt, c)


def random_line(line):
    """
    Creates a random color and maps the whole line to it

    Args:
        line (vtkCell) : Polyline

    Returns:
        Dictionary from all point ids to the random color
    """
    color = [random.randint(0, 255) for i in ('r', 'g', 'b')]
    pts = line.GetPointIds()
    color_dict = {}
    for i in xrange(pts.GetNumberOfIds()):
        color_dict[pts.GetId(i)] = color
    return color_dict


def line_curvature(line):
    """
    Calculates a color based on the curvature of the polyline

    Implements the simple formula from http://en.wikipedia.org/wiki/Curvature

    Args:
        line (vtkCell) : Polyline

    Returns:
        Dictionary from all point ids to the random color

    """

    ids = line.GetPointIds()
    pts = line.GetPoints()
    color_dict = {}
    # require 3 points
    for i in xrange(1, line.GetNumberOfPoints() - 1):
        p0, p1, p2 = [np.array(pts.GetPoint(j)) for j in range(i - 1, i + 2)]
        arch = np.linalg.norm(p0 - p1) + np.linalg.norm(p2 - p1)
        chord = np.linalg.norm(p0 - p2)
        curv = np.sqrt(24 * (arch - chord) / arch**3)
        curv = np.clip(curv, 0, 0.5)
        if math.isnan(curv):
            curv = 0
        color = (135, 255, 255)
        color = np.dot(curv * 2, color)
        color = map(int, color)
        color_dict[ids.GetId(i)] = color
    # Extremes
    color_dict[ids.GetId(0)] = color_dict[ids.GetId(1)]
    color_dict[ids.GetId(line.GetNumberOfPoints() - 1)
               ] = color_dict[ids.GetId(line.GetNumberOfPoints() - 2)]
    return color_dict


def scalars_from_image(fibers, nifti_image):
    """
    Assigns scalars taken from an image to a polydata

    Args:
        fibers (vtkPolyData) : Tractography
        nifti_image (nibabel.spatialimages.SpatialImage) : Image to grab scalars from. It should be on the same
            coordinates system as the tractography

    """

    affine = nifti_image.get_affine()
    iaffine = np.linalg.inv(affine)
    data = nifti_image.get_data()

    # update scalars
    # remove colors array
    pd = fibers.GetPointData()
    pd.RemoveArray(0)

    npoints = fibers.GetNumberOfPoints()
    new_array = vtk.vtkDoubleArray()
    new_array.SetNumberOfTuples(npoints)
    new_array.SetNumberOfComponents(1)

    coords = np.array([fibers.GetPoint(i) + (1,) for i in xrange(npoints)])
    coords = np.dot(iaffine, coords.T)
    coords = coords[:3] / coords[3]
    coords = coords.reshape(3, -1)
    image_val = ndimage.map_coordinates(data, coords, mode="nearest")
    for i in xrange(npoints):
        new_array.SetComponent(i, 0, image_val[i])

    pd.SetScalars(new_array)


def scalars_from_image_int(fibers, nifti_image):
    """
    Assigns scalars taken from an image to a polydata without interpolation (nearest neighbour)

    Args:
        fibers (vtkPolyData) : Tractography
        nifti_image (nibabel.spatialimages.SpatialImage) : Image to grab scalars from. It should be on the same
            coordinates system as the tractography

    """

    affine = nifti_image.get_affine()
    iaffine = np.linalg.inv(affine)
    data = nifti_image.get_data()

    # update scalars
    # remove colors array
    pd = fibers.GetPointData()
    pd.RemoveArray(0)

    npoints = fibers.GetNumberOfPoints()
    new_array = vtk.vtkIntArray()
    new_array.SetNumberOfTuples(npoints)
    new_array.SetNumberOfComponents(1)

    coords = np.array([fibers.GetPoint(i) + (1,) for i in xrange(npoints)])
    coords = np.dot(iaffine, coords.T)
    coords = coords[:3] / coords[3]
    coords = coords.reshape(3, -1)
    coords = coords.astype(np.int)

    image_val = data[coords[0], coords[1], coords[2]]
    for i in xrange(npoints):
        new_array.SetComponent(i, 0, image_val[i])

    pd.SetScalars(new_array)


def scalars_lines_from_image(fibers, nifti_image):
    """
    Averages scalars along lines and assigns one scalar to each line, based on an image

    Args:
        fibers (vtkPolyData) : Tractography
        nifti_image (nibabel.spatialimages.SpatialImage) : Image to grab scalars from. It should be on the same
            coordinates system as the tractography

    """
    affine = nifti_image.get_affine()
    iaffine = np.linalg.inv(affine)
    data = nifti_image.get_data()

    # update scalars
    # remove colors array
    pd = fibers.GetPointData()
    pd.RemoveArray(0)

    cd = fibers.GetCellData()
    ncells = fibers.GetNumberOfCells()
    new_array = vtk.vtkDoubleArray()
    new_array.SetNumberOfTuples(ncells)
    new_array.SetNumberOfComponents(1)

    npoints = fibers.GetNumberOfPoints()
    coords = np.array([fibers.GetPoint(i) + (1,) for i in xrange(npoints)])
    coords = np.dot(iaffine, coords.T)
    coords = coords[:3] / coords[3]
    coords = coords.reshape(3, -1)
    image_val = ndimage.map_coordinates(data, coords, mode="nearest")

    for i in xrange(ncells):
        c = fibers.GetCell(i)
        npts = c.GetNumberOfPoints()
        point_values = [image_val[c.GetPointId(j)] for j in xrange(npts)]
        value = np.mean(point_values)
        new_array.SetComponent(i, 0, value)

    cd.SetScalars(new_array)


def scalars_from_length(fibers):
    """
    Assigns scalars to each line representing its length

    Args:
        fibers (vtkPolyData) : Tractography

    """
    pd = fibers.GetPointData()
    pd.RemoveArray(0)
    ncells = fibers.GetNumberOfCells()
    new_array = vtk.vtkDoubleArray()
    new_array.SetNumberOfTuples(ncells)
    new_array.SetNumberOfComponents(1)
    for i in xrange(ncells):
        c = fibers.GetCell(i)
        npts = c.GetNumberOfPoints()

        length = 0
        last_point = None
        for j in xrange(1, npts):
            p_id = c.GetPointId(j)
            coords = np.array(fibers.GetPoint(p_id))
            if last_point is not None:
                step = np.linalg.norm(coords - last_point)
                length += step
            last_point = coords

        value = length
        new_array.SetComponent(i, 0, value)
    cd = fibers.GetCellData()
    cd.SetScalars(new_array)


def get_fa_lut():
    """
    A generic FA lookuptable

    Returns:
        vtkColorTransferFunction
    """
    import braviz.visualization
    lut = braviz.visualization.get_colorbrewer_lut(
        0.35, 0.82, "YlGn", 9, invert=True, continuous=True, skip=1)
    return lut


def get_length_lut():
    """
    A generic length lookuptable

    Returns:
        vtkColorTransferFunction
    """
    import braviz.visualization
    lut = braviz.visualization.get_colorbrewer_lut(
        41, 125, "YlOrBr", 9, invert=True)
    return lut

if __name__ == "__main__":
    import braviz
    import os
    from braviz.utilities import configure_logger_from_conf
    from braviz.readAndFilter.config_file import get_apps_config
    import logging
    configure_logger_from_conf(__file__)
    reader = braviz.readAndFilter.BravizAutoReader()
    conf = get_apps_config()
    subj = conf.get_default_subject()
    log = logging.getLogger(__name__)
    log.info("md_p")
    pd = reader.get("fibers", subj, scalars="md_p")
    log.info("md_l")
    pd = reader.get("fibers", subj, scalars="md_l")
    log.info("aparc")
    pd = reader.get("fibers", subj, scalars="aparc")
