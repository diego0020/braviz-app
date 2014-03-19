from __future__ import division

__author__ = 'Diego'

import vtk
import braviz
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt4.QtGui import QFrame, QHBoxLayout
from PyQt4.QtCore import pyqtSignal


class SubjectViewer:
    def __init__(self, render_window_interactor, reader, widget):

        render_window_interactor.Initialize()
        render_window_interactor.Start()
        self.iren = render_window_interactor
        self.ren_win = render_window_interactor.GetRenderWindow()
        self.ren = vtk.vtkRenderer()
        #self.ren.SetBackground((0.75,0.75,0.75))
        self.ren.GradientBackgroundOn()
        self.ren.SetBackground2((0.5, 0.5, 0.5))
        self.ren.SetBackground((0.2, 0.2, 0.2))
        self.ren.SetUseDepthPeeling(1)
        self.ren_win.SetMultiSamples(0)
        self.ren_win.AlphaBitPlanesOn()
        self.ren.SetOcclusionRatio(0.1)
        self.ren_win.AddRenderer(self.ren)
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.axes = braviz.visualization.OrientationAxes()
        self.axes.initialize(self.iren)

        self.reader = reader

        #state
        self.__current_subject = None
        self.__current_space = "world"
        self.__current_image = None
        self.__current_image_orientation = 0
        self.__curent_fmri_paradigm = None
        self.__current_mri_window_level = None
        self.__current_fa_window_level = None

        #internal data
        self.__image_plane_widget = None
        self.__mri_lut = None
        self.__fmri_blender = braviz.visualization.fMRI_blender()
        self.__model_manager = ModelManager(self.reader,self.ren)

        #reset camera and render
        self.reset_camera(0)
        self.ren.Render()

        #widget, signal handling
        self.__widget = widget

    def show_cone(self):
        """Useful for testing"""
        cone = vtk.vtkConeSource()
        cone.SetResolution(8)
        cone_mapper = vtk.vtkPolyDataMapper()
        cone_mapper.SetInputConnection(cone.GetOutputPort())
        cone_actor = vtk.vtkActor()
        cone_actor.SetMapper(cone_mapper)
        self.ren.AddActor(cone_actor)
        self.ren_win.Render()

    def change_subject(self, new_subject_img_code):
        if len(new_subject_img_code)<3:
            new_subject_img_code="0"+new_subject_img_code
        self.__current_subject = new_subject_img_code

        #update image
        self.change_image_modality(self.__current_image, self.__curent_fmri_paradigm, force_reload=True)

        #update models
        self.__model_manager.reload_models(subj=new_subject_img_code)

        self.ren_win.Render()


    def hide_image(self):
        if self.__image_plane_widget is not None:
            self.__image_plane_widget.Off()
            #self.image_plane_widget.SetVisibility(0)

    def show_image(self):
        if self.__image_plane_widget is not None:
            self.__image_plane_widget.On()
        self.change_image_modality(self.__current_image,self.__curent_fmri_paradigm,True)

    def create_image_plane_widget(self):
        if self.__image_plane_widget is not None:
            #already created
            return
        self.__image_plane_widget = braviz.visualization.persistentImagePlane(self.__current_image_orientation)
        self.__image_plane_widget.SetInteractor(self.iren)
        self.__image_plane_widget.On()
        self.__mri_lut = vtk.vtkLookupTable()
        self.__mri_lut.DeepCopy(self.__image_plane_widget.GetLookupTable())

        def slice_change_handler(source, event):
            new_slice = self.__image_plane_widget.GetSliceIndex()
            self.__widget.slice_change_handle(new_slice)

        def detect_window_level_event(source, event):
            window, level = self.__image_plane_widget.GetWindow(), self.__image_plane_widget.GetLevel()
            self.__widget.window_level_change_handle(window, level)

        self.__image_plane_widget.AddObserver(self.__image_plane_widget.slice_change_event, slice_change_handler)
        self.__image_plane_widget.AddObserver("WindowLevelEvent", detect_window_level_event)

    def change_image_modality(self, modality, paradigm=None, force_reload=False):
        """Changes the modality of the current image
        to hide the image call hide_image
        in the case of fMRI modality should be fMRI and paradigm the name of the paradigm"""
        if modality is not None:
            modality = modality.upper()
        if (self.__current_image is not None) and (modality == self.__current_image) and (paradigm == self.__curent_fmri_paradigm) and \
            self.__image_plane_widget.GetEnabled() and not force_reload:
            #nothing to do
            return

        self.__current_image = modality

        if modality is None:
            self.hide_image()
            self.ren_win.Render()
            return

        if self.__image_plane_widget is None:
            self.create_image_plane_widget()
        self.__image_plane_widget.On()

        if (self.__image_plane_widget is not None) and self.__image_plane_widget.GetEnabled():
            if (self.__current_image == "MRI") and (self.__current_mri_window_level is not None):
                self.__image_plane_widget.GetWindowLevel(self.__current_mri_window_level)
            elif (self.__current_image == "FA") and (self.__current_fa_window_level is not None):
                self.__image_plane_widget.GetWindowLevel(self.__current_fa_window_level)

        if self.__current_subject is None:
            return





        #update image labels:
        try:
            aparc_img = self.reader.get("APARC", self.__current_subject, format="VTK", space=self.__current_space)
            aparc_lut = self.reader.get("APARC", self.__current_subject, lut=True)
            self.__image_plane_widget.addLabels(aparc_img)
            self.__image_plane_widget.setLabelsLut(aparc_lut)
        except Exception:
            self.hide_image()
            raise

        if modality == "FMRI":
            mri_image = self.reader.get("MRI", self.__current_subject, format="VTK", space=self.__current_space)
            fmri_image = self.reader.get("fMRI", self.__current_subject, format="VTK", space=self.__current_space,
                                         name=paradigm)
            if fmri_image is None:
                self.hide_image()
                raise Exception("%s not available for subject %s" % (paradigm, self.__current_subject))
            fmri_lut = self.reader.get("fMRI", self.__current_subject, lut=True)
            self.__fmri_blender.set_luts(self.__mri_lut, fmri_lut)
            new_image = self.__fmri_blender.set_images(mri_image, fmri_image)
            self.__image_plane_widget.SetInputData(new_image)
            self.__image_plane_widget.GetColorMap().SetLookupTable(None)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            self.ren_win.Render()
            self.__current_image = modality
            self.__curent_fmri_paradigm = paradigm
            self.__image_plane_widget.text1_value_from_img(fmri_image)
            self.ren_win.Render()
            return

        self.__image_plane_widget.text1_to_std()
        #Other images
        new_image = self.reader.get(modality, self.__current_subject, space=self.__current_space, format="VTK")

        self.__image_plane_widget.SetInputData(new_image)

        if modality == "MRI":
            lut = self.__mri_lut
            self.__image_plane_widget.SetLookupTable(lut)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            if self.__current_mri_window_level is None:
                self.__current_mri_window_level = [0, 0]
                self.reset_window_level()
            self.__image_plane_widget.SetWindowLevel(*self.__current_mri_window_level)
        elif modality == "FA":
            lut = self.reader.get("FA", self.__current_subject, lut=True)
            self.__image_plane_widget.SetLookupTable(lut)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            if self.__current_fa_window_level is None:
                self.__current_fa_window_level = [0, 0]
                self.reset_window_level()
            self.__image_plane_widget.SetWindowLevel(*self.__current_fa_window_level)
        elif modality == "APARC":
            lut = self.reader.get("APARC", self.__current_subject, lut=True)
            self.__image_plane_widget.SetLookupTable(lut)
            #Important:
            self.__image_plane_widget.SetResliceInterpolateToNearestNeighbour()
        #self.__current_image = modality
        self.ren_win.Render()

    def change_image_orientation(self, orientation):
        """Changes the orientation of the current image
        to hide the image call hide_image
        orientation is a number from 0, 1 or 2 """
        if self.__image_plane_widget is None:
            self.create_image_plane_widget()
        self.__image_plane_widget.set_orientation(orientation)
        self.__current_image_orientation = orientation
        self.ren_win.Render()

    def get_number_of_image_slices(self):
        if self.__image_plane_widget is None:
            return 0
        dimensions = self.__image_plane_widget.GetInput().GetDimensions()

        return dimensions[self.__current_image_orientation]

    def get_current_image_slice(self):
        if self.__image_plane_widget is None:
            return 0
        return self.__image_plane_widget.GetSliceIndex()

    def set_image_slice(self, new_slice):
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetSliceIndex(new_slice)
        self.ren_win.Render()

    def get_current_image_window(self):
        return self.__image_plane_widget.GetWindow()

    def get_current_image_level(self):
        return self.__image_plane_widget.GetLevel()

    def set_image_window(self, new_window):
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetWindowLevel(new_window, self.get_current_image_level())
        self.ren_win.Render()

    def set_image_level(self, new_level):
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetWindowLevel(self.get_current_image_window(), new_level)
        self.ren_win.Render()

    def reset_window_level(self):
        if self.__image_plane_widget is None:
            return
        if self.__current_image == "MRI":
            self.__image_plane_widget.SetWindowLevel(3000, 1500)
            self.__image_plane_widget.GetWindowLevel(self.__current_mri_window_level)
            self.__image_plane_widget.InvokeEvent("WindowLevelEvent")
        elif self.__current_image == "FA":
            self.__image_plane_widget.SetWindowLevel(1.20, 0.6)
            self.__image_plane_widget.GetWindowLevel(self.__current_fa_window_level)
            self.__image_plane_widget.InvokeEvent("WindowLevelEvent")
        self.ren_win.Render()
        return

    def change_current_space(self, new_space):
        if self.__current_space == new_space:
            return
        self.__current_space = new_space
        if self.__image_plane_widget is not None and self.__image_plane_widget.GetEnabled():
            self.change_image_modality(self.__current_image, self.__curent_fmri_paradigm, force_reload=True)
        self.__model_manager.reload_models(space=new_space)
        self.ren_win.Render()

    __camera_positions_dict = {
        0: ((-3.5, 0, 13), (157, 154, 130), (0, 0, 1)),
        2: ((-3.5, 0, 10), (250, 0, 10), (0, 0, 1)),
        1: ((-3.5, 0, 10), (-250, 0, 10), (0, 0, 1)),
        4: ((-3.5, 0, 10), (-3.5, -200, 10), (0, 0, 1)),
        3: ((-3.5, 0, 10), (-3.5, 200, 10), (0, 0, 1)),
        5: ((-3, 0, 3), (-3, 0, 252), (0, 1, 0)),
        6: ((-3, 0, 3), (-3, 0, -252), (0, 1, 0)),
    }

    def reset_camera(self, position):
        """resets the current camera to standard locations. Position may be:
        0: initial 3d view
        1: left
        2: right
        3: front
        4: back
        5: top
        6: bottom"""

        focal, position, viewup = self.__camera_positions_dict[position]

        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal)
        cam1.SetPosition(position)
        cam1.SetViewUp(viewup)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()

    def print_camera(self):
        cam1 = self.ren.GetActiveCamera()
        print "Camera coordinates:"
        print "focal: ",
        print cam1.GetFocalPoint()
        print "position: ",
        print cam1.GetPosition()
        print "viewUp: ",
        print cam1.GetViewUp()

    def set_structures(self,new_structures):
        self.__model_manager.set_models(new_structures)
        self.ren_win.Render()


class QSuvjectViwerWidget(QFrame):
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)

    def __init__(self, reader):
        QFrame.__init__(self)
        self.__qwindow_interactor = QVTKRenderWindowInteractor()
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        self.__reader = reader
        self.__subject_viewer = SubjectViewer(self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)
        self.subject_viewer.ren_win.Render()

    @property
    def subject_viewer(self):
        return self.__subject_viewer

    def slice_change_handle(self, new_slice):
        self.slice_changed.emit(new_slice)
        #print new_slice

    def window_level_change_handle(self, window, level):
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)

class ModelManager:
    def __init__(self,reader,ren,initial_subj="093",initial_space="World"):
        self.ren = ren
        self.__active_models_set=set()
        self.__pd_map_act=dict()
        self.__available_models=set()
        self.__current_subject=initial_subj
        self.__reader = reader
        self.__current_space = initial_space
        self.__actor_to_model={} # for picking

        self.reload_models(subj=initial_subj,space=initial_space)

    def reload_models(self,subj=None,space=None):
        if subj is not None:
            self.__current_subject = subj
            self.__available_models = self.__reader.get("MODEL",subj,index=True)
        if space is not None:
            self.__current_space = space

        if (space is not None) or (subj is not None):
            self.__refresh_models()

    def __refresh_models(self):
        for mod_name in self.__active_models_set:
            self.__addModel(mod_name)

    def __addModel(self,model_name):
        #if already exists make visible
        trio = self.__pd_map_act.get(model_name)
        if trio is not None:
            model,mapper,actor=trio
            if model_name in self.__available_models:
                model=self.__reader.get('MODEL',self.__current_subject,name=model_name,space=self.__current_space)
                mapper.SetInputData(model)
                actor.SetVisibility(1)
                self.__pd_map_act[model_name]=(model,mapper,actor)
            else:
                actor.SetVisibility(0)  # Hide
        else:
            #New model
            if model_name in self.__available_models:
                model=self.__reader.get('MODEL',self.__current_subject,name=model_name,space=self.__current_space)
                model_color=self.__reader.get('MODEL',None,name=model_name,color='T')
                model_mapper=vtk.vtkPolyDataMapper()
                model_actor=vtk.vtkActor()
                model_properties=model_actor.GetProperty()
                model_properties.SetColor(list(model_color[0:3]))
                model_mapper.SetInputData(model)
                model_actor.SetMapper(model_mapper)
                self.ren.AddActor(model_actor)
                self.__pd_map_act[model_name]=(model,model_mapper,model_actor)
                self.__actor_to_model[id(model_actor)]=model_name

        #actor=self.__pd_map_act[model_name][2]
        #model_volume=self.__reader.get('model',self.currSubj,name=model_name,volume=1)
        #add_solid_balloon(balloon_widget, actor, model_name,model_volume)

    def __removeModel(self,model_name):
        """Deletes internal data structures
        """
        #check that it actually exists
        trio = self.__pd_map_act.get(model_name)
        if trio is None:
            return
        model, mapper, actor=trio
        self.ren.RemoveActor(actor)
        del self.__pd_map_act[model_name]
        del self.__actor_to_model[id(actor)]
        #balloon_widget.RemoveBalloon(actor)
        del actor
        del mapper
        del model

    def __hide_model(self,model_name):
        trio = self.__pd_map_act.get(model_name)
        if trio is None:
            return
        actor = trio[2]
        actor.SetVisibility(0)

    def set_models(self,new_model_set):
        new_set=set(new_model_set)
        current_models=self.__active_models_set

        to_add = new_set - current_models
        to_hide = current_models - new_set

        for mod_name in to_add:
            self.__addModel(mod_name)
        for mod_name in to_hide:
            self.__hide_model(mod_name)

        self.__active_models_set=new_set



