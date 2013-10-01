'''
Created on 4/09/2013

@author: da.angulo39
'''
from __future__ import division
import braviz
import vtk
import os

reader=braviz.readAndFilter.kmc40AutoReader()
aparc_img=reader.get('aparc','144',format='vtk',space='dartel')


color_file_name=os.path.join(reader.getDataRoot(),'FreeSurferColorLUT.txt')
try:
    color_file=open(color_file_name)
except IOError as e:
    print e
    raise
color_lines=color_file.readlines()
color_file.close()
color_lists=[l.split() for l in color_lines if l[0] not in ['#','\n',' '] ]
color_tuples=[(int(l[0]),
              ( tuple( [float(c)/256 for c in l[2:2+3] ]+[1.0])
                ,l[1]) ) 
              for l in color_lists]           #(index,(color,annot) )
color_dict=dict(color_tuples)

out_lut=vtk.vtkLookupTable()
out_lut.SetNanColor(0.0, 1.0, 0.0, 1.0)
out_lut.SetNumberOfTableValues(max(color_dict.keys())+1)
out_lut.IndexedLookupOn()
#out_lut.Build()
for i in color_dict.keys():
    out_lut.SetAnnotation(i,color_dict[i][1])
for i in color_dict.keys():    #HACKY.... maybe there is a bug?
    idx=out_lut.GetAnnotatedValueIndex(i)
    out_lut.SetTableValue(idx,color_dict[i][0] )






print aparc_img


viewer=braviz.visualization.simpleVtkViewer()
pw=viewer.addImg(aparc_img)
pw.SetResliceInterpolateToNearestNeighbour() 
pw.SetLookupTable(out_lut)
viewer.start()

# 
# reader=braviz.readAndFilter.kmc40AutoReader()
# aparc_img=reader.get('aparc','144',format='vtk',space='native')
# aparc_img
# print aparc_img
# aparc_img.GetScalarComponentAsDouble(120,120,120)
# aparc_img.GetScalarComponentAsDouble(120,120,120,0)
# aparc_img.GetScalarComponentAsDouble(120,120,120,1)
# aparc_img.GetScalarComponentAsDouble(120,120,120)
# aparc_img.GetScalarComponentAsDouble(120,120,120,0)
# aparc_img=reader.get('aparc','144',format='nii')
# aparc_img
# d=aparc_img.get_data()
# d
# max(d)
# import numpy as np
# np.max(d)
# np.argmax(d)
# np.unravel_index(np.argmax(d),d.shape)
# d[128,128,128]
# aparc_img=reader.get('aparc','144',format='vtk',space='native')
# aparc_img.GetDimensions()
# aparc_img.GetScalarComponentAsDouble(86,128,115)
# aparc_img.GetScalarComponentAsDouble(86,128,115,0)
# aparc_img.GetScalarComponentAsDouble(86,128,115,1)
# aparc_img=reader.get('aparc','144',format='nii')
# vtk_img=braviz.readAndFilter.nibNii2vtk(aparc_img)
# vtk_img.GetScalarComponentAsDouble(86,128,115,0)
# vtk_img.GetScalarComponentAsDouble(128,128,128,0)
# a=[vtk_img.GetScalarComponentAsDouble(i,128,128,0) for i in range(256)]