'''
Created on 9/11/2013

@author: jc.forero47
'''

from SpiderPlotClass import SpiderPlotClass

from os.path import join as path_join 
import random



axes_names = ['eje 1', 'eje 2', 'eje 3', 'eje 4', 'eje 5']
axes_ranges = {'eje 1':[0,10], 'eje 2':[0,10], 'eje 3':[0,10], 'eje 4':[0,10], 'eje 5':[0,10]}
num_tuples = 12
title = 'ejemplo'

data = []
for i_data in range(0,5):
    data_row = []
    for j_data in range(0,num_tuples):
        data_row.append(random.randint(1,10))
    data.append(data_row)
    
spiderPlot = SpiderPlotClass(title, num_tuples,axes_names, axes_ranges, 500, 500)
spiderPlot.update_data(data)
#===============================================================================
# spiderPlot = SpiderPlotClass()
#===============================================================================
spiderPlot.render_standalone()



