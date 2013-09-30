from __future__ import division
import random
import math

import numpy as np


def color_by_z(pt):
        z=pt[2]
        z_norm=(z+60)/(60+75)
        z_col=int(255*z_norm)
        z_col=np.clip(z_col, 0, 255)
        color=(0,z_col,0)
        return color

def color_by_fa(pt,fa_img):
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
    n_pts=fibers.GetNumberOfPoints()
    pts=fibers.GetPoints()
    scalars=fibers.GetPointData().GetScalars()
    for i in xrange(n_pts):
        point=pts.GetPoint(i)
        color=color_function(point,*args,**kw)
        scalars.SetTupleValue(i,color)

def color_fibers_lines(fibers,polyline_color_function,*args,**kw):
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
    color=[random.randint(0,255) for i in ('r','g','b')]
    pts=line.GetPointIds()
    color_dict={}
    for i in xrange(pts.GetNumberOfIds()):
        color_dict[pts.GetId(i)]=color
    return color_dict

def line_curvature(line):
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
        
    