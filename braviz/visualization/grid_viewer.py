from __future__ import division
import vtk
import random
import math
import numpy as np
from braviz.visualization import get_arrow
from braviz.visualization.vtk_charts import mini_scatter_plot
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


        self.set_background((0.2,0.2,0.2),(0.5,0.5,0.5))
        # subj->actor
        self.__actors_dict={}
        # actor -> subj
        self.__picking_dict={}
        self.__poly_data_dict={}
        self.__mapper_dict={}
        self.__messages_dict={}
        self.__positions_dict={}
        self.balloon_w=vtk.vtkBalloonWidget()
        self.balloon_repr=vtk.vtkBalloonRepresentation()
        self.balloon_w.SetRepresentation(self.balloon_repr)

        self.max_space=0
        self.n_rows=0
        self.n_cols=0
        self.__modified_actor=None
        self.__panning=False
        self.__panning_start_pos=None
        self.__panning_start_cam_focal=None
        self.__panning_start_cam_pos=None
        self.__color_function = None
        self.__actor_observer_fun = None
        self.__color_bar_visibility=False
        self.__scalar_bar_actor=None
        self.__arrow_actor=None
        self.__sort_message_actor=None
        self.__sort_message_visibility=False
        self.__sort_modified=False
        self.__mini_scatter=None
        self.__mini_scatter_visible=False
        #observers
    def set_interactor(self,iren=None):
        if iren is None:
            iren = vtk.vtkRenderWindowInteractor()
        self.iren = iren
        self.SetInteractor(iren)
        self.iren.SetRenderWindow(self)
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballActor())
        self.balloon_w.SetInteractor(self.iren)
        self.balloon_w.On()
        self.iren.SetPicker(self.picker)

        def register_change(caller=None, envent=None):
            self.__panning = False
            if self.__modified_actor is not None:
                return
            self.__modified_actor = caller
            #print 'auch %s'%self.__picking_dict[caller]
        def unregister_object(caller=None,event=None):
            self.__modified_actor=None

        def after_intareaction(caller=None, event=None):
            #print "finito"
            if self.__modified_actor is None:
                return
            if len(self.__positions_dict)>0:
                sorted_position=np.array(self.__positions_dict[self.__modified_actor])
                if self.__sort_modified is False and np.linalg.norm(sorted_position-self.__modified_actor.GetPosition())>self.max_space:
                    if self.__sort_message_actor is not None:
                        self.__sort_message_actor.SetInput(self.__sort_message_actor.GetInput()+' (modified)')
                    self.__sort_modified=True
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
                if self.__modified_actor is not None or (self.ren.PickProp(event_pos_x, event_pos_y) is not None):
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
        def follow_bar(caller=None,event=None):
            if self.__color_bar_visibility is True:
                width, height = self.GetSize()
                if width > 60:
                    new_pos = 1 - 60 / width
                    self.__scalar_bar_actor.SetPosition(new_pos, 0.1)
        def follow_arrow(caller=None,event=None):
            if self.__sort_message_visibility is True:
                width, height = self.GetSize()
                if height > 30:
                    new_pos = height-30
                    orig_pos=self.__sort_message_actor.GetPosition()
                    self.__sort_message_actor.SetPosition(orig_pos[0],new_pos)
                    self.__arrow_actor.SetPosition(orig_pos[0],new_pos)
        #register observers

        self.iren.AddObserver(vtk.vtkCommand.EndInteractionEvent, after_intareaction)
        self.iren.AddObserver(vtk.vtkCommand.MouseWheelForwardEvent, wheel_zoom)
        self.iren.AddObserver(vtk.vtkCommand.MouseWheelBackwardEvent, wheel_zoom)
        self.iren.AddObserver(vtk.vtkCommand.MiddleButtonPressEvent, pan)
        self.iren.AddObserver(vtk.vtkCommand.MouseMoveEvent, pan)
        self.iren.AddObserver(vtk.vtkCommand.MiddleButtonReleaseEvent, pan, 100)
        self.AddObserver(vtk.vtkCommand.ModifiedEvent,follow_bar)
        self.AddObserver(vtk.vtkCommand.ModifiedEvent,follow_arrow)
        self.__actor_observer_fun=register_change
        for actor in self.__picking_dict:
            actor.AddObserver(vtk.vtkCommand.PickEvent, self.__actor_observer_fun)
        def print_event(caller=None,event=None):
            print event
        self.balloon_w.AddObserver('AnyEvent',unregister_object)

    def set_background(self,color1,color2=None):
        if color2 is not None:
            self.ren.GradientBackgroundOn()
            self.ren.SetBackground2(color2)
        self.ren.SetBackground(color1)
    def set_data(self,data_dict):
        "data_dict must be a dictionary with ids as keys and polydata as values"
        #hide all actors
        for act in self.__picking_dict:
            act.SetVisibility(0)
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
            if not self.__mapper_dict.has_key(id):
                mapper=vtk.vtkPolyDataMapper()
                self.__mapper_dict[id] = mapper
            mapper=self.__mapper_dict[id]
            mapper.SetInputData(polydata2)
            if not self.__actors_dict.has_key(id):
                actor=vtk.vtkActor()
                self.__actors_dict[id] = actor
                self.ren.AddActor(actor)
                self.__picking_dict[actor] = id
                if self.__actor_observer_fun is not None:
                    actor.AddObserver(vtk.vtkCommand.PickEvent, self.__actor_observer_fun)
            actor=self.__actors_dict[id]
            actor.SetMapper(mapper)
            actor.SetVisibility(1)
            if self.__color_function is not None:
                actor.GetProperty().SetColor(self.__color_function(id))


    def set_balloon_messages(self,messages_dict):
        for key,message in messages_dict.iteritems():
            self.balloon_w.AddBalloon(self.__actors_dict[key],message)
    def sort(self,sorted_ids,title=None):
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
        if self.__color_bar_visibility is True:
            #reserve room for color bar
            if width>60:
                width-=60
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
            self.__positions_dict[actor]=(x,y,0)
            actor.SetVisibility(1)
        self.n_rows=n_row
        self.n_cols=n_col
        self.__sort_modified=False
        pass
    def set_color_function(self,color_function,scalar_colors=False):
        self.__color_function=color_function
        for subj,ac in self.__actors_dict.iteritems():
            ac.GetProperty().SetColor(color_function(subj))
        if scalar_colors is True:
            for mapper in self.__mapper_dict.itervalues():
                mapper.ScalarVisibilityOn()
        else:
            for mapper in self.__mapper_dict.itervalues():
                mapper.ScalarVisibilityOff()
    def set_color_bar_visibility(self,color_bar_visibility):
        self.__color_bar_visibility=color_bar_visibility
        if self.__scalar_bar_actor is not None and color_bar_visibility is False:
            self.__color_bar_visibility.SetVisibility(0)
    def reset_camera(self):
        n_col=self.n_cols
        max_space=self.max_space
        n_row=self.n_rows
        self.Render()
        cam1 = self.ren.GetActiveCamera()
        cam1.ParallelProjectionOn()
        offset=0
        if self.__color_bar_visibility is True:
            offset=60
        cam1.SetFocalPoint(n_col * max_space / 2 - max_space / 2+offset/2, n_row * max_space / 2 - max_space / 2, 0)
        cam1.SetViewUp(0, -1, 0)
        cam1.SetParallelScale(0.54 * n_row * max_space)
        cam_distance = cam1.GetDistance()
        cam1.SetPosition(n_col * max_space / 2 - max_space / 2 + offset/2, n_row * max_space / 2 - max_space / 2,
                         -1 * cam_distance)
        self.ren.ResetCameraClippingRange()

    def start_interaction(self):
        self.iren.Initialize()
        self.Start()
        self.iren.Start()
    def set_orientation(self,orientation):
        for actor in self.__picking_dict:
            actor.SetOrientation(orientation)
    def update_color_bar(self,lut,title):
        if self.__scalar_bar_actor is None:
            self.__scalar_bar_actor=vtk.vtkScalarBarActor()
            self.ren.AddActor(self.__scalar_bar_actor)
        self.__scalar_bar_actor.SetLookupTable(lut)
        self.__scalar_bar_actor.SetTitle(title)
        self.__scalar_bar_actor.SetNumberOfLabels(4)
        self.__scalar_bar_actor.SetMaximumWidthInPixels(60)
        width, height = self.GetSize()
        if width>60:
            new_pos=1-60/width
            self.__scalar_bar_actor.SetPosition(new_pos,0.1)
    def __add_sort_indication(self):
        width, height = self.GetSize()
        arrow=get_arrow((width*0.5,0,0),(0,0,0))
        arrow_mapper=vtk.vtkPolyDataMapper2D()
        arrow_mapper.SetInputData(arrow)
        arrow_actor=vtk.vtkActor2D()
        arrow_actor.SetMapper(arrow_mapper)
        arrow_actor.SetPosition(30,height-30)
        self.ren.AddActor2D(arrow_actor)
        message=vtk.vtkTextActor()
        message.SetTextScaleModeToProp()
        message.SetPosition(30,height-30)
        message.SetWidth(width*0.4)
        message.SetHeight(25)
        self.ren.AddActor2D(message)
        self.__sort_message_actor=message
        self.__arrow_actor=arrow_actor
        self.__sort_message_actor.SetVisibility(0)
        self.__arrow_actor.SetVisibility(0)
    def set_sort_message_visibility(self,visibility):
        self.__sort_message_visibility=visibility
        if self.__sort_message_actor is not None:
            self.__sort_message_actor.SetVisibility(visibility)
        if self.__arrow_actor is not None:
            self.__arrow_actor.SetVisibility(visibility)
    def update_sort_message(self,title):
        if self.__arrow_actor is None:
            self.__add_sort_indication()
        message_text = 'Sorted by: %s' % title
        if self.__sort_modified is True:
            message_text+= ' (modified)'
        self.__sort_message_actor.SetInput(message_text)
        self.set_sort_message_visibility(self.__sort_message_visibility)
        self.Render()
    def __add_mini_scatter_plot(self,title_x=None,title_y=None,color=None):
        mini_scatter=mini_scatter_plot()
        mini_scatter.set_renderer(self.ren)
        self.ren.AddViewProp(mini_scatter)
        width, height = self.GetSize()
        mini_scatter.set_position(0,0,width/3,height/3)
        mini_scatter.set_x_axis(title_x)
        mini_scatter.set_y_axis(title_y)
        mini_scatter.set_color((1.0,1.0,1.0))
        self.__mini_scatter=mini_scatter
    def update_mini_scatter(self,data,x_title=None,y_title=None):
        if self.__mini_scatter is None:
            self.__add_mini_scatter_plot()
        self.__mini_scatter.set_x_axis(x_title)
        self.__mini_scatter.set_y_axis(y_title)
        self.__mini_scatter.set_values(data)
        self.__mini_scatter.SetVisibility(self.__mini_scatter_visible)
    def set_mini_scatter_visible(self,visible):
        self.__mini_scatter_visible=visible
        if self.__mini_scatter is not None:
            self.__mini_scatter.SetVisibility(visible)








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
    iren=vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(test)
    test.set_interactor(iren)
    test.start_interaction()
    ids=range(10)
    random.shuffle(ids)
    test.sort(ids)
    test.reset_camera()
    test.set_sort_message_visibility(True)
    test.update_sort_message('hola')
    data=[(random.random(),random.random()) for i in range(10)]
    test.update_mini_scatter(data)
    test.set_mini_scatter_visible(True)
    test.Render()
    test.start_interaction()