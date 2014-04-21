"""Contains functions for transforming ColorBrewer schemes into lookuptables"""
from __future__ import division
import vtk
import colorbrewer


__author__ = 'Diego'


def get_colorbrewer_lut(minimum,maximum,scheme,steps,continuous=True,nan_color=(1.0,0,0),invert=False,skip=0):
    """Creates a vtkColorTransferFunction from a colorbrewer scheme
    the values will be clamped between minimum and maximum,
    the name of the scheme and number of steps must correspond to those in colorbrewer2.org
    if continuous is True the resulting lookuptable interpolates linearly (in Lab space) between the different steps,
    otherwise no interpolation is used and the output function is stair like
    The nan_color is returned by the vtkColorTransferFunction for non finite values"""
    scalar_lookup_table = vtk.vtkColorTransferFunction()

    scalar_lookup_table.ClampingOn()
    scalar_lookup_table.SetColorSpaceToLab()
    #scalar_lookup_table.SetColorSpaceToHSV()
    assert steps>1
    sharpness=1
    if continuous is True:
        sharpness=0
    #load colorbrewer scheme
    try:
        cb_list=getattr(colorbrewer,scheme)
    except AttributeError:
        print "Unknown scheme %s, please look at http://colorbrewer2.org/ for available schemes"%scheme
        raise

    try:
        cb_list=cb_list[steps]
    except KeyError:
        print "this scheme is not available for %d steps"%steps
        raise

    cb_list = cb_list[skip:]
    steps = steps-skip
    if invert is True:
        cb_list.reverse()
    delta=(maximum-minimum)/(steps-1)
    scalar_lookup_table.RemoveAllPoints()
    for i in range(steps):
        c_int = cb_list[i]
        c=map(lambda x:x/255.0 , c_int)
        #                                    x            ,r   ,g   , b, midpoint, sharpness
        scalar_lookup_table.AddRGBPoint(minimum+delta*i,c[0],c[1],c[2], 0.5,  sharpness)
        #print minimum+delta*i, c_int
    scalar_lookup_table.SetNanColor(nan_color)
    #scalar_lookup_table.AdjustRange((minimum2, maximum2))
    scalar_lookup_table.SetClamping(1)
    return scalar_lookup_table