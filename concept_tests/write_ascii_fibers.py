'''
Created on 13/09/2013

@author: da.angulo39
'''
import os

import vtk

import braviz


os.chdir(r'C:\Users\da.angulo39\Documents')

r=braviz.readAndFilter.kmc40AutoReader()

fibers=r.get('fibers','144',space='dartel')
writer=vtk.vtkPolyDataWriter()
writer.SetInputData(fibers)
writer.SetFileTypeToASCII()
writer.SetFileName('acii_fibers_.vtk')
writer.Update()