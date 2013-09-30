from __future__ import division
from os.path import join as path_join

import vtk

import braviz

reader=braviz.readAndFilter.kmc40AutoReader()
data_root=reader.getDataRoot()
file_name=path_join(data_root,'test_small2.csv')

def get_column(name,numeric=False):
    csv_file=open(file_name)
    headers=csv_file.readline()
    headers=headers.rstrip('\n')
    headers=headers.split(';')
    if name not in headers:
        print "column %s not found in file"%name
        return None
    idx=headers.index(name)
    column=[]
    for l in iter(csv_file.readline,''):
        l2=l.rstrip('\n')
        l2=l2.split(';')
        item=l2[idx]
        if numeric:
            try:
                num=float(item)
            except ValueError:
                num=float('nan')
            item=num
        column.append(item)
    csv_file.close()
    return column

def column_to_vtk_array(col,name='unknown'):
    if isinstance(col[0],float):
        array=vtk.vtkFloatArray()
    else:
        array=vtk.vtkStringArray()
    for item in col:
        array.InsertNextValue(item)
    array.SetName(name)
    return array


def get_struct_volume(struct_name,code):
    try:
        model=reader.get('model',code,name=struct_name)
    except:
        return float('nan')
    _,volume=braviz.interaction.compute_volume_and_area(model)
    return volume

table=vtk.vtkTable()
wmi=get_column('WMIIQ', True)
table.AddColumn(column_to_vtk_array(wmi,'wmi'))
codes=get_column('code', False)
volumes=map(lambda code: get_struct_volume('CC_Anterior',code) ,codes)
table.AddColumn(column_to_vtk_array(volumes,'volume'))
table.AddColumn(column_to_vtk_array(codes,'code'))

view=vtk.vtkContextView()
view.GetRenderer().SetBackground(1.0,1.0,1.0)
view.GetRenderWindow().SetSize(400,300)

chart=vtk.vtkChartXY()
view.GetScene().AddItem(chart)
chart.SetShowLegend(False)

points=chart.AddPlot(vtk.vtkChart.POINTS)
points.SetInputData(table,0,1)
points.SetColor(0,0,0,255)
points.SetWidth(1.0)
points.SetMarkerStyle(vtk.vtkPlotPoints.CIRCLE)
points.SetIndexedLabels(column_to_vtk_array(codes,'code'))
points.SetTooltipLabelFormat('code=%i')
xaxis=chart.GetAxis(0)
xaxis.SetTitle('wmi')
#xaxis.SetTicksVisible(1)
#xaxis.SetLabelsVisible(1)

yaxis=chart.GetAxis(1)
yaxis.SetTitle('CC_Anterior - Volume (mm3)')

view.GetRenderWindow().SetMultiSamples(0)
view.GetInteractor().Initialize()
view.GetInteractor().Start()