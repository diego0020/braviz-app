from __future__ import division
import vtk
import colorbrewer


__author__ = 'Diego'


def get_colorbrewer_lut(minimum,maximum,scheme,steps,continuous=True,nan_color=(1.0,0,0)):
    #build lut
    scalar_lookup_table = vtk.vtkColorTransferFunction()

    scalar_lookup_table.ClampingOn()
    scalar_lookup_table.SetColorSpaceToLab()
    width=maximum-minimum
    #scalar_lookup_table.SetRange(minimum, maximum)
    #minimum-=0.001*width
    #maximum+=0.001*width
    #scalar_lookup_table.Build()
    assert steps>1
    sharpness=1
    if continuous is True:
        sharpness=0
    #load colorbrewer scheme
    try:
        cb_list=getattr(colorbrewer,scheme)
    except AttributeError:
        print "Unknown scheme %s, please look at http://colorbrewer2.org/ for available strings"%scheme
        raise

    try:
        cb_list=cb_list[steps]
    except KeyError:
        print "this scheme is not available for %d steps"%steps
        raise

    delta=(maximum-minimum)/(steps-1)
    scalar_lookup_table.RemoveAllPoints()
    for i in range(steps):
        c_int = cb_list[i]
        c=map(lambda x:x/256.0 , c_int)
        #                                    x            ,r   ,g   , b, midpoint, sharpness
        scalar_lookup_table.AddRGBPoint(minimum+delta*i,c[0],c[1],c[2], 0.5,  sharpness)
    scalar_lookup_table.SetNanColor(nan_color)
    #scalar_lookup_table.AdjustRange((minimum2, maximum2))
    scalar_lookup_table.SetClamping(1)
    return scalar_lookup_table