#Visualizations based on vtkCharts
from __future__ import division
import vtk
import numpy as np
#line plot
class LinePlot(vtk.vtkContextActor):
    def __init__(self):
        chart = vtk.vtkChartXY()
        scene = vtk.vtkContextScene()

        chart.SetAutoSize(True)
        scene.AddItem(chart)
        self.SetScene(scene)

        self.chart=chart
        self.scene=scene
        self.x_limits = None
        self.y_limits = None
        self.x_ticks = None
        self.y_ticks = None
        self.x_axis = None
        self.y_axis = None
        self.x_title = None
        self.y_title = None
        self.x_visible = True
        self.y_visible = True
        self.vertical_line_id=None
    def set_position(self, x, y, width, height):
        self.chart.SetAutoSize(False)
        self.chart.SetSize(vtk.vtkRectf(x, y, width, height))
        self.position=(x,y,width,height)
    def get_position(self):
        "Return (x,y,width,height)"
        if self.position is not None:
            return self.position
        x1,y1=self.chart.GetPoint1()
        x2, y2 = self.chart.GetPoint2()
        return x1,y1,x2-x1,y2-y1
    def set_renderer(self, ren):
        self.scene.SetRenderer(ren)
    def set_values(self, values, color=None,width=None,marker=None):
        """Values should be a list of lists, the first list will be used for the x asis
        color,width,and marker if provided should be arrays,
        index 0 will correspond to signal 1 (this properties don't apply for the x signal)
        None can be provided in any field to leave the default value"""
        if len(values)<2:
            return

        #Create table
        table = vtk.vtkTable()
        arrX = vtk.vtkFloatArray()
        arrX.SetName("X_axis")
        table.AddColumn(arrX)

        for i in xrange(len(values)-1):
            arrS = vtk.vtkFloatArray()
            arrS.SetName("Signal_%d" % i)
            table.AddColumn(arrS)

        table.SetNumberOfRows(len(values[0]))
        try:
            for c,column in enumerate(values):
                for i in xrange(len(column)):
                    table.SetValue(i,c,float(column[i]) )
        except IndexError:
            print "All arrays in values must have the same length"
            raise Exception("All arrays in values must have the same length")
        #create line plots
        self.chart.ClearPlots()
        for signal in xrange(1,len(values)):
            line_plot = self.chart.AddPlot(vtk.vtkChart.LINE)
            line_plot.SetInputData(table, 0, signal)
            if color is not None and color[signal-1] is not None:
                line_plot.SetColor(*(color[signal-1]))
            if width is not None and width[signal-1] is not None:
                line_plot.SetWidth(width[signal-1])
            if marker is not None and marker[signal-1] is not None:
                line_plot.SetMarkerStyle(marker[signal-1])
        #=========AXIS=================
        axis_y = self.chart.GetAxis(0)
        if self.y_limits is not None:
            minimum, maximum = self.y_limits
            axis_y.SetMinimum(minimum)
            axis_y.SetMaximum(maximum)
            axis_y.SetBehavior(1)
        else:
            axis_y.SetBehavior(0)
        if self.y_title is not None:
            axis_y.SetTitle(self.y_title)
        if self.y_ticks is not None:
            axis_y.SetCustomTickPositions(self.y_ticks)

        if self.y_title is not None:
            axis_y.SetTitle(self.y_title)
        if not self.y_visible:
            axis_y.SetGridVisible(0)
            axis_y.SetTicksVisible(0)
            axis_y.SetLabelsVisible(0)
            #===========================================
        axis_x = self.chart.GetAxis(1)
        if self.x_limits is not None:
            minimum, maximum = self.x_limits
            axis_x.SetMinimum(minimum)
            axis_x.SetMaximum(maximum)
            axis_x.SetBehavior(1)
        else:
            axis_x.SetBehavior(0)
        if self.x_title is not None:
            axis_x.SetTitle(self.x_title)
        if self.x_ticks is not None:
            axis_x.SetCustomTickPositions(self.x_ticks)
        if not self.x_visible:
            axis_x.SetGridVisible(0)
            axis_x.SetTicksVisible(0)
            axis_x.SetLabelsVisible(0)

        #================================================
        self.x_axis = axis_x
        self.y_axis = axis_y
    def set_x_axis(self, title=None, limits=None, ticks=None, visible=True):
        self.x_limits = limits
        if ticks is not None:
            ticks_array = vtk.vtkDoubleArray()
            ticks_array.SetNumberOfTuples(len(ticks))
            for i, t in enumerate(ticks):
                ticks_array.SetTupleValue(i, t)
            self.x_ticks = ticks_array
        else:
            self.x_ticks = None
        self.x_title = title
        self.x_visible = visible

    def set_y_axis(self, title=None, limits=None, ticks=None, visible=True):
        self.y_limits = limits
        if ticks is not None:
            ticks_array = vtk.vtkDoubleArray()
            ticks_array.SetNumberOfTuples(len(ticks))
            for i, t in enumerate(ticks):
                ticks_array.SetTupleValue(i, (t,))
            self.y_ticks = ticks_array
        else:
            self.y_ticks = None
        self.y_title = title
        self.y_visible = visible

    def add_vertical_line(self,x_coordinate,min_y=None,max_y=None,color=(255,0,0,255)):
        if self.vertical_line_id is not None:
            self.chart.RemovePlot(self.vertical_line_id)
        if x_coordinate is None:
            return
        if min_y is None:
            min_y=self.y_axis.GetMinimum()
        if max_y is None:
            max_y = self.y_axis.GetMaximum()
        self.vertical_line_id = self.chart.GetNumberOfPlots()
        line = self.chart.AddPlot(vtk.vtkChart.LINE)
        line.SetColor(*color)
        line_table = vtk.vtkTable()
        arrlX = vtk.vtkFloatArray()
        arrlX.SetName('X line')
        arrlY = vtk.vtkFloatArray()
        arrlY.SetName('Y line')
        line_table.AddColumn(arrlX)
        line_table.AddColumn(arrlY)
        line_table.SetNumberOfRows(2)
        line_table.SetValue(0, 0, x_coordinate) #x
        line_table.SetValue(1, 0, x_coordinate) #x
        line_table.SetValue(0, 1, min_y) #y
        line_table.SetValue(1, 1, max_y) #y
        line.SetInputData(line_table, 0, 1)

class BarPlot(vtk.vtkContextActor):
    def __init__(self):
        chart = vtk.vtkChartXY()
        scene = vtk.vtkContextScene()

        scene.AddItem(chart)
        self.SetScene(scene)

        table = vtk.vtkTable()
        arr_x = vtk.vtkFloatArray()
        arr_x.SetName("x")

        arri_y = vtk.vtkFloatArray()
        arri_y.SetName("y")

        table.AddColumn(arri_y)
        table.AddColumn(arr_x)
        table.SetNumberOfRows(1)

        self.table = table
        self.scene = scene
        self.chart = chart
        self.x_limits = None
        self.y_limits = None
        self.x_ticks = None
        self.y_ticks = None
        self.x_axis = None
        self.y_axis = None
        self.x_title = None
        self.y_title = None
        self.x_visible = True
        self.y_visible = True
        self.position=None
    def set_renderer(self, ren):
        self.scene.SetRenderer(ren)

    def set_value(self, value, color=None):
        self.chart.ClearPlots()
        #=============================================
        self.table.SetValue(0, 0, 1) #dummy for x axis
        self.table.SetValue(0, 1, value)
        bar = self.chart.AddPlot(vtk.vtkChart.BAR)
        bar.SetInputData(self.table, 0, 1)
        rgb_color = np.concatenate((np.dot(color, 255), (255,)))
        rgb_color = rgb_color.astype(int)
        bar.SetColor(*rgb_color)
        bar.SetWidth(4.0)
        axis_y = self.chart.GetAxis(0)
        if self.y_limits is not None:
            minimum, maximum = self.y_limits
            axis_y.SetMinimum(minimum)
            axis_y.SetMaximum(maximum)
            axis_y.SetBehavior(1)
        else:
            axis_y.SetBehavior(0)
        if self.y_title is not None:
            axis_y.SetTitle(self.y_title)
        if self.y_ticks is not None:
            axis_y.SetCustomTickPositions(self.y_ticks)

        if self.y_title is not None:
            if "%(value)" in self.x_title:
                axis_y.SetTitle(self.y_title % {"value": value})
            else:
                axis_y.SetTitle(self.y_title)
        if not self.y_visible:
            axis_y.SetGridVisible(0)
            axis_y.SetTicksVisible(0)
            axis_y.SetLabelsVisible(0)
            #===========================================
        axis_x = self.chart.GetAxis(1)
        if self.x_limits is not None:
            minimum, maximum = self.x_limits
            axis_x.SetMinimum(minimum)
            axis_x.SetMaximum(maximum)
            axis_x.SetBehavior(1)
        else:
            axis_x.SetBehavior(0)
        if self.x_title is not None:
            if "%(value)" in self.x_title:
                axis_x.SetTitle(self.x_title % {"value": value})
            else:
                axis_x.SetTitle(self.x_title)
        axis_x.SetTitle('%f' % value)
        if self.x_ticks is not None:
            axis_x.SetCustomTickPositions(self.x_ticks)
        if not self.x_visible:
            axis_x.SetGridVisible(0)
            axis_x.SetTicksVisible(0)
            axis_x.SetLabelsVisible(0)

        #================================================
        self.x_axis = axis_x
        self.y_axis = axis_y

    def set_position(self, x, y, width, height):
        self.chart.SetAutoSize(False)
        self.chart.SetSize(vtk.vtkRectf(x, y, width, height))
        self.position=(x,y,width,height)
    def get_position(self):
        "Return (x,y,width,height)"
        if self.position is not None:
            return self.position
        x1,y1=self.chart.GetPoint1()
        x2, y2 = self.chart.GetPoint2()
        return x1,y1,x2-x1,y2-y1


    def set_x_axis(self, title=None, limits=None, ticks=None,visible=True):
        self.x_limits = limits
        if ticks is not None:
            ticks_array = vtk.vtkDoubleArray()
            ticks_array.SetNumberOfTuples(len(ticks))
            for i,t in enumerate(ticks):
                ticks_array.SetTupleValue(i,t)
            self.x_ticks = ticks_array
        else:
            self.x_ticks = None
        self.x_title = title
        self.x_visible = visible

    def set_y_axis(self, title=None, limits=None, ticks=None,visible=True):
        self.y_limits = limits
        if ticks is not None:
            ticks_array = vtk.vtkDoubleArray()
            ticks_array.SetNumberOfTuples(len(ticks))
            for i,t in enumerate(ticks):
                ticks_array.SetTupleValue(i,(t,))
            self.y_ticks = ticks_array
        else:
            self.y_ticks = None
        self.y_title = title
        self.y_visible = visible


