from __future__ import division
import vtk
import braviz
from os.path import join as path_join 
import random
import Tkinter as tk
import ttk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

class SpiderPlotClass:
    def __init__(self, title, num_tuples, axes_names, axes_ranges, width, height):
        '''
        num_tuples: number of patients to plot
        axes_names: name of each axis
        axes_ranges: dictionary with axis_name, [min, max]
        width: width of the plot
        height: height of the plot
        '''
         
        self.width = width
        self.height = height
         
        self.num_tuples = num_tuples #Numero de redes a pintar, puntaje del paciente maximo, puntaje del paciente minimo y valor del paciente
         
        self.floats_array = []
       
        #create the float arrays 
        for index in range(0,len(axes_names)):
            array_i = vtk.vtkFloatArray()
            array_i.SetNumberOfTuples(self.num_tuples)
            self.floats_array.append(array_i)
        
        self.actor=vtk.vtkSpiderPlotActor()
        self.actor.SetTitle(title)
        self.actor.SetIndependentVariablesToColumns()
        self.actor.GetProperty().SetColor(1,0,0)
        self.actor.SetNumberOfRings(0)
                
        self.actor.GetPositionCoordinate().SetValue(0.05,0.1,0.0)
        self.actor.GetPosition2Coordinate().SetValue(0.95,0.85,0.0)
         
        self.actor.SetLegendVisibility(False)

        
        #Set the axis label and ranges
        index = 0
        for axis_name in axes_names:
            #self.actor.SetAxisLabel(index,axis_name)
            self.actor.SetAxisLabel(index,"%s \n(%.1f,%.1f)" %(axis_name,axes_ranges[axis_name][0],axes_ranges[axis_name][1]))
            
            self.actor.SetAxisRange(index,axes_ranges[axis_name][0],axes_ranges[axis_name][1])
            index = index + 1
        
        self.actor.GetLegendActor().SetNumberOfEntries(self.num_tuples)

        for i in range(self.num_tuples):
            self.actor.SetPlotColor(i,random.random(),random.random(),random.random())
        
        ############################
        #VTK
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.renderer.SetBackground(0.0, 0.0, 0.0)
        
        
    def update_data(self, data):
        float_array_index = 0
        for tuple_data in data:
            tuple_index = 0
            for tuple_value in tuple_data:
                self.floats_array[float_array_index].SetTuple(tuple_index, [tuple_value])
                tuple_index = tuple_index + 1
            float_array_index = float_array_index + 1
        
        dobj=vtk.vtkDataObject()
        for array in self.floats_array:
            dobj.GetFieldData().AddArray(array)
            
        self.actor.SetInputData(dobj)
    
    def update_title(self, title):
        self.actor.SetTitle(title)
        self.title = title

    def get_actor(self):
        return self.actor
    
    def get_render_window(self):
        return self.render_window
    
    def init_render(self, render_widget):
        self.interactor = render_widget.GetRenderWindow().GetInteractor()   
        self.renderer.AddActor(self.actor)
        self.interactor.Initialize()
        self.interactor.Start()
        
    def refresh(self):
        self.render_window.Render()