# Based on the io.py file from the pySurfer library
# http://pysurfer.github.io
from __future__ import division
import numpy as np
import vtk

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
    "reads a freesurfer wireframe structure"
#based on pysurfer.io.read_geometry  '
    with open(filepath,'rb') as fobj:
        magic = _fread3(fobj)
        if magic != 16777214 :
            print "Invalid file %s"%filepath
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
    curv : numpy array
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

    Parameters
    ----------
    filepath : str
        Path to annotation file
    orig_ids : bool
        Whether to return the vertex ids as stored in the annotation
        file or the positional colortable ids

    Returns
    -------
    labels : n_vtx numpy array
        Annotation id at each vertex
    ctab : numpy array
        RGBA + label id colortable array
    names : numpy array
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



def apply_offset(coords,offset):
    "applies an offset to all the coordinates in coords"
    f_offset=map(float,offset)
    def add_offset(a):
        return [f_offset[i]+a[i] for i in [0,1,2]]
    b=np.apply_along_axis(add_offset,1,coords)
    return b
    
def create_polydata(coords,faces):
    "Creates a polydata using the coords and faces array (must contain only triangles)"
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
    
def surface2vtkPolyData(surf_file):
    "cached function to read a freesurfer structure file"
    #check cache
    vtkFile=None
    try:
        vtkFile=open(surf_file+'.vtk')
        vtkFile.close()
    except IOError:
        pass
    if vtkFile is not None:
        #print 'reading from vtk-file'
        vtkreader=vtk.vtkPolyDataReader()
        vtkreader.SetFileName(surf_file+'.vtk')
        vtkreader.Update()
        return vtkreader.GetOutput()
    
    #print 'reading from surfer file'    
    coords, faces, geom = read_surface(surf_file)
    coords2=apply_offset(coords,geom['cras'])
    poly=create_polydata(coords2,faces)
    #try to write to cache
    try:
        vtkWriter=vtk.vtkPolyDataWriter()
        vtkWriter.SetInputData(poly)
        vtkWriter.SetFileName(surf_file+'.vtk')
        vtkWriter.SetFileTypeToBinary()
        vtkWriter.Update()
    except:
        print 'cache write failed'
    return poly
def addScalars(surf_polydata,scalars):
    "Scalaras are expected as a numpy array"
    surf=surf_polydata
    if not len(scalars)==surf.GetNumberOfPoints():
        print "scalars don't match with input polydata"
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
    """Expects as input a numpy 2darray with R G B [A] [X] columns.
    The index of the row will be used as label. This method is designed
    to work with the ctab array returned by read_annot; labels may be used to annotate values"""
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
    """Creates a vtkLookUpTable from color0 to color1 or from color0 to color2 passing by color1
    The range of the LUT will be (start,end)
    midpoint and sharpness can be used to change the characteristics of the function between colors
    (see vtkPiecewiseFunction)
    if three colors are used, the resulting function will be symmetric, this means the actual midpoint for the second half will be 1-midpoint"""
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
    
def getMorphLUT(name):
    "Returns a LUT appropriate for the display of the given scalars.\nName must be 'curv', 'sulc', 'thickness', 'volume' or 'area'"
    parameters_d={'curv' : (-2 ,2 , 0.9, 0.0,      (0,1,0)  ,   (0.5,0.5,0.5),   (1,0,0)),
                  'avg_curv' : (-2 ,2 , 0.9, 0.0,      (0,1,0)  ,   (0.5,0.5,0.5),   (1,0,0)),
                  'area' : (0 ,2 , 0.5, 0.0,    (0.5,0.5,0.5), (0,1,0) ),
                  'thickness': (0 ,5 , 0.5, 0.0,    (1,0,0)  ,   (0.5,0.5,0.5),   (0,1,0)),
                  'volume' : (0 ,5 , 0.5, 0.0,    (0.5,0.5,0.5), (0,1,0) ),
                  'sulc' : (-2 ,2 , 0.5, 0.0,      (0,1,0)  ,   (0.5,0.5,0.5),   (1,0,0))            
                  }
    if not parameters_d.has_key(name):
        print 'Unkown scalar type'
        raise(Exception('unknown scalar type'))
    out_lut=getColorTransferLUT(*parameters_d[name])    
    return out_lut