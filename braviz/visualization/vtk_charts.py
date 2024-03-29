##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


"""Visualizations based on vtkCharts"""
from __future__ import division
import logging

import vtk
import numpy as np

# line plot


class LinePlot(vtk.vtkContextActor):

    """A vtk line plot"""

    def __init__(self):
        """Initializes internal structures"""
        chart = vtk.vtkChartXY()
        scene = vtk.vtkContextScene()

        chart.SetAutoSize(True)
        scene.AddItem(chart)
        self.SetScene(scene)

        self.chart = chart
        self.scene = scene
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
        self.vertical_line_id = None
        self.position = None

    def set_position(self, x, y, width, height):
        """Sets the position in the render of the plot"""
        self.chart.SetAutoSize(False)
        self.chart.SetSize(vtk.vtkRectf(x, y, width, height))
        self.position = (x, y, width, height)

    def get_position(self):
        """Return (x,y,width,height)"""
        if self.position is not None:
            return self.position
        x1, y1 = self.chart.GetPoint1()
        x2, y2 = self.chart.GetPoint2()
        return x1, y1, x2 - x1, y2 - y1

    def set_renderer(self, ren):
        """Sets the renderer for the plot"""
        self.scene.SetRenderer(ren)

    def set_values(self, values, color=None, width=None, marker=None):
        """Values should be a list of lists, the first list will be used for the x asis
        color,width,and marker if provided should be arrays,
        index 0 will correspond to signal 1 (this properties don't apply for the x signal)
        None can be provided in any field to leave the default value"""
        if len(values) < 2:
            return

        # Create table
        table = vtk.vtkTable()
        arrX = vtk.vtkFloatArray()
        arrX.SetName("X_axis")
        table.AddColumn(arrX)

        for i in xrange(len(values) - 1):
            arrS = vtk.vtkFloatArray()
            arrS.SetName("Signal_%d" % i)
            table.AddColumn(arrS)

        table.SetNumberOfRows(len(values[0]))
        try:
            for c, column in enumerate(values):
                for i in xrange(len(values[0])):
                    table.SetValue(i, c, float(column[i]))
        except IndexError:
            log = logging.getLogger(__name__)
            log.error("All arrays in values must have the same length")
            raise Exception("All arrays in values must have the same length")
        # create line plots
        self.chart.ClearPlots()
        for signal in xrange(1, len(values)):
            line_plot = self.chart.AddPlot(vtk.vtkChart.LINE)
            line_plot.SetInputData(table, 0, signal)
            if color is not None and color[signal - 1] is not None:
                line_plot.SetColor(*(color[signal - 1]))
            if width is not None and width[signal - 1] is not None:
                line_plot.SetWidth(width[signal - 1])
            if marker is not None and marker[signal - 1] is not None:
                line_plot.SetMarkerStyle(marker[signal - 1])
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
        """Sets parameters for the x axis"""
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
        """Sets parameters for the y axis"""
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

    def add_vertical_line(self, x_coordinate, min_y=None, max_y=None, color=(255, 0, 0, 255)):
        """Adds a vertical line at x_coordinate to the chart"""
        if self.vertical_line_id is not None:
            self.chart.RemovePlot(self.vertical_line_id)
        if x_coordinate is None:
            return
        if min_y is None:
            min_y = self.y_axis.GetMinimum()
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
        line_table.SetValue(0, 0, x_coordinate)  # x
        line_table.SetValue(1, 0, x_coordinate)  # x
        line_table.SetValue(0, 1, min_y)  # y
        line_table.SetValue(1, 1, max_y)  # y
        line.SetInputData(line_table, 0, 1)


class BarPlot(vtk.vtkContextActor):

    """A vtk based bar plot which displays a single bar"""

    def __init__(self):
        """Initializes internal structures"""
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
        self.position = None

    def set_renderer(self, ren):
        """Sets the renderer for the plot"""
        self.scene.SetRenderer(ren)

    def set_value(self, value, color=None):
        """Set the value for the bar"""
        self.chart.ClearPlots()
        #=============================================
        self.table.SetValue(0, 0, 1)  # dummy for x axis
        self.table.SetValue(0, 1, value)
        bar = self.chart.AddPlot(vtk.vtkChart.BAR)
        bar.SetInputData(self.table, 0, 1)
        if color is not None:
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
        """sets the position for the bar plot"""
        self.chart.SetAutoSize(False)
        self.chart.SetSize(vtk.vtkRectf(x, y, width, height))
        self.position = (x, y, width, height)

    def get_position(self):
        """Return (x,y,width,height)"""
        if self.position is not None:
            return self.position
        x1, y1 = self.chart.GetPoint1()
        x2, y2 = self.chart.GetPoint2()
        return x1, y1, x2 - x1, y2 - y1

    def set_x_axis(self, title=None, limits=None, ticks=None, visible=True):
        """sets parameters for the x axis"""
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
        """Sets parameters for the y axis"""
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


class multi_bar_plot(vtk.vtkContextView):

    """This class is designed to use inside a single widget, displays several bars (buggy)"""

    def __init__(self):
        """Initialize internal structures"""
        # easy access to renderer
        self.ren = self.GetRenderer()

        chart = vtk.vtkChartXY()
        self.GetScene().AddItem(chart)
        chart.SetShowLegend(False)
        chart.SetHiddenAxisBorder(0)
        chart.SetInteractive(False)
        # chart.SetForceAxesToBounds(True)
        self.GetInteractor().Initialize()

        self.width = 5
        self.start = 100
        self.max_elements = 20
        self.color_fun = None
        self.chart = chart
        self.data = []
        self.data_tip = None
        self.lines = []
        self.y_min = None
        self.y_max = None
        self.y_title = ""
        self.x_title = ""
        self.enphasis = None

    def set_enphasis(self, index):
        """Highlights a bar"""
        self.enphasis = index

    def get_bar_graph_width(self):
        """Gets the current width of bars"""
        n_elements = self.max_elements
        col_width = self.width
        return n_elements * (col_width + 1) - 1
    # What follows is all very hacky, and probable dependant on implementation
    # details

    def get_minimum_start(self):
        #2*s > w*n
        n_elements = self.max_elements
        col_width = self.width
        return n_elements * col_width / 2

    def get_maximum_width(self):
        start = self.start
        n_elements = self.max_elements
        return 2 * start / n_elements

    def set_bar_width(self, width):
        if width < self.get_maximum_width():
            self.width = width
            return True
        else:
            log = logging.getLogger(__name__)
            log.error("width must be smaller than %f" %
                      self.get_maximum_width())
            return False

    def set_start(self, graph_start):
        if graph_start < self.get_minimum_start():
            self.start = graph_start
            return True
        else:
            log = logging.getLogger(__name__)
            log.error("start must be larger than %f" %
                      self.get_minimum_start())
            return False

    def set_n_elements(self, n_elements):
        n_elements_low_limit = 2 * self.start / self.width
        if n_elements > n_elements_low_limit:
            self.max_elements = n_elements
            return True
        else:
            log = logging.getLogger(__name__)
            log.error("the number of elements must be larger than %f" %
                      n_elements_low_limit)
            return False

    def set_all(self, n_elements, width, start):
        s = start
        n = n_elements
        w = width
        if 2 * s > w * n:
            self.start = s
            self.width = w
            self.max_elements = n
            return True
        else:
            log = logging.getLogger(__name__)
            log.error("2*s > w*n must hold!")
            return False

    def __add_bar2(self, position, value, code, color_fun=None, enphasize=False):
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

        bars = self.chart.AddPlot(vtk.vtkChart.BAR)
        bars.SetInputData(vtk_table, 0, 1)

        vtk_table.SetValue(0, 0, position)
        vtk_table.SetValue(0, 0, position)
        vtk_table.SetValue(0, 1, value)
        vtk_table.SetValue(1, 1, 0)
        if color_fun is not None:
            rgb_color = color_fun(value)
            bars.SetColor(*rgb_color)
        if code is not None:
            bars.SetIndexedLabels(arri_c)
            bars.SetTooltipLabelFormat('%i:%y')
        if enphasize is True:
            pen = bars.GetPen()
            pen.SetColor(255, 255, 20)
            pen.SetWidth(3)

        return bars

    def set_color_fun(self, color_function):
        """color_function must take an scalar value and rerturn a (r,g,b,a) tuple"""
        self.color_fun = color_function

    def __add_line2(self, y_pos, dashed, limits):
        line = self.chart.AddPlot(vtk.vtkChart.LINE)
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
        vtk_table.SetValue(1, 0, limits[1])
        vtk_table.SetValue(1, 1, y_pos)
        line.SetInputData(vtk_table, 0, 1)
        line.SetColor(0, 0, 0, 255)
        if dashed is True:
            pen = line.GetPen()
            pen.SetLineType(vtk.vtkPen.DASH_LINE)

    def set_data(self, data, data_tips=None):
        """sets data for the bar chart, and optionally data tips"""
        self.data = data
        self.data_tip = data_tips

    def set_lines(self, line_pos, dashed=None):
        """Dashed must be a true or false array of the same length as line_pos"""
        if dashed and len(dashed) == len(line_pos):
            lines = zip(line_pos, dashed)
        else:
            lines = zip(line_pos, [False] * len(line_pos))
        self.lines = lines
        return True

    def set_y_limis(self, y_min, y_max):
        """sets limits for the y axis"""
        self.y_min = y_min
        self.y_max = y_max

    def set_y_title(self, y_title):
        """set y title for y axis"""
        self.y_title = y_title

    def set_x_title(self, x_title):
        """sets title for x axis"""
        self.x_title = x_title

    def paint_bar_chart(self):
        """paints the chart"""
        w = self.width
        s = self.start
        data = self.data
        n = self.max_elements

        self.chart.ClearPlots()
        if len(data) > 0:
            if not (2 * s > w * n):
                raise Exception(
                    "2*s > w*n must hold!, use get mimimum start to calculate a proper start position")
            b = 2 / (2 * s / (w * n) + 1)
            x_2 = s + w * n / 2
            if self.data_tip is None:
                codes = [None] * len(data)
            else:
                codes = self.data_tip
            enph_vect = [False] * len(data)
            if self.enphasis is not None:
                enph_vect[self.enphasis] = True
            positions = [x_2 + x for x in range(len(data))]
            all_values = zip(positions, data, codes, enph_vect)
            for pos, d, code, enph in all_values:
                self.chart.SetBarWidthFraction(b)
                bar_n = self.__add_bar2(
                    pos, d, code, color_fun=self.color_fun, enphasize=enph)

        chart_width = self.get_bar_graph_width()
        min_x = self.start - chart_width * 0.05
        max_x = self.start + chart_width * 1.05

        for ln in self.lines:
            self.__add_line2(ln[0], ln[1], (min_x, max_x))

        ax = self.chart.GetAxis(vtk.vtkAxis.BOTTOM)
        ax.SetBehavior(1)
        ax.SetMinimum(min_x)
        ax.SetMaximum(max_x)
        ax.SetTitle("")
        ax.SetGridVisible(0)
        ax.SetTicksVisible(0)
        ax.SetLabelsVisible(0)

        ay = self.chart.GetAxis(vtk.vtkAxis.LEFT)
        if self.y_min is not None and self.y_max is not None:
            ay.SetBehavior(1)
            ay.SetMinimum(self.y_min)
            ay.SetMaximum(self.y_max)
            # print self.y_min
        ay.SetTitle(self.y_title)
        if len(self.y_title) == 0:
            ay.SetGridVisible(1)
            ay.SetTicksVisible(1)
            ay.SetLabelsVisible(0)
            ay.SetVisible(False)

            # print ln


class mini_scatter_plot(vtk.vtkContextActor):

    """A scatter plot designed to be overlayed on top of a 3d scene"""

    def __init__(self):
        """Initializes all itnernal structures"""
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

        self.ren = None
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
        self.position = None
        self.color = (0, 0, 0)
        self.reg_line_table = None
        self.scatter = None
        self.locator = None

    def set_renderer(self, ren):
        """Sets the renderer for the plot"""
        self.scene.SetRenderer(ren)
        self.ren = ren

    def set_position(self, x, y, width, height):
        """Sets the position of the plot"""
        self.chart.SetAutoSize(False)
        self.chart.SetSize(vtk.vtkRectf(x, y, width, height))
        self.position = (x, y, width, height)

    def get_position(self):
        """Return (x,y,width,height)"""
        if self.position is not None:
            return self.position
        x1, y1 = self.chart.GetPoint1()
        x2, y2 = self.chart.GetPoint2()
        return x1, y1, x2 - x1, y2 - y1

    def set_x_axis(self, title=None, limits=None, ticks=None, visible=True):
        """sets parameter for the x axis"""
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
        """sets parameter for the y axis"""
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

    def set_color(self, color):
        """sets colors for the dots"""
        if type(color[0]) == float:
            rgb_color = np.dot(color, 255)
            color = map(int, rgb_color)
        self.color = color

    def add_correlation(self, data):
        """Adds a regression line"""
        from scipy.stats import linregress
        x, y = zip(*data)
        if len(x) < 2:
            return
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        if np.isnan(slope) or np.isnan(intercept):
            self.chart.SetTitle("r=NaN")
            return
        self.chart.SetTitle("r=%.2f" % r_value)
        self.chart.GetTitleProperties().SetColor(np.dot(self.color, 1 / 255))
        reg_line = self.chart.AddPlot(vtk.vtkChart.LINE)
        if self.reg_line_table is None:
            line_table = vtk.vtkTable()
            arrX = vtk.vtkFloatArray()
            arrX.SetName("X_axis")
            line_table.AddColumn(arrX)
            arrY = vtk.vtkFloatArray()
            arrY.SetName("Y_axis")
            line_table.AddColumn(arrY)
            self.reg_line_table = line_table
        table = self.reg_line_table
        min_x = self.x_axis.GetMinimum()
        max_x = self.x_axis.GetMaximum()
        min_y = self.y_axis.GetMinimum()
        max_y = self.y_axis.GetMaximum()
        self.x_axis.SetBehavior(1)
        self.y_axis.SetBehavior(1)
        min_y_intercept = (min_y - intercept) / slope
        max_y_intercept = (max_y - intercept) / slope
        min_x_intercept = min_x * slope + intercept
        max_x_intercept = max_x * slope + intercept
        interceptions = 0
        table.SetNumberOfRows(2)
        if min_y <= min_x_intercept < max_y:
            table.SetValue(interceptions, 0, min_x)
            table.SetValue(interceptions, 1, min_x_intercept)
            interceptions += 1
        if min_x <= max_y_intercept < max_x:
            table.SetValue(interceptions, 0, max_y_intercept)
            table.SetValue(interceptions, 1, max_y)
            interceptions += 1
        if min_y < max_x_intercept <= max_y:
            table.SetValue(interceptions, 0, max_x)
            table.SetValue(interceptions, 1, max_x_intercept)
            interceptions += 1
        if min_x < min_y_intercept <= max_x:
            table.SetValue(interceptions, 0, min_y_intercept)
            table.SetValue(interceptions, 1, min_y)
            interceptions += 1
        assert(interceptions == 2 or interceptions == 0)
        if interceptions == 2:
            reg_line.SetInputData(table, 0, 1)

    def set_values(self, values):
        """Sets the values for the plot and updates it"""
        self.chart.ClearPlots()
        #=============================================
        self.table.SetNumberOfRows(len(values))
        for i, (x, y) in enumerate(values):
            self.table.SetValue(i, 0, x)  # dummy for x axis
            self.table.SetValue(i, 1, y)
            # print '%.2f , %.2f'%(x,y)

        scatter = self.chart.AddPlot(vtk.vtkChart.POINTS)
        scatter.SetInputData(self.table, 0, 1)
        color = self.color
        scatter.SetColor(color[0], color[1], color[2], 255)
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
        axis_x.GetPen().SetColor(color)
        axis_y.GetPen().SetColor(color)
        axis_x.GetGridPen().SetColor(color)
        axis_y.GetGridPen().SetColor(color)
        axis_x.GetTitleProperties().SetColor(np.dot(color, 1 / 255))
        axis_y.GetTitleProperties().SetColor(np.dot(color, 1 / 255))
        axis_x.GetLabelProperties().SetColor(np.dot(color, 1 / 255))
        axis_y.GetLabelProperties().SetColor(np.dot(color, 1 / 255))

        # locator=vtk.vtkKdTreePointLocator()
        locator = vtk.vtkOctreePointLocator()
        data_set = vtk.vtkPolyData()
        points = vtk.vtkPoints()
        points.SetNumberOfPoints(len(values))
        for i, (x, y) in enumerate(values):
            points.SetPoint(i, (x, y, 0))
        data_set.SetPoints(points)
        locator.SetDataSet(data_set)
        self.locator = locator
        #================================================
        self.x_axis = axis_x
        self.y_axis = axis_y
        self.scatter = scatter
        self.ren.Render()
        self.add_correlation(values)

    def select_point(self, point_id):
        """Selects a point in the scatter"""
        selected_ids = vtk.vtkIdTypeArray()
        if point_id is not None:
            selected_ids.InsertNextValue(point_id)
        self.scatter.SetSelection(selected_ids)
        self.InvokeEvent(vtk.vtkCommand.InteractionEvent)

    def find_point(self, coordinates):
        """Finds the id of the point closer to coordinates"""
        coordinates3 = (coordinates[0], coordinates[1], 0)
        closest_id = self.locator.FindClosestPoint(coordinates3)
        return closest_id

    def get_point_by_id(self, point_id):
        """Returns the coordinates of a point given its id"""
        return self.locator.GetDataSet().GetPoint(point_id)
