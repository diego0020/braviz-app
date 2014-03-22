from __future__ import division

import numpy as np

import braviz


__author__ = 'Diego'

subject = "093"
structs = ["CC_Anterior","CC_Posterior","CC_Mid_Posterior"]

reader= braviz.readAndFilter.kmc40AutoReader()
#find label
labels = [int(reader.get("Model",subject,name=struct,label=True)) for struct in structs]
#print "label:",label
#find voxels in structure
aparc_img = reader.get("APARC",subject,space="world",format="nii")
aparc_data = aparc_img.get_data()
locations = [aparc_data == label for label in labels]
shape=aparc_data.shape
shape2 = shape + (1,)
locations = [l.reshape(shape2) for l in locations]
locations2 = np.concatenate(locations,3)
locations3=np.any(locations2,3)
indexes = np.where(locations3)
n_voxels = len(indexes[0])
#print indexes
#find mm coordinates of voxels in aparc
img_coords=np.vstack(indexes)
ones = np.ones(len(indexes[0]))
img_coords=np.vstack((img_coords,ones))
t=aparc_img.get_affine()
mm_coords = img_coords.T.dot(t.T)
#print mm_coords

#find voxel coordinates in fa
fa_img = reader.get("FA",subject,space="world",format="nii")
t2=fa_img.get_affine()
t2i = np.linalg.inv(t2)
fa_coords=mm_coords.dot(t2i.T)
fa_coords=np.round(fa_coords)
fa_coords=fa_coords.astype(np.int32)

splitted=np.hsplit(fa_coords,4)
fa_coords2=splitted[0:3]
fa_data=fa_img.get_data()
#sample and sum
res=np.sum(fa_data[fa_coords2])
res /= n_voxels
print res
