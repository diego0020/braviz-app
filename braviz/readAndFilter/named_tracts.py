
__author__ = 'Diego'
# Functions to get special named tracts, All shoud have the signature tract_name(reader,subject,color)
# they return fibers,space tuples, where space is the space of the resulting fibers.. this is used to avoid unnecessary
# transformation of solution
# Functions that don't start with _ will be added to the named tracts index

import os
import functools
import logging

import vtk

from braviz.readAndFilter.tabular_data import get_var_value as __get_var_value
from braviz.readAndFilter.tabular_data import LATERALITY,LEFT_HANDED
from braviz.interaction.structure_metrics import get_right_or_left_hemisphere as __get_right_or_left_hemisphere


def _cached_named_tract(name_tract_func):
    """
    Wraps a named tract function so that it uses the disk cache

    Args:
        name_tract_func (function) : Function to wrap
    """
    @functools.wraps(name_tract_func)
    def cached_func(reader, subject, color,scalars = None):
        log = logging.getLogger(__name__)
        if scalars is None:
            cache_key = 'named_fibs_%s_%s_%s' % (name_tract_func.__name__, subject, color)
        else:
            cache_key = 'named_fibs_%s_%s_%s_%s' % (name_tract_func.__name__, subject, color, scalars)
        out_fib = reader.load_from_cache(cache_key)
        if out_fib is not None:
            return out_fib, name_tract_func(None, None, None,None, get_out_space=True)

        fibers, out_space = name_tract_func(reader, subject, color,scalars)
        reader.save_into_cache(cache_key,fibers)
        return fibers, out_space

    return cached_func


@_cached_named_tract
def cortico_spinal_l(reader, subject, color,scalars, get_out_space=False):
    """
    Gets the left cortico-spinal tract

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Braviz reader
        subject : subject id
        color (str) : color for the output fibers
        get_out_space (bool) : If True return only the space in which the tracts are defined

    Returns:
        vtkPolyData of left cortico-spinal tract
    """
    log = logging.getLogger(__name__)
    if get_out_space is True:
        return 'dartel'
    try:
        tracts = reader.get('fibers', subject, space='dartel', waypoint=['ctx-lh-precentral', 'Brain-Stem'],
                            color=color,scalars=scalars)
    except Exception:
        log.warning("Tracts not found for subject %s" % subject)
        raise


    #first cut
    implicit_plane = vtk.vtkPlane()
    implicit_plane.SetOrigin(6, -61, 80)
    implicit_plane.SetNormal(1, 0, 0)
    extractor = vtk.vtkExtractPolyDataGeometry()
    extractor.SetImplicitFunction(implicit_plane)
    extractor.SetInputData(tracts)

    #second cut
    implicit_plane2 = vtk.vtkPlane()
    implicit_plane2.SetOrigin(36.31049165648922, -77.57854727291647, 28.38018295355981)
    implicit_plane2.SetNormal(0.5489509727116981, 0.8332155694558181, -0.06636749486983169)
    extractor2 = vtk.vtkExtractPolyDataGeometry()
    extractor2.SetImplicitFunction(implicit_plane2)
    extractor2.SetInputConnection(extractor.GetOutputPort())
    extractor2.SetExtractInside(0)
    extractor2.Update()
    tracts3 = extractor2.GetOutput()

    return tracts3, 'dartel'


@_cached_named_tract
def cortico_spinal_r(reader, subject, color ,scalars, get_out_space=False):
    """
    Gets the right corticospinal tract

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Braviz reader
        subject : subject id
        color (str) : color for the output fibers
        get_out_space (bool) : If True return only the space in which the tracts are defined

    Returns:
        vtkPolyData of right cortico-spinal tract
    """
    log = logging.getLogger(__name__)
    if get_out_space is True:
        return 'dartel'
    try:
        tracts = reader.get('fibers', subject, space='dartel', waypoint=['ctx-rh-precentral', 'Brain-Stem'],
                            color=color,scalars=scalars)
    except Exception:
        log.warning("Tracts not found for subject %s" % subject)
        raise Exception("Tracts not found for subject %s" % subject)

    #first cut
    implicit_plane = vtk.vtkPlane()
    implicit_plane.SetOrigin(-6, -61, 80)
    implicit_plane.SetNormal(1, 0, 0)
    extractor = vtk.vtkExtractPolyDataGeometry()
    extractor.SetImplicitFunction(implicit_plane)
    extractor.SetInputData(tracts)
    extractor.SetExtractInside(0)

    #second cut
    implicit_plane2 = vtk.vtkPlane()
    implicit_plane2.SetOrigin(-16.328958156651115, -49.25892912169191, -107.77320322976459)
    implicit_plane2.SetNormal(-0.0627833116822967, 0.993338233060421, 0.09663027742174941)
    extractor2 = vtk.vtkExtractPolyDataGeometry()
    extractor2.SetImplicitFunction(implicit_plane2)
    extractor2.SetInputConnection(extractor.GetOutputPort())
    extractor2.SetExtractInside(0)
    extractor2.Update()
    tracts3 = extractor2.GetOutput()

    #move back to world coordinates
    #tracts3 = reader.transformPointsToSpace(tracts3, 'dartel', subject, inverse=True)
    return tracts3, 'dartel'


def cortico_spinal_d(reader, subject, color,scalars, get_out_space=False):
    """
    Gets the dominant hemisphere corticospinal tract

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Braviz reader
        subject : subject id
        color (str) : color for the output fibers
        get_out_space (bool) : If True return only the space in which the tracts are defined

    Returns:
        vtkPolyData of dominant cortico-spinal tract
    """
    if get_out_space is True:
        return 'dartel'
    laterality = __get_var_value(LATERALITY, int(subject))
    if laterality != LEFT_HANDED:
        lat = 'r'
    else:
        lat = 'l'
    hemi = __get_right_or_left_hemisphere('d', lat)
    if hemi == 'r':
        return cortico_spinal_r(reader, subject, color,scalars)
    elif hemi == 'l':
        return cortico_spinal_l(reader, subject, color,scalars)
    else:
        raise Exception("Unknown laterality")


def cortico_spinal_n(reader, subject, color,scalars, get_out_space=False):
    """
    Gets the non-dominant hemisphere corticospinal tract

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Braviz reader
        subject : subject id
        color (str) : color for the output fibers
        get_out_space (bool) : If True return only the space in which the tracts are defined

    Returns:
        vtkPolyData of non-dominant cortico-spinal tract
    """
    if get_out_space is True:
        return 'dartel'
    laterality = __get_var_value(LATERALITY, int(subject))
    if laterality != LEFT_HANDED:
        lat = 'r'
    else:
        lat = 'l'
    hemi = __get_right_or_left_hemisphere('n', lat)
    if hemi == 'r':
        return cortico_spinal_r(reader, subject, color,scalars)
    elif hemi == 'l':
        return cortico_spinal_l(reader, subject, color,scalars)
    else:
        raise Exception("Unknown laterality")


def corpus_callosum(reader, subject, color,scalars, get_out_space=False):
    """
    Gets the corpus callosum bundle
    

    Args:
        reader (braviz.readAndFilter.base_reader.BaseReader) : Braviz reader
        subject : subject id
        color (str) : color for the output fibers
        get_out_space (bool) : If True return only the space in which the tracts are defined

    Returns:
        vtkPolyData of the corpus callosum bundle
    """
    if get_out_space is True:
        return 'world'
    return reader.get('fibers', subject, operation='or',
                      waypoint=['CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior', 'CC_Posterior'],
                      color=color, scalars=scalars), 'world'


