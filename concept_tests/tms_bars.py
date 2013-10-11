from __future__ import division
import braviz
from braviz.readAndFilter.read_csv import get_column, column_to_vtk_array
import os
import numpy as np
import vtk
import random
__author__ = 'Diego'

#parameters
delta_p=20 # changes total width, width,
delta_p2=20 #changes separation between bars, and total width and bar width
bar_width_fraction=1 #changes separation between bars, and total width and bar width

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

def get_color(value):
    z_score=abs(value-term_mean)/term_std_dev

    if  z_score <= 0.5:
        return (49, 163, 84,255)
    elif z_score <=1:
        return (161, 217, 155,255)
    elif z_score <= 1.5:
        return (254, 224, 210,255)
    elif z_score <=2:
        return (252, 146, 114,255)
    else:
        return (222, 45, 38,255)

def add_bar(position,value,code,delta_p=delta_p):
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
    vtk_table.SetNumberOfRows(2)

    bars = chart.AddPlot(vtk.vtkChart.BAR)
    bars.SetInputData(vtk_table, 0, 1)

    vtk_table.SetValue(0, 0, position)
    vtk_table.SetValue(0, 0, position+delta_p)
    vtk_table.SetValue(0, 1, value)
    vtk_table.SetValue(1, 1, 0)
    rgb_color = get_color(value)
    bars.SetColor(*rgb_color)
    bars.SetIndexedLabels(arri_c)
    bars.SetTooltipLabelFormat('%i:%y')
    #bars.SetUseIndexForXSeries(True)
    return bars

def add_line(y_pos,dashed=False):
    line=chart.AddPlot(vtk.vtkChart.LINE)
    vtk_table = vtk.vtkTable()
    arr_x = vtk.vtkFloatArray()
    arr_x.SetName("x")

    arri_y = vtk.vtkFloatArray()
    arri_y.SetName("y")

    vtk_table.AddColumn(arri_y)
    vtk_table.AddColumn(arr_x)
    vtk_table.SetNumberOfRows(2)

    vtk_table.SetValue(0, 0, -70)
    vtk_table.SetValue(0, 1, y_pos)
    #vtk_table.SetValue(1, 0, 0.2*len(codes2))
    vtk_table.SetValue(1, 0, 120)
    vtk_table.SetValue(1, 1, y_pos)
    line.SetInputData(vtk_table, 0, 1)
    line.SetColor(0,0,0,255)
    if dashed is True:
        pen=line.GetPen()
        pen.SetLineType(vtk.vtkPen.DASH_LINE)



add_line(term_mean+term_std_dev,True)
add_line(term_mean-term_std_dev,True)
add_line(term_mean)



#add_bar(0,21,'4444')
#add_bar(0.1,49,'888')

#bars=chart.AddPlot(vtk.vtkChart.BAR)
#bars.SetInputData(vtk_table,0,1)
#bars.SetUseIndexForXSeries(True)

chart.SetBarWidthFraction(bar_width_fraction)

ax=chart.GetAxis(vtk.vtkAxis.BOTTOM)
ax.SetBehavior(1)
ax.SetMinimum(95)
ax.SetMaximum(160)

ay=chart.GetAxis(vtk.vtkAxis.LEFT)
ay.SetBehavior(1)
ay.SetMinimum(-20)
ay.SetMaximum(100)


view.GetInteractor().Initialize()
pos0=0
#for values in zip([delta_p2+x for x in range(len(codes2))],tms_data2,codes2):
#    #print values
#    bar_n=add_bar(*values)
#    #first three are lines
#    bar_0=chart.GetPlot(3)
#    view.Render()
#    print values
#    print "width=%f"%bar_n.GetWidth()
#    print "width=%f" % bar_0.GetWidth()
#    print (delta_p2+delta_p)*bar_width_fraction/(chart.GetNumberOfPlots()-3) #predicted width
#    print
#    print "offset=%f"%bar_n.GetOffset()
#    print "offset=%f" % bar_0.GetOffset()
#    #print values[0]-bar_n.GetOffset()+bar_n.GetWidth()/2+delta_p #predicted graph end
#    print values[0]-bar_n.GetOffset()+bar_n.GetWidth()/2+delta_p #predicted graph end
#    print 0-(delta_p2+delta_p)*bar_width_fraction/2+(delta_p+delta_p2) #predicted graph START
#    print ((delta_p2+delta_p)*bar_width_fraction/(chart.GetNumberOfPlots()-3))/(values[0]-bar_n.GetOffset()+bar_n.GetWidth()/2+delta_p - (pos0+0-(delta_p2+delta_p)*bar_width_fraction/2+(delta_p+delta_p2)))*(chart.GetNumberOfPlots()-3)
#    print
#    print '==========='
#    n=(chart.GetNumberOfPlots()-3)
#    w=bar_width=(delta_p2+delta_p)*bar_width_fraction/(chart.GetNumberOfPlots()-3) #(delta_p2+delta_p)*bar_width_fraction
#    width_0=(delta_p2+delta_p)*bar_width_fraction/2
#    graph_start=(delta_p+delta_p2)*(1-bar_width_fraction/2)
#    graph_end=delta_p+delta_p2-1+n*(2+w)/2
#    print "start=%f"%graph_start
#    print "end=%f"%graph_end
#    print "end_-1=%f" % (graph_end-w)
#    try:
#        print w/((graph_end-graph_start-w)/(n-1))
#    except ZeroDivisionError:
#        print 0
#    #view.GetInteractor().Start()
#view.GetInteractor().Start()

#fixed width bar graph

w=1
start=100
delta_p=110

all_values=zip([delta_p+x for x in range(len(codes2))],tms_data2,codes2)
#some_values=all_values[:20]
some_values=[]
for values in some_values:
    #print values

    #first three are lines
    bar_0=chart.GetPlot(3)
    #n = (chart.GetNumberOfPlots() - 3)+1
    n=len(some_values)
    print n
    b=2/(2*start/(w*n)+1)
    x_2=start+w*n/2
    print b
    print x_2
    chart.SetBarWidthFraction(b)
    bar_width_fraction=b
    delta_pp=x_2-delta_p
    bar_n = add_bar(*values,delta_p=delta_pp)
    print "delta_pp=%f"%delta_pp
    view.Render()
    #print values
    print "width=%f"%bar_n.GetWidth()
    #print "width=%f" % bar_0.GetWidth()
    #print (delta_p2+delta_p)*bar_width_fraction/(chart.GetNumberOfPlots()-3) #predicted width
    #print x_2*b/n
    #print
    #print "offset=%f"%bar_n.GetOffset()
    #print "offset=%f" % bar_0.GetOffset()
    #print values[0]-bar_n.GetOffset()+bar_n.GetWidth()/2+delta_p #predicted graph end
    #print values[0]-bar_n.GetOffset()+bar_n.GetWidth()/2+delta_p #predicted graph end
    #print 0-(delta_p2+delta_p)*bar_width_fraction/2+(delta_p+delta_p2) #predicted graph START
    #print ((delta_p2+delta_p)*bar_width_fraction/(chart.GetNumberOfPlots()-3))/(values[0]-bar_n.GetOffset()+bar_n.GetWidth()/2+delta_p - (pos0+0-(delta_p2+delta_p)*bar_width_fraction/2+(delta_p+delta_p2)))*(chart.GetNumberOfPlots()-3)
    #print

    #w=bar_width=(delta_p2+delta_p)*bar_width_fraction/(chart.GetNumberOfPlots()-3) #(delta_p2+delta_p)*bar_width_fraction
    #width_0=(delta_p2+delta_p)*bar_width_fraction/2
    graph_start=(x_2)*(1-bar_width_fraction/2)
    graph_end=graph_start+n*(w+1)-1
    #graph_end=x_2*(1+b)+n
    print "start=%f"%graph_start
    print "end=%f"%graph_end
    #print "end_-1=%f" % (graph_end-w)
    print (graph_end-graph_start-w)/(n-1)-w
    #try:
    #    print w/((graph_end-graph_start-w)/(n-1))
    #except ZeroDivisionError:
    #    print 0
    print '==========='
    #view.GetInteractor().Start()


def get_bar_graph_width(col_width,n_elements):
    #There is alaways a space of 1 between bars
    return n_elements*(col_width+1)-1

def get_minimum_start(col_width,n_elements):
    #2*s > w*n
    return n_elements*col_width/2

def get_maximum_width(start,n_elements):
    return 2*start/n_elements

def paint_bar_chart(chart,data,codes=None,col_width=5,start=100,color_fun=None):
    w=col_width
    s=start
    n=len(data)
    if not (2*s>w*n):
        raise Exception("2*s > w*n must hold!, use get mimimum start to calculate a proper start position")
    b=2/(2*start/(w*n)+1)
    x_2=start+w*n/2
    if codes is None:
        codes=[None]*len(data)
    all_values = zip([x_2 + x for x in range(len(data))], data, codes)
    for values in all_values:
        chart.SetBarWidthFraction(b)
        delta_pp = 0
        bar_n = add_bar(*values, delta_p=delta_pp)

def add_bar2(position,value,code,color_fun=None):
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
    vtk_table.SetValue(0, 0, position)
    if color_fun is not None:
        rgb_color = get_color(value)
        bars.SetColor(*rgb_color)
    if code is not None:
        bars.SetIndexedLabels(arri_c)
        bars.SetTooltipLabelFormat('%i:%y')
    #bars.SetUseIndexForXSeries(True)
    return bars
def add_line2(y_pos,dashed=False,limits=(-100,100)):
    line=chart.AddPlot(vtk.vtkChart.LINE)
    vtk_table = vtk.vtkTable()
    arr_x = vtk.vtkFloatArray()
    arr_x.SetName("x")

    arri_y = vtk.vtkFloatArray()
    arri_y.SetName("y")

    vtk_table.AddColumn(arri_y)
    vtk_table.AddColumn(arr_x)
    vtk_table.SetNumberOfRows(2)

    vtk_table.SetValue(0, 0, limits[0])
    vtk_table.SetValue(0, 1, y_pos)
    #vtk_table.SetValue(1, 0, 0.2*len(codes2))
    vtk_table.SetValue(1, 0, limits[1])
    vtk_table.SetValue(1, 1, y_pos)
    line.SetInputData(vtk_table, 0, 1)
    line.SetColor(0,0,0,255)
    if dashed is True:
        pen=line.GetPen()
        pen.SetLineType(vtk.vtkPen.DASH_LINE)



col_width = 5
chart_start = 100

for seq in range(1,len(tms_data2)):
    chart.ClearPlots()
    paint_bar_chart(chart,tms_data2[:seq],codes2[:seq],color_fun=get_color,col_width=col_width,start=chart_start)

    chart_width=get_bar_graph_width(col_width,len(tms_data2))

    min_x=start-chart_width*0.05
    max_x=start+chart_width*1.05

    ax=chart.GetAxis(vtk.vtkAxis.BOTTOM)
    ax.SetBehavior(1)
    ax.SetMinimum(min_x)
    ax.SetMaximum(max_x)

    ay=chart.GetAxis(vtk.vtkAxis.LEFT)
    ay.SetBehavior(1)
    ay.SetMinimum(-20)
    ay.SetMaximum(100)

    add_line2(term_mean+term_std_dev,True,(min_x,max_x))
    add_line2(term_mean-term_std_dev,True,(min_x,max_x))
    add_line2(term_mean,False,(min_x,max_x))

    view.GetInteractor().Start()