"""A class for displaying multiple solids organized in a grid, and related functions"""

from __future__ import division
import math
from itertools import izip
import gc
import logging

import vtk
import numpy as np

from braviz.visualization import get_arrow, OutlineActor
from braviz.visualization.vtk_charts import mini_scatter_plot


__author__ = 'Diego'


class GridView(vtk.vtkRenderWindow):
    """A class for displaying multiple solids organized in a grid
    All objects inside the grid have a name which is the key for all the dictionaries in the class,
    and the common way to refer to it in most functions"""
    def __init__(self,use_lod=False):
        """Initializes the grid viewer, use_lod is very experimental, attempts to create level of detail actors
        in order to keep interactivity when multiple complex actors are in the scene"""
        self.ren = vtk.vtkRenderer()
        self.ren.SetUseDepthPeeling(1)
        self.SetMultiSamples(0)
        self.AlphaBitPlanesOn()
        self.ren.SetOcclusionRatio(0.1)

        self.AddRenderer(self.ren)
        self.SetSize(600, 400)
        #self.ren.Render()
        self.iren=None
        #self.Initialize()
        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.005)
        self.__use__lod=use_lod
        self.set_background((0.2, 0.2, 0.2), (0.5, 0.5, 0.5))
        # subj->actor
        self.__actors_dict = {}
        # actor -> subj
        self.__picking_dict = {}
        self.__poly_data_dict = {}
        self.__mapper_dict = {}
        self.__messages_dict = {}
        self.__positions_dict = {}
        self.__prop_dict={}
        self.__decimation_dicts={}
        self.__lod_indexed_dict={}
        self.balloon_w = vtk.vtkBalloonWidget()
        self.balloon_repr = vtk.vtkBalloonRepresentation()
        self.balloon_w.SetRepresentation(self.balloon_repr)
        self.balloon_w.SetTimerDuration(1000)

        self.__outline_actor=OutlineActor()
        self.ren.AddActor(self.__outline_actor)
        self.__outline_actor.SetVisibility(0)

        self.max_space = 0
        self.n_rows = 0
        self.n_cols = 0
        self.__modified_actor = None
        self.__selected_actor=None

        self.__panning = False
        self.__panning_start_pos = None
        self.__panning_start_cam_focal = None
        self.__panning_start_cam_pos = None
        self.__color_function = None
        self.__opacity = 1.0
        self.__actor_observer_fun = None
        self.__color_bar_visibility = False
        self.__scalar_bar_actor = None
        self.__arrow_actor = None
        self.__sort_message_actor = None
        self.__sort_message_visibility = False
        self.__sort_modified = False
        self.__mini_scatter = None
        self.__mini_scatter_visible = False
        self.__mini_scatter_dict={}

        self.__orientation = (0, -90, 90)
        self.__captions_dict={}
        self.__labels_dict={}
        #observers
        self.actor_selected_event=vtk.vtkCommand.UserEvent+1

    def set_interactor(self, iren=None):
        """Set the windowInteractor associated to the viewer and registers all the callback functions
        """
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
            """Keeps track of the actor which whom the user is iteracting"""
            #self.__panning = False
            if self.__modified_actor is not None:
                return
            self.__modified_actor = caller
            #self.select_actor(self.__modified_actor)

            #print 'auch %s'%self.__picking_dict[caller]

        def unregister_object(caller=None, event=None):
            """Finishes the interaction"""
            self.__modified_actor = None


        def after_intareaction(caller=None, event=None):
            """If an actor was modified, make the other actors mimic the new position and orientation
            Additionally, if movement is too high, displays a sort(modified) message
            Also updates the position of the corresponding label"""
            #print "finito"
            if self.__modified_actor is None:
                return
            if len(self.__positions_dict) > 0:
                sorted_position = np.array(self.__positions_dict[self.__modified_actor])
                if self.__sort_modified is False and np.linalg.norm(
                        sorted_position - self.__modified_actor.GetPosition()) > self.max_space:
                    if self.__sort_message_actor is not None:
                        self.__sort_message_actor.SetInput(self.__sort_message_actor.GetInput() + ' (modified)')
                    self.__sort_modified = True
            mimic_actor(self.__modified_actor)
            self.__orientation=self.__modified_actor.GetOrientation()
            self.select_actor(self.__modified_actor)
            self.__modified_actor = None
            if len(self.__labels_dict)>0 :
                self.add_labels()

        def mimic_actor(caller=None, event=None):
            """Copies orientation and position from another actor"""
            for ac in self.__picking_dict:
                if ac is not caller:
                    ac.SetOrientation(caller.GetOrientation())
                    ac.SetScale(caller.GetScale())

        def wheel_zoom(caller=None, event=None):
            """Does a zoom operation when rotating the mouse wheel
            TODO: Requieres higher granularity zoom
            """
            factor = 0.5
            cam1 = self.ren.GetActiveCamera()
            if event == 'MouseWheelForwardEvent':
                cam1.SetParallelScale(cam1.GetParallelScale() * factor)
            else:
                cam1.SetParallelScale(cam1.GetParallelScale() / factor)
            if len(self.__labels_dict) > 0:
                self.add_labels()
            self.iren.Render()


        def pan(caller=None, event=None):
            """Pans the camera along the view"""
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
            delta = np.dot(delta, 0.003 * cam1.GetParallelScale())
            cam1.SetPosition(self.__panning_start_cam_pos - delta)
            cam1.SetFocalPoint(self.__panning_start_cam_focal - delta)
            caller.Render()

        def follow_bar(caller=None, event=None):
            """Keeps the color bar in the right position when the window is resized"""
            if self.__color_bar_visibility is True:
                width, height = self.GetSize()
                if width > 60:
                    new_pos = 1 - 60 / width
                    self.__scalar_bar_actor.SetPosition(new_pos, 0.1)

        def follow_arrow(caller=None, event=None):
            """Keeps the arrow in the right position when the window is resized"""
            if self.__sort_message_visibility is True:
                width, height = self.GetSize()
                if height > 30:
                    new_pos = height - 30
                    orig_pos = self.__sort_message_actor.GetPosition()
                    self.__sort_message_actor.SetPosition(orig_pos[0], new_pos)
                    self.__arrow_actor.SetPosition(orig_pos[0], new_pos)

        #register observers

        self.iren.AddObserver(vtk.vtkCommand.EndInteractionEvent, after_intareaction)
        self.iren.AddObserver(vtk.vtkCommand.MouseWheelForwardEvent, wheel_zoom)
        self.iren.AddObserver(vtk.vtkCommand.MouseWheelBackwardEvent, wheel_zoom)
        self.iren.AddObserver(vtk.vtkCommand.MiddleButtonPressEvent, pan)
        self.iren.AddObserver(vtk.vtkCommand.MouseMoveEvent, pan)
        self.iren.AddObserver(vtk.vtkCommand.MiddleButtonReleaseEvent, pan, 100)
        self.AddObserver(vtk.vtkCommand.ModifiedEvent, follow_bar)
        self.AddObserver(vtk.vtkCommand.ModifiedEvent, follow_arrow)
        self.__actor_observer_fun = register_change
        for actor in self.__picking_dict:
            actor.AddObserver(vtk.vtkCommand.PickEvent, self.__actor_observer_fun)

        def print_event(caller=None, event=None):
            """Useful for tests"""
            print event

        #Unregister the modified actor when the event is showing a balloon
        self.balloon_w.AddObserver('AnyEvent', unregister_object)

    def select_name(self,name):
        """Set selected actor by name"""
        actor=self.__actors_dict.get(name)
        self.select_actor(actor,propagate=False)

    def select_actor(self,actor,propagate=True):
        """Set selected actor by explicitly giving the actor object,
        if propagate is True an actor_selected_event is invoked"""
        if actor is None:
            return
        if self.__selected_actor is not None:
            prop = self.__prop_dict[self.__selected_actor]
            prop.SetOpacity(self.__opacity)
            prop.SetLineWidth(1.0)
            if self.__use__lod is True:
                lod_idxs = self.__lod_indexed_dict[self.__selected_actor]
                self.__selected_actor.EnableLOD(lod_idxs[1])
                #self.__selected_actor.EnableLOD(lod_idxs[2])
        key = self.__picking_dict[actor]
        poly_data = self.__poly_data_dict[key]
        self.__outline_actor.SetInputData(poly_data)
        self.__outline_actor.SetVisibility(1)
        self.__outline_actor.SetPosition(actor.GetPosition())
        self.__outline_actor.SetOrientation(actor.GetOrientation())
        self.__outline_actor.SetScale(actor.GetScale())
        self.__selected_actor = actor
        prop=self.__prop_dict[self.__selected_actor]
        prop.SetOpacity(1.0)
        prop.SetLineWidth(2.0)
        if self.__use__lod is True:
            lod_idxs = self.__lod_indexed_dict[self.__selected_actor]
            self.__selected_actor.DisableLOD(lod_idxs[1])
            #self.__selected_actor.DisableLOD(lod_idxs[2])
        if self.__mini_scatter is not None:
            scatter_id = self.__mini_scatter_dict.get(key, None)
            self.__mini_scatter.select_point(scatter_id)
        if propagate is True:
            self.InvokeEvent(self.actor_selected_event)
        self.iren.Render()
    def clear_selection(self):
        """Clear actors selection"""
        self.__outline_actor.SetVisibility(0)
        if self.__selected_actor is not None:
            prop = self.__prop_dict[self.__selected_actor]
            prop.SetOpacity(self.__opacity)
            prop.SetLineWidth(1.0)
            if self.__use__lod is True:
                lod_idxs = self.__lod_indexed_dict[self.__selected_actor]
                self.__selected_actor.EnableLOD(lod_idxs[1])
                #self.__selected_actor.EnableLOD(lod_idxs[2])
        self.__selected_actor = None
        if self.__mini_scatter is not None:
            self.__mini_scatter.select_point(None)
        if self.iren is not None:
            self.iren.Render()
    def get_selection(self):
        """Gets name of currently selected actor"""
        return self.__picking_dict.get(self.__selected_actor,None)
    def set_background(self, color1, color2=None):
        "Set background color"
        if color2 is not None:
            self.ren.GradientBackgroundOn()
            self.ren.SetBackground2(color2)
        self.ren.SetBackground(color1)

    def set_data(self, data_dict):
        """data_dict must be a dictionary with ids as keys and polydata as values"""
        #hide all actors
        self.clear_selection()
        for act in self.__picking_dict:
            act.SetVisibility(0)
        for id, polydata in data_dict.iteritems():
            #center polydata
            if hasattr(polydata,'__iter__'):
                polydata=merge_polydata(polydata)

            center = polydata.GetCenter()
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
                mapper = vtk.vtkPolyDataMapper()
                self.__mapper_dict[id] = mapper
            mapper = self.__mapper_dict[id]
            mapper.SetInputData(polydata2)
            if not self.__actors_dict.has_key(id):
                #actor = vtk.vtkActor()
                if self.__use__lod is True:
                    actor=vtk.vtkLODProp3D()
                else:
                    actor = vtk.vtkActor()

                self.__actors_dict[id] = actor
                self.ren.AddActor(actor)
                actor.SetOrientation(self.__orientation)
                self.__picking_dict[actor] = id
                if self.__actor_observer_fun is not None:
                    actor.AddObserver(vtk.vtkCommand.PickEvent, self.__actor_observer_fun)
            actor = self.__actors_dict[id]
            #actor.SetMapper(mapper)
            prop=vtk.vtkProperty()
            if self.__use__lod is True:
                idx0=actor.AddLOD(mapper,prop,0)
                self.__lod_indexed_dict[actor]=[idx0]
            else:
                actor.SetMapper(mapper)
                actor.SetProperty(prop)
            if self.__use__lod is True:
                tringle_filter,decimation_filter,decimation_mapper=self.__decimation_dicts.setdefault(id,
                                            (vtk.vtkTriangleFilter(),vtk.vtkDecimatePro(),vtk.vtkPolyDataMapper()))
                tringle_filter.SetInputData(polydata2)
                decimation_filter.SetInputConnection(tringle_filter.GetOutputPort())
                decimation_filter.SetTargetReduction(0.95)
                decimation_mapper.SetInputConnection(decimation_filter.GetOutputPort())
                dummy_pd=vtk.vtkPolyData()
                dummy_mapper=vtk.vtkPolyDataMapper()
                dummy_mapper.SetInputData(dummy_pd)
                idx0 = actor.AddLOD(decimation_mapper,prop,0)
                self.__lod_indexed_dict[actor].append(idx0)
                idx0 = actor.AddLOD(dummy_mapper, 0)
                self.__lod_indexed_dict[actor].append(idx0)
            self.__prop_dict[actor]=prop
            #actor.GetProperty = lambda: self.__prop_dict[actor]
            actor.SetVisibility(1)
            if self.__color_function is not None:
                prop.SetColor(self.__color_function(id))
                prop.SetOpacity(self.__opacity)

    def clear_all(self):
        """Clear all internal data structures in order to recover memory, call only from main thread"""
        for act in self.__picking_dict:
            self.ren.RemoveViewProp(act)
            self.balloon_w.RemoveBalloon(act)
        self.__actors_dict={}
        self.__picking_dict={}
        self.__mapper_dict = {}
        self.__poly_data_dict={}
        self.__messages_dict = {}
        self.__positions_dict = {}
        self.__prop_dict={}
        self.__decimation_dicts={}
        self.__lod_indexed_dict={}
        self.__captions_dict={}
        self.__labels_dict={}
        self.__selected_actor=None

        self.iren.Render()
        gc.collect()
    def set_balloon_messages(self, messages_dict):
        """messages_dict must be a dictionary containing names and messages"""
        #for key, message in messages_dict.iteritems():
        #    self.balloon_w.AddBalloon(self.__actors_dict[key], message)
        for key,actor in self.__actors_dict.iteritems():
            self.balloon_w.AddBalloon(actor,messages_dict.get(key,key))


    def sort(self, sorted_ids, title=None,overlay=False):
        """actors will be displayed in the grid according to the sorted_ids list,
        actors not in list will become invisible, if overlay is true then sorted ids should containg group of ids"""

        if len(self.__picking_dict) == 0:
            return

        for ac in self.__picking_dict:
            ac.SetVisibility(0)

        def get_max_diagonal(actor):
            Xmin, Xmax, Ymin, Ymax, Zmin, Zmax = actor.GetBounds()
            return math.sqrt((Xmax - Xmin) ** 2 + (Ymax - Ymin) ** 2 + (Zmax - Zmin) ** 2)


        self.max_space = max([get_max_diagonal(actor) for actor in self.__picking_dict])
        self.max_space *= 0.90
        #calculate renWin proportions
        width, height = self.GetSize()
        if self.__color_bar_visibility is True:
            #reserve room for color bar
            if width > 60:
                width -= 60
        row_proportion = width / height

        len1=len(sorted_ids)
        n_row = math.floor(math.sqrt(len1 / row_proportion))
        if n_row<=0:
            n_row=1
        n_col = math.ceil(len1 / n_row)

        #positions_dict={}
        for i, subj_group in enumerate(sorted_ids):
            if overlay is False:
                subj_group=(subj_group,)
            #column ,row= i % n_col , i // n_col
            row ,column= i % n_row , i // n_row
            x , y = column * self.max_space , row * self.max_space
            for subj_id in subj_group:
                actor = self.__actors_dict[subj_id]
                actor.SetPosition(x, y, 0)
                self.__positions_dict[actor] = (x, y, 0)
                actor.SetVisibility(1)
        self.n_rows = n_row
        self.n_cols = n_col
        self.__sort_modified = False
        pass

    def set_color_function(self, color_function, opacity=1.0, scalar_colors=False):
        """Sets the function that will be called for determining the color of each actor
        The function by default must take as arguments a name and a scalar value,
        if scalar_colors is True, the first argument is ommited
        the opacity value will be applied to all actors"""
        self.__color_function = color_function
        for subj, ac in self.__actors_dict.iteritems():
            prop=self.__prop_dict[ac]
            prop.SetColor(color_function(subj))
            prop.SetOpacity(opacity)
        if scalar_colors is True:
            for mapper in self.__mapper_dict.itervalues():
                mapper.ScalarVisibilityOn()
        else:
            for mapper in self.__mapper_dict.itervalues():
                mapper.ScalarVisibilityOff()
        self.__opacity=opacity

    def set_color_bar_visibility(self, color_bar_visibility):
        """Displays or hides the color bar"""
        self.__color_bar_visibility = color_bar_visibility
        if self.__scalar_bar_actor is not None and color_bar_visibility is False:
            self.__color_bar_visibility.SetVisibility(0)

    def reset_camera(self):
        """Resets camera to a standard position"""
        n_col = self.n_cols
        max_space = self.max_space
        n_row = self.n_rows
        self.Render()
        cam1 = self.ren.GetActiveCamera()
        cam1.ParallelProjectionOn()
        offset = 0
        if self.__color_bar_visibility is True:
            offset = 60
        cam1.SetFocalPoint(n_col * max_space / 2 - max_space / 2 + offset / 2, n_row * max_space / 2 - max_space / 2, 0)
        cam1.SetViewUp(0, -1, 0)
        cam1.SetParallelScale(0.54 * n_row * max_space)
        cam_distance = cam1.GetDistance()
        cam1.SetPosition(n_col * max_space / 2 - max_space / 2 + offset / 2, n_row * max_space / 2 - max_space / 2,
                         -1 * cam_distance)
        self.ren.ResetCameraClippingRange()

    def start_interaction(self):
        """Initialize interactor"""
        self.iren.Initialize()
        self.Start()
        self.iren.Start()

    def set_orientation(self, orientation):
        """Sets the orientation of actors"""
        self.__orientation=orientation
        for actor in self.__picking_dict:
            actor.SetOrientation(orientation)
    def get_orientation(self):
        """Gets the current orientation of actors"""
        for actor in self.__picking_dict:
            return actor.GetOrientation()

    def update_color_bar(self, lut, title):
        """Updates the color bar, given a lookuptable and a title"""
        if self.__scalar_bar_actor is None:
            self.__scalar_bar_actor = vtk.vtkScalarBarActor()
            self.ren.AddActor(self.__scalar_bar_actor)
        self.__scalar_bar_actor.SetLookupTable(lut)
        self.__scalar_bar_actor.SetTitle(title)
        self.__scalar_bar_actor.SetNumberOfLabels(4)
        self.__scalar_bar_actor.SetMaximumWidthInPixels(60)
        width, height = self.GetSize()
        if width > 60:
            new_pos = 1 - 60 / width
            self.__scalar_bar_actor.SetPosition(new_pos, 0.1)

    def __add_sort_indication(self):
        """Adds the message and arrow indicating the sort operation"""
        width, height = self.GetSize()
        arrow = get_arrow((width * 0.5, 0, 0), (0, 0, 0))
        arrow_mapper = vtk.vtkPolyDataMapper2D()
        arrow_mapper.SetInputData(arrow)
        arrow_actor = vtk.vtkActor2D()
        arrow_actor.SetMapper(arrow_mapper)
        arrow_actor.SetPosition(30, height - 30)
        self.ren.AddActor2D(arrow_actor)
        message = vtk.vtkTextActor()
        message.SetTextScaleModeToProp()
        message.SetPosition(30, height - 30)
        message.SetWidth(width * 0.4)
        message.SetHeight(25)
        self.ren.AddActor2D(message)
        self.__sort_message_actor = message
        self.__arrow_actor = arrow_actor
        self.__sort_message_actor.SetVisibility(0)
        self.__arrow_actor.SetVisibility(0)

    def set_sort_message_visibility(self, visibility):
        """Hides or displays the sort message"""
        self.__sort_message_visibility = visibility
        if self.__sort_message_actor is not None:
            self.__sort_message_actor.SetVisibility(visibility)
        if self.__arrow_actor is not None:
            self.__arrow_actor.SetVisibility(visibility)

    def update_sort_message(self, title):
        """Sets the title of the sort message"""
        if self.__arrow_actor is None:
            self.__add_sort_indication()
        message_text = 'Sorted by: %s' % title
        if self.__sort_modified is True:
            message_text += ' (modified)'
        self.__sort_message_actor.SetInput(message_text)
        self.set_sort_message_visibility(self.__sort_message_visibility)
        self.select_actor(self.__selected_actor)
        self.Render()

    def __add_mini_scatter_plot(self, title_x=None, title_y=None, color=None):
        """Adds a mini mini_scatter_plot in the corner, connected to the actors
        The values displayed in the scatter plot are set by update_mini_scatter"""
        mini_scatter = mini_scatter_plot()
        mini_scatter.set_renderer(self.ren)
        self.ren.AddViewProp(mini_scatter)
        width, height = self.GetSize()
        mini_scatter.set_position(0, 0, width / 3, height / 3)
        mini_scatter.set_x_axis(title_x)
        mini_scatter.set_y_axis(title_y)
        mini_scatter.set_color((1.0, 1.0, 1.0))
        self.__mini_scatter = mini_scatter

    def update_mini_scatter(self, data_dict, x_title=None, y_title=None):
        """Updates the data displayed in the scatter plot
        data dict must contain the names of the objects as keys, and tuples as values"""
        if self.__mini_scatter is None:
            self.__add_mini_scatter_plot()
        self.__mini_scatter.set_x_axis(x_title)
        self.__mini_scatter.set_y_axis(y_title)
        data_list=[]
        self.__mini_scatter_dict.clear()
        reverse_scatter_dict={}
        for i,(key,val) in enumerate(data_dict.iteritems()):
            self.__mini_scatter_dict[key]=i
            reverse_scatter_dict[i]=key
            data_list.append(val)
        #print data_list
        self.__mini_scatter.set_values(data_list)
        self.__mini_scatter.SetVisibility(self.__mini_scatter_visible)

        def scatter_pick_observer(caller=None, event=None):
            position = caller.GetEventPosition()
            x_axis = self.__mini_scatter.x_axis
            ax_position1 = x_axis.GetPoint1()[0]
            ax_position2 = x_axis.GetPoint2()[0]
            y_axis = self.__mini_scatter.y_axis
            ay_position1 = y_axis.GetPoint1()[1]
            ay_position2 = y_axis.GetPoint2()[1]
            if (ax_position1 <= position[0] <= ax_position2) and (ay_position1 <= position[1] <= ay_position2):
                tx = (position[0] - ax_position1) / (ax_position2 - ax_position1)
                ty = (position[1] - ay_position1) / (ay_position2 - ay_position1)
                cx=x_axis.GetMinimum()+tx*(x_axis.GetMaximum()-x_axis.GetMinimum())
                cy=y_axis.GetMinimum()+ty*(y_axis.GetMaximum()-y_axis.GetMinimum())
                point_id=self.__mini_scatter.find_point((cx,cy))
                closest_point=self.__mini_scatter.get_point_by_id(point_id)
                if np.linalg.norm(np.array(closest_point[:2])-(cx,cy))<=0.1*np.sqrt((x_axis.GetMaximum()-x_axis.GetMinimum())*(y_axis.GetMaximum()-y_axis.GetMinimum())):
                    self.__mini_scatter.select_point(point_id)
                #print closest_point
                key=reverse_scatter_dict[point_id]
                self.select_actor(self.__actors_dict[key])
                self.iren.Render()


        self.iren.AddObserver('LeftButtonPressEvent', scatter_pick_observer, 10)

    def set_mini_scatter_visible(self, visible):
        """Hides or displays mini_scatter_plot"""
        self.__mini_scatter_visible = visible
        if self.__mini_scatter is not None:
            self.__mini_scatter.SetVisibility(visible)
        self.iren.Render()
    def add_labels(self,labels_dict=None):
        """Adds labels to objects in the grid"""
        if labels_dict is not None:
            self.remove_labels()
            self.__labels_dict=labels_dict
        else:
            #only remove actors
            self.remove_labels(True)
            labels_dict=self.__labels_dict



        for key,value in labels_dict.iteritems():
            try:
                center_point=self.__actors_dict[key].GetPosition()
            except:
                log = logging.getLogger(__name__)
                log.error("%s actor not found"%key)
                continue
            caption=vtk.vtkTextActor()
            self.__captions_dict[key]=caption
            caption=self.__captions_dict[key]
            caption.SetInput(value)
            point1 = np.array(center_point)-(self.max_space/2.2,-1*self.max_space*(0.5+1/2.2) ,0)
            point2 = np.array(center_point) + (self.max_space / 2.2,-1* self.max_space*(-0.5+1/2.2), 0)
            #caption.SetAttachmentPoint(center_point)
            coordinate=vtk.vtkCoordinate()
            coordinate.SetCoordinateSystemToWorld()
            coordinate.SetValue(point1)
            pos=coordinate.GetComputedDisplayValue(self.ren)
            caption.GetPositionCoordinate().SetReferenceCoordinate(None)
            caption.GetPositionCoordinate().SetCoordinateSystemToWorld ()
            caption.GetPositionCoordinate().SetValue(point1)
            coordinate.SetCoordinateSystemToWorld()
            coordinate.SetValue(point2)
            pos2 = coordinate.GetComputedDisplayValue(self.ren)
            caption.GetPosition2Coordinate().SetReferenceCoordinate(None)
            caption.GetPosition2Coordinate().SetCoordinateSystemToWorld ()
            caption.GetPosition2Coordinate().SetValue(point2)
            caption.GetTextProperty().SetVerticalJustificationToCentered ()
            caption.GetTextProperty().SetJustificationToCentered ()
            caption.GetTextProperty().ShadowOn()
            caption.SetTextScaleModeToProp()
            self.ren.AddViewProp(caption)
        self.iren.Render()

    def remove_labels(self,partial=False):
        """Removes the labels associated to each object
        if partial is True, only the actors are removed """
        for caption in self.__captions_dict.itervalues():
            self.ren.RemoveViewProp(caption)
        self.__captions_dict.clear()
        if partial is False:
            self.__labels_dict={}
            self.iren.Render()


def merge_polydata(models):
    """Combines various polydata objects into one polydata"""
    if len(models)==1:
        return models[0]
    append_filter=vtk.vtkAppendPolyData()
    for mod in models:
        append_filter.AddInputData(mod)
    append_filter.Update()
    merged=append_filter.GetOutput()
    return merged

if __name__ == '__main__':
    test = GridView()
    test_data = {}
    for i in range(10):
        sp = vtk.vtkSphereSource()
        sp.SetRadius(1)
        sp.Update()
        test_data[i] = sp.GetOutput()
    test.set_data(test_data)
    test.sort(range(2, 10))
    test.reset_camera()
    import random

    def rand_color(id):
        return [random.random() for i in range(3)]

    messages = {}
    for i in range(10):
        if i % 2 == 0:
            messages[i] = "%d : even" % i
        else:
            messages[i] = "%d : odd" % i
    test.set_balloon_messages(messages)
    test.set_color_function(rand_color)
    test.Render()
    test_iren = vtk.vtkRenderWindowInteractor()
    test_iren.SetRenderWindow(test)
    test.set_interactor(test_iren)
    test.start_interaction()
    ids = range(10)
    random.shuffle(ids)
    test.sort(ids)
    test.reset_camera()
    test.set_sort_message_visibility(True)
    test.update_sort_message('hola')
    data = [(random.random(), random.random()) for i in range(10)]
    data_dict=dict(izip(range(10),data))
    test.update_mini_scatter(data_dict)
    test.set_mini_scatter_visible(True)
    labels_dict=dict(izip(range(10),['probando']*10))
    test.start_interaction()
    test.add_labels(labels_dict)
    test.Render()
    test.start_interaction()