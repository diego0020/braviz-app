'''
Created on 26/10/2013

@author: jc.forero47
'''
import braviz
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

reader=braviz.readAndFilter.kmc40AutoReader()


filename = 'File\\directories.txt'
data= open(filename, 'r').read()
patient_list = data.split()

my_list = list()
for patient in patient_list:
    names = reader.get('model',patient,index=1)
    for name in names:
        if name not in my_list:
            my_list.append(name)
myfile=open('File\\rdfqueries\\VolumesNames','w')
for item in my_list:
    myfile.write("%s\n" % item)
print 'end writing file'