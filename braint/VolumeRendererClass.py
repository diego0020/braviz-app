'''
Created on 26/10/2013

@author: jc.forero47
'''
import braviz
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

class VolumeRendererClass:
    def __init__(self):
        self.reader = braviz.readAndFilter.kmc40AutoReader()
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.renderer.SetBackground(1.0, 0.0, 0.0)
        
    def load_model(self, vtk_structure, patient_number, vol_name):
        model = self.reader.get(vtk_structure, patient_number, name = vol_name)
        model_mapper=vtk.vtkPolyDataMapper()
        model_mapper.SetInputData(model)
        model_actor=vtk.vtkActor()
        model_actor.SetMapper(model_mapper)
        self.renderer.AddActor(model_actor)
        
    def load_image_plane(self, type_image, patient_name, image_format):
        image=self.reader.get(type_image,patient_name, format = image_format)
        self.image_plane=braviz.visualization.persistentImagePlane()
        self.image_plane.SetInputData(image)
        
    def load_fibers(self,patient_number, fiber_color, fiber_waypoint):
        fibers_l=self.reader.get('fibers',patient_number,color = fiber_color, waypoint = fiber_waypoint)
        fiber_mapper=vtk.vtkPolyDataMapper()
        fiber_mapper.SetInputData(fibers_l)
        fiber_actor=vtk.vtkActor()
        fiber_actor.SetMapper(fiber_mapper)
        self.renderer.AddActor(fiber_actor)

    def get_render_window(self):
        return self.render_window

    def render(self, render_widget):
        interactor = render_widget.GetRenderWindow().GetInteractor()
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        
        self.image_plane.SetInteractor(interactor)
        self.image_plane.On()
        interactor.Initialize()
        interactor.Start()
        
    def clean_exit(self):
         self.render_window.Finalize()
         del self.render_window