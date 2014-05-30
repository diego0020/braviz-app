'''
Created on 5/10/2013

@author: imagine
'''
from os.path import join as path_join

from ScatterPlotClass import ScatterPlotClass
import braviz


reader=braviz.readAndFilter.BravizAutoReader()
data_root=reader.getDataRoot()
file_name=path_join(data_root,'test_small2.csv')
#file_name = 'File\\testPacientes.csv'

scatterPlot = ScatterPlotClass()
wmi = scatterPlot.get_columnFromCSV(file_name, 'WMIIQ', True)
codes = scatterPlot.get_columnFromCSV(file_name, 'CODE', False)
volumes=map(lambda code: scatterPlot.get_struct_volume(reader, 'CC_Anterior',code) ,codes)

scatterPlot.addAxes(wmi, 'wmi', volumes, 'volume', codes, 'code')
scatterPlot.render()