#Based on the io.py file from the pySurfer library
# http://pysurfer.github.io
#import os
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
#filepath='lh.pial'
    with open(filepath,'rb') as fobj:
        magic = _fread3(fobj)
        if magic != 16777214 :
            print "Invalid file %s"%filepath
            fobj.close()
            return None
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

def apply_offset(coords,offset):
    f_offset=map(float,offset)
    def add_offset(a):
        return [f_offset[i]+a[i] for i in [0,1,2]]
    b=np.apply_along_axis(add_offset,1,coords)
    return b
    
def create_polydata(coords,faces):
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
    #check cache
    vtkFile=None
    try:
        vtkFile=open(surf_file+'.vtk')
        vtkFile.close()
    except IOError:
        pass
    if vtkFile != None:
        #print 'reading from vtk-file'
        vtkreader=vtk.vtkPolyDataReader()
        vtkreader.SetFileName(surf_file+'.vtk')
        vtkreader.Update()
        return vtkreader.GetOutput()
    
    #print 'reading from slicer file'    
    coords, faces, geom = read_surface(surf_file)
    coords2=apply_offset(coords,geom['cras'])
    poly=create_polydata(coords2,faces)
    #try to write to cache
    try:
        vtkWriter=vtk.vtkPolyDataWriter()
        vtkWriter.SetInput(poly)
        vtkWriter.SetFileName(surf_file+'.vtk')
        vtkWriter.SetFileTypeToBinary()
        vtkWriter.Update()
    except:
        print 'cache write failed'
    return poly