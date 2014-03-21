__author__ = 'Diego'
# Functions to get special named tracts, All shoud have the signature tract_name(reader,subject,color)
# they return fibers,space tuples, where space is the space of the resulting fibers.. this is used to avoid unnecessary
# transformation of solution
# Functions that don't start with _ will be added to the named tracts index

import os
import functools

import vtk

from braviz.readAndFilter.tabular_data import get_var_value as __get_var_value
from braviz.readAndFilter.tabular_data import LATERALITY
from braviz.interaction.structure_metrics import get_right_or_left_hemisphere as __get_right_or_left_hemisphere


def __cached_named_tract(name_tract_func):
    @functools.wraps(name_tract_func)
    def cached_func(reader, subject, color):
        cache_file = 'named_fibs_%s_%s_%s.vtk' % (name_tract_func.__name__, subject, color)
        cache_full_path = os.path.join(reader.getDataRoot(), 'pickles', cache_file)
        if os.path.isfile(cache_full_path):
            fib_reader = vtk.vtkPolyDataReader()
            fib_reader.SetFileName(cache_full_path)
            try:
                fib_reader.Update()
            except Exception:
                print "problems reading %s" % cache_full_path
                raise
            else:
                out_fib = fib_reader.GetOutput()
                fib_reader.CloseVTKFile()
                return out_fib, name_tract_func(None, None, None, get_out_space=True)

        fibers, out_space = name_tract_func(reader, subject, color)
        fib_writer = vtk.vtkPolyDataWriter()
        fib_writer.SetFileName(cache_full_path)
        fib_writer.SetInputData(fibers)
        fib_writer.SetFileTypeToBinary()
        try:
            fib_writer.Update()
            if fib_writer.GetErrorCode() != 0:
                print 'cache write failed'
        except Exception:
            print 'cache write failed'
        finally:
            fib_writer.CloseVTKFile()
        return fibers, out_space

    return cached_func


@__cached_named_tract
def cortico_spinal_l(reader, subject, color, get_out_space=False):
    if get_out_space is True:
        return 'dartel'
    try:
        tracts = reader.get('fibers', subject, space='dartel', waypoint=['ctx-lh-precentral', 'Brain-Stem'],
                            color=color)
    except Exception:
        print "Tracts not found for subject %s" % subject
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


@__cached_named_tract
def cortico_spinal_r(reader, subject, color, get_out_space=False):
    if get_out_space is True:
        return 'dartel'
    try:
        tracts = reader.get('fibers', subject, space='dartel', waypoint=['ctx-rh-precentral', 'Brain-Stem'],
                            color=color)
    except Exception:
        print "Tracts not found for subject %s" % subject
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


def cortico_spinal_d(reader, subject, color, get_out_space=False):
    if get_out_space is True:
        return 'dartel'
    laterality = __get_var_value(LATERALITY, int(subject))
    if laterality == 1:
        lat = 'r'
    else:
        lat = 'l'
    hemi = __get_right_or_left_hemisphere('d', lat)
    if hemi == 'r':
        return cortico_spinal_r(reader, subject, color)
    elif hemi == 'l':
        return cortico_spinal_l(reader, subject, color)
    else:
        raise Exception("Unknown laterality")


def cortico_spinal_n(reader, subject, color, get_out_space=False):
    if get_out_space is True:
        return 'dartel'
    laterality = __get_var_value(LATERALITY, int(subject))
    if laterality == 1:
        lat = 'r'
    else:
        lat = 'l'
    hemi = __get_right_or_left_hemisphere('n', lat)
    if hemi == 'r':
        return cortico_spinal_r(reader, subject, color)
    elif hemi == 'l':
        return cortico_spinal_l(reader, subject, color)
    else:
        raise Exception("Unknown laterality")


def corpus_callosum(reader, subject, color, get_out_space=False):
    if get_out_space is True:
        return 'world'
    return reader.get('fibers', subject, operation='or',
                      waypoint=['CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior', 'CC_Posterior'],
                      color=color), 'world'


