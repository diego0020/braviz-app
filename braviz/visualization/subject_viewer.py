from __future__ import division

import vtk
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt4 import QtCore
from PyQt4.QtGui import QFrame, QHBoxLayout, QApplication
from PyQt4.QtCore import pyqtSignal

from braviz.interaction.structure_metrics import solve_laterality
import braviz.readAndFilter.tabular_data
import seaborn as sbs
from itertools import izip
from braviz.interaction import structure_metrics
from functools import wraps
import numpy as np
import logging

__author__ = 'Diego'

# TODO: Abstract viewer classes

def do_and_render(f):
    """requiers the class to have the rendered accesible as self.ren"""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if "skip_render" in kwargs:
            skip = kwargs.pop("skip_render")
        else:
            skip = False
        try:
            f(*args, **kwargs)
        except Exception:
            raise
        finally:
            if not skip:
                self = args[0]
                rw = self.ren.GetRenderWindow()
                rw.Render()

    return wrapped


class SubjectViewer(object):
    def __init__(self, render_window_interactor, reader, widget):

        # render_window_interactor.Initialize()
        # render_window_interactor.Start()
        self.iren = render_window_interactor
        self.ren_win = render_window_interactor.GetRenderWindow()
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground((0.75, 0.75, 0.75))
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

        self.light = vtk.vtkLight()
        self.ren.AddLight(self.light)
        self.light.SetLightTypeToHeadlight()

        self.reader = reader

        # state
        self.__current_subject = None
        self.__current_space = "world"

        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.0005)
        self.iren.SetPicker(self.picker)

        # internal data
        self.__model_manager = ModelManager(self.reader, self.ren)
        self.__tractography_manager = TractographyManager(self.reader, self.ren)
        self.__image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                            picker=self.picker)
        self.__surface_manager = SurfaceManager(self.reader, self.ren, self.iren, picker=self.picker)

        self.__contours_manager = FmriContours(self.ren)
        fmri_lut = self.reader.get("fmri",None,lut=True)
        self.__contours_manager.set_lut(fmri_lut)
        self.__contours_paradigm = None
        self.__contours_contrast = None
        self.set_contours_visibility(False)
        self.__contours_img = None
        #reset camera and render
        #self.reset_camera(0)
        #        self.ren.Render()

        #widget, signal handling
        self.__widget = widget

    @property
    def models(self):
        return self.__model_manager

    @property
    def tractography(self):
        return self.__tractography_manager

    @property
    def image(self):
        return self.__image_manager

    @property
    def surface(self):
        return self.__surface_manager

    @property
    def contours(self):
        return self.__contours_manager

    def show_cone(self):
        """Useful for testing"""
        log = logging.getLogger(__name__)
        log.warning("Showing cone... this should only happen during testing")
        cone = vtk.vtkConeSource()
        cone.SetResolution(8)
        cone_mapper = vtk.vtkPolyDataMapper()
        cone_mapper.SetInputConnection(cone.GetOutputPort())
        cone_actor = vtk.vtkActor()
        cone_actor.SetMapper(cone_mapper)
        self.ren.AddActor(cone_actor)
        self.ren_win.Render()

    def change_subject(self, new_subject_img_code):
        self.__current_subject = new_subject_img_code
        errors = []
        log = logging.getLogger(__name__)
        # update image
        try:
            self.image.change_subject(new_subject_img_code, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Image")

        # update models
        try:
            self.models.reload_models(subj=new_subject_img_code, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Models")

        # update fibers
        try:
            self.tractography.set_subject(new_subject_img_code, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Fibers")

        # update surfaces
        try:
            self.surface.set_subject(new_subject_img_code, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Surfaces")

        #update fmri
        try:
            self.set_fmri_contours_image(skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Contours")

        self.ren_win.Render()
        if len(errors) > 0:
            log.error("Couldn't load " + ", ".join(errors))
            raise Exception("Couldn't load " + ", ".join(errors))

    @do_and_render
    def change_current_space(self, new_space):
        if self.__current_space == new_space:
            return
        self.__current_space = new_space
        log = logging.getLogger(__name__)
        try:
            self.image.change_space(new_space, skip_render=True)
        except Exception as e:
            log.error(e)
        try:
            self.models.reload_models(space=new_space, skip_render=True)
        except Exception as e:
            log.error(e)
        try:
            self.tractography.set_current_space(new_space, skip_render=True)
        except Exception as e:
            log.error(e)
        try:
            self.surface.set_space(new_space, skip_render=True)
        except Exception as e:
            log.error(e)

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

    def set_camera(self, focal_point, position, view_up):
        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal_point)
        cam1.SetPosition(position)
        cam1.SetViewUp(view_up)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()


    def print_camera(self):
        cam1 = self.ren.GetActiveCamera()
        log = logging.getLogger(__name__)
        log.info("Camera coordinates:")
        log.info("focal: ")
        log.info(cam1.GetFocalPoint())
        log.info("position: ")
        log.info(cam1.GetPosition())
        log.info("viewUp: ")
        log.info(cam1.GetViewUp())

    def get_camera_parameters(self):
        cam1 = self.ren.GetActiveCamera()
        fp = cam1.GetFocalPoint()
        pos = cam1.GetPosition()
        vu = cam1.GetViewUp()
        return fp, pos, vu

    @do_and_render
    def set_fmri_contours_image(self,paradigm=None,contrast=None):
        if paradigm is None:
            paradigm = self.__contours_paradigm
        else:
            self.__contours_paradigm = paradigm
        if contrast is None:
            contrast = self.__contours_contrast
        else:
            self.__contours_contrast = contrast

        log = logging.getLogger(__name__)

        if paradigm is None:
            self.__contours_img = None
        else:
            try:
                fmri_img = self.reader.get("fmri",self.__current_subject,space=self.__current_space,
                                   name=paradigm,contrast=contrast,format="vtk")
            except Exception as e:
                self.__contours_img = None
                log.exception(e)
            else:
                self.__contours_img = fmri_img

        if self.__contours_img is None:
            self.contours.actor.SetVisibility(0)
        else:

            self.contours.set_image(fmri_img)
            if not self.__contours_hidden:
                self.contours.actor.SetVisibility(1)

    @do_and_render
    def set_contours_visibility(self,visible):
        self.__contours_hidden = not visible
        if self.__contours_hidden:
            self.contours.actor.SetVisibility(0)
        elif self.__contours_img is not None:
            self.contours.actor.SetVisibility(1)



class FilterArrows(QtCore.QObject):
    key_pressed = pyqtSignal(QtCore.QEvent)

    def __init__(self, parent=None, other_keys=tuple()):
        super(FilterArrows, self).__init__(parent)
        keys = {QtCore.Qt.Key_Left, QtCore.Qt.Key_Right,QtCore.Qt.Key_Up,QtCore.Qt.Key_Down}
        keys.update(other_keys)
        self.__filter_keys = frozenset(keys)

    def eventFilter(self, QObject, QEvent):
        if QEvent.type() == QEvent.KeyPress:
            q_event_key = QEvent.key()
            if q_event_key in self.__filter_keys:
                #print "intercepted key"
                self.key_pressed.emit(QEvent)
                return True
        return False


class QSubjectViwerWidget(QFrame):
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)

    def __init__(self, reader, parent):
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        filt = FilterArrows(self)
        filt.key_pressed.connect(lambda e: self.event(e))
        self.__qwindow_interactor.installEventFilter(filt)

        self.__reader = reader
        self.__subject_viewer = SubjectViewer(self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        # self.subject_viewer.ren_win.Render()

        # self.__qwindow_interactor.show()

    def initialize_widget(self):
        """call after showing the interface"""
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        self.subject_viewer.reset_camera(0)
        # self.__subject_viewer.show_cone()

    @property
    def subject_viewer(self):
        return self.__subject_viewer

    def slice_change_handle(self, new_slice):
        self.slice_changed.emit(new_slice)
        # print new_slice

    def window_level_change_handle(self, window, level):
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)


class ImageManager(object):
    def __init__(self, reader, ren, widget, interactor, initial_subj=None, initial_space="World", picker=None):
        self.ren = ren
        self.reader = reader
        if initial_subj is None:
            initial_subj = reader.get("ids", None)[0]
        self.__current_subject = initial_subj
        self.__current_space = initial_space
        self.__current_image = None
        self.__current_contrast = None
        self.__current_image_orientation = 0
        self.__curent_fmri_paradigm = None
        self.__current_mri_window_level = None
        self.__current_fa_window_level = None
        self.__image_plane_widget = None
        self.__mri_lut = None
        self.__fmri_blender = braviz.visualization.fMRI_blender()
        self.__widget = widget
        self.__outline_filter = None
        self.__picker = picker
        self.__hidden = False  # Should only change when user selects to hide the image
        self.iren = interactor

    @property
    def image_plane_widget(self):
        if self.__image_plane_widget is None:
            self.create_image_plane_widget()
        return self.__image_plane_widget

    @do_and_render
    def hide_image(self):
        self.__hidden = True
        if self.__image_plane_widget is not None:
            self.__image_plane_widget.Off()
            # self.image_plane_widget.SetVisibility(0)

    @do_and_render
    def show_image(self):
        self.__hidden = False
        self.change_image_modality(self.__current_image, self.__curent_fmri_paradigm, True, self.__current_contrast)

    @do_and_render
    def create_image_plane_widget(self):
        if self.__image_plane_widget is not None:
            # already created
            return
        self.__image_plane_widget = braviz.visualization.persistentImagePlane(self.__current_image_orientation)
        self.__image_plane_widget.SetInteractor(self.iren)
        self.__image_plane_widget.On()
        self.__mri_lut = vtk.vtkWindowLevelLookupTable()
        self.__mri_lut.DeepCopy(self.__image_plane_widget.GetLookupTable())


        def slice_change_handler(source, event):
            new_slice = self.__image_plane_widget.GetSliceIndex()
            self.__widget.slice_change_handle(new_slice)

        def detect_window_level_event(source, event):
            window, level = self.__image_plane_widget.GetWindow(), self.__image_plane_widget.GetLevel()
            self.__widget.window_level_change_handle(window, level)

        self.__image_plane_widget.AddObserver(self.__image_plane_widget.slice_change_event, slice_change_handler)
        self.__image_plane_widget.AddObserver("WindowLevelEvent", detect_window_level_event)

        if self.__picker is not None:
            self.__image_plane_widget.SetPicker(self.__picker)

        outline = vtk.vtkOutlineFilter()

        outlineMapper = vtk.vtkPolyDataMapper()
        outlineMapper.SetInputConnection(outline.GetOutputPort())

        outlineActor = vtk.vtkActor()
        outlineActor.SetMapper(outlineMapper)
        outlineActor.GetProperty().SetColor(0, 0, 0)
        self.ren.AddActor(outlineActor)
        self.__outline_filter = outline

    @do_and_render
    def change_subject(self, new_subject):
        self.__current_subject = new_subject
        if not self.__hidden:
            self.change_image_modality(self.__current_image, self.__curent_fmri_paradigm, force_reload=True,
                                       contrast=self.__current_contrast)

    @do_and_render
    def change_space(self, new_space):
        if self.__current_space == new_space:
            return
        self.__current_space = new_space
        if not self.__hidden:
            self.change_image_modality(self.__current_image, self.__curent_fmri_paradigm, force_reload=True,
                                       skip_render=True)

    @do_and_render
    def change_image_modality(self, modality, paradigm=None, force_reload=False, contrast=1):
        """Changes the modality of the current image;
        to hide the image call hide_image;
        After this, the only way of showing back the image is by calling show_image
        in the case of fMRI modality should be fMRI and paradigm the name of the paradigm"""

        if modality is not None:
            modality = modality.upper()

        if (self.__current_image is not None) and (modality == self.__current_image) and (
                    paradigm == self.__curent_fmri_paradigm) and (contrast == self.__current_contrast) and \
                not force_reload:
            # nothing to do
            return

        # save previous state
        if (self.__image_plane_widget is not None) and self.__image_plane_widget.GetEnabled():
            if (self.__current_image == "MRI" or self.__current_image == "MD") and (
                        self.__current_mri_window_level is not None):
                self.__image_plane_widget.GetWindowLevel(self.__current_mri_window_level)
            elif (self.__current_image == "FA") and (self.__current_fa_window_level is not None):
                self.__image_plane_widget.GetWindowLevel(self.__current_fa_window_level)

        self.__current_image = modality
        self.__current_contrast = contrast

        if modality is None:
            if self.__image_plane_widget is not None:
                self.__image_plane_widget.Off()
            return

        if self.__current_subject is None:
            return

        if self.__image_plane_widget is None:
            self.create_image_plane_widget()
            self.__image_plane_widget.On()

        # update image labels:
        log = logging.getLogger(__name__)
        try:
            if modality == "WMPARC":
                ref = "WMPARC"
            else:
                ref = "APARC"
            aparc_img = self.reader.get(ref, self.__current_subject, format="VTK", space=self.__current_space)
            aparc_lut = self.reader.get(ref, self.__current_subject, lut=True)
            self.__image_plane_widget.addLabels(aparc_img)
            self.__image_plane_widget.setLabelsLut(aparc_lut)
        except Exception as e:
            log.warning(e)
            log.warning("APARC image not found")
            # raise Exception("Aparc not available")
            self.__image_plane_widget.addLabels(None)

        if modality == "FMRI":
            try:
                mri_image = self.reader.get("MRI", self.__current_subject, format="VTK", space=self.__current_space)
                fmri_image = self.reader.get("fMRI", self.__current_subject, format="VTK", space=self.__current_space,
                                             name=paradigm, contrast=contrast)
            except Exception:
                fmri_image = None
                log.warning("FMRI IMAGE NOT FOUND pdgm = %s" % paradigm)

            if fmri_image is None:
                self.image_plane_widget.Off()
                #raise
                raise Exception("%s not available for subject %s" % (paradigm, self.__current_subject))
            fmri_lut = self.reader.get("fMRI", self.__current_subject, lut=True)
            if self.__current_mri_window_level is None:
                #we need to load the mri image first to get a valid window_level
                self.__image_plane_widget.SetLookupTable(self.__mri_lut)
                self.__image_plane_widget.SetInputData(mri_image)
                self.__current_mri_window_level = [0, 0]
                self.reset_window_level(skip_render=True)

            self.__fmri_blender.set_luts(self.__mri_lut, fmri_lut)
            new_image = self.__fmri_blender.set_images(mri_image, fmri_image)

            self.__image_plane_widget.SetInputData(new_image)
            self.__outline_filter.SetInputData(new_image)

            self.__image_plane_widget.GetColorMap().SetLookupTable(None)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            self.__current_image = modality
            self.__curent_fmri_paradigm = paradigm
            self.__image_plane_widget.text1_value_from_img(fmri_image)
            if not self.__hidden:
                self.__image_plane_widget.On()
            return

        elif modality == "DTI":
            try:
                dti_image = self.reader.get("DTI", self.__current_subject, format="VTK", space=self.__current_space)
                fa_image = self.reader.get("FA", self.__current_subject, format="VTK", space=self.__current_space)
            except Exception:
                log.warning("DTI, not available")
                self.image_plane_widget.Off()
                raise Exception("DTI, not available")

            self.__image_plane_widget.SetInputData(dti_image)
            self.__outline_filter.SetInputData(dti_image)

            self.__image_plane_widget.GetColorMap().SetLookupTable(None)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            self.__current_image = modality
            self.__image_plane_widget.text1_value_from_img(fa_image)
            if not self.__hidden:
                self.__image_plane_widget.On()
            return

        # Other images
        self.__image_plane_widget.text1_to_std()
        try:
            new_image = self.reader.get(modality, self.__current_subject, space=self.__current_space, format="VTK")
        except Exception:
            self.image_plane_widget.Off()
            raise

        self.__image_plane_widget.SetInputData(new_image)
        self.__outline_filter.SetInputData(new_image)

        if modality == "MRI" or modality == "MD":
            lut = self.__mri_lut
            self.__image_plane_widget.SetLookupTable(lut)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            if self.__current_mri_window_level is None:
                self.__current_mri_window_level = [0, 0]
                self.reset_window_level(skip_render=True)
            else:
                self.__image_plane_widget.SetWindowLevel(*self.__current_mri_window_level)
        elif modality == "FA":
            # lut = self.reader.get("FA", self.__current_subject, lut=True)
            #self.__image_plane_widget.SetLookupTable(lut)
            lut = self.__mri_lut
            self.__image_plane_widget.SetLookupTable(lut)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            if self.__current_fa_window_level is None:
                self.__current_fa_window_level = [0, 0]
                self.reset_window_level(skip_render=True)
            else:
                self.__image_plane_widget.SetWindowLevel(*self.__current_fa_window_level)

        elif modality in {"APARC", "WMPARC"}:
            lut = self.reader.get("APARC", self.__current_subject, lut=True)
            self.__image_plane_widget.SetLookupTable(lut)

            # Important:
            self.__image_plane_widget.SetResliceInterpolateToNearestNeighbour()

        # self.__current_image = modality
        if self.__hidden is False:
            self.image_plane_widget.On()


    @do_and_render
    def change_image_orientation(self, orientation):
        """Changes the orientation of the current image
        to hide the image call hide_image
        orientation is a number from 0, 1 or 2 """
        log = logging.getLogger(__name__)
        if self.__image_plane_widget is None:
            self.__current_image_orientation = orientation
            log.warning("Set an image first")
            return
        self.__image_plane_widget.set_orientation(orientation)
        self.__current_image_orientation = orientation

    def get_number_of_image_slices(self):
        if self.__image_plane_widget is None:
            return 0
        img = self.__image_plane_widget.GetInput()
        if img is None:
            return 0
        dimensions = img.GetDimensions()

        return dimensions[self.__current_image_orientation]

    def get_current_image_slice(self):
        if self.__image_plane_widget is None:
            return 0
        return self.__image_plane_widget.GetSliceIndex()

    @do_and_render
    def set_image_slice(self, new_slice):
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetSliceIndex(int(new_slice))
        self.__image_plane_widget.InvokeEvent(self.__image_plane_widget.slice_change_event)


    def get_current_image_window(self):
        return self.__image_plane_widget.GetWindow()

    def get_current_image_level(self):
        return self.__image_plane_widget.GetLevel()

    @do_and_render
    def set_image_window(self, new_window):
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetWindowLevel(new_window, self.get_current_image_level())

    @do_and_render
    def set_image_level(self, new_level):
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetWindowLevel(self.get_current_image_window(), new_level)

    @do_and_render
    def reset_window_level(self, button=None):
        # print button
        if self.__image_plane_widget is None:
            return
        if self.__current_image == "MRI" or self.__current_image == "MD" or self.__current_image == "FMRI":
            if braviz.readAndFilter.PROJECT == "kmc40":
                self.__image_plane_widget.SetWindowLevel(3000, 1500)
            elif braviz.readAndFilter.PROJECT == "kmc400":
                self.__image_plane_widget.SetWindowLevel(500, 200)
            else:
                raise Exception("Unknown project")
            self.__image_plane_widget.GetWindowLevel(self.__current_mri_window_level)
            self.__image_plane_widget.InvokeEvent("WindowLevelEvent")
        elif self.__current_image == "FA":
            self.__image_plane_widget.SetWindowLevel(1.20, 0.6)
            self.__image_plane_widget.GetWindowLevel(self.__current_fa_window_level)
            self.__image_plane_widget.InvokeEvent("WindowLevelEvent")

        return


class ModelManager(object):
    def __init__(self, reader, ren, initial_subj=None, initial_space="World"):
        self.ren = ren
        if initial_subj is None:
            initial_subj = reader.get("ids", None)[0]
        self.__active_models_set = set()
        self.__pd_map_act = dict()
        self.__available_models = set()
        self.__current_subject = initial_subj
        self.__reader = reader
        self.__current_space = initial_space
        self.__actor_to_model = {}  # for picking
        self.__laterality = None

        # visual attributes
        self.__opacity = 1
        self.__current_color = None

        self.reload_models(subj=initial_subj, space=initial_space, skip_render=True)


    def __get_laterality(self):
        lat_var_idx = braviz.readAndFilter.tabular_data.LATERALITY
        lat_dict = {1: 'r', 2: 'l'}
        log = logging.getLogger(__file__)
        try:
            label = braviz.readAndFilter.tabular_data.get_var_value(lat_var_idx, self.__current_subject)
        except Exception:
            log.warning("Laterality no found for subject %s, assuming right handed" % self.__current_subject)
            label = 1
        return lat_dict.get(label, 'r')

    @do_and_render
    def reload_models(self, subj=None, space=None):
        if subj is not None:
            self.__current_subject = subj
            try:
                self.__available_models = set(self.__reader.get("MODEL", subj, index=True))
            except Exception:
                self.__available_models = set()
            self.__laterality = self.__get_laterality()
        if space is not None:
            self.__current_space = space

        if (space is not None) or (subj is not None):
            self.__refresh_models()

    def __refresh_models(self):
        for mod_name in self.__active_models_set:
            self.__addModel(mod_name)
        if len(self.__available_models) == 0:
            log = logging.getLogger(__name__)
            log.warning("No models found")
            #raise Exception("No models found")

    def __addModel(self, model_name):
        # if already exists make visible
        trio = self.__pd_map_act.get(model_name)
        if trio is not None:
            model, mapper, actor = trio
            rl_name = solve_laterality(self.__laterality, model_name)
            if rl_name in self.__available_models:
                model = self.__reader.get('MODEL', self.__current_subject, name=rl_name, space=self.__current_space)
                mapper.SetInputData(model)
                actor.SetVisibility(1)
                self.__pd_map_act[model_name] = (model, mapper, actor)
            else:
                actor.SetVisibility(0)  # Hide
        else:
            # New model
            rl_name = solve_laterality(self.__laterality, model_name)
            if rl_name in self.__available_models:
                model = self.__reader.get('MODEL', self.__current_subject, name=rl_name, space=self.__current_space)
                model_mapper = vtk.vtkPolyDataMapper()
                model_actor = vtk.vtkActor()
                model_properties = model_actor.GetProperty()
                if self.__current_color is None:
                    model_color = self.__reader.get('MODEL', None, name=rl_name, color='T')
                    model_properties.SetColor(list(model_color[0:3]))
                else:
                    model_properties.SetColor(self.__current_color)
                model_properties.SetOpacity(self.__opacity)
                model_properties.LightingOn()
                model_mapper.SetInputData(model)
                model_actor.SetMapper(model_mapper)
                self.ren.AddActor(model_actor)
                self.__pd_map_act[model_name] = (model, model_mapper, model_actor)
                self.__actor_to_model[id(model_actor)] = model_name

                # actor=self.__pd_map_act[model_name][2]
                # model_volume=self.__reader.get('model',self.currSubj,name=model_name,volume=1)
                #add_solid_balloon(balloon_widget, actor, model_name,model_volume)

    def __removeModel(self, model_name):
        """Deletes internal data structures
        """
        # check that it actually exists
        trio = self.__pd_map_act.get(model_name)
        if trio is None:
            return
        model, mapper, actor = trio
        self.ren.RemoveActor(actor)
        del self.__pd_map_act[model_name]
        del self.__actor_to_model[id(actor)]
        # balloon_widget.RemoveBalloon(actor)
        del actor
        del mapper
        del model

    def __hide_model(self, model_name):
        trio = self.__pd_map_act.get(model_name)
        if trio is None:
            return
        actor = trio[2]
        actor.SetVisibility(0)

    @do_and_render
    def set_models(self, new_model_set):
        new_set = set(new_model_set)
        current_models = self.__active_models_set

        to_add = new_set - current_models
        to_hide = current_models - new_set

        # print "act:", self.__active_models_set
        # print "new" , new_set
        # print "hide", to_hide

        for mod_name in to_add:
            self.__addModel(mod_name)
        for mod_name in to_hide:
            self.__hide_model(mod_name)

        self.__active_models_set = new_set

    @do_and_render
    def set_opacity(self, int_opacity):
        float_opacity = int_opacity / 100
        self.__opacity = float_opacity
        for _, _, ac in self.__pd_map_act.itervalues():
            prop = ac.GetProperty()
            prop.SetOpacity(float_opacity)

    def get_opacity(self):
        return self.__opacity * 100

    @do_and_render
    def set_color(self, float_rgb_color):
        self.__current_color = float_rgb_color
        for k, (_, _, ac) in self.__pd_map_act.iteritems():
            prop = ac.GetProperty()
            if self.__current_color is None:
                rl_name = solve_laterality(self.__laterality, k)
                model_color = self.__reader.get('MODEL', None, name=rl_name, color='T')
                prop.SetColor(list(model_color[0:3]))
            else:
                prop.SetColor(self.__current_color)

    def get_scalar_metrics(self, metric_name):
        try:
            value = structure_metrics.get_mult_struct_metric(self.__reader, self.__active_models_set,
                                                             self.__current_subject, metric_name)
        except Exception as e:
            log = logging.getLogger(__name__)
            log.error(e)
            value = float("nan")
            raise
        return value


class TractographyManager(object):
    def __init__(self, reader, ren, initial_subj=None, initial_space="World"):
        self.reader = reader
        self.ren = ren
        if initial_subj is None:
            initial_subj = reader.get("ids", None)[0]
        self.__current_subject = initial_subj
        self.__current_space = initial_space
        self.__current_color = "orient"
        self.__current_color_parameters = {"color": "orient", "scalars": None}
        self.__opacity = 1.0
        self.__lut = None
        self.__show_color_bar = False

        self.__ad_hoc_pd_mp_ac = None
        self.__ad_hoc_fiber_checks = None
        self.__ad_hoc_throug_all = True
        self.__ad_hoc_visibility = False

        self.__db_tracts = dict()
        self.__active_db_tracts = set()
        self.__bundle_colors = None
        self.__bundle_labels = None

        self.__color_bar_actor = None

    @do_and_render
    def set_subject(self, subj):
        self.__current_subject = subj
        self.__reload_fibers()

    @do_and_render
    def set_current_space(self, space):
        self.__current_space = space
        self.__reload_fibers()

    @do_and_render
    def set_bundle_from_checkpoints(self, checkpoints, throug_all):
        checkpoints = list(checkpoints)
        self.__ad_hoc_fiber_checks = checkpoints
        self.__ad_hoc_throug_all = throug_all
        self.__ad_hoc_visibility = True
        self.__ad_hock_checkpoints = checkpoints
        if self.__ad_hoc_pd_mp_ac is None:
            mapper = vtk.vtkPolyDataMapper()
            actor = vtk.vtkActor()
            self.ren.AddActor(actor)
            actor.SetMapper(mapper)
        else:
            _, mapper, actor = self.__ad_hoc_pd_mp_ac
        if throug_all is True:
            operation = "and"
        else:
            operation = "or"
        try:
            poly_data = self.reader.get("Fibers", self.__current_subject, waypoint=checkpoints, operation=operation,
                                        space=self.__current_space, **self.__current_color_parameters)
        except Exception as e:
            actor.SetVisibility(0)
            poly_data = None
            self.__ad_hoc_pd_mp_ac = (poly_data, mapper, actor)
            log = logging.getLogger(__name__)
            log.warning("Fibers not found")
            log.error(e.message)
            raise
        else:
            actor.GetProperty().SetOpacity(self.__opacity)
            mapper.SetInputData(poly_data)

            actor.SetVisibility(1)
            if self.__current_color == "bundle":
                colors = self.get_bundle_colors()
                c = colors[-1]
                actor.GetProperty().SetColor(*c)
            self.__set_lut_in_maper(mapper)

            self.__ad_hoc_pd_mp_ac = (poly_data, mapper, actor)
        return


    @do_and_render
    def hide_checkpoints_bundle(self):
        if self.__ad_hoc_pd_mp_ac is None:
            return
        act = self.__ad_hoc_pd_mp_ac[2]
        act.SetVisibility(0)
        self.__ad_hoc_visibility = False

    def __set_lut_in_maper(self, mapper):
        if self.__current_color == "bundle":
            mapper.SetScalarVisibility(0)
            return
        mapper.SetScalarVisibility(1)
        # print "setting lut"
        if self.__lut is None:
            mapper.SetColorModeToDefault()
        else:
            mapper.SetScalarVisibility(1)
            mapper.UseLookupTableScalarRangeOn()
            mapper.SetColorModeToMapScalars()
            mapper.SetLookupTable(self.__lut)


    @do_and_render
    def add_from_database(self, b_id):

        self.__active_db_tracts.add(b_id)
        if b_id not in self.__db_tracts:
            mapper = vtk.vtkPolyDataMapper()
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            self.ren.AddActor(actor)
            self.__db_tracts[b_id] = (None, mapper, actor)

        _, mapper, actor = self.__db_tracts[b_id]
        try:
            poly_data = self.get_polydata(b_id)
            mapper.SetInputData(poly_data)
        except Exception as e:
            log = logging.getLogger(__name__)
            log.error(e.message)
            log.warning("Couldn't load fibers from db")
            actor.SetVisibility(0)
            raise

        self.__db_tracts[b_id] = (poly_data, mapper, actor)
        actor.SetVisibility(1)
        actor.GetProperty().SetOpacity(self.__opacity)
        if self.__current_color == "bundle":
            colors = self.get_bundle_colors()
            c = colors[self.__bundle_labels[b_id]]
            actor.GetProperty().SetColor(*c)
        self.__set_lut_in_maper(mapper)


    def get_bundle_colors(self):
        number_of_bundles = len(self.__active_db_tracts)
        if self.__ad_hoc_visibility is True:
            number_of_bundles += 1
        if self.__bundle_colors is not None and len(self.__bundle_colors) == number_of_bundles:
            return self.__bundle_colors
        n = number_of_bundles
        n = max(n, 3)

        colors = sbs.color_palette("Set1",n)
        self.__bundle_colors = colors
        # print colors
        return colors

    @do_and_render
    def set_show_color_bar(self, value):
        self.__show_color_bar = bool(value)
        self.__set_color_bar()

    def get_show_color_bar(self):
        return self.__show_color_bar

    def get_polydata(self, b_id):
        poly = self.reader.get("FIBERS", self.__current_subject, space=self.__current_space,
                               db_id=b_id, **self.__current_color_parameters)
        return poly


    @do_and_render
    def hide_database_tract(self, bid):
        trio = self.__db_tracts.get(bid)
        if trio is None:
            return
        actor = trio[2]
        actor.SetVisibility(0)
        self.__active_db_tracts.remove(bid)

    @do_and_render
    def change_color(self, new_color):
        if self.__current_color == new_color:
            return
        self.__current_color = new_color
        self.__lut = None
        if new_color in ("bundle", "orient"):
            self.__current_color_parameters["color"] = "orient"
            self.__current_color_parameters["scalars"] = None
        elif new_color == "rand":
            self.__current_color_parameters["color"] = "rand"
            self.__current_color_parameters["scalars"] = None
        else:
            self.__current_color_parameters["color"] = None
            self.__current_color_parameters["scalars"] = new_color
            self.__lut = self.reader.get("Fibers", None, scalars=new_color, lut=True)


        # print self.__current_color
        self.__set_color_bar()
        self.__reload_fibers()


    def __set_color_bar(self):
        scalars = self.__current_color_parameters.get("scalars")
        if (not self.__show_color_bar) or (scalars is None):
            if self.__color_bar_actor is None:
                return
            else:
                self.__color_bar_actor.SetVisibility(0)
        else:
            if self.__color_bar_actor is None:
                self.__color_bar_actor = vtk.vtkScalarBarActor()
                self.__color_bar_actor.SetNumberOfLabels(4)
                # self.__color_bar_actor.SetMaximumWidthInPixels(100)
                #self.__color_bar_actor.GetTitleTextProperty().SetFontSize(10)
                #self.__color_bar_actor.GetLabelTextProperty().SetFontSize(10)
                # self.__color_bar_actor.GetTitleTextProperty().SetColor(1,0,0)
                # self.__color_bar_actor.GetLabelTextProperty().SetColor(1,0,0)


                self.__color_bar_widget = vtk.vtkScalarBarWidget()
                self.__color_bar_widget.SetScalarBarActor(self.__color_bar_actor)
                self.__color_bar_widget.RepositionableOn()
                iren = self.ren.GetRenderWindow().GetInteractor()
                self.__color_bar_widget.SetInteractor(iren)


                rep = self.__color_bar_widget.GetRepresentation()
                coord1 = rep.GetPositionCoordinate()
                coord2 = rep.GetPosition2Coordinate()
                # coord1.SetCoordinateSystemToViewport()
                #coord2.SetCoordinateSystemToViewport()
                #width, height = self.ren.GetRenderWindow().GetSize()
                #print width, height
                coord1.SetValue(0.89, 0.05)
                #coord1.SetValue(width-110,50)
                coord2.SetValue(0.1, 0.9)
                #coord2.SetValue(width-10,height-50)
                self.__color_bar_widget.On()
                #self.ren.AddActor2D(self.__color_bar_actor)

            self.__color_bar_actor.SetVisibility(1)
            self.__color_bar_actor.SetLookupTable(self.__lut)
            # self.__color_bar_actor.SetTitle(scalars[:2].upper())
            self.__color_bar_actor.SetTitle("")


    def __reload_fibers(self):
        # reload ad_hoc
        error = False
        if self.__ad_hoc_visibility is True:
            try:
                self.set_bundle_from_checkpoints(self.__ad_hoc_fiber_checks, self.__ad_hoc_throug_all)
            except Exception:
                error = True

        # reload db
        for bid in self.__active_db_tracts:
            try:
                self.add_from_database(bid)
            except Exception:
                error = True
        if error is True:
            raise Exception("Couldn't load fibers")

    @do_and_render
    def set_active_db_tracts(self, new_set):
        new_set = set(new_set)
        to_hide = self.__active_db_tracts - new_set
        to_add = new_set - self.__active_db_tracts
        errors = 0
        self.__bundle_labels = dict(izip(new_set, range(len(new_set) + 1)))
        for i in to_hide:
            self.hide_database_tract(i)
        self.__active_db_tracts = new_set
        for i in to_add:
            try:
                self.add_from_database(i)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.error(e)
                raise

        if errors > 0:
            log = logging.getLogger(__name__)
            log.warning("Couldn't load all tracts")
            raise Exception("Couldn't load all tracts")

    @do_and_render
    def set_opacity(self, float_opacity):
        self.__opacity = float_opacity
        self.__reload_fibers()

    def get_scalar_from_db(self, scalar, bid):
        if bid in self.__active_db_tracts:
            if scalar in ("number", "mean_length"):
                pd = self.__db_tracts[bid][0]
                return structure_metrics.get_scalar_from_fiber_ploydata(pd, scalar)
            elif scalar == "mean_fa":
                fiber = self.reader.get("FIBERS", self.__current_subject, space=self.__current_space,
                                        db_id=bid, color=None, scalars="fa_p")
                n = structure_metrics.get_scalar_from_fiber_ploydata(fiber, "mean_color")
                return n
            elif scalar == "mean_md":
                fiber = self.reader.get("FIBERS", self.__current_subject, space=self.__current_space,
                                        db_id=bid, color=None, scalars="md_p")
                n = structure_metrics.get_scalar_from_fiber_ploydata(fiber, "mean_color")
                return n

        else:
            return float("nan")

    def get_scalar_from_structs(self, scalar):
        if self.__ad_hoc_visibility is False:
            return float("nan")
        try:
            if scalar in ("number", "mean_length"):
                fiber = self.__ad_hoc_pd_mp_ac[0]
                n = structure_metrics.get_scalar_from_fiber_ploydata(fiber, scalar)
                return n
            elif scalar == "mean_fa":
                operation = "and" if self.__ad_hoc_throug_all else "or"
                fiber = self.reader.get("Fibers", self.__current_subject, waypoint=self.__ad_hock_checkpoints,
                                        operation=operation, space=self.__current_space, color=None, scalars="fa_p")
                n = structure_metrics.get_scalar_from_fiber_ploydata(fiber, "mean_color")
                return n
            elif scalar == "mean_md":
                operation = "and" if self.__ad_hoc_throug_all else "or"
                fiber = self.reader.get("Fibers", self.__current_subject, waypoint=self.__ad_hock_checkpoints,
                                        operation=operation, space=self.__current_space, color=None, scalars="md_p")
                n = structure_metrics.get_scalar_from_fiber_ploydata(fiber, "mean_color")
                return n
        except Exception:
            return float("nan")
        return float("nan")


class SurfaceManager(object):
    def __init__(self, reader, ren, iren, initial_subj=None, initial_space="World", picker=None,
                 persistent_cone=False):
        self.ren = ren
        self.reader = reader
        self.picker = picker
        self.iren = iren
        self.picking_event = vtk.vtkCommand.UserEvent + 1

        self.__persistent_cone = persistent_cone
        self.__last_picked_pos = None
        self.__left_active = False
        self.__right_active = False
        self.__current_surface = "white"
        self.__current_scalars = "curv"
        self.__lut = None
        self.__surf_trios = {}

        self.__current_space = initial_space
        self.__subject = initial_subj
        self.__opacity = 100

        self.__active_color_bar = False
        self.__color_bar_actor = None
        self.__color_bar_widget = None

        # for interaction
        if self.picker is not None:
            self.__picking_dict = dict()
            self.__cone_trio = None
            self.__locators = dict()
            self.__active_picking = False
            self.__picking_events = dict()
            self.__picking_text = None
            self.__create_pick_cone()
            self.__create_pick_text()
            self.__setup_picking()

        self.__update_lut()


    def __create_pick_cone(self):
        coneSource = vtk.vtkConeSource()
        coneSource.CappingOn()
        coneSource.SetHeight(12)
        coneSource.SetRadius(5)
        coneSource.SetResolution(31)
        coneSource.SetCenter(6, 0, 0)
        coneSource.SetDirection(-1, 0, 0)

        coneMapper = vtk.vtkDataSetMapper()
        coneMapper.SetInputConnection(coneSource.GetOutputPort())

        redCone = vtk.vtkActor()
        redCone.PickableOff()
        redCone.SetMapper(coneMapper)
        redCone.GetProperty().SetColor(1, 0, 0)
        redCone.SetVisibility(0)

        self.ren.AddActor(redCone)
        self.__cone_trio = coneSource, coneMapper, redCone

    def __create_pick_text(self):
        text2 = vtk.vtkTextActor()
        cor = text2.GetPositionCoordinate()
        cor.SetCoordinateSystemToNormalizedDisplay()
        text2.SetPosition([0.99, 0.01])
        text2.SetInput('probando')
        tprop = text2.GetTextProperty()
        tprop.SetJustificationToRight()
        tprop.SetFontSize(18)
        self.ren.AddActor(text2)
        text2.SetVisibility(0)
        self.__picking_text = text2

    def __point_cone(self, nx, ny, nz):
        actor = self.__cone_trio[2]
        actor.SetOrientation(0.0, 0.0, 0.0)
        n = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
        if (nx < 0.0):
            actor.RotateWXYZ(180, 0, 1, 0)
            n = -n
        actor.RotateWXYZ(180, (nx + n) * 0.5, ny * 0.5, nz * 0.5)

    def __setup_picking(self):
        log = logging.getLogger(__name__)

        def get_message(picker):
            hemi = self.__picking_dict[id(picker.GetProp3D())]
            pd = self.__surf_trios[hemi][0]
            ptId = picker.GetPointId()
            point_data = pd.GetPointData()
            scalars = point_data.GetScalars()
            scalar = self.__current_scalars
            t = scalars.GetTuple(ptId)
            annotations = {'aparc', 'aparc.a2009s', 'BA', "aparc.DKTatlas40"}
            if scalar in annotations:
                label = self.__lut.GetAnnotation(int(t[0]))
                return "%s-Label: %s" % (scalar, label)
            return "%s = %f" % (scalar, t[0])

        def picking(caller, event):
            active_picking = self.__active_picking
            if event == 'MouseMoveEvent' and not active_picking:
                return
            if event == 'LeftButtonReleaseEvent':
                self.__active_picking = False
                if self.__persistent_cone is False:
                    self.__cone_trio[2].SetVisibility(0)
                    self.__picking_text.SetVisibility(0)
                log.debug("done picking")
                return
            x, y = caller.GetEventPosition()
            picked = self.picker.Pick(x, y, 0, self.ren)
            p = self.picker.GetPickPosition()
            n = self.picker.GetPickNormal()
            picked_prop = self.picker.GetProp3D()
            if picked and (id(picked_prop) in self.__picking_dict):
                self.__active_picking = True
                redCone = self.__cone_trio[2]
                redCone.InvokeEvent(self.picking_event)
                redCone.SetPosition(p)
                self.__last_picked_pos = p
                self.__point_cone(*n)
                self.__picking_text.SetVisibility(1)
                redCone.SetVisibility(1)
                message = get_message(self.picker)
                self.__picking_text.SetInput(message)
                event_id = self.__picking_events[event]
                command = caller.GetCommand(event_id)
                command.SetAbortFlag(1)
                self.iren.Render()
            else:
                self.__active_picking = False
                if self.__persistent_cone is False:
                    self.__cone_trio[2].SetVisibility(0)
                    self.__picking_text.SetVisibility(0)
            return

        iren = self.iren
        self.__picking_events["LeftButtonPressEvent"] = iren.AddObserver(vtk.vtkCommand.LeftButtonPressEvent, picking,
                                                                         10)
        iren.AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent, picking, 10)
        self.__picking_events["MouseMoveEvent"] = iren.AddObserver(vtk.vtkCommand.MouseMoveEvent, picking, 10)


    def __update_hemisphere(self, h):
        # print "updating hemisphere ",h
        if h == "l":
            active = self.__left_active
        elif h == "r":
            active = self.__right_active
        else:
            log = logging.getLogger(__name__)
            log.error("Unknown hemisphere %s" % h)
            raise Exception("Unknown hemisphere %s" % h)

        trio = self.__surf_trios.get(h)
        if not active:
            if trio is None:
                return
            ac = trio[2]
            ac.SetVisibility(0)
            return
        if trio is None:
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetLookupTable(self.__lut)
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            self.ren.AddActor(actor)
            self.__picking_dict[id(actor)] = h
            locator = vtk.vtkCellTreeLocator()
            locator.LazyEvaluationOn()
            self.__locators[h] = locator
            if self.picker is not None:
                self.picker.AddLocator(locator)
                self.picker.AddPickList(actor)
        else:
            surf, mapper, actor = trio

        surf = self.reader.get("surf", self.__subject, name=self.__current_surface, hemi=h,
                               scalars=self.__current_scalars,
                               space=self.__current_space)
        mapper.SetInputData(surf)
        actor.SetVisibility(1)
        actor.GetProperty().SetOpacity(self.__opacity / 100)
        trio = surf, mapper, actor
        self.__locators[h].SetDataSet(surf)
        self.__surf_trios[h] = trio

    def __update_lut(self):
        ref = self.__subject
        lut = self.reader.get("SURF_SCALAR", ref, scalars=self.__current_scalars, lut=True, hemi="l")
        for trio in self.__surf_trios.itervalues():
            mapper = trio[1]
            mapper.SetLookupTable(lut)
        self.__lut = lut
        if (self.__color_bar_actor is not None) and (self.__active_color_bar):
            self.__color_bar_actor.SetLookupTable(lut)


    def __update_both(self):
        self.__update_hemisphere("r")
        self.__update_hemisphere("l")

    @do_and_render
    def set_hemispheres(self, left=None, right=None):

        if left is not None:
            left = bool(left)
            if left != self.__left_active:
                self.__left_active = left
                self.__update_hemisphere("l")

        if right is not None:
            right = bool(right)
            if right != self.__right_active:
                self.__right_active = right
                self.__update_hemisphere("r")

    @do_and_render
    def set_scalars(self, scalars):

        if scalars == self.__current_scalars:
            return
        self.__current_scalars = scalars
        self.__update_both()
        self.__update_lut()

    @do_and_render
    def set_surface(self, surface):
        surface = surface.lower()
        if surface == self.__current_surface:
            return
        self.__current_surface = surface
        self.__update_both()

    @do_and_render
    def show_color_bar(self, show):
        if show == self.__active_color_bar:
            return
        self.__active_color_bar = show
        if not show:
            if self.__color_bar_actor is None:
                return
            self.__color_bar_actor.SetVisibility(0)
            return
        if self.__color_bar_actor is None:
            self.__color_bar_actor = vtk.vtkScalarBarActor()
            self.__color_bar_actor.SetNumberOfLabels(4)
            self.__color_bar_widget = vtk.vtkScalarBarWidget()
            self.__color_bar_widget.SetScalarBarActor(self.__color_bar_actor)
            self.__color_bar_widget.RepositionableOn()
            iren = self.iren
            self.__color_bar_widget.SetInteractor(iren)
            self.__color_bar_widget.On()
            rep = self.__color_bar_widget.GetRepresentation()
            coord1 = rep.GetPositionCoordinate()
            coord2 = rep.GetPosition2Coordinate()
            coord1.SetValue(0.01, 0.05)
            coord2.SetValue(0.1, 0.9)
        self.__color_bar_actor.SetVisibility(1)
        self.__color_bar_actor.SetLookupTable(self.__lut)
        self.__color_bar_actor.SetTitle("")

    @do_and_render
    def set_subject(self, new_subject):
        self.__subject = new_subject
        self.__update_both()

    @do_and_render
    def set_space(self, new_space):
        self.__current_space = new_space
        self.__update_both()

    @do_and_render
    def set_opacity(self, new_opacity):
        if new_opacity == self.__opacity:
            return
        self.__opacity = new_opacity
        for trio in self.__surf_trios.itervalues():
            ac = trio[2]
            ac.GetProperty().SetOpacity(self.__opacity / 100)

    def hide_cone(self):
        self.__cone_trio[2].SetVisibility(0)
        self.__picking_text.SetVisibility(0)

    def get_last_picked_pos(self):
        return self.__last_picked_pos

    @property
    def pick_cone_actor(self):
        return self.__cone_trio[2]


class OrthogonalPlanesViewer(object):
    def __init__(self, render_window_interactor, reader, widget):
        # render_window_interactor.Initialize()
        # render_window_interactor.Start()
        self.iren = render_window_interactor
        self.ren_win = render_window_interactor.GetRenderWindow()
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground((0.75, 0.75, 0.75))
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

        self.light = vtk.vtkLight()
        self.ren.AddLight(self.light)
        self.light.SetLightTypeToHeadlight()

        self.reader = reader
        self.__widget = widget

        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.0005)
        self.iren.SetPicker(self.picker)

        # state
        self.__current_subject = None
        self.__current_space = "world"
        self.__curent_modality = None

        # internal data
        self.__cursor = AdditionalCursors(self.ren)

        self.__x_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__y_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__z_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__image_planes = (self.__x_image_manager, self.__y_image_manager, self.__z_image_manager)
        self.x_image.change_image_orientation(0)
        self.y_image.change_image_orientation(1)
        self.z_image.change_image_orientation(2)
        self.hide_image()

        self.__sphere = SphereProp(self.ren)
        self.__cortex = SurfaceManager(self.reader, self.ren, self.iren, self.__current_subject, self.__current_space,
                                       picker=self.picker, persistent_cone=True)

        self.__active_cursor_plane = True


    def finish_initializing(self):
        self.link_window_level()
        self.connect_cursors()
        self.ren.ResetCameraClippingRange()
        self.ren.ResetCamera()

    def link_window_level(self):
        "call after initializing the planes"
        if self.__curent_modality not in ("DTI", "FMRI"):
            self.y_image.image_plane_widget.SetLookupTable(self.x_image.image_plane_widget.GetLookupTable())
            self.z_image.image_plane_widget.SetLookupTable(self.x_image.image_plane_widget.GetLookupTable())

    def connect_cursors(self):
        def draw_cursor2(caller, event):
            self.cortex.hide_cone()
            self.__active_cursor_plane = True
            if caller == self.x_image.image_plane_widget:
                axis = 0
            elif caller == self.y_image.image_plane_widget:
                axis = 1
            else:
                axis = 2
            pw = self.image_planes[axis].image_plane_widget
            coords = pw.GetCurrentCursorPosition()
            assert coords is not None
            self.__cursor.set_axis_coords(axis, coords)

        def slice_movement(caller, event):
            self.cortex.hide_cone()
            self.__active_cursor_plane = True
            last_pos = self.__cursor.get_coords()
            if last_pos is None:
                return
            last_pos = np.array(last_pos)
            if caller == self.x_image.image_plane_widget:
                axis = 0
            elif caller == self.y_image.image_plane_widget:
                axis = 1
            else:
                axis = 2
            sl = self.image_planes[axis].get_current_image_slice()
            last_pos[axis] = sl
            self.__cursor.set_axis_coords(axis, last_pos)

        self.x_image.image_plane_widget.AddObserver(self.x_image.image_plane_widget.cursor_change_event, draw_cursor2)
        self.y_image.image_plane_widget.AddObserver(self.y_image.image_plane_widget.cursor_change_event, draw_cursor2)
        self.z_image.image_plane_widget.AddObserver(self.z_image.image_plane_widget.cursor_change_event, draw_cursor2)

        self.x_image.image_plane_widget.AddObserver(self.x_image.image_plane_widget.slice_change_event, slice_movement)
        self.y_image.image_plane_widget.AddObserver(self.y_image.image_plane_widget.slice_change_event, slice_movement)
        self.z_image.image_plane_widget.AddObserver(self.z_image.image_plane_widget.slice_change_event, slice_movement)

        def change_cursor_to_cone(caller, event):
            self.__active_cursor_plane = False
            self.__cursor.hide()

        self.cortex.pick_cone_actor.AddObserver(self.cortex.picking_event, change_cursor_to_cone)

    @do_and_render
    def show_image(self):
        for im in self.__image_planes:
            im.show_image(skip_render=True)

    @do_and_render
    def hide_image(self):
        for im in self.__image_planes:
            im.hide_image(skip_render=True)

    @do_and_render
    def change_subject(self, subj):
        ex = None
        for im in self.__image_planes:
            try:
                im.change_subject(subj, skip_render=True)
            except Exception as e:
                ex = e
        try:
            self.__cortex.set_subject(subj, skip_render=True)
        except Exception:
            log = logging.getLogger(__file__)
            log.warning("Cortex not found for subject %s" % subj)
        if ex is not None:
            raise ex

        self.__cursor.set_image(self.x_image.image_plane_widget.GetInput())
        self.link_window_level()

    @do_and_render
    def change_image_modality(self, mod, contrast=None):
        mod = mod.upper()
        if contrast is not None:
            pdgm = mod
            mod = "FMRI"
        else:
            pdgm = None
        for im in self.__image_planes:
            im.change_image_modality(mod, pdgm, mod, skip_render=True, contrast=contrast)
        self.__curent_modality = mod
        self.__cursor.set_image(self.x_image.image_plane_widget.GetInput())
        self.link_window_level()

    def get_number_of_slices(self):
        n_slices = self.x_image.image_plane_widget.GetInput().GetDimensions()
        return n_slices

    def get_current_slice(self):
        return (self.x_image.get_current_image_slice(),
                self.y_image.get_current_image_slice(),
                self.z_image.get_current_image_slice(),)

    def get_camera_parameters(self):
        cam1 = self.ren.GetActiveCamera()
        fp = cam1.GetFocalPoint()
        pos = cam1.GetPosition()
        vu = cam1.GetViewUp()
        return fp, pos, vu

    def set_camera(self, focal_point, position, view_up):
        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal_point)
        cam1.SetPosition(position)
        cam1.SetViewUp(view_up)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()

    @property
    def image_planes(self):
        return self.__image_planes

    @property
    def x_image(self):
        return self.__x_image_manager

    @property
    def y_image(self):
        return self.__y_image_manager

    @property
    def z_image(self):
        return self.__z_image_manager

    @property
    def sphere(self):
        return self.__sphere

    @property
    def cortex(self):
        return self.__cortex

    def current_position(self):
        if self.__active_cursor_plane:
            return self.__cursor.get_position()
        else:
            return self.cortex.get_last_picked_pos()

    @do_and_render
    def change_space(self, new_space):
        for im in self.image_planes:
            im.change_space(new_space, skip_render=True)
        self.cortex.set_space(new_space, skip_render=True)
        self.__current_space = new_space
        self.__cursor.set_image(self.x_image.image_plane_widget.GetInput())
        self.iren.Render()


class MeasurerViewer(object):
    camera_positions = {
            0: ((-5.5, -5.5, 4.5), (535,-5.5,4.5), (0, 0, 1)), # SAGITAL
            1: ((-5.5, -8, 2.8), (-5.5, 530, 2.8), (1, 0, 0)),  #  CORONAL
            2: ((-3.5, 0, 10), (-3.5, 0, 550), (0, 1, 0)),  #  AXIAL
    }
    def __init__(self, render_window_interactor, reader, widget):
        self.iren = render_window_interactor
        self.ren_win = render_window_interactor.GetRenderWindow()
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground((0.75, 0.75, 0.75))
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

        self.light = vtk.vtkLight()
        self.ren.AddLight(self.light)
        self.light.SetLightTypeToHeadlight()

        self.reader = reader
        self.__widget = widget

        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.0005)
        self.iren.SetPicker(self.picker)

        self.__measure_axis = None
        self.__pax1, self.__pax2 = None, None  # perpendicular to measure axis
        self.set_measure_axis(2)
        # state
        self.__current_subject = None
        self.__current_space = "talairach"
        self.__curent_modality = None

        # internal data

        self.__x_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__y_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__z_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__image_planes = (self.__x_image_manager, self.__y_image_manager, self.__z_image_manager)
        self.x_image.change_image_orientation(0)
        self.y_image.change_image_orientation(1)
        self.z_image.change_image_orientation(2)
        #for pw in self.__image_planes:
        #    pw.image_plane_widget.InteractionOff()
        self.hide_image()

        self.__placed = False
        self.measure_widget = vtk.vtkDistanceWidget()
        self.measure_widget.KeyPressActivationOff()
        self.measure_repr = vtk.vtkDistanceRepresentation3D()
        self.measure_repr.GetLineProperty().SetLineWidth(2)
        self.measure_repr.SetLabelFormat("")
        self.measure_repr.RulerModeOn()
        self.measure_repr.SetRulerDistance(5.0)
        self.measure_widget.SetRepresentation(self.measure_repr)
        self.measure_widget.SetInteractor(self.iren)
        self.measure_widget.SetPriority(self.x_image.image_plane_widget.GetPriority()+1)
        self.obs_id = self.measure_widget.AddObserver(vtk.vtkCommand.PlacePointEvent, self.restrict_points_to_plane)
        self.obs_id2 = self.measure_widget.AddObserver(vtk.vtkCommand.InteractionEvent, self.restrict_points_to_plane)
        self.obs_id3 = self.measure_widget.AddObserver(vtk.vtkCommand.InteractionEvent, self.emit_distance_changed_signal)

    def restrict_points_to_plane(self, object, event):
        modifiers = QApplication.keyboardModifiers()
        straight = False
        if QtCore.Qt.ControlModifier & modifiers:
            straight = True
        ax = self.__measure_axis
        slice_coords = self.image_planes[ax].image_plane_widget.GetSlicePosition()
        plane_point = np.zeros(3)
        plane_point[ax] = slice_coords
        pa1, pa2 = self.__pax1, self.__pax2

        repr = object.GetRepresentation()
        r1 = repr.GetPoint1Representation()
        r2 = repr.GetPoint2Representation()
        r1i = r1.GetInteractionState()
        r2i = r2.GetInteractionState()
        camera = self.ren.GetActiveCamera()
        view_vec = np.array(camera.GetDirectionOfProjection())
        if r1i > 0 or not self.__placed:
            p1 = np.zeros(3)
            repr.GetPoint1WorldPosition(p1)
            if np.dot(view_vec, p1) != 0:
                t = (slice_coords - p1[ax]) / view_vec[ax]
                p1 = p1 + view_vec * t
            else:
                p1[ax] = slice_coords

            if straight and self.__placed:
                ref = np.zeros(3)
                repr.GetPoint2WorldPosition(ref)
                dif = np.abs(p1 - ref)
                if dif[pa1] > dif[pa2]:
                    p1[pa2] = ref[pa2]
                else:
                    p1[pa1] = ref[pa1]
            repr.SetPoint1WorldPosition(p1)
            self.__placed = True
        else:
            p2 = np.zeros(3)
            repr.GetPoint2WorldPosition(p2)
            if np.dot(view_vec, p2) != 0:
                t = (slice_coords - p2[ax]) / view_vec[ax]
                p2 = p2 + view_vec * t
            else:
                p2[ax] = slice_coords
            if straight:
                ref = np.zeros(3)
                repr.GetPoint1WorldPosition(ref)
                dif = np.abs(p2 - ref)
                if dif[pa1] > dif[pa2]:
                    p2[pa2] = ref[pa2]
                else:
                    p2[pa1] = ref[pa1]
            repr.SetPoint2WorldPosition(p2)


    def finish_initializing(self):
        self.link_window_level()
        self.ren.ResetCameraClippingRange()
        self.ren.ResetCamera()
        self.measure_widget.On()


    def link_window_level(self):
        "call after initializing the planes"
        if self.__curent_modality not in ("DTI", "FMRI"):
            self.y_image.image_plane_widget.SetLookupTable(self.x_image.image_plane_widget.GetLookupTable())
            self.z_image.image_plane_widget.SetLookupTable(self.x_image.image_plane_widget.GetLookupTable())

        def slice_movement(caller, event):
            if caller == self.x_image.image_plane_widget:
                axis = 0
            elif caller == self.y_image.image_plane_widget:
                axis = 1
            else:
                axis = 2
            sl = self.image_planes[axis].get_current_image_slice()
            if axis == self.__measure_axis and self.__placed:
                c = self.image_planes[axis].image_plane_widget.GetSlicePosition()
                p1,p2 = np.zeros(3),np.zeros(3)
                self.measure_repr.GetPoint1WorldPosition(p1)
                self.measure_repr.GetPoint2WorldPosition(p2)
                p1[axis] = c
                p2[axis] = c
                self.measure_repr.SetPoint1WorldPosition(p1)
                self.measure_repr.SetPoint2WorldPosition(p2)
                #self.ren_win.Render()

        self.x_image.image_plane_widget.AddObserver(self.x_image.image_plane_widget.slice_change_event, slice_movement)
        self.y_image.image_plane_widget.AddObserver(self.y_image.image_plane_widget.slice_change_event, slice_movement)
        self.z_image.image_plane_widget.AddObserver(self.z_image.image_plane_widget.slice_change_event, slice_movement)

    @do_and_render
    def set_measure_axis(self, axis):
        assert axis in {0, 1, 2}
        self.__measure_axis = axis
        if axis == 0:
            self.__pax1 = 1
            self.__pax2 = 2
        elif axis == 1:
            self.__pax1 = 0
            self.__pax2 = 2
        else:
            self.__pax1 = 0
            self.__pax2 = 1
        self.reset_camera(skip_render = True)

    @do_and_render
    def set_slice_coords(self,coords):
        pw = self.image_planes[self.__measure_axis].image_plane_widget
        pw.SetSlicePosition(coords)
        pw.InvokeEvent(pw.slice_change_event)


    def emit_distance_changed_signal(self,caller,event):
        d = self.distance
        self.__widget.distance_changed_handle(d)


    @do_and_render
    def show_image(self):
        for im in self.__image_planes:
            im.show_image(skip_render=True)

    @do_and_render
    def hide_image(self):
        for im in self.__image_planes:
            im.hide_image(skip_render=True)

    @do_and_render
    def change_subject(self, subj):
        ex = None
        for im in self.__image_planes:
            try:
                im.change_subject(subj, skip_render=True)
            except Exception as e:
                ex = e
        self.link_window_level()

    @do_and_render
    def change_image_modality(self, mod, contrast=None):
        mod = mod.upper()
        if contrast is not None:
            pdgm = mod
            mod = "FMRI"
        else:
            pdgm = None
        for im in self.__image_planes:
            im.change_image_modality(mod, pdgm, mod, skip_render=True, contrast=contrast)
        self.__curent_modality = mod
        self.link_window_level()

    def get_number_of_slices(self):
        #TODO: Something is not working right
        n_slices = self.x_image.image_plane_widget.GetInput().GetDimensions()
        return n_slices

    def get_current_slice(self):
        return (self.x_image.get_current_image_slice(),
                self.y_image.get_current_image_slice(),
                self.z_image.get_current_image_slice(),)

    def get_camera_parameters(self):
        cam1 = self.ren.GetActiveCamera()
        fp = cam1.GetFocalPoint()
        pos = cam1.GetPosition()
        vu = cam1.GetViewUp()
        return fp, pos, vu

    @do_and_render
    def reset_camera(self):
        fp,pos,vu = self.camera_positions[self.__measure_axis]
        self.set_camera(fp,pos,vu,skip_render = True)

    @do_and_render
    def set_camera(self, focal_point, position, view_up):
        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal_point)
        cam1.SetPosition(position)
        cam1.SetViewUp(view_up)

        self.ren.ResetCameraClippingRange()

    @property
    def image_planes(self):
        return self.__image_planes

    @property
    def x_image(self):
        return self.__x_image_manager

    @property
    def y_image(self):
        return self.__y_image_manager

    @property
    def z_image(self):
        return self.__z_image_manager


    @do_and_render
    def change_space(self, new_space):
        for im in self.image_planes:
            im.change_space(new_space, skip_render=True)
        self.__current_space = new_space
        self.iren.Render()

    @do_and_render
    def reset_measure(self):
        self.measure_widget.Off()
        self.measure_widget.SetWidgetStateToStart()
        self.measure_widget.On()
        self.__placed = False
        self.__widget.distance_changed_handle(np.nan)


    @property
    def distance(self):
        if not self.__placed:
            return np.nan
        else:
            return self.measure_repr.GetDistance()

    @property
    def point1(self):
        if self.__placed:
            p1 = np.zeros(3)
            self.measure_repr.GetPoint1WorldPosition(p1)
            return p1
        else:
            return None

    @property
    def point2(self):
        if self.__placed:
            p2 = np.zeros(3)
            self.measure_repr.GetPoint2WorldPosition(p2)
            return p2
        else:
            return None
    @do_and_render
    def set_points(self,p1,p2):
        self.measure_repr.SetPoint1WorldPosition(p1)
        self.measure_repr.SetPoint2WorldPosition(p2)
        if not self.__placed:
            self.measure_widget.SetWidgetStateToManipulate()
            acs = vtk.vtkPropCollection()
            self.measure_repr.GetActors(acs)
            self.measure_repr.VisibilityOn()

            self.__placed = True

    @do_and_render
    def set_measure_color(self,r,g,b):
        r,g,b = r/255,g/255,b/255
        self.measure_repr.GetLineProperty().SetColor(r,g,b)
        self.measure_repr.GetGlyphActor().GetProperty().SetColor(r,g,b)
        print r,g,b


class AdditionalCursors(object):
    def __init__(self, ren):
        self.__cursors = braviz.visualization.cursors()
        self.__cursors.SetVisibility(0)
        self.__image = None
        self.__coords = None
        self.__axis = None
        ren.AddActor(self.__cursors)

    def set_image(self, img):
        self.__image = img
        dim = img.GetDimensions()
        sp = img.GetSpacing()
        org = img.GetOrigin()
        max_sp = max(sp)

        self.__cursors.set_dimensions(*dim)
        self.__cursors.set_spacing(*sp)
        self.__cursors.set_origin(*org)
        self.__cursors.set_delta(max_sp / 5)

    def get_position(self):
        if self.__coords is None:
            return None
        pos = np.array(self.__coords)
        org = np.array(self.__image.GetOrigin())
        sp = np.array(self.__image.GetSpacing())
        return pos * sp + org

    def get_coords(self):
        return self.__coords

    def set_axis_coords(self, axis=None, coords=None):
        if axis is None or coords is None or self.__image is None:
            self.__cursors.SetVisibility(0)
            self.__coords = None
        self.__cursors.SetVisibility(1)
        if axis != self.__axis:
            self.__cursors.change_axis(axis)
            self.__axis = axis
        self.__cursors.set_cursor(*coords)
        self.__coords = coords
        self.__cursors.SetVisibility(1)
        pass

    def hide(self):
        self.__cursors.SetVisibility(0)


class SphereProp(object):
    def __init__(self, ren):
        self.__source = vtk.vtkSphereSource()
        self.__mapper = vtk.vtkPolyDataMapper()
        self.__actor = vtk.vtkActor()
        self.__center = None
        self.__radius = None
        self.__RESOLUTION = 20

        self.__actor.SetMapper(self.__mapper)
        self.__mapper.SetInputConnection(self.__source.GetOutputPort())
        self.__source.SetThetaResolution(self.__RESOLUTION)
        self.__source.SetPhiResolution(self.__RESOLUTION)
        self.__source.LatLongTessellationOn()
        self.__actor.SetVisibility(0)
        ren.AddActor(self.__actor)

    def set_center(self, ctr):
        self.__source.SetCenter(*ctr)
        self.__center = ctr

    def set_radius(self, r):
        self.__source.SetRadius(r)
        self.__radius = r

    def set_repr(self, rep):
        if rep.startswith("w"):
            self.__actor.GetProperty().SetRepresentationToWireframe()
        else:
            self.__actor.GetProperty().SetRepresentationToSurface()

    def hide(self):
        self.__actor.SetVisibility(0)

    def show(self):
        self.__actor.SetVisibility(1)

    def set_opacity(self, opac_int):
        opac = opac_int / 100.0
        self.__actor.GetProperty().SetOpacity(opac)

    def set_color(self, r, g, b):
        r, g, b = map(lambda x: x / 255.0, (r, g, b))
        self.__actor.GetProperty().SetColor(r, g, b)


class QMeasurerWidget(QFrame):
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)
    distance_changed = pyqtSignal(float)

    def __init__(self, reader, parent):
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        filt = FilterArrows(self, (QtCore.Qt.Key_C,))
        filt.key_pressed.connect(lambda e: self.event(e))
        self.__qwindow_interactor.installEventFilter(filt)
        self.__reader = reader
        self.__vtk_viewer = MeasurerViewer(self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        # self.subject_viewer.ren_win.Render()

        # self.__qwindow_interactor.show()

    def initialize_widget(self):
        """call after showing the interface"""
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        # self.__subject_viewer.show_cone()

    @property
    def orthogonal_viewer(self):
        return self.__vtk_viewer

    def slice_change_handle(self, new_slice):
        self.slice_changed.emit(new_slice)
        # print new_slice

    def window_level_change_handle(self, window, level):
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)

    def distance_changed_handle(self,distance):
        self.distance_changed.emit(distance)

class QOrthogonalPlanesWidget(QFrame):
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)

    def __init__(self, reader, parent):
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        filt = FilterArrows(self, (QtCore.Qt.Key_C,QtCore.Qt.Key_O))
        filt.key_pressed.connect(lambda e: self.event(e))
        self.__qwindow_interactor.installEventFilter(filt)
        self.__reader = reader
        self.__vtk_viewer = OrthogonalPlanesViewer(self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        # self.subject_viewer.ren_win.Render()

        # self.__qwindow_interactor.show()

    def initialize_widget(self):
        """call after showing the interface"""
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        # self.__subject_viewer.show_cone()

    @property
    def orthogonal_viewer(self):
        return self.__vtk_viewer

    def slice_change_handle(self, new_slice):
        self.slice_changed.emit(new_slice)
        # print new_slice

    def window_level_change_handle(self, window, level):
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)


class fMRI_viewer(object):
    def __init__(self, render_window_interactor, reader, widget):
        self.iren = render_window_interactor
        self.ren_win = render_window_interactor.GetRenderWindow()
        self.ren = vtk.vtkRenderer()
        self.ren.SetBackground((0.75, 0.75, 0.75))
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

        self.light = vtk.vtkLight()
        self.ren.AddLight(self.light)
        self.light.SetLightTypeToHeadlight()

        self.reader = reader

        # state
        self.__current_subject = None
        self.__current_space = "func"
        self.__current_paradigm = None
        self.__current_contrast = 1

        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.0005)
        self.iren.SetPicker(self.picker)

        # internal data
        self.__image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                            picker=self.picker)
        self.__cursor = AdditionalCursors(self.ren)
        self.__contours = FmriContours(self.ren)
        fmri_lut = self.reader.get("fMRI", self.__current_subject, lut=True)
        self.__contours.set_lut(fmri_lut)

        self.__image_loaded = False
        #reset camera and render
        self.reset_camera(0)
        #widget, signal handling
        self.__widget = widget

    def change_orientation(self, orientation_index):
        #find cursor position
        pos = self.__cursor.get_coords()
        self.image.change_image_orientation(orientation_index)
        if pos is None:
            new_slice = self.image.get_number_of_image_slices() // 2
        else:
            new_slice = int(pos[orientation_index])
            self.__cursor.set_axis_coords(orientation_index, pos)
        self.image.set_image_slice(new_slice)


    def connect_cursors(self):
        def draw_cursor2(caller, event):
            self.__active_cursor_plane = True
            axis = self.image.image_plane_widget.GetPlaneOrientation()
            pw = self.image.image_plane_widget
            coords = pw.GetCurrentCursorPosition()
            assert coords is not None
            self.__cursor.set_axis_coords(axis, coords)
            self.__widget.cursor_move_handler(coords)

        def slice_movement(caller, event):
            self.__active_cursor_plane = True
            last_pos = self.__cursor.get_coords()
            if last_pos is None:
                return
            last_pos = np.array(last_pos)
            axis = self.image.image_plane_widget.GetPlaneOrientation()
            sl = self.image.get_current_image_slice()
            last_pos[axis] = sl
            self.__cursor.set_axis_coords(axis, last_pos)
            self.__widget.cursor_move_handler(last_pos)

        self.image.image_plane_widget.AddObserver(self.image.image_plane_widget.cursor_change_event, draw_cursor2)
        self.image.image_plane_widget.AddObserver(self.image.image_plane_widget.slice_change_event, slice_movement)

    def current_coords(self):
        return self.__cursor.get_coords()

    @do_and_render
    def set_cursor_coords(self, coords):
        axis = self.image.image_plane_widget.GetPlaneOrientation()
        self.__cursor.set_axis_coords(axis, coords)
        slice = coords[axis]
        self.image.set_image_slice(slice)

    @property
    def image(self):
        return self.__image_manager

    @property
    def contours(self):
        return self.__contours

    @do_and_render
    def change_subject(self, new_subj):
        if self.__current_subject != new_subj:
            self.__current_subject = new_subj
            self.update_view(skip_render=True)

    @do_and_render
    def change_paradigm(self, new_pdgm):
        if self.__current_paradigm != new_pdgm:
            self.__current_paradigm = new_pdgm
            self.update_view(skip_render=True)

    @do_and_render
    def change_contrast(self, new_contrast):
        if self.__current_contrast != new_contrast:
            self.__current_contrast = new_contrast
            self.update_view(skip_render=True)

    @do_and_render
    def set_all(self, new_subject, new_pdgm, new_contrast):
        if self.__current_subject != new_subject:
            self.__current_subject = new_subject
        if self.__current_paradigm != new_pdgm:
            self.__current_paradigm = new_pdgm
        if self.__current_contrast != new_contrast:
            self.__current_contrast = new_contrast
        self.update_view(skip_render=True)

    @do_and_render
    def set_contour_value(self, value):
        self.__contours.set_value(value)

    @do_and_render
    def set_contour_opacity(self, value):
        self.__contours.actor.GetProperty().SetOpacity(value / 100)

    @do_and_render
    def set_contour_visibility(self, value):
        self.__contours.actor.SetVisibility(value)

    @do_and_render
    def update_view(self):
        if self.__current_subject is None or self.__current_paradigm is None or self.__current_contrast is None:
            return
        try:
            self.image.change_subject(self.__current_subject)
        except Exception:
            pass

        try:
            self.image.change_space("func-%s" % self.__current_paradigm)
        except Exception:
            pass

        self.image.change_image_modality("fMRI", self.__current_paradigm, contrast=self.__current_contrast)
        if not self.__image_loaded:
            self.connect_cursors()
            self.__image_loaded = True
        self.__cursor.set_image(self.image.image_plane_widget.GetInput())
        if self.image.image_plane_widget.GetEnabled():
            self.__contours.set_image(self.image.image_plane_widget.alternative_img)
            self.__contours.actor.SetVisibility(1)

        else:
            self.__contours.actor.SetVisibility(0)


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

    def get_camera_parameters(self):
        cam1 = self.ren.GetActiveCamera()
        fp = cam1.GetFocalPoint()
        pos = cam1.GetPosition()
        vu = cam1.GetViewUp()
        return fp, pos, vu

    def set_camera(self, focal_point, position, view_up):
        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal_point)
        cam1.SetPosition(position)
        cam1.SetViewUp(view_up)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()


class FmriContours(object):
    def __init__(self, ren):
        self.__contour_filter = vtk.vtkContourFilter()
        self.__contour_filter.UseScalarTreeOn()
        self.__contour_filter.ComputeNormalsOff()

        self.__mapper = vtk.vtkPolyDataMapper()
        self.__mapper.SetInputConnection(self.__contour_filter.GetOutputPort())

        self.__actor = vtk.vtkActor()
        self.__actor.SetMapper(self.__mapper)
        ren.AddActor(self.__actor)

        self.__value = None
        self.__contour_filter.SetValue(0, 5)
        self.__contour_filter.SetValue(1, -5)
        self.__img = None
        self.__lut = None

    def set_value(self, value):
        self.__value = value
        self.__contour_filter.SetValue(0, value)
        self.__contour_filter.SetValue(1, -1 * value)

    def set_image(self, img):
        self.__img = img
        self.__contour_filter.SetInputData(img)
        self.__contour_filter.Update()

    def set_lut(self, lut):
        self.__mapper.SetLookupTable(lut)
        self.__mapper.UseLookupTableScalarRangeOn()

    @property
    def actor(self):
        return self.__actor



class QFmriWidget(QFrame):
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)
    cursor_moved = pyqtSignal(tuple)

    def __init__(self, reader, parent):
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        self.__reader = reader
        self.__vtk_viewer = fMRI_viewer(self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        # self.subject_viewer.ren_win.Render()

        # self.__qwindow_interactor.show()

    def initialize_widget(self):
        """call after showing the interface"""
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        # self.__subject_viewer.show_cone()

    @property
    def viewer(self):
        return self.__vtk_viewer

    def slice_change_handle(self, new_slice):
        self.slice_changed.emit(new_slice)
        # print new_slice

    def window_level_change_handle(self, window, level):
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)

    def cursor_move_handler(self, coordinates):
        self.cursor_moved.emit(tuple(coordinates))


if __name__ == "__main__":
    import sys
    import PyQt4.QtGui as QtGui
    import braviz

    reader = braviz.readAndFilter.BravizAutoReader()
    app = QtGui.QApplication(sys.argv)
    main_window = QSubjectViwerWidget(reader, None)
    main_window.show()
    main_window.initialize_widget()

    app.exec_()
    log = logging.getLogger(__name__)
    log.info("es todo")