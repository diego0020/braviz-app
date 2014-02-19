
from __future__ import division
import vtk
import braviz
from os.path import join as path_join 

class ScatterPlotClass:
    def __init__(self, width, height):
        self.table=vtk.vtkTable()
        self.table_2 = vtk.vtkTable()
        
        self.chart=vtk.vtkChartXY()
       
       
        self.points=self.chart.AddPlot(vtk.vtkChart.POINTS)
        self.points.SetColor(0,0,0,255)
        self.points.SetWidth(1.0)
        self.points.SetMarkerStyle(vtk.vtkPlotPoints.CROSS)
        self.points.SetTooltipLabelFormat('code=%i')
        
        self.view=vtk.vtkContextView()
        self.renderer = self.view.GetRenderer()
        self.renderer.SetBackground(1.0,1.0,1.0)
        self.view.GetRenderWindow().SetSize(width,height)
        self.view.GetScene().AddItem(self.chart)
        
        ############ CODIGO NUEVO
        

        self.chart.SetSelectionMode(vtk.vtkContextScene.SELECTION_DEFAULT)
        self.annotationLink = vtk.vtkAnnotationLink()
        self.chart.SetAnnotationLink(self.annotationLink)
        #self.annotationLink.AddObserver('AnnotationChangedEvent', self.select_callback)
        #=======================================================================
        # self.propPicker = vtk.vtkPropPicker()
        # 
        # self.interactor = self.view.GetRenderWindow().GetInteractor()
        # self.interactor.AddObserver('LeftButtonReleaseEvent', self.LeftButtonReleaseCallback)
        #=======================================================================
        
        ##################################
         
         
    def set_callback(self, callback):
        self.annotationLink.AddObserver('AnnotationChangedEvent', callback)
        
    def addAxes(self,xAxisList, xAxisName, yAxisList, yAxisName, zAxisList, zAxisName):     

        self.table.ReleaseData()
        
        self.table.AddColumn(self.column_to_vtk_array(xAxisList, xAxisName))
        self.table.AddColumn(self.column_to_vtk_array(yAxisList, yAxisName))
        self.table.AddColumn(self.column_to_vtk_array(zAxisList, zAxisName))
        
        indexedLabels = self.column_to_vtk_array(zAxisList, zAxisName)
        self.points.SetIndexedLabels(indexedLabels)
        self.points.SetInputData(self.table,0,1)
        
        
        self.points.Update()
        self.chart.RecalculateBounds()
        
        xaxis=self.chart.GetAxis(1)
        xaxis.SetTitle(xAxisName)
        yaxis=self.chart.GetAxis(0)
        yaxis.SetTitle(yAxisName)
        
    def add_axes_complete(self,xAxisList, xAxisName, yAxisList, yAxisName, zAxisList, zAxisName, pointxAxis, pointyAxis):     

        self.table.ReleaseData()
        
        #=======================================================================
        # print xAxisName, 'vs', yAxisName
        # print 'xAxislist', len(xAxisList)
        # print 'yAxislist', len(yAxisList)
        # print 'zAxisList', len(zAxisList)
        # print xAxisList
        # print yAxisList
        # print zAxisList
        # print pointxAxis
        # print pointyAxis
        #=======================================================================
        
        
        self.table.AddColumn(self.column_to_vtk_array(xAxisList, xAxisName))
        self.table.AddColumn(self.column_to_vtk_array(yAxisList, yAxisName))
        self.table.AddColumn(self.column_to_vtk_array(zAxisList, zAxisName))
        
        self.table_2.ReleaseData()
        self.table_2.AddColumn(self.column_to_vtk_array(pointxAxis, 'pointx'))
        self.table_2.AddColumn(self.column_to_vtk_array(pointyAxis, 'pointy'))
        

        
        
        indexedLabels = self.column_to_vtk_array(zAxisList, zAxisName)
        self.points.SetIndexedLabels(indexedLabels)
        self.points.SetInputData(self.table,0,1)
        
        singlePoints = self.chart.AddPlot(vtk.vtkChart.POINTS)
        singlePoints.SetInputData(self.table_2, 0,1)
        singlePoints.SetColor(255,0,0,255)
        singlePoints.SetWidth(5.0)
        singlePoints.SetMarkerStyle(vtk.vtkPlotPoints.CROSS)
        
        singlePoints.Update()
        
        self.points.Update()
        self.chart.RecalculateBounds()
        
        xaxis=self.chart.GetAxis(1)
        xaxis.SetTitle(xAxisName)
        yaxis=self.chart.GetAxis(0)
        yaxis.SetTitle(yAxisName)

    def get_columnFromCSV(self, file_name, name,numeric=False):
        csv_file=open(file_name)
        headers=csv_file.readline()
        headers=headers.rstrip('\n')
        headers=headers.split(';')
        if name not in headers:
            raise  Exception("column %s not found in file %s"%(name,file_name))
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
        except Exception:
            return float('nan')
        _,volume=braviz.interaction.compute_volume_and_area(model)
        return volume
    
        
    def render(self):
        self.view.GetRenderWindow().SetMultiSamples(0)
        self.view.GetInteractor().Initialize()
        self.view.GetInteractor().Start()
    
    def get_vtk_view(self):
        return self.view

    def picker_event_handler(self, event):
        print self.picker.GetSelectionPoint()
        
    def select_callback(self,caller,event):
        # In this particular data representation the current selection in the
        # annotation link should always contain two nodes: one for the edges and
        # one for the vertices. Which is which is not consistent, so you need to
        # check the FieldType of each SelectionNode
        print 'selected'
        sel = caller.GetCurrentSelection()
      
        for nn in range(sel.GetNumberOfNodes()):
            sel_ids = sel.GetNode(nn).GetSelectionList()
            field_type = sel.GetNode(nn).GetFieldType()
            if field_type == 3:
                print "Vertex selection Pedigree IDs"
            if field_type == 4:
                print "Edge selection Pedigree IDs"
            if sel_ids.GetNumberOfTuples() > 0:
                for ii in range(sel_ids.GetNumberOfTuples()):
                    print int(sel_ids.GetTuple1(ii))
            else:
                print "-- empty"
      
        print ""
    def clean_exit(self):
        self.render_window.Finalize()
        del self.render_window
