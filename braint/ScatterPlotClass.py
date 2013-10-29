
from __future__ import division
import vtk
import braviz
from os.path import join as path_join 

class ScatterPlotClass:
    def __init__(self, width, height):
        self.table=vtk.vtkTable()
        
        self.chart=vtk.vtkChartXY()
       
        self.points=self.chart.AddPlot(vtk.vtkChart.POINTS)
        self.points.SetColor(0,0,0,255)
        self.points.SetWidth(1.0)
        self.points.SetMarkerStyle(vtk.vtkPlotPoints.CIRCLE)
        self.points.SetTooltipLabelFormat('code=%i')
        
        self.view=vtk.vtkContextView()
        self.view.GetRenderer().SetBackground(1.0,1.0,1.0)
        self.view.GetRenderWindow().SetSize(width,height)
        self.view.GetScene().AddItem(self.chart)
         
        
    def addAxes(self,xAxisList, xAxisName, yAxisList, yAxisName, zAxisList, zAxisName):     
        self.table.RemoveColumn(0)
        self.table.RemoveColumn(1)
        
        self.table.AddColumn(self.column_to_vtk_array(xAxisList, xAxisName))
        self.table.AddColumn(self.column_to_vtk_array(yAxisList, yAxisName))
        self.table.AddColumn(self.column_to_vtk_array(zAxisList, zAxisName))
        
        indexedLabels = self.column_to_vtk_array(zAxisList, zAxisName)
        self.points.SetIndexedLabels(indexedLabels)
        self.points.SetInputData(self.table,0,1)
        
        self.points.Update()
        self.chart.RecalculateBounds()
        
        xaxis=self.chart.GetAxis(0)
        xaxis.SetTitle(xAxisName)
        yaxis=self.chart.GetAxis(1)
        yaxis.SetTitle(yAxisName)

    def get_columnFromCSV(self, file_name, name,numeric=False):
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
    
    def column_to_vtk_array(self, col,name='unknown'):
        if isinstance(col[0],float):
            array=vtk.vtkFloatArray()
        else:
            array=vtk.vtkStringArray()
        for item in col:
            array.InsertNextValue(item)
        array.SetName(name)
        return array
    
    def get_struct_volume(self,reader, struct_name,code):
        try:
            model=reader.get('model',code,name=struct_name)
        except:
            return float('nan')
        _,volume=braviz.interaction.compute_volume_and_area(model)
        return volume
        
    def render(self):
        self.view.GetRenderWindow().SetMultiSamples(0)
        self.view.GetInteractor().Initialize()
        self.view.GetInteractor().Start()
    
    def get_vtk_view(self):
        return self.view

