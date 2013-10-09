import braviz
from braviz.readAndFilter.read_csv import get_column, column_to_vtk_array
import os
import numpy as np
import vtk
import random
__author__ = 'Diego'


#===============read data=====================
tms_column='ICId'
invert_data=True #perform 100 - tms_data
genre='1' #1=girls, 2=boys

reader=braviz.readAndFilter.kmc40AutoReader()
csv_file=os.path.join(reader.getDataRoot(),'baseFinal_TMS.csv')
codes=get_column(csv_file,'CODE')
genres=get_column(csv_file,'GENDE')
grupo=get_column(csv_file,'UBICA') #1=canguro, 2=control, 3=gorditos
TMS_metric=get_column(csv_file,tms_column,True)
TMS_metric=map(lambda x:100-x,TMS_metric)

table=zip(codes,genres,grupo,TMS_metric)
table_genre=filter(lambda y: y[1]=='2',table)
term=filter(lambda x:x[2]=='3',table_genre)

term_data=zip(*term)[3]

term_mean=np.mean(term_data)
term_std_dev=np.std(term_data)

#only keep codes and tms_data columns from filtered table
codes2,_,_,tms_data2=zip(*table_genre)


#=============create graph===========






#vtk_table=vtk.vtkTable()
#
#vtk_table.AddColumn(column_to_vtk_array(codes2,'codes'))
#vtk_table.AddColumn(column_to_vtk_array(tms_data2,tms_column))
#vtk_table.SetNumberOfRows(len(codes2))


view=vtk.vtkContextView()
view.GetRenderer().SetBackground(1.0,1.0,1.0)
view.GetRenderWindow().SetSize(400,300)

chart=vtk.vtkChartXY()
view.GetScene().AddItem(chart)
chart.SetShowLegend(False)

def add_bar(position,value,code):
    vtk_table = vtk.vtkTable()
    arr_x = vtk.vtkFloatArray()
    arr_x.SetName("x")

    arri_y = vtk.vtkFloatArray()
    arri_y.SetName("y")

    arri_c = vtk.vtkStringArray()
    arri_c.SetName("c")
    arri_c.InsertNextValue(code)

    vtk_table.AddColumn(arri_y)
    vtk_table.AddColumn(arr_x)
    vtk_table.SetNumberOfRows(1)

    bars = chart.AddPlot(vtk.vtkChart.BAR)
    bars.SetInputData(vtk_table, 0, 1)

    vtk_table.SetValue(0, 0, position)
    vtk_table.SetValue(0, 1, value)
    rgb_color = [random.randint(0,255) for c in range(3)]+[255]
    bars.SetColor(*rgb_color)
    bars.SetIndexedLabels(arri_c)
    bars.SetTooltipLabelFormat('%i:%y')

def add_line(y_pos):
    line=chart.AddPlot(vtk.vtkChart.LINE)
    vtk_table = vtk.vtkTable()
    arr_x = vtk.vtkFloatArray()
    arr_x.SetName("x")

    arri_y = vtk.vtkFloatArray()
    arri_y.SetName("y")

    vtk_table.AddColumn(arri_y)
    vtk_table.AddColumn(arr_x)
    vtk_table.SetNumberOfRows(2)

    vtk_table.SetValue(0, 0, -2)
    vtk_table.SetValue(0, 1, y_pos)
    #vtk_table.SetValue(1, 0, 0.2*len(codes2))
    vtk_table.SetValue(1, 0, 8)
    vtk_table.SetValue(1, 1, y_pos)
    line.SetInputData(vtk_table, 0, 1)

for values in zip([x*0.2 for x in range(len(codes2))],tms_data2,codes2):
    print values
    add_bar(*values)

add_line(term_mean+term_std_dev)
add_line(term_mean-term_std_dev)

chart.SetBarWidthFraction(1.0)

#add_bar(0,21,'4444')
#add_bar(0.1,49,'888')

#bars=chart.AddPlot(vtk.vtkChart.BAR)
#bars.SetInputData(vtk_table,0,1)
#bars.SetUseIndexForXSeries(True)



view.GetInteractor().Initialize()
view.GetInteractor().Start()