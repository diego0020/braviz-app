from __future__ import division
import braviz
from braviz.visualization.create_lut import get_colorbrewer_lut
import vtk
import random
import math
from os.path import join as path_join
import numpy as np

__author__ = 'Diego'

class grid_view(vtk.vtkRenderWindow):
    def __init__(self):
        self.ren=vtk.vtkRenderer()
        self.AddRenderer(self.ren)
        self.SetSize(600,400)
        self.ren.Render()
        #self.Initialize()
        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.005)
        if self.GetInteractor() is None:
            self.iren=vtk.vtkRenderWindowInteractor()
        else:
            self.iren=self.GetInteractor()
        self.iren.SetRenderWindow(self)
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballActor())
        self.set_background((0.2,0.2,0.2),(0.5,0.5,0.5))
        # subj->actor
        self.__actors_dict={}
        # actor -> subj
        self.__picking_dict={}
        self.__poly_data_dict={}
        self.__mapper_dict={}
        self.__messages_dict={}
        self.balloon_w=vtk.vtkBalloonWidget()
        self.balloon_repr=vtk.vtkBalloonRepresentation()
        self.balloon_w.SetRepresentation(self.balloon_repr)
        self.balloon_w.SetInteractor(self.iren)
        self.balloon_w.On()
        self.max_space=0
        self.n_rows=0
        self.n_cols=0
        self.__modified_actor=None
        self.__panning=False
        self.__panning_start_pos=None
        self.__panning_start_cam_focal=None
        self.__panning_start_cam_pos=None
        self.color_function = None
        #observers
        def register_change(caller=None, envent=None):
            self.panning = False
            if self.__modified_actor is not None:
                return
            self.__modified_actor = caller


        def after_intareaction(caller=None, event=None):
            if self.__modified_actor is not None:
                mimic_actor(self.__modified_actor)
            self.__modified_actor = None

        def mimic_actor(caller=None, event=None):
            for ac in self.__picking_dict:
                if ac is not caller:
                    ac.SetOrientation(caller.GetOrientation())
                    ac.SetScale(caller.GetScale())

        def wheel_zoom(caller=None, event=None):
            factor = 0.5
            cam1=self.ren.GetActiveCamera()
            if event == 'MouseWheelForwardEvent':
                cam1.SetParallelScale(cam1.GetParallelScale() * factor)
            else:
                cam1.SetParallelScale(cam1.GetParallelScale() / factor)
            self.iren.Render()

        def pan(caller=None, event=None):
            if event == 'MiddleButtonPressEvent':
                event_pos_x, event_pos_y = caller.GetEventPosition()
                if (self.ren.PickProp(event_pos_x, event_pos_y) is not None):
                    self.__panning = False
                    return
                self.__panning = True
                cam1 = self.ren.GetActiveCamera()
                self.__panning_start_pos = np.array(caller.GetEventPosition())
                self.__panning_start_cam_pos = np.array(cam1.GetPosition())
                self.__panning_start_cam_focal = np.array(cam1.GetFocalPoint())
            else:
                if self.__panning == False:
                    return
                if event == 'MiddleButtonReleaseEvent':
                    self.__panning = False
            cam1 = self.ren.GetActiveCamera()
            delta = caller.GetEventPosition() - self.__panning_start_pos
            delta = (delta[0], -delta[1], 0)
            delta=np.dot(delta,0.01*cam1.GetParallelScale())
            cam1.SetPosition(self.__panning_start_cam_pos - delta)
            cam1.SetFocalPoint(self.__panning_start_cam_focal - delta)
            caller.Render()
        #register observers

        self.iren.AddObserver(vtk.vtkCommand.EndInteractionEvent, after_intareaction)
        self.iren.AddObserver(vtk.vtkCommand.MouseWheelForwardEvent, wheel_zoom)
        self.iren.AddObserver(vtk.vtkCommand.MouseWheelBackwardEvent, wheel_zoom)
        self.iren.AddObserver(vtk.vtkCommand.MiddleButtonPressEvent, pan)
        self.iren.AddObserver(vtk.vtkCommand.MouseMoveEvent, pan)
        self.iren.AddObserver(vtk.vtkCommand.MiddleButtonReleaseEvent, pan, 100)
        self.actor_observer_fun=register_change

    def set_background(self,color1,color2=None):
        if color2 is not None:
            self.ren.GradientBackgroundOn()
            self.ren.SetBackground2(color2)
        self.ren.SetBackground(color1)
    def set_data(self,data_dict):
        "data_dict must be a dictionary with ids as keys and polydata as values"
        for id,polydata in data_dict.iteritems():
            #center polydata
            center=polydata.GetCenter()
            trans = vtk.vtkTransformPolyDataFilter()
            t = vtk.vtkTransform()
            t.Identity()
            t.Translate(center)
            t.Inverse()
            trans.SetTransform(t)
            trans.SetInputData(polydata)
            trans.Update()
            polydata2 = trans.GetOutput()
            self.__poly_data_dict[id] = polydata2
            mapper=vtk.vtkPolyDataMapper()
            mapper.SetInputData(polydata2)
            self.__mapper_dict[id]=mapper
            actor=vtk.vtkActor()
            actor.SetMapper(mapper)
            self.__actors_dict[id]=actor
            self.ren.AddActor(actor)
            self.__picking_dict[actor]=id
            if self.color_function is not None:
                actor.GetProperty().SetColor(self.color_function(id))
            actor.AddObserver(vtk.vtkCommand.PickEvent, self.actor_observer_fun)

    def set_balloon_messages(self,messages_dict):
        for key,message in messages_dict.iteritems():
            self.balloon_w.AddBalloon(self.__actors_dict[key],message)
    def sort(self,sorted_ids):
        "actors will be displayed in the grid according to the sorted_ids list, actors not in list will become invisible"
        for ac in self.__picking_dict:
            ac.SetVisibility(0)
        def get_max_diagonal(actor):
            Xmin, Xmax, Ymin, Ymax, Zmin, Zmax = actor.GetBounds()
            return math.sqrt((Xmax - Xmin) ** 2 + (Ymax - Ymin) ** 2 + (Zmax - Zmin) ** 2)

        self.max_space = max([get_max_diagonal(actor) for actor in self.__picking_dict])
        self.max_space *= 0.95
        #calculate renWin proportions
        width, height = self.GetSize()
        row_proportion = width / height
        n_row = math.ceil(math.sqrt(len(sorted_ids) / row_proportion))
        n_col = math.ceil(len(sorted_ids) / n_row)

        #positions_dict={}
        for i, subj in enumerate(sorted_ids):
            actor = self.__actors_dict[subj]
            column = i % n_col
            row = i // n_col
            x = column * self.max_space
            y = row * self.max_space
            actor.SetPosition(x, y, 0)
            actor.SetVisibility(1)
        self.n_rows=n_row
        self.n_cols=n_col

        pass
    def set_color_function(self,color_function):
        self.color_function=color_function
        for subj,ac in self.__actors_dict.iteritems():
            ac.GetProperty().SetColor(color_function(id))

    def reset_camera(self):
        n_col=self.n_cols
        max_space=self.max_space
        n_row=self.n_rows
        self.Render()
        cam1 = self.ren.GetActiveCamera()
        cam1.ParallelProjectionOn()
        cam1.SetFocalPoint(n_col * max_space / 2 - max_space / 2, n_row * max_space / 2 - max_space / 2, 0)
        cam1.SetViewUp(0, -1, 0)
        cam1.SetParallelScale(0.55 * n_row * max_space)
        cam_distance = cam1.GetDistance()
        cam1.SetPosition(n_col * max_space / 2 - max_space / 2, n_row * max_space / 2 - max_space / 2,
                         -1 * cam_distance)

    def start_interaction(self):
        self.iren.Initialize()
        self.Start()
        self.iren.Start()


if __name__=='__main__':
    test=grid_view()
    test_data={}
    for i in range(10):
        sp=vtk.vtkSphereSource()
        sp.SetRadius(1)
        sp.Update()
        test_data[i]=sp.GetOutput()
    test.set_data(test_data)
    test.sort(range(2,10))
    test.reset_camera()
    import random
    def rand_color(id):
        return [random.random() for i in range(3)]
    messages={}
    for i in range(10):
        if i%2==0:
            messages[i]="%d : even"%i
        else:
            messages[i] = "%d : odd" % i
    test.set_balloon_messages(messages)
    test.set_color_function(rand_color)
    test.Render()
    test.start_interaction()
    ids=range(10)
    random.shuffle(ids)
    test.sort(ids)
    test.reset_camera()
    test.Render()
    test.start_interaction()