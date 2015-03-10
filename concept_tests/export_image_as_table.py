from __future__ import division
import braviz
import csv
import vtk
import numpy as np
import os

__author__ = 'da.angulo39'


file_name=os.path.normpath(r"C:\Users\da.angulo39\Documents\mri.csv")
perpendicular=np.array((0,0,1))
x=np.array((0,-1,0))
y=np.array((-1,0,0))


# file_name=os.path.normpath(r"C:\Users\da.angulo39\Documents\sagital2.png")
# perpendicular=np.array((-1,0,0))
# x=np.array((0,1,0))
# y=np.array((0,0,1))

#file_name=os.path.normpath(r"C:\Users\da.angulo39\Documents\sagital.png")
#perpendicular=np.array((1,0,0))
#x=np.array((0,1,0))
#y=np.array((0,0,1))


r=braviz.readAndFilter.BravizAutoReader()

lh=r.get("surf",15,hemi="l",name="pial",scalars="aparc")
rh=r.get("surf",15,hemi="r",name="pial",scalars="aparc")
lut=r.get("surf_scalar",15,lut=True,scalars="aparc")
img = r.get("MRI",15)
affine=img.get_affine()
data=img.get_data()
def get_mm(i,j,k):
    return affine.dot((i,j,k,1))[0:3]


box=vtk.vtkBox()
box.AddBounds(lh.GetBounds())
box.AddBounds(rh.GetBounds())
print box


xmin=np.array([0,0,0])
box.GetXMin(xmin)
xmax=np.array([0,0,0])
box.GetXMax(xmax)

tuples=[]

first_i,first_j,first_k=None,None,None


i_max,j_mak,k_max=data.shape
for i in xrange(i_max):
    mm_coords=get_mm(i,j_mak//2,k_max//2)
    if not np.all(np.logical_and(xmin<=mm_coords,mm_coords<=xmax)):
        continue
    if first_i is None:
        first_i=i
    for j in xrange(j_mak):
        mm_coords=get_mm(i,j,k_max//2)
        if not np.all(np.logical_and(xmin<=mm_coords,mm_coords<=xmax)):
            continue
        if first_j is None:
            first_j=j
        for k in xrange(k_max):
            mm_coords=get_mm(i,j,k)
            if np.all(np.logical_and(xmin<=mm_coords,mm_coords<=xmax)):
                if first_k is None:
                    first_k=k
                norm_coords=(mm_coords-xmin)/(xmax-xmin)
                tuples.append((i-first_i,j-first_j,j-first_k,data[i,j,k]))


with open(file_name,"wb") as f:
    writer=csv.writer(f,delimiter=" ")
    writer.writerows(tuples)
