'''
Created on 4/09/2013

@author: da.angulo39
'''
from __future__ import division
import os

import vtk

import braviz
from braviz import _test_arrow


reader=braviz.readAndFilter.BravizAutoReader()
aparc_img=reader.get('aparc','144',format='vtk',space='dartel')


color_file_name=os.path.join(reader.get_data_root(),'FreeSurferColorLUT.txt')
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


viewer= simpleVtkViewer()
pw=viewer.addImg(aparc_img)
pw.SetResliceInterpolateToNearestNeighbour() 
pw.SetLookupTable(out_lut)
viewer.start()

