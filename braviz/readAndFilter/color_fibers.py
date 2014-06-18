from __future__ import division
import random
import math

import vtk
import numpy as np
from scipy import ndimage

import braviz


def color_by_z(pt):
        "calculates color based on the z coordinate"
        z=pt[2]
        z_norm=(z+60)/(60+75)
        z_col=int(255*z_norm)
        z_col=np.clip(z_col, 0, 255)
        color=(0,z_col,0)
        return color

def color_by_fa(pt,fa_img):
    "calculates colores based on the fa value, taken from fa_img"
    org=fa_img.GetOrigin()
    delta=fa_img.GetSpacing()
    v_pt=np.subtract(pt, org)
    v_pt=v_pt/delta
    
    
    r_pt=map(round,v_pt)
    r_pt=r_pt+[0]
    r_pt=map(int,r_pt)
    fa=fa_img.GetScalarComponentAsDouble(*r_pt)
    fa=np.clip(fa, 0, 1)
    red=int(fa*255)
    color=(red,0,0)
    return color

def color_fibers_pts(fibers,color_function,*args,**kw):
    "color fiber bundles based on a function from each point"
    n_pts=fibers.GetNumberOfPoints()
    pts=fibers.GetPoints()
    scalars=fibers.GetPointData().GetScalars()
    for i in xrange(n_pts):
        point=pts.GetPoint(i)
        color=color_function(point,*args,**kw)
        scalars.SetTupleValue(i,color)

def color_fibers_lines(fibers,polyline_color_function,*args,**kw):
    "color fiber bundles based on a function that requires access to the whole line"
    nlines=fibers.GetNumberOfLines()
    ncells=fibers.GetNumberOfCells()
    if nlines != ncells:
        raise Exception('fibers must have only polylines')
    scalars=fibers.GetPointData().GetScalars()
    for i in xrange(nlines):
        l=fibers.GetCell(i)
        color_dict=polyline_color_function(l,*args,**kw)
        for pt,c in color_dict.iteritems():
            scalars.SetTupleValue(pt,c)
        
    
def random_line(line):
    "Creates a random color for the whole polyline"
    color=[random.randint(0,255) for i in ('r','g','b')]
    pts=line.GetPointIds()
    color_dict={}
    for i in xrange(pts.GetNumberOfIds()):
        color_dict[pts.GetId(i)]=color
    return color_dict

def line_curvature(line):
    "Calculates a color based on a curvature function"
    #simple formula from http://en.wikipedia.org/wiki/Curvature
    ids=line.GetPointIds()
    pts=line.GetPoints()
    color_dict={}
    #require 3 points
    for i in xrange(1,line.GetNumberOfPoints()-1):
        p0,p1,p2=[np.array(pts.GetPoint(j)) for j in range(i-1,i+2)]
        arch=np.linalg.norm(p0-p1)+np.linalg.norm(p2-p1)
        chord=np.linalg.norm(p0-p2)
        curv=np.sqrt(24*(arch-chord)/arch**3)
        curv=np.clip(curv,0,0.5)
        if math.isnan(curv):
            curv=0
        color=(135,255,255)
        color=np.dot(curv*2,color)
        color=map(int,color)
        color_dict[ids.GetId(i)]=color
    #Extremes
    color_dict[ids.GetId(0)]=color_dict[ids.GetId(1)]
    color_dict[ids.GetId(line.GetNumberOfPoints()-1)]=color_dict[ids.GetId(line.GetNumberOfPoints()-2)]
    return color_dict
        

def scalars_from_image(fibers,nifti_image):

    affine = nifti_image.get_affine()
    iaffine = np.linalg.inv(affine)
    data = nifti_image.get_data()

    #update scalars
    #remove colors array
    pd = fibers.GetPointData()
    pd.RemoveArray(0)

    npoints = fibers.GetNumberOfPoints()
    new_array = vtk.vtkDoubleArray()
    new_array.SetNumberOfTuples(npoints)
    new_array.SetNumberOfComponents(1)

    for i in xrange(npoints):
        coords = fibers.GetPoint(i) + (1,)
        coords = np.dot(iaffine,coords)
        coords = coords[:3]/coords[3]
        coords = coords.reshape(3, 1)
        image_val = ndimage.map_coordinates(data,coords,order=1)
        new_array.SetComponent(i,0,image_val)

    pd.SetScalars(new_array)

def scalars_lines_from_image(fibers,nifti_image):

    affine = nifti_image.get_affine()
    iaffine = np.linalg.inv(affine)
    data = nifti_image.get_data()

    #update scalars
    #remove colors array
    pd = fibers.GetPointData()
    pd.RemoveArray(0)

    cd = fibers.GetCellData()
    ncells = fibers.GetNumberOfCells()
    new_array = vtk.vtkDoubleArray()
    new_array.SetNumberOfTuples(ncells)
    new_array.SetNumberOfComponents(1)
    for i in xrange(ncells):
        c = fibers.GetCell(i)
        npts = c.GetNumberOfPoints()

        point_values = np.zeros(npts)
        for j in xrange(npts):
            p_id = c.GetPointId(j)
            coords = fibers.GetPoint(p_id) + (1,)
            coords = np.dot(iaffine,coords)
            coords = coords[:3]/coords[3]
            coords = coords.reshape(3, 1)
            image_val = ndimage.map_coordinates(data,coords,order=1)
            point_values[j]=image_val

        value = point_values.mean()
        new_array.SetComponent(i,0,value)

    cd.SetScalars(new_array)


def scalars_from_length(fibers):

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
        for j in xrange(1,npts):
            p_id = c.GetPointId(j)
            coords = np.array(fibers.GetPoint(p_id))
            if last_point is not None:
                step = np.linalg.norm(coords-last_point)
                length += step
            last_point = coords

        value = length
        new_array.SetComponent(i,0,value)
    cd = fibers.GetCellData()
    cd.SetScalars(new_array)



def get_fa_lut():
    lut = braviz.visualization.get_colorbrewer_lut(0.35,0.82,"YlGn",9,invert=True,continuous=True,skip=1)
    return lut

def get_md_lut():
    if braviz.readAndFilter.PROJECT == "kmc40":
        lut = braviz.visualization.get_colorbrewer_lut(6e-10, 11e-10,"YlGnBu",9,invert=False)
    elif braviz.readAndFilter.PROJECT == "kmc400":
        lut = braviz.visualization.get_colorbrewer_lut(491e-6, 924e-6, "YlGnBu",9, invert=False)
    else:
        raise Exception("Wrong project")
    return lut

def get_length_lut():
    lut = braviz.visualization.get_colorbrewer_lut(41,125,"YlOrBr",9,invert=False)
    return lut