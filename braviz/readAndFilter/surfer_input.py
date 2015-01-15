
# Based on the io.py file from the pySurfer library
# http://pysurfer.github.io
from __future__ import division
import os
import logging

import numpy as np
import vtk

from braviz.visualization.create_lut import get_colorbrewer_lut


def _fread3(fobj):
    """Read a 3-byte int from an open binary file object."""
    b1, b2, b3 = np.fromfile(fobj, ">u1", 3)
    return (b1 << 16) + (b2 << 8) + b3
def _fread3_many(fobj, n):
    """Read 3-byte ints from an open binary file object."""
    b1, b2, b3 = np.fromfile(fobj, ">u1", 3 * n).reshape(-1,
                                                    3).astype(np.int).T
    return (b1 << 16) + (b2 << 8) + b3

#==================================================================
def read_surface(filepath):
    """
    reads a freesurfer wireframe structure

    Args:
        filepath (str) : Path to freesurfer surface file

    Returns:
        (coords,faces,geom), where coords are the coordinates of each point, faces are the indeces of points in each
        face, and geom is a dictionary containing ``['cras', 'volume',  'voxelsize',  'xras',  'yras',  'zras']`` which
        can be used to determine the affine transform required to move the surface to the MRI space
    """
#based on pysurfer.io.read_geometry  '
    with open(filepath,'rb') as fobj:
        magic = _fread3(fobj)
        if magic != 16777214 :
            log = logging.getLogger(__name__)
            log.error("Invalid file %s"%filepath)
            fobj.close()
            raise(Exception('Invalid file'))
        create_stamp = fobj.readline()
        basura = fobj.readline() #reemplazar por _
        vnum = np.fromfile(fobj, ">i4", 1)[0]
        fnum = np.fromfile(fobj, ">i4", 1)[0]
        coords = np.fromfile(fobj, ">f4", vnum * 3).reshape(vnum, 3)
        faces = np.fromfile(fobj, ">i4", fnum * 3).reshape(fnum, 3)

        #Read geometry information at the end of the file
        #12 unknown bytes
        u1 = np.fromfile(fobj, ">i4", 3)
        #Always [ 2, 0 ,20 ] ?
        info_valid_file=fobj.readline()
        info_filename=fobj.readline()
        geom={}
        for i in range(0,6):
            line=fobj.readline().split()
            geom[line[0]]=tuple(line[2:])
        info_log=fobj.readline()
        return coords,faces,geom


def read_morph_data(filepath):
#copied directly from pysurfer.io
    """Read a Freesurfer morphometry data file.

    *copied directly from pysurfer.io*

    This function reads in what Freesurfer internally calls "curv" file types,
    (e.g. ?h. curv, ?h.thickness), but as that has the potential to cause
    confusion where "curv" also refers to the surface curvature values,
    we refer to these files as "morphometry" files with PySurfer.

    Parameters
    ----------
    filepath : str
        Path to morphometry file

    Returns
    -------
    curv : numpy.ndarray
        Vector representation of surface morpometry values

    """
    with open(filepath, "rb") as fobj:
        magic = _fread3(fobj)
        if magic == 16777215:
            vnum = np.fromfile(fobj, ">i4", 3)[0]
            curv = np.fromfile(fobj, ">f4", vnum)
        else:
            vnum = magic
            _ = _fread3(fobj)
            curv = np.fromfile(fobj, ">i2", vnum) / 100
    return curv


def read_annot(filepath, orig_ids=False):
    #copied directly from pysurfer.io

    """Read in a Freesurfer annotation from a .annot file.

    *copied directly from pysurfer.io*

    Parameters
    ----------
    filepath : str
        Path to annotation file
    orig_ids : bool
        Whether to return the vertex ids as stored in the annotation
        file or the positional colortable ids

    Returns
    -------
    labels : n_vtx numpy.ndarray
        Annotation id at each vertex
    ctab : numpy.ndarray
        RGBA + label id colortable array
    names : numpy.ndarray
        Array of region names as stored in the annot file

    """
    with open(filepath, "rb") as fobj:
        dt = ">i4"
        vnum = np.fromfile(fobj, dt, 1)[0]
        data = np.fromfile(fobj, dt, vnum * 2).reshape(vnum, 2)
        labels = data[:, 1]
        ctab_exists = np.fromfile(fobj, dt, 1)[0]
        if not ctab_exists:
            raise Exception('Color table not found in annotation file')
        n_entries = np.fromfile(fobj, dt, 1)[0]
        if n_entries > 0:
            length = np.fromfile(fobj, dt, 1)[0]
            orig_tab = np.fromfile(fobj, '>c', length)
            orig_tab = orig_tab[:-1]

            names = list()
            ctab = np.zeros((n_entries, 5), np.int)
            for i in xrange(n_entries):
                name_length = np.fromfile(fobj, dt, 1)[0]
                name = np.fromfile(fobj, "|S%d" % name_length, 1)[0]
                names.append(name)
                ctab[i, :4] = np.fromfile(fobj, dt, 4)
                ctab[i, 4] = (ctab[i, 0] + ctab[i, 1] * (2 ** 8) +
                              ctab[i, 2] * (2 ** 16) +
                              ctab[i, 3] * (2 ** 24))
        else:
            ctab_version = -n_entries
            if ctab_version != 2:
                raise Exception('Color table version not supported')
            n_entries = np.fromfile(fobj, dt, 1)[0]
            ctab = np.zeros((n_entries, 5), np.int)
            length = np.fromfile(fobj, dt, 1)[0]
            _ = np.fromfile(fobj, "|S%d" % length, 1)[0]  # Orig table path
            entries_to_read = np.fromfile(fobj, dt, 1)[0]
            names = list()
            for i in xrange(entries_to_read):
                _ = np.fromfile(fobj, dt, 1)[0]  # Structure
                name_length = np.fromfile(fobj, dt, 1)[0]
                name = np.fromfile(fobj, "|S%d" % name_length, 1)[0]
                names.append(name)
                ctab[i, :4] = np.fromfile(fobj, dt, 4)
                ctab[i, 4] = (ctab[i, 0] + ctab[i, 1] * (2 ** 8) +
                                ctab[i, 2] * (2 ** 16))
        ctab[:, 3] = 255
    if not orig_ids:
        ord = np.argsort(ctab[:, -1])
        labels = ord[np.searchsorted(ctab[ord, -1], labels)]
    return labels, ctab, names



def create_polydata(coords,faces):
    """
    Creates a polydata using the coords and faces array (must contain only triangles)

    See :func:`read_surface`

    Args:
        coords (numpy.ndarray) : Points coordinates array
        faces (numpy.ndarray) : Faces array

    Returns:
        vtkPolyData with same points and faces
    """
    poly=vtk.vtkPolyData()
    points=vtk.vtkPoints()
    points.SetDataTypeToFloat()
    points.SetNumberOfPoints(coords.shape[0])
    for i, pt in enumerate(coords):
        points.InsertPoint(i,pt)
    poly.SetPoints(points)
    poly.Allocate()
    for f in faces:
        idList=vtk.vtkIdList()
        for i in f:
            idList.InsertNextId(i)
        poly.InsertNextCell(vtk.VTK_TRIANGLE , idList)
    return poly

def apply_offset(coords,offset):
    """
    applies an offset to all the coordinates in coords

    Args:
        coords (numpy.ndarray) : nx3 coordinates array

    Returns: nx3 coordinates array of translated coordinates
    """
    f_offset=map(float,offset)
    def add_offset(a):
        return [f_offset[i]+a[i] for i in [0,1,2]]
    b=np.apply_along_axis(add_offset,1,coords)
    return b


def _cached_surface_read(surf_file):
    """
    cached function to read a freesurfer structure file

    .. deprecated :: 3.0b
        Use a :class:`~braviz.readAndFilter.base_reader.BaseReader` to do all cache operations

    see :func:`surface2vtkPoly`
    """
    #check cache
    vtkFile=surf_file+'.vtk'
    if os.path.isfile(vtkFile):
        #print 'reading from vtk-file'
        vtkreader=vtk.vtkPolyDataReader()
        vtkreader.SetFileName(surf_file+'.vtk')
        vtkreader.Update()
        return vtkreader.GetOutput()

    #print 'reading from surfer file'
    poly=surface2vtkPolyData(surf_file)
    #try to write to cache
    log = logging.getLogger(__name__)
    try:
        vtkWriter=vtk.vtkPolyDataWriter()
        vtkWriter.SetInputData(poly)
        vtkWriter.SetFileName(surf_file+'.vtk')
        vtkWriter.SetFileTypeToBinary()
        vtkWriter.Update()
    except Exception:
        log.warning('cache write failed')
    if vtkWriter.GetErrorCode() != 0:
        log.warning('cache write failed')
    return poly

def surface2vtkPolyData(surf_file):
    """
    read free surfer surface and transform to poly data

    Args:
        surf_file (str) : Path to freesurfer surface file

    Returns:
        vtkPolyData representation of the surface

    """
    coords, faces, geom = read_surface(surf_file)
    coords2=apply_offset(coords,geom['cras'])
    poly=create_polydata(coords2,faces)
    return poly
def addScalars(surf_polydata,scalars):
    """
    Add scalars to a vtkPolyData representation of a freesurfer surface

    Args:
        surf_polydata (vtkPolyData) : freesurfer surface
        scalars (numpy.ndarray) : scalars belonging to the same freesurfer surface (same number of points)

    Returns:
        vtkPolyData with scalar data
    """

    surf=surf_polydata
    log = logging.getLogger(__name__)
    if not len(scalars)==surf.GetNumberOfPoints():
        log.error("scalars don't match with input polydata")
        raise(Exception("scalars don't match with input polydata"))
    if scalars.dtype.kind=='f':
        vtk_scalars=vtk.vtkFloatArray()
    else:
        vtk_scalars=vtk.vtkIntArray()
    vtk_scalars.SetNumberOfComponents(1)
    vtk_scalars.SetNumberOfValues(len(scalars))
    for i,s in enumerate(scalars):
        vtk_scalars.SetValue(i, s)
    surf_polydata.GetPointData().RemoveArray(0)    
    surf_polydata.GetPointData().SetScalars(vtk_scalars)
    return surf_polydata
def surfLUT2VTK(ctab,names=None):
    """
    Transform freesurfer lookuptable into a vtkLookupTable

    The index of the row will be used as label. This method is designed
    to work with the ctab array returned by read_annot; labels may be used to annotate values

    Args:
        ctab (numpy.ndarray) : 2darray with R G B [A] [X] columns.
        names (list) : Same length as ctab, add annotations to the lookuptable

    Retruns:
        vtkLookupTable with colors and annotations.
    """
    out_lut=vtk.vtkLookupTable()
    out_lut.SetNumberOfTableValues(ctab.shape[0])
    out_lut.IndexedLookupOn()
    out_lut.Build()
    if names:
        for i in xrange(ctab.shape[0]):
            out_lut.SetAnnotation(i,names[i])
    else:
        for i in xrange(ctab.shape[0]):
            out_lut.SetAnnotation(i,'-')
    for i in xrange(ctab.shape[0]):
        out_lut.SetTableValue(i,(ctab[i,0:4]/255) )
    return out_lut


def getColorTransferLUT(start,end,midpoint,sharpness,color0,color1,color2=None):
    """
    Creates a vtkLookUpTable from color0 to color1 or from color0 to color2 passing by color1

    The domain of the LUT will be (start,end)
    midpoint and sharpness can be used to change the characteristics of the function between colors
    (see `vtkPiecewiseFunction <http://www.vtk.org/doc/nightly/html/classvtkPiecewiseFunction.html#details>`_)
    if three colors are used, the resulting function will be symmetric, this means the actual midpoint for the second half will be 1-midpoint

    Args:
        start (float) : first value in the lookuptable domain
        end (float) : last value in the lookuptable domain
        midpoint (float) : Midpoint for function between colors
        sharpness (float) : Sharpness for function between colors
        color0 (tuple) : First color in the lookuptable
        color1 (tuple) : Second color in the lookuptable
        color2 (tuple) : Optional, third color in the lookuptable

    Returns:
        vtkColorTransferFunction

    """
    lut=vtk.vtkColorTransferFunction()
    lut.SetColorSpaceToRGB()
    if color2:
        mid=(start+end)/2
    else:
        mid=end
    lut.SetRange(start, end )
    lut.AddRGBPoint(start, color0[0],color0[1],color0[2],    midpoint,sharpness)
    lut.AddRGBPoint(mid,   color1[0],color1[1],color1[2], 1 - midpoint,sharpness)
    if color2:
        lut.AddRGBPoint(end,   color2[0],color2[1],color2[2],      midpoint,sharpness) #midpoint and sharpness ignored for last point
    return lut


def get_free_surfer_lut(name):
    """
    Get standard freesurfer lookup tables

    Args:
        name (str) : Name of table, available tables are
            - curv / avg_curv
            - area
            - thickness
            - volume
            - sulc

    Returns:
        vtkColorTransferFunction
    """
    parameters_d={'curv' : (-0.5 ,0.5 , "RdYlGn", 11,True),
              'avg_curv' : (-0.5 ,0.5 , "RdYlGn", 11,True),
              'area' : (0 ,2 , "PuBuGn", 9 ),
              'thickness': (0 ,5 , "RdYlGn", 11),
              'volume' : (0 ,5,    "PuBuGn", 9 ),
              'sulc' : (-2 ,2 , "RdYlGn",11,True),
              }
    try:
        params = parameters_d[name]
        out_lut = get_colorbrewer_lut(*params)
    except KeyError:
        log = logging.getLogger(__name__)
        log.error('Unkown scalar type')
        raise (Exception('unknown scalar type'))
    return out_lut