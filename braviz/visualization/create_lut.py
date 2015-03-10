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


"""Contains functions for transforming ColorBrewer schemes into lookuptables"""
from __future__ import division
import logging

import vtk
import colorbrewer


__author__ = 'Diego'


def get_colorbrewer_lut(minimum, maximum, scheme, steps, invert=False, continuous=True, nan_color=(1.0, 0, 0), skip=0):
    """Creates a vtkColorTransferFunction from a colorbrewer scheme
    the values will be clamped between minimum and maximum,
    the name of the scheme and number of steps must correspond to those in colorbrewer2.org
    if continuous is True the resulting lookuptable interpolates linearly (in Lab space) between the different steps,
    otherwise no interpolation is used and the output function is stair like
    The nan_color is returned by the vtkColorTransferFunction for non finite values"""
    scalar_lookup_table = vtk.vtkColorTransferFunction()

    scalar_lookup_table.ClampingOn()
    scalar_lookup_table.SetColorSpaceToLab()
    # scalar_lookup_table.SetColorSpaceToHSV()
    assert steps > 1
    sharpness = 1
    log = logging.getLogger(__name__)
    if continuous is True:
        sharpness = 0
    # load colorbrewer scheme
    try:
        cb_list = getattr(colorbrewer, scheme)
    except AttributeError:
        log.error(
            "Unknown scheme %s, please look at http://colorbrewer2.org/ for available schemes" % scheme)
        raise

    try:
        cb_list = cb_list[steps]
    except KeyError:
        log.error("this scheme is not available for %d steps" % steps)
        raise

    cb_list = cb_list[skip:]
    steps = steps - skip
    if invert is True:
        cb_list.reverse()
    delta = (maximum - minimum) / (steps - 1)
    scalar_lookup_table.RemoveAllPoints()
    for i in range(steps):
        c_int = cb_list[i]
        c = map(lambda x: x / 255.0, c_int)
        #                                    x            ,r   ,g   , b, midpoint, sharpness
        scalar_lookup_table.AddRGBPoint(
            minimum + delta * i, c[0], c[1], c[2], 0.5,  sharpness)
        # print minimum+delta*i, c_int
    scalar_lookup_table.SetNanColor(nan_color)
    #scalar_lookup_table.AdjustRange((minimum2, maximum2))
    scalar_lookup_table.SetClamping(1)
    return scalar_lookup_table
