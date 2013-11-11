import vtk
import random
numTuples = 3

#===============================================================================
# bitter=vtk.vtkFloatArray()
# bitter.SetNumberOfTuples(numTuples)
# 
# crispy=vtk.vtkFloatArray()
# crispy.SetNumberOfTuples(numTuples)
# 
# crunchy=vtk.vtkFloatArray()
# crunchy.SetNumberOfTuples(numTuples)
# 
# salty=vtk.vtkFloatArray()
# salty.SetNumberOfTuples(numTuples)
# 
# oily=vtk.vtkFloatArray()
# oily.SetNumberOfTuples(numTuples)
#===============================================================================

floats_array = []
axes_names = ['eje 1', 'eje 2', 'eje 3', 'eje 4', 'eje 5']
axes_ranges = {'eje 1':[0,10], 'eje 2':[0,10], 'eje 3':[0,10], 'eje 4':[0,10], 'eje 5':[0,10]}

for index in range(0,5):
    array_i = vtk.vtkFloatArray()
    array_i.SetNumberOfTuples(numTuples)
    floats_array.append(array_i)


    
#===============================================================================
# for i in range(numTuples):
#     floats_array[0].SetTuple1(i, random.randint(1,10))
#     floats_array[1].SetTuple1(i, random.randint(1,10))
#     floats_array[2].SetTuple1(i, random.randint(1,10))
#     floats_array[3].SetTuple1(i, random.randint(1,10))
#     floats_array[4].SetTuple1(i, random.randint(1,10))
#===============================================================================

#===============================================================================
# dobj=vtk.vtkDataObject()
# dobj.GetFieldData().AddArray(floats_array[0])
# dobj.GetFieldData().AddArray(floats_array[1])
# dobj.GetFieldData().AddArray(floats_array[2])
# dobj.GetFieldData().AddArray(floats_array[3])
# dobj.GetFieldData().AddArray(floats_array[4])
#===============================================================================

actor=vtk.vtkSpiderPlotActor()

actor.SetTitle("spider plot")
actor.SetIndependentVariablesToColumns()
#===============================================================================
# actor.GetPositionCoordinate().SetValue(0.05,0.1,0.0)
# actor.GetPosition2Coordinate().SetValue(0.95,0.85,0.0)
#===============================================================================
actor.GetProperty().SetColor(0,1,0)

index = 0
for axis_name in axes_names:
    actor.SetAxisLabel(index,axis_name)
    actor.SetAxisRange(index,axes_ranges[axis_name][0],axes_ranges[axis_name][1])
    index = index + 1

#===============================================================================
# actor.SetAxisLabel(0,"Bitter")
# actor.SetAxisRange(0,0,10)
# 
# actor.SetAxisLabel(1,"Crispy")
# actor.SetAxisRange(1,0,10)
# 
# actor.SetAxisLabel(2,"Crunchy")
# actor.SetAxisRange(2,0,10)
# 
# actor.SetAxisLabel(3,"Salty")
# actor.SetAxisRange(3,0,10)
# 
# actor.SetAxisLabel(4,"Oily")
# actor.SetAxisRange(4,0,10)
#===============================================================================

actor.GetLegendActor().SetNumberOfEntries(numTuples)

for i in range(numTuples):
    actor.SetPlotColor(i,random.random(),random.random(),random.random())

actor.LegendVisibilityOn()


#  // Set text colors (same as actor for backward compat with test)
#  actor.GetTitleTextProperty().SetColor(1,1,0)
#  actor.GetLabelTextProperty().SetColor(1,0,0)

data = []
for i_data in range(0,5):
    data_row = []
    for j_data in range(0,numTuples):
        data_row.append(random.randint(1,10))
    data.append(data_row)
         
 
float_array_index = 0
for tuple_data in data:
    tuple_index = 0
    for tuple_value in tuple_data:
        floats_array[float_array_index].SetTuple(tuple_index, [tuple_value])
        tuple_index = tuple_index + 1
    float_array_index = float_array_index + 1

dobj=vtk.vtkDataObject()
for array in floats_array:
    dobj.GetFieldData().AddArray(array)
    
actor.SetInputData(dobj)

ren1=vtk.vtkRenderer()
renWin=vtk.vtkRenderWindow()
renWin.AddRenderer(ren1)
iren=vtk.vtkRenderWindowInteractor()
iren.SetRenderWindow(renWin)
ren1.AddActor(actor)
ren1.SetBackground(0,0,0)
renWin.SetSize(500,500)

iren.Initialize()
renWin.Render()
iren.Start()