from __future__ import division
import os

import braviz
import numpy as np
import scipy.spatial
import nibabel

__author__ = 'da.angulo39'
os.chdir(r"D:\KAB-db\093\Models")

aseg = nibabel.load("aparc+aseg.nii.gz")

label = 17

data = aseg.get_data()
coords = np.where(data == label)
coords_h = np.array((coords[0],coords[1],coords[2],np.ones(len(coords[0]))))
affine = aseg.get_affine()
mm_h = np.dot(affine,coords_h)
mm = mm_h[0:3,:]/np.tile(mm_h[3,:],(3,1))

points = mm.T
hull = scipy.spatial.ConvexHull(points)
verts = points[hull.vertices]

m_p=scipy.spatial.distance.pdist(verts)
m = scipy.spatial.distance.squareform(m_p)

max_distance = np.max(m)
i1,i2 = np.unravel_index(np.argmax(m),m.shape)
p1, p2 = verts[i1],verts[i2]

# project into the plane perpendicular to p1-p2
norm = (p2 - p1)/np.linalg.norm(p2-p1)

verts2 = verts - np.dot(verts,norm)[:,np.newaxis]*norm

m_p2=scipy.spatial.distance.pdist(verts2)
m_2 = scipy.spatial.distance.squareform(m_p2)
max_distance2 = np.max(m_2)
i3,i4 = np.unravel_index(np.argmax(m_2),m_2.shape)
p3, p4 = verts2[i3],verts2[i4]

#project into line perependicular to p3-p4

norm2 = (p4 - p3)/np.linalg.norm(p4-p3)
verts3 = verts2 - np.dot(verts2,norm2)[:,np.newaxis]*norm2

m_p3=scipy.spatial.distance.pdist(verts3)
m_3 = scipy.spatial.distance.squareform(m_p3)
max_distance3 = np.max(m_3)
i5,i6 = np.unravel_index(np.argmax(m_3),m_3.shape)
p5, p6 = verts3[i5],verts3[i6]

print (max_distance,max_distance2,max_distance3)

# visualization
import vtk
viewer = braviz.visualization.simpleVtkViewer()

def paint_verts(vs,color,size=2):
    if vs.shape[1]!=3:
        vs = vs.T
    points = vtk.vtkPoints()
    points.SetNumberOfPoints(len(vs))
    len(vs)
    for i in xrange(len(vs)):
        points.SetPoint(i,vs[i,:])
    pd = vtk.vtkPolyData()
    pd.SetPoints(points)
    gf = vtk.vtkVertexGlyphFilter()
    gf.SetInputData(pd)
    gf.Update()
    gs = gf.GetOutput()
    ac = viewer.addPolyData(gs)
    prop = ac.GetProperty()
    prop.SetColor(color)
    prop.SetPointSize(size)

def paint_line(p1,p2,color):
    line = vtk.vtkLineSource()
    line.SetPoint1(p1)
    line.SetPoint2(p2)
    line.Update()
    ac = viewer.addPolyData(line.GetOutput())
    ac.GetProperty().SetColor(color)
    ac.GetProperty().SetLineWidth(5)

paint_verts(points,(1,1,1),size=1)
viewer.start()

paint_verts(verts,(1,0,0))
paint_line(p1,p2,(1,0,0))
viewer.start()

c=np.dot((p2+p1)/2,norm)*norm
paint_verts(verts2+c,(1,1,0))
paint_line(p3+c,p4+c,(1,1,0))
viewer.start()

c2=(np.linalg.norm(p3-p4)/2+np.dot(p3+c,norm2))*norm2+c
paint_verts(verts3+c2,(1,0,1))
paint_line(p5+c2,p6+c2,(1,0,1))
viewer.start()





