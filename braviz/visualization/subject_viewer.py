from __future__ import division
__author__ = 'Diego'

import vtk
import braviz

class SubjectViewer:
    def __init__(self,render_window_interactor,reader):

        render_window_interactor.Initialize()
        render_window_interactor.Start()
        self.iren=render_window_interactor
        self.ren_win=render_window_interactor.GetRenderWindow()
        self.ren=vtk.vtkRenderer()
        #self.ren.SetBackground((0.75,0.75,0.75))
        self.ren.GradientBackgroundOn()
        self.ren.SetBackground2( (0.5, 0.5, 0.5))
        self.ren.SetBackground((0.2, 0.2, 0.2))
        self.ren_win.AddRenderer(self.ren)
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.axes=braviz.visualization.OrientationAxes()
        self.axes.initialize(self.iren)

        self.reader=reader

        #state
        self.current_subject="093"
        self.current_space="world"
        self.current_image=None
        self.current_image_orientation="Axial"

    def show_cone(self):
        """Useful for testing"""
        cone=vtk.vtkConeSource()
        cone.SetResolution(8)
        cone_mapper=vtk.vtkPolyDataMapper()
        cone_mapper.SetInputConnection(cone.GetOutputPort())
        cone_actor=vtk.vtkActor()
        cone_actor.SetMapper(cone_mapper)
        self.ren.AddActor(cone_actor)
        self.ren_win.Render()

