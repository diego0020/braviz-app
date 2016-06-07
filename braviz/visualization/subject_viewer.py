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


from __future__ import division

import vtk
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt4 import QtCore
from PyQt4.QtGui import QFrame, QHBoxLayout, QApplication
from PyQt4.QtCore import pyqtSignal

from braviz.visualization.simple_vtk import OrientationAxes, persistentImagePlane, cursors, estimate_window_level
from braviz.visualization.fmri_view import fMRI_blender

from braviz.interaction.structure_metrics import solve_laterality
import braviz.readAndFilter.tabular_data
import braviz.readAndFilter.config_file
import seaborn as sbs
from itertools import izip
from braviz.interaction import structure_metrics
from functools import wraps
import numpy as np
import logging

__author__ = 'Diego'


_axis_dict = {"axial": 2, "sagital": 0,  "coronal": 1}

# TODO: Abstract viewer classes


def do_and_render(f):
    """
    Wraps drawing methods, adding an optional call to *Render* at the end.

    It adds the *skip_render* kwarg argument, which if True will avoid the call to Render. This is
    useful to avoid repeated call renders when performing several draw operations.

    requires the class to have the renderer accessible as self.ren

    Args:
        f (function) : Function that changes vtk scene
    """

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

    """
    A general viewer to show data on a particular subject

    It provides access to

        - Images
        - fMRI Contours
        - Segmentation reconstruction models
        - Surface parcellations
        - Tractographies
        - Tracula Bundles
    """

    def __init__(self, render_window_interactor, reader, widget):
        """
        Creates the viewer

        Args:
            render_window_interactor (vtkRenderWindowInteractor) : The intaractor that will be used with this viewer
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            widget (QObject) : Must implement *slice_change_handle* and *window_level_change_handle*

        """
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
        self.axes = OrientationAxes()
        self.axes.initialize(self.iren)

        self.light = vtk.vtkLight()
        self.ren.AddLight(self.light)
        self.light.SetLightTypeToHeadlight()

        self.reader = reader

        # state
        self.__current_subject = None
        self.__current_space = "subject"

        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.0005)
        self.iren.SetPicker(self.picker)

        # internal data
        self.__model_manager = ModelManager(self.reader, self.ren)
        self.__tractography_manager = TractographyManager(
            self.reader, self.ren)
        self.__image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                            picker=self.picker)
        self.__surface_manager = SurfaceManager(
            self.reader, self.ren, self.iren, picker=self.picker)

        self.__contours_manager = FmriContours(self.ren)
        self.__tracula_manager = TraculaManager(
            self.reader, self.ren, self.__current_subject, self.__current_space)
        fmri_lut = self.reader.get("fmri", None, lut=True)
        self.__contours_manager.set_lut(fmri_lut)
        self.__contours_paradigm = None
        self.__contours_contrast = None
        self.set_contours_visibility(False, skip_render=True)
        self.__contours_img = None
        # reset camera and render
        # self.reset_camera(0)
        #        self.ren.Render()

        # widget, signal handling
        self.__widget = widget

    @property
    def models(self):
        """
        Access to :class:`ModelManager`
        """
        return self.__model_manager

    @property
    def tractography(self):
        """
        Access to :class:`TractographyManager`
        """
        return self.__tractography_manager

    @property
    def image(self):
        """
        Access to :class:`ImageManager`
        """
        return self.__image_manager

    @property
    def surface(self):
        """
        Access to :class:`SurfaceManager`
        """
        return self.__surface_manager

    @property
    def contours(self):
        """
        Access to :class:`FmriContours`
        """
        return self.__contours_manager

    @property
    def tracula(self):
        """
        Access to :class:`TraculaManager`
        """
        return self.__tracula_manager

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

    def change_subject(self, new_subject):
        """
        Changes the subject associated to the viewer

        Args:
            new_subject : new subject id
        """
        self.__current_subject = new_subject
        errors = []
        log = logging.getLogger(__name__)
        # update image
        try:
            self.image.change_subject(new_subject, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Image")

        # update models
        try:
            self.models.reload_models(subj=new_subject, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Models")

        # update fibers
        try:
            self.tractography.set_subject(new_subject, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Fibers")

        # update surfaces
        try:
            self.surface.set_subject(new_subject, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Surfaces")

        # update fmri
        try:
            self.set_fmri_contours_image(skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Contours")
        try:
            self.tracula.reload_bundles(
                self.__current_subject, self.__current_space, skip_render=True)
        except Exception as e:
            log.exception(e)
            errors.append("Tracula")

        self.ren_win.Render()
        if len(errors) > 0:
            log.error("Couldn't load " + ", ".join(errors))
            raise Exception("Couldn't load " + ", ".join(errors))

    @do_and_render
    def change_current_space(self, new_space):
        """
        Changes the current coordinate system

        Args:
            new_space (str) : New coordinate system
        """
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
        try:
            self.tracula.reload_bundles(
                self.__current_subject, new_space, skip_render=True)
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
        """
        resets the current camera to standard locations.

        Args:
            position (int) :

                - 0: initial 3d view
                - 1: left
                - 2: right
                - 3: front
                - 4: back
                - 5: top
                - 6: bottom
        """

        focal, position, viewup = self.__camera_positions_dict[position]

        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal)
        cam1.SetPosition(position)
        cam1.SetViewUp(viewup)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()

    def set_camera(self, focal_point, position, view_up):
        """
        Sets the camera position

        Args:
            focal_point (tuple) : Focal point
            position (tuple) : Camera position
            view_up (tuple) : View up vector

        """
        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal_point)
        cam1.SetPosition(position)
        cam1.SetViewUp(view_up)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()

    def print_camera(self):
        """
        Logs information about the current camera position

        Data is send to the current logger with *info* level
        """
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
        """
        Gets current camera parameters

        Returs:
            focal_point, position, view_up
        """
        cam1 = self.ren.GetActiveCamera()
        fp = cam1.GetFocalPoint()
        pos = cam1.GetPosition()
        vu = cam1.GetViewUp()
        return fp, pos, vu

    @do_and_render
    def set_fmri_contours_image(self, paradigm=None, contrast=None):
        """
        Sets the image to use for calculating fMRI contours

        Args:
            paradigm (str) : Name of fMRI paradigm
            contrast (int): Index (Matlab style) of desired contrast
        """
        if paradigm is None:
            paradigm = self.__contours_paradigm
        else:
            self.__contours_paradigm = paradigm
        if contrast is None:
            contrast = self.__contours_contrast
        else:
            self.__contours_contrast = contrast

        log = logging.getLogger(__name__)

        if self.__contours_hidden:
            return

        if paradigm is None:
            self.__contours_img = None
        else:
            try:
                fmri_img = self.reader.get("fmri", self.__current_subject, space=self.__current_space,
                                           name=paradigm, contrast=contrast, format="vtk")
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
    def set_contours_visibility(self, visible):
        """
        Toggle visibility of fMRI contours

        Args:
            visible (bool) : If ``True`` contours will show, if ``False`` contours will be hidden,
        """
        self.__contours_hidden = not visible
        if self.__contours_hidden:
            self.contours.actor.SetVisibility(0)
        else:
            self.set_fmri_contours_image(
                self.__contours_paradigm, self.__contours_contrast, skip_render=True)
            self.contours.actor.SetVisibility(1)


class FilterArrows(QtCore.QObject):

    """
    A Qt event filter to prevent the main vtk widget from swallowing certain keys. By default this are the arrows,
    but additional keys can be added in the constructor.
    """
    key_pressed = pyqtSignal(QtCore.QEvent)

    def __init__(self, parent=None, other_keys=tuple()):
        """
        Construct the Qt Event Filter to avoid certain key presses from arriving to the VTK widget

        Args:
            parent (QOject) : Parent of the current object
            other_keys (list) : List of additional keys to filter out

        """
        super(FilterArrows, self).__init__(parent)
        keys = {QtCore.Qt.Key_Left, QtCore.Qt.Key_Right,
                QtCore.Qt.Key_Up, QtCore.Qt.Key_Down}
        keys.update(other_keys)
        self.__filter_keys = frozenset(keys)

    def eventFilter(self, QObject, QEvent):
        if QEvent.type() == QEvent.KeyPress:
            q_event_key = QEvent.key()
            if q_event_key in self.__filter_keys:
                # print "intercepted key"
                self.key_pressed.emit(QEvent)
                return True
        return False


class QSubjectViewerWidget(QFrame):

    """
    A Qt Widget that wraps :class:`SubjectViewer` and lets it connect naturally to Qt Applications
    """
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)

    def __init__(self, reader, parent):
        """
        Creates the subject viewer widget

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            parent (QObject) : Parent
        """
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        filt = FilterArrows(self)
        filt.key_pressed.connect(lambda e: self.event(e))
        self.__qwindow_interactor.installEventFilter(filt)

        self.__reader = reader
        self.__subject_viewer = SubjectViewer(
            self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        # self.subject_viewer.ren_win.Render()

        # self.__qwindow_interactor.show()

    def initialize_widget(self):
        """
        Call this function **after** calling show on the widget or a parent
        """
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        self.subject_viewer.reset_camera(0)
        # self.__subject_viewer.show_cone()

    @property
    def subject_viewer(self):
        """
        Access to the underlying :class:`SubjectViewer`
        """
        return self.__subject_viewer

    def slice_change_handle(self, new_slice):
        """
        Emits a signal when the current image slice is changed on the vtkWidget
        """
        self.slice_changed.emit(new_slice)
        # print new_slice

    def window_level_change_handle(self, window, level):
        """
        Emits a signal when window or level are changed by interacting in the vtkWidget
        """
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)


class ImageManager(object):

    """
    Controls an ImagePlaneWidget
    """

    def __init__(self, reader, ren, widget, interactor, initial_subj=None, initial_space="subject", picker=None):
        """
        Initializes the ImageManager

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            ren (vtkRenderer) : Renderer in which to draw the plane
            widget (QObject) : Must implement *slice_change_handle* and *window_level_change_handle*
            interactor (vtkRenderWindowInteractor) : The render window interactor of the output window
            initial_subj : Code of initial subject, if None an arbitrary subject will be selected
            initial_space (str) : Initial coordinate system
            picker (vtkPicker) : A vtkPicker may be used to pick on several objects. If None a new picker is created
        """
        self.ren = ren
        self.reader = reader
        if initial_subj is None:
            conf = braviz.readAndFilter.config_file.get_apps_config()
            initial_subj = conf.get_default_subject()
        self.__current_subject = initial_subj
        self.__current_space = initial_space
        self.__current_image_class = None
        self.__current_image_name = None
        self.__current_contrast = None
        self.__current_image_orientation = 0
        self.__past_window_levels = {}
        self.__image_plane_widget = None
        self.__window_level_lut = vtk.vtkWindowLevelLookupTable()
        self.__fmri_blender = fMRI_blender()
        self.__widget = widget
        self.__outline_filter = None
        self.__picker = picker
        # Should only change when user selects to hide the image
        self.__hidden = False
        self.iren = interactor

    @property
    def image_plane_widget(self):
        """
        Get the vtkImagePlaneWidget
        """
        if self.__image_plane_widget is None:
            self._create_image_plane_widget()
        return self.__image_plane_widget

    @do_and_render
    def hide_image(self):
        """
        Hide the plane widget
        """
        self.__hidden = True
        if self.__image_plane_widget is not None:
            self.__image_plane_widget.Off()
            # self.image_plane_widget.SetVisibility(0)

    @do_and_render
    def show_image(self):
        """
        Show the plane widget
        """
        self.__hidden = False
        self.change_image_modality(
            self.__current_image_class, self.__current_image_name, True, self.__current_contrast)

    @do_and_render
    def _create_image_plane_widget(self):
        """
        Creates the internal plane widget
        """
        if self.__image_plane_widget is not None:
            # already created
            return
        self.__image_plane_widget = persistentImagePlane(
            self.__current_image_orientation)
        self.__image_plane_widget.SetInteractor(self.iren)
        #self.__image_plane_widget.On()
        self.__window_level_lut = vtk.vtkWindowLevelLookupTable()
        self.__window_level_lut.DeepCopy(self.__image_plane_widget.GetLookupTable())

        def slice_change_handler(source, event):
            new_slice = self.__image_plane_widget.GetSliceIndex()
            self.__widget.slice_change_handle(new_slice)

        def detect_window_level_event(source, event):
            window, level = self.__image_plane_widget.GetWindow(
            ), self.__image_plane_widget.GetLevel()
            self.__widget.window_level_change_handle(window, level)

        self.__image_plane_widget.AddObserver(
            self.__image_plane_widget.slice_change_event, slice_change_handler)
        self.__image_plane_widget.AddObserver(
            "WindowLevelEvent", detect_window_level_event)

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
    def change_subject(self, new_subject, force=False):
        """
        Change subject associated to the plane

        Args:
            new_subject : Id of new subject
        """
        self.__current_subject = new_subject
        if not self.__hidden or force:
            self.change_image_modality(self.__current_image_class, self.__current_image_name, force_reload=True,
                                       contrast=self.__current_contrast)

    @do_and_render
    def change_space(self, new_space):
        """
        Change current coordinate system

        new_space (str) : new coordinate system, see :meth:`~braviz.readAndFilter.base_reader.BaseReader.get`
        """
        if self.__current_space == new_space:
            return
        self.__current_space = new_space
        if not self.__hidden:
            self.change_image_modality(self.__current_image_class, self.__current_image_name, force_reload=True,
                                       skip_render=True)

    @do_and_render
    def change_image_modality(self, image_class, image_name, force_reload=False, contrast=1):
        """Changes the modality of the current image;

        In the case of fMRI modality should be fMRI and paradigm the name of the paradigm

        Args:
            image_class (str) : New image class, may be one of  ``["image","label","dti","fmri"]``
            image_name (str) : New image modality name. Use ``None`` if *image_class* is ``"dti"``,
                otherwise it should be inside the index of the given class.
                In case of *FMRI* the paradigm should be entered here
                See :meth:`~braviz.readAndFilter.base_reader.BaseReader.get`
            force_reload (bool) : if True, forces the plane to reload the image if it appears to be the same as before
            contrast (int) : contrast to show in case image_class is ``"fmri"``

        """

        if image_name is not None:
            image_name = image_name.upper()

        if image_class is not None:
            image_class = image_class.upper()

        if (self.__current_image_class is not None) and (image_class == self.__current_image_class) and \
            (contrast == self.__current_contrast) and \
            (self.__current_image_name == image_name) and not force_reload:
            # nothing to do
            return

        # save window and level values (only for standard image class)
        if self.__current_image_class == "IMAGE" and \
            (self.__image_plane_widget is not None) and self.__image_plane_widget.GetEnabled():
            window_level = [0, 0]
            self.__image_plane_widget.GetWindowLevel(window_level)
            self.__past_window_levels[self.__current_image_name] = window_level

        self.__current_image_name = image_name
        self.__current_image_class = image_class
        self.__current_contrast = contrast

        if image_class is None:
            if self.__image_plane_widget is not None:
                self.__image_plane_widget.Off()
            return

        if self.__current_subject is None:
            return

        if self.__image_plane_widget is None:
            self._create_image_plane_widget()
            #self.__image_plane_widget.On()

        # update image labels:
        log = logging.getLogger(__name__)
        try:
            if image_name == "WMPARC":
                ref = "WMPARC"
            else:
                ref = "APARC"
            aparc_img = self.reader.get("LABEL", self.__current_subject, name=ref,
                                        format="VTK", space=self.__current_space)
            aparc_lut = self.reader.get("LABEL", self.__current_subject, name=ref, lut=True)
            self.__image_plane_widget.addLabels(aparc_img)
            self.__image_plane_widget.setLabelsLut(aparc_lut)
        except Exception as e:
            log.warning(e)
            log.warning("APARC image not found")
            # raise Exception("Aparc not available")
            self.__image_plane_widget.addLabels(None)

        if image_class == "FMRI":
            try:
                mri_image = self.reader.get("IMAGE", self.__current_subject, format="VTK", name="MRI",
                                            space=self.__current_space)
                fmri_image = self.reader.get("fMRI", self.__current_subject, format="VTK", space=self.__current_space,
                                             name=image_name, contrast=contrast)
            except Exception:
                fmri_image = None
                mri_image = None
                log.warning("FMRI IMAGE NOT FOUND pdgm = %s" % image_name)

            if fmri_image is None or mri_image is None:
                self.image_plane_widget.Off()
                # raise
                raise Exception(
                    "%s not available for subject %s" % (image_name, self.__current_subject))
            fmri_lut = self.reader.get(
                "fMRI", self.__current_subject, lut=True)
            # we need to load the mri image first to get a valid
            # window_level
            w_l = self.__past_window_levels.get("MRI")
            if w_l is None:
                w_l = estimate_window_level(mri_image)
            self.__window_level_lut.SetWindow(w_l[0])
            self.__window_level_lut.SetLevel(w_l[1])

            self.__fmri_blender.set_luts(self.__window_level_lut, fmri_lut)
            new_image = self.__fmri_blender.set_images(mri_image, fmri_image)

            self.__image_plane_widget.SetInputData(new_image)
            self.__outline_filter.SetInputData(new_image)

            self.__image_plane_widget.GetColorMap().SetLookupTable(None)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            self.__current_image_class = image_class
            self.__current_image_name = image_name
            self.__image_plane_widget.text1_value_from_img(fmri_image)
            if not self.__hidden:
                self.__image_plane_widget.On()
            return

        elif image_class == "DTI":
            try:
                dti_image = self.reader.get(
                    "DTI", self.__current_subject, format="VTK", space=self.__current_space)
                fa_image = self.reader.get("IMAGE", self.__current_subject, format="VTK", space=self.__current_space,
                                           name="FA")
            except Exception:
                log.warning("DTI, not available")
                self.image_plane_widget.Off()
                raise Exception("DTI, not available")

            self.__image_plane_widget.SetInputData(dti_image)
            self.__outline_filter.SetInputData(dti_image)

            self.__image_plane_widget.SetResliceInterpolateToCubic()
            self.__image_plane_widget.text1_value_from_img(fa_image)
            self.__image_plane_widget.GetColorMap().SetLookupTable(None)
            if not self.__hidden:
                self.__image_plane_widget.On()
            return

        # Other images
        self.__image_plane_widget.text1_to_std()
        try:
            new_image = self.reader.get(image_class, self.__current_subject, space=self.__current_space,
                                        name=image_name, format="VTK")
        except Exception:
            self.image_plane_widget.Off()
            raise

        self.__image_plane_widget.SetInputData(new_image)
        self.__outline_filter.SetInputData(new_image)

        if image_class == "IMAGE":
            lut = self.__window_level_lut
            self.__image_plane_widget.SetLookupTable(lut)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
            w_l = self.__past_window_levels.get(image_name)
            if w_l is None:
                self.reset_window_level(skip_render=True)
            else:
                self.__image_plane_widget.SetWindowLevel(
                    *w_l)
        elif image_class == "LABEL":
            lut = self.reader.get("LABEL", self.__current_subject, lut=True, name=image_name)
            self.__image_plane_widget.SetLookupTable(lut)

            # Important:
            self.__image_plane_widget.SetResliceInterpolateToNearestNeighbour()

        # self.__current_image = modality
        if self.__hidden is False:
            self.image_plane_widget.On()

    @do_and_render
    def change_image_orientation(self, orientation):
        """
        Changes the orientation of the current image

        Args:
            orientation (int) : 0 for X, 1 for Y and 2 for Z
        """
        log = logging.getLogger(__name__)
        if self.__image_plane_widget is None:
            self.__current_image_orientation = orientation
            log.warning("Set an image first")
            return
        self.__image_plane_widget.set_orientation(orientation)
        self.__current_image_orientation = orientation

    def get_number_of_image_slices(self):
        """
        Gets the number of slices in the current orientation

        Returns:
            The number of available slicer for the current image and orientation
        """
        if self.__image_plane_widget is None:
            return 0
        img = self.__image_plane_widget.GetInput()
        if img is None:
            return 0
        dimensions = img.GetDimensions()

        return dimensions[self.__current_image_orientation]

    def get_current_image_slice(self):
        """
        Get the index of the actual slice

        Returns:
            The index of the current slice
        """
        if self.__image_plane_widget is None:
            return 0
        return self.__image_plane_widget.GetSliceIndex()

    @do_and_render
    def set_image_slice(self, new_slice):
        """
        Sets the image slice

        Args:
            new_slice (int) : Number of the desired slice
        """
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetSliceIndex(int(new_slice))
        self.__image_plane_widget.InvokeEvent(
            self.__image_plane_widget.slice_change_event)

    def get_current_image_window(self):
        """
        Current window

        Returns:
            Current window value
        """
        if self.__image_plane_widget is None:
            return 0
        return self.__image_plane_widget.GetWindow()

    def get_current_image_level(self):
        """
        Current level

        Returns:
            Current level value
        """
        if self.__image_plane_widget is None:
            return 0
        return self.__image_plane_widget.GetLevel()

    @do_and_render
    def set_image_window(self, new_window):
        """
        Changes window value

        Args:
            new_window (float) : New window value
        """
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetWindowLevel(
            new_window, self.get_current_image_level())

    @do_and_render
    def set_image_level(self, new_level):
        """
        Changes level value

        Args:
            new_level (float) : New level value
        """
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetWindowLevel(
            self.get_current_image_window(), new_level)

    @do_and_render
    def reset_window_level(self, _=None):
        """
        Resets window and level to standard values
        """
        if self.__image_plane_widget is None:
            return
        if self.__current_image_class == "IMAGE":
            img = self.__image_plane_widget.GetInput()
            window, level = estimate_window_level(img)
            self.__image_plane_widget.SetWindowLevel(window, level)
            self.__image_plane_widget.InvokeEvent("WindowLevelEvent")


class ModelManager(object):

    """
    A manager for segmented structure models
    """

    def __init__(self, reader, ren, initial_subj=None, initial_space="subject"):
        """
        Initializes a model manager

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            ren (vtkRenderer) : Renderer in which to draw the models
            initial_subj : Code of initial subject, if None an arbitrary subject will be selected
            initial_space (str) : Initial coordinate system
        """

        conf = braviz.readAndFilter.config_file.get_apps_config()
        lat_var = conf.get_laterality()
        self.lat_idx = braviz.readAndFilter.tabular_data.get_var_idx(
            lat_var[0])
        self.left_handed = lat_var[1]

        self.ren = ren
        if initial_subj is None:
            conf = braviz.readAndFilter.config_file.get_apps_config()
            initial_subj = conf.get_default_subject()
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

        self.reload_models(
            subj=initial_subj, space=initial_space, skip_render=True)

    def __get_laterality(self):
        log = logging.getLogger(__file__)
        try:
            label = braviz.readAndFilter.tabular_data.get_var_value(
                self.lat_idx, self.__current_subject)
        except Exception:
            log.warning(
                "Laterality no found for subject %s, assuming right handed" % self.__current_subject)
            label = 1
        if label is None or (int(label) == self.left_handed):
            return "l"
        else:
            return "r"

    @do_and_render
    def reload_models(self, subj=None, space=None):
        """
        Reloads all models

        Args:
            subj : Code for new subject, if ``None`` the subject is not changed
            space (str) : new coordinate system, if ``None`` the coordinates are not changed
        """
        if subj is not None:
            self.__current_subject = subj
            try:
                self.__available_models = set(
                    self.__reader.get("MODEL", subj, index=True))
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
            # raise Exception("No models found")

    def __addModel(self, model_name):
        # if already exists make visible
        trio = self.__pd_map_act.get(model_name)
        if trio is not None:
            model, mapper, actor = trio
            rl_name = solve_laterality(self.__laterality, model_name)
            if rl_name in self.__available_models:
                model = self.__reader.get(
                    'MODEL', self.__current_subject, name=rl_name, space=self.__current_space)
                mapper.SetInputData(model)
                actor.SetVisibility(1)
                self.__pd_map_act[model_name] = (model, mapper, actor)
            else:
                actor.SetVisibility(0)  # Hide
        else:
            # New model
            rl_name = solve_laterality(self.__laterality, model_name)
            if rl_name in self.__available_models:
                model = self.__reader.get(
                    'MODEL', self.__current_subject, name=rl_name, space=self.__current_space)
                model_mapper = vtk.vtkPolyDataMapper()
                model_actor = vtk.vtkActor()
                model_properties = model_actor.GetProperty()
                if self.__current_color is None:
                    model_color = self.__reader.get(
                        'MODEL', None, name=rl_name, color='T')
                    model_properties.SetColor(list(model_color[0:3]))
                else:
                    model_properties.SetColor(self.__current_color)
                model_properties.SetOpacity(self.__opacity)
                model_properties.LightingOn()
                model_mapper.SetInputData(model)
                model_actor.SetMapper(model_mapper)
                self.ren.AddActor(model_actor)
                self.__pd_map_act[model_name] = (
                    model, model_mapper, model_actor)
                self.__actor_to_model[id(model_actor)] = model_name

                # actor=self.__pd_map_act[model_name][2]
                # model_volume=self.__reader.get('model',self.currSubj,name=model_name,volume=1)
                # add_solid_balloon(balloon_widget, actor, model_name,model_volume)

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
        """
        Sets the currently shown models

        Args:
            new_model_set (set) : An iterable of strings with names of valid models.
        """
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
        """
        Opacity for displaying the models

        Args:
            int_opacity (int) : A number from 0 to 100; where 0 is invisible and 100 is opaque
        """
        float_opacity = int_opacity / 100
        self.__opacity = float_opacity
        for _, _, ac in self.__pd_map_act.itervalues():
            prop = ac.GetProperty()
            prop.SetOpacity(float_opacity)

    def get_opacity(self):
        """
        Gets actual opacity

        Returns:
            An integer from 0 to 100 indicating the current opacity percentage
        """
        return self.__opacity * 100

    @do_and_render
    def set_color(self, float_rgb_color):
        """
        Sets the color for displaying the models

        Args:
            float_rgb_color (tuple) : An rgb value, if ``None`` the freesurfer lookuptable is used
        """
        self.__current_color = float_rgb_color
        for k, (_, _, ac) in self.__pd_map_act.iteritems():
            prop = ac.GetProperty()
            if self.__current_color is None:
                rl_name = solve_laterality(self.__laterality, k)
                model_color = self.__reader.get(
                    'MODEL', None, name=rl_name, color='T')
                prop.SetColor(list(model_color[0:3]))
            else:
                prop.SetColor(self.__current_color)

    def get_scalar_metrics(self, metric_name):
        """
        Get an scalar metric from the current models

        Args:
            metric_name (str): May be

                - ``volume`` : Total volume occupied by all models
                - ``area`` : Sum of superficial areas of all models
                - ``fa_inside`` : Mean value of FA inside the current models
                - ``md_inside`` : Mean value of MD inside the current models
                - ``nfibers`` : Number of fibers that cross any of the current models
                - ``lfibers`` : Mean length of fibers that cross any of the current models
                - ``fa-fibers`` : Mean FA of fibers that cross any of the current models
        Returns:
            Scalar value or ``nan`` if there was an error
        """
        models = self.__active_models_set
        rl_models = [solve_laterality(self.__laterality, m) for m in models]
        try:
            value = structure_metrics.get_mult_struct_metric(self.__reader, rl_models,
                                                             self.__current_subject, metric_name)
        except Exception as e:
            log = logging.getLogger(__name__)
            log.error(e)
            value = float("nan")
            raise
        return value


class TractographyManager(object):

    """
    A manager for tractography data
    """

    def __init__(self, reader, ren, initial_subj=None, initial_space="subject"):
        """
        Initializes the tractography manager

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            ren (vtkRenderer) : Renderer in which to draw the planeow
            initial_subj : Code of initial subject, if None an arbitrary subject will be selected
            initial_space (str) : Initial coordinate system
        """
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
        self.__color_bar_widget = None

    @do_and_render
    def set_subject(self, subj):
        """
        Sets the subject associated to the manager

        Args:
            subj : New subject
        """
        self.__current_subject = subj
        self.__reload_fibers()

    @do_and_render
    def set_current_space(self, space):
        """
        Set current coordinate system

        new_space (str) : new coordinate system, see :meth:`~braviz.readAndFilter.base_reader.BaseReader.get`
        """
        self.__current_space = space
        self.__reload_fibers()

    @do_and_render
    def set_bundle_from_checkpoints(self, checkpoints, through_all):
        """
        Creates a fiber bundle based on a list of structures

        Args:
            checkpoints (list) : Structure model names list
            through_all (bool): If ``True`` the bundle will contain lines that pass though all checkpoints,
                otherwise it will contain lines that pass through any checkpoint
        """
        checkpoints = list(checkpoints)
        self.__ad_hoc_fiber_checks = checkpoints
        self.__ad_hoc_throug_all = through_all
        self.__ad_hoc_visibility = True
        self.__ad_hock_checkpoints = checkpoints
        if self.__ad_hoc_pd_mp_ac is None:
            mapper = vtk.vtkPolyDataMapper()
            actor = vtk.vtkActor()
            self.ren.AddActor(actor)
            actor.SetMapper(mapper)
        else:
            _, mapper, actor = self.__ad_hoc_pd_mp_ac
        if through_all is True:
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
                c = colors[0]
                actor.GetProperty().SetColor(*c)
            self.__set_lut_in_maper(mapper)

            self.__ad_hoc_pd_mp_ac = (poly_data, mapper, actor)
        return

    @do_and_render
    def hide_checkpoints_bundle(self):
        """
        Hide the checkpoints bundle created with :meth:`set_bundle_from_checkpoints`
        """
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
        """
        Add a bundle from the database

        See :mod:`braviz.readAndFilter.bundles_db`

        Args:
            b_id (int) : Bundle id in the database
        """

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
        """
        Get a set of colors for coloring each active bundle in a different color

        Returns:
            A color palette with length equal to the number of active bundles
        """
        # reserve one color for ad_hoc bundles
        number_of_bundles = len(self.__active_db_tracts) + 1

        if self.__bundle_colors is not None and len(self.__bundle_colors) == number_of_bundles:
            return self.__bundle_colors

        colors = sbs.color_palette("Set2", number_of_bundles)
        self.__bundle_colors = colors
        # print colors
        return colors

    @do_and_render
    def set_show_color_bar(self, value):
        """
        Activates a vtk color bar

        Args:
            value (bool) : If ``True`` the bar is activated, if ``False`` it is hidden
        """
        self.__show_color_bar = bool(value)
        self.__set_color_bar()

    def get_show_color_bar(self):
        """
        Status of the color bar

        Returns:
            ``True`` if the color bar is active, ``False`` otherwise
        """
        return self.__show_color_bar

    def get_polydata(self, b_id):
        """
        Gets the polydata object associated to a database bundle.

        The current subject, coordinate system and scalars are maintained

        Args:
            b_id (int) :  Bundle database id

        Returns:
            vtkPolyData from the requested bundle
        """
        poly = self.reader.get("FIBERS", self.__current_subject, space=self.__current_space,
                               db_id=b_id, **self.__current_color_parameters)
        return poly

    @do_and_render
    def hide_database_tract(self, bid):
        """
        Hides a bundle previously added from the database

        Args:
            bid (int) : Bundle database id
        """
        trio = self.__db_tracts.get(bid)
        if trio is None:
            return
        actor = trio[2]
        actor.SetVisibility(0)
        self.__active_db_tracts.remove(bid)

    @do_and_render
    def change_color(self, new_color):
        """
        Sets the coloring scheme for the rendered data.

        Args:
            new_color (str) : New coloring scheme, the following values are accepted

                - ``bundle`` : A different color for each bundle
                - ``orient`` : Color tractography based on local orientation
                - ``rand`` : A different color for each line
                - ``fa_p`` : Use FA values at each point and a lookuptable
                - ``fa_l`` : Use mean fa of each line and a lookuptable
                - ``md_p`` : Use MD values at each point and a lookuptable
                - ``md_l`` : Use mean MD of each line and a lookuptable
                - ``length``: Use length of each line and a lookuptable
                - ``aparc``: Use the *aparc* label at each point and the freesurfer lookuptable
                - ``wmparc``: Use the *wmparc* label at each point and the freesurfer lookuptable

        """
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
            self.__lut = self.reader.get(
                "Fibers", None, scalars=new_color, lut=True)

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

                self.__color_bar_widget = vtk.vtkScalarBarWidget()
                self.__color_bar_widget.SetScalarBarActor(
                    self.__color_bar_actor)
                self.__color_bar_widget.RepositionableOn()
                iren = self.ren.GetRenderWindow().GetInteractor()
                self.__color_bar_widget.SetInteractor(iren)
                self.__color_bar_widget.On()

                rep = self.__color_bar_widget.GetRepresentation()
                coord1 = rep.GetPositionCoordinate()
                coord2 = rep.GetPosition2Coordinate()
                coord1.SetValue(0.85, 0.05)
                coord2.SetValue(0.1, 0.9)

            self.__color_bar_actor.SetVisibility(1)
            self.__color_bar_actor.SetLookupTable(self.__lut)
            # self.__color_bar_actor.SetTitle(scalars[:2].upper())
            self.__color_bar_actor.SetTitle("")
            self.__color_bar_widget.On()

    def __reload_fibers(self):
        # reload ad_hoc
        log = logging.getLogger(__name__)
        if self.__ad_hoc_visibility is True:
            try:
                self.set_bundle_from_checkpoints(
                    self.__ad_hoc_fiber_checks, self.__ad_hoc_throug_all)
            except Exception as e:
                log.exception(e)

        # reload db
        for bid in self.__active_db_tracts:
            try:
                self.add_from_database(bid)
            except Exception as e:
                log.exception(e)

    @do_and_render
    def set_active_db_tracts(self, new_set):
        """
        Selects active database tracts

        Args:
            new_set (list) : List of database ids
        """
        new_set = set(new_set)
        to_hide = self.__active_db_tracts - new_set
        to_add = new_set - self.__active_db_tracts
        errors = 0
        self.__bundle_labels = {b: i+1 for i,b in enumerate(new_set)}

        for i in to_hide:
            self.hide_database_tract(i)
        self.__active_db_tracts = new_set
        for i in to_add:
            try:
                self.add_from_database(i)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.error(e)
                errors += 1

        if errors > 0:
            log = logging.getLogger(__name__)
            log.warning("Couldn't load all tracts")
        if self.__current_color == "bundle":
            # we need to refresh all active bundles to get colors right
            self.__reload_fibers()

    @do_and_render
    def set_opacity(self, float_opacity):
        """
        Sets opacity for the displayed bundles

        Args:
            float_opacity (float) : From 0 to 1; where 0 is transparent and 1 is opaque
        """
        self.__opacity = float_opacity
        self.__reload_fibers()

    def get_scalar_from_db(self, scalar, bid):
        """
        Gets an scalar metric from an active database bundle

        Args:
            scalar (str) : Scalar metric, available options are:

                - ``number`` : Number of lines
                - ``mean_length`` : Mean length of lines
                - ``mean_fa`` : Mean FA of the bundle
                - ``mean_md`` : Mean MD of the bundle

            bid (int) :  Database id

        Returns:
            Scalar value or ``nan`` if there was an error
        """
        if bid in self.__active_db_tracts:
            try:
                if scalar in ("number", "mean_length"):
                    pd = self.__db_tracts[bid][0]
                    return structure_metrics.get_scalar_from_fiber_ploydata(pd, scalar)
                elif scalar == "mean_fa":
                    fiber = self.reader.get("FIBERS", self.__current_subject, space=self.__current_space,
                                            db_id=bid, color=None, scalars="fa_p")
                    n = structure_metrics.get_scalar_from_fiber_ploydata(
                        fiber, "mean_color")
                    return n
                elif scalar == "mean_md":
                    fiber = self.reader.get("FIBERS", self.__current_subject, space=self.__current_space,
                                            db_id=bid, color=None, scalars="md_p")
                    n = structure_metrics.get_scalar_from_fiber_ploydata(
                        fiber, "mean_color")
                    return n
            except Exception as e:
                log = logging.getLogger(__name__)
                log.exception(e)

        return float("nan")

    def get_scalar_from_structs(self, scalar):
        """
        Gets an scalar metric from the active checkpoints bundle

        see :meth:`set_bundle_from_checkpoints`

        Args:
            scalar (str) : Scalar metric, available options are:

                - ``number`` : Number of lines
                - ``mean_length`` : Mean length of lines
                - ``mean_fa`` : Mean FA of the bundle
                - ``mean_md`` : Mean MD of the bundle

        Returns:
            Scalar value or ``nan`` if there was an error
        """
        if self.__ad_hoc_visibility is False:
            return float("nan")
        try:
            if scalar in ("number", "mean_length"):
                fiber = self.__ad_hoc_pd_mp_ac[0]
                n = structure_metrics.get_scalar_from_fiber_ploydata(
                    fiber, scalar)
                return n
            elif scalar == "mean_fa":
                operation = "and" if self.__ad_hoc_throug_all else "or"
                fiber = self.reader.get("Fibers", self.__current_subject, waypoint=self.__ad_hock_checkpoints,
                                        operation=operation, space=self.__current_space, color=None, scalars="fa_p")
                n = structure_metrics.get_scalar_from_fiber_ploydata(
                    fiber, "mean_color")
                return n
            elif scalar == "mean_md":
                operation = "and" if self.__ad_hoc_throug_all else "or"
                fiber = self.reader.get("Fibers", self.__current_subject, waypoint=self.__ad_hock_checkpoints,
                                        operation=operation, space=self.__current_space, color=None, scalars="md_p")
                n = structure_metrics.get_scalar_from_fiber_ploydata(
                    fiber, "mean_color")
                return n
        except Exception:
            return float("nan")
        return float("nan")


class TraculaManager(object):

    """
    A data manager for Tracula bundles
    """

    def __init__(self, reader, ren, initial_subj=None, initial_space="subject"):
        """
        Initializes the manager

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            ren (vtkRenderer) : Renderer in which to draw the models
            initial_subj : Code of initial subject, if None an arbitrary subject will be selected
            initial_space (str) : Initial coordinate system
        """
        self.ren = ren
        if initial_subj is None:
            initial_subj = reader.get("ids", None)[0]
        self.__active_bundles_set = set()
        self.__pd_map_act = dict()
        self.__current_subject = initial_subj
        self.__reader = reader
        self.__current_space = initial_space
        self.__actor_to_model = {}  # for picking

        # visual attributes
        self.__opacity = 1

        self.reload_bundles(
            subj=initial_subj, space=initial_space, skip_render=True)

    @do_and_render
    def reload_bundles(self, subj, space):
        """
        Reloads all bundles

        Args:
            subj : Code for new subject, if ``None`` the subject is not changed
            space (str) : new coordinate system, if ``None`` the coordinates are not changed
        """
        self.__current_subject = subj
        self.__current_space = space
        log = logging.getLogger(__name__)
        for b in self.__active_bundles_set:
            try:
                self.__load_bundle(b)
            except Exception as e:
                log.exception(e)
                self.__hide_bundle(b)

    @do_and_render
    def set_bundles(self, bundle_names):
        """
        Sets the currently shown bundles

        Args:
            bundle_names (set) : An iterable of strings with names of tracula bundles.
        """
        wanted_bundles = frozenset(bundle_names)
        to_add = wanted_bundles - self.__active_bundles_set
        to_hide = self.__active_bundles_set - wanted_bundles

        for b in to_add:
            self.__load_bundle(b)

        for b in to_hide:
            self.__hide_bundle(b)

        self.__active_bundles_set = wanted_bundles

    @do_and_render
    def set_opacity(self, int_opacity):
        """
        Opacity for displaying the models

        Args:
            int_opacity (int) : A number from 0 to 100; where 0 is invisible and 100 is opaque
        """
        for b in self.__active_bundles_set:
            _, _, ac = self.__pd_map_act[b]
            ac.GetProperty().SetOpacity(int_opacity / 100)

    def __load_bundle(self, bundle_name):
        trio = self.__pd_map_act.get(bundle_name)
        if trio is None:
            color = self.__reader.get(
                "TRACULA", self.__current_subject, name=bundle_name, color=True)
            mapper = vtk.vtkPolyDataMapper()
            mapper.ScalarVisibilityOff()
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(color)
            self.ren.AddActor(actor)
        else:
            pd, mapper, actor = trio
        try:
            pd = self.__reader.get(
                "TRACULA", self.__current_subject, name=bundle_name, space=self.__current_space)
        except Exception as e:
            log = logging.getLogger(__name__)
            log.exception(e)
            actor.SetVisibility(0)
            pd = None
        else:
            mapper.SetInputData(pd)
            actor.SetVisibility(1)
        self.__pd_map_act[bundle_name] = (pd, mapper, actor)

    def __hide_bundle(self, bundle_name):
        trio = self.__pd_map_act.get(bundle_name)
        if trio is None:
            return
        ac = trio[2]
        ac.SetVisibility(0)

    @property
    def active_bundles(self):
        """
        Gets the set of active bundles

        Returns:
            A frozenSet of currently active bundles
        """
        return self.__active_bundles_set


class SurfaceManager(object):

    """
    A data manager for freesurfer sufaces parcelations
    """

    def __init__(self, reader, ren, iren, initial_subj=None, initial_space="subject", picker=None,
                 persistent_cone=False):
        """
        Initializes the manager

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            ren (vtkRenderer) : Renderer in which to draw the plane
            iren (vtkRenderWindowInteractor) : The render window interactor of the output window
            initial_subj : Code of initial subject, if None an arbitrary subject will be selected
            initial_space (str) : Initial coordinate system
            picker (vtkPicker) : A vtkPicker may be used to pick on several objects. If None a new picker is created
            persistent_cone (bool) : If ``True`` the cone used for picking will not disappear at the end of
                the operation
        """
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
        if nx < 0.0:
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
        self.__picking_events["MouseMoveEvent"] = iren.AddObserver(
            vtk.vtkCommand.MouseMoveEvent, picking, 10)

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

        try:
            surf = self.reader.get("surf", self.__subject, name=self.__current_surface, hemi=h,
                                   scalars=self.__current_scalars,
                                   space=self.__current_space)
        except Exception as e:
            log = logging.getLogger(__name__)
            log.exception(e)
            actor.SetVisibility(0)
            surf = None
        else:
            mapper.SetInputData(surf)
            actor.SetVisibility(1)
            actor.GetProperty().SetOpacity(self.__opacity / 100)
            self.__locators[h].SetDataSet(surf)

        trio = surf, mapper, actor
        self.__surf_trios[h] = trio

    def __update_lut(self):
        ref = self.__subject
        lut = self.reader.get(
            "SURF_SCALAR", ref, scalars=self.__current_scalars, lut=True, hemi="l")
        for trio in self.__surf_trios.itervalues():
            mapper = trio[1]
            mapper.SetLookupTable(lut)
        self.__lut = lut
        if (self.__color_bar_actor is not None) and self.__active_color_bar:
            self.__color_bar_actor.SetLookupTable(lut)

    def __update_both(self):
        self.__update_hemisphere("r")
        self.__update_hemisphere("l")

    @do_and_render
    def set_hemispheres(self, left=None, right=None):
        """
        Sets the active hemisphers

        Args:
            left (bool) : If ``True`` the left hemisphere is activated, if ``False`` it is deactivated,
                if ``None`` it is unchanged
            right (bool) : If ``True`` the right hemisphere is activated, if ``False`` it is deactivated,
                if ``None`` it is unchanged
        """

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
        """
        Sets the current scalars to use for the surfaces

        Args:
            scalars (str) : See :meth:`braviz.readAndFilter.base_reader.BaseReader.get` for options
        """

        if scalars == self.__current_scalars:
            return
        self.__current_scalars = scalars
        self.__update_both()
        self.__update_lut()

    @do_and_render
    def set_surface(self, surface):
        """
        Sets the current surface to display at both hemispheres

        Args:
            surface (str) : See :meth:`braviz.readAndFilter.base_reader.BaseReader.get` for options
        """
        surface = surface.lower()
        if surface == self.__current_surface:
            return
        self.__current_surface = surface
        self.__update_both()

    @do_and_render
    def show_color_bar(self, show):
        """
        Activates a vtk color bar

        Args:
            value (bool) : If ``True`` the bar is activated, if ``False`` it is hidden
        """
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
        """
        Change subject associated to the manager

        Args:
            new_subject : Id of new subject
        """
        self.__subject = new_subject
        self.__update_both()

    @do_and_render
    def set_space(self, new_space):
        """
        Change current coordinate system

        new_space (str) : new coordinate system, see :meth:`~braviz.readAndFilter.base_reader.BaseReader.get`
        """
        self.__current_space = new_space
        self.__update_both()

    @do_and_render
    def set_opacity(self, int_opacity):
        """
        Opacity for displaying the surfaces

        Args:
            int_opacity (int) : A number from 0 to 100; where 0 is invisible and 100 is opaque
        """
        if int_opacity == self.__opacity:
            return
        self.__opacity = int_opacity
        for trio in self.__surf_trios.itervalues():
            ac = trio[2]
            opac = self.__opacity / 100
            ac.GetProperty().SetOpacity(opac)

    def hide_cone(self):
        """
        Hides the picking cone
        """
        self.__cone_trio[2].SetVisibility(0)
        self.__picking_text.SetVisibility(0)

    def get_last_picked_pos(self):
        """
        Coordinates of the last picked position

        Returns:
            A tuple with the coordinates of the last pickedposition
        """
        return self.__last_picked_pos

    @property
    def pick_cone_actor(self):
        """
        Access to the pick cone actor
        """
        return self.__cone_trio[2]


class OrthogonalPlanesViewer(object):

    """
    A viewer with three orthogonal planes

    It provides access to

        - Images
        - Surfaces
        - A sphere

    """

    def __init__(self, render_window_interactor, reader, widget):
        """
        Initializes the viewer

        Args:
            render_window_interactor (vtkRenderWindowInteractor) : The intaractor that will be used with this viewer
            widget (QObject) : Must implement *slice_change_handle* and *window_level_change_handle*

        """
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
        self.axes = OrientationAxes()
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
        self.__current_space = "subject"
        self.__current_class = None
        self.__current_name = None

        # internal data
        self.__cursor = AdditionalCursors(self.ren)

        self.__x_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__y_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__z_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__image_planes = (
            self.__x_image_manager, self.__y_image_manager, self.__z_image_manager)
        self.x_image.change_image_orientation(0, skip_render=True)
        self.y_image.change_image_orientation(1, skip_render=True)
        self.z_image.change_image_orientation(2, skip_render=True)
        self.hide_image(skip_render=True)

        self.__sphere = SphereProp(self.ren)
        self.__cortex = SurfaceManager(self.reader, self.ren, self.iren, self.__current_subject, self.__current_space,
                                       picker=self.picker, persistent_cone=True)

        self.__active_cursor_plane = True

    def finish_initializing(self):
        """
        Finish viewer initialization, only call this after calling "show" on the widget or its parents
        """
        self._link_window_level()
        self._connect_cursors()
        self.ren.ResetCameraClippingRange()
        self.ren.ResetCamera()

    def _link_window_level(self):
        """
        Link window and level of all planes

        call after initializing the planes
        """
        if self.__current_class == "IMAGE":
            self.y_image.image_plane_widget.SetLookupTable(
                self.x_image.image_plane_widget.GetLookupTable())
            self.z_image.image_plane_widget.SetLookupTable(
                self.x_image.image_plane_widget.GetLookupTable())

    def _connect_cursors(self):
        """
        Connects the additional cursors
        """
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

        self.x_image.image_plane_widget.AddObserver(
            self.x_image.image_plane_widget.cursor_change_event, draw_cursor2)
        self.y_image.image_plane_widget.AddObserver(
            self.y_image.image_plane_widget.cursor_change_event, draw_cursor2)
        self.z_image.image_plane_widget.AddObserver(
            self.z_image.image_plane_widget.cursor_change_event, draw_cursor2)

        self.x_image.image_plane_widget.AddObserver(
            self.x_image.image_plane_widget.slice_change_event, slice_movement)
        self.y_image.image_plane_widget.AddObserver(
            self.y_image.image_plane_widget.slice_change_event, slice_movement)
        self.z_image.image_plane_widget.AddObserver(
            self.z_image.image_plane_widget.slice_change_event, slice_movement)

        def change_cursor_to_cone(caller, event):
            self.__active_cursor_plane = False
            self.__cursor.hide()

        self.cortex.pick_cone_actor.AddObserver(
            self.cortex.picking_event, change_cursor_to_cone)

    @do_and_render
    def show_image(self):
        """
        Shows all planes
        """
        for im in self.__image_planes:
            im.show_image(skip_render=True)

    @do_and_render
    def hide_image(self):
        """
        Hide all planes
        """
        for im in self.__image_planes:
            im.hide_image(skip_render=True)

    @do_and_render
    def change_subject(self, subj):
        """
        Changes the subject associated to the viewer

        Args:
            new_subject : new subject id
        """
        ex = None
        for im in self.__image_planes:
            try:
                im.change_subject(subj, skip_render=True, force=True)
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
        self._link_window_level()

    @do_and_render
    def change_image_modality(self, image_class, image_name, contrast=1):
        """
        Change image modality in all planes

        See :meth:`ImageManager.change_image_modality`


        Args:
            image_class (str): New image class (IMAGE, LABELS or FMRI)
            image_name (str): New image name, for fMRI enter the paradigm here
            contrast (int): If modality is fMRI the index of the contrast
        """
        log = logging.getLogger(__name__)
        if image_class is not None:
            image_class = image_class.upper()
        if image_name is not None:
            image_name = image_name.upper()

        for im in self.__image_planes:
            try:
                im.change_image_modality(
                    image_class, image_name, skip_render=True, contrast=contrast)
            except Exception as e:
                log.exception(e)
        self.__current_class = image_class
        self.__current_name = image_name
        self.__cursor.set_image(self.x_image.image_plane_widget.GetInput())
        self._link_window_level()

    def get_number_of_slices(self):
        """
        Get number of slices in each plane

        Returns:
            A tuple with the image dimension
        """
        n_slices = self.x_image.image_plane_widget.GetInput().GetDimensions()
        return n_slices

    def get_current_slice(self):
        """
        Get current slices of all planes

        Returns:
            A tuple with the current slice of each plane (x,y,z)
        """
        return (self.x_image.get_current_image_slice(),
                self.y_image.get_current_image_slice(),
                self.z_image.get_current_image_slice(),)

    def get_camera_parameters(self):
        """
        Gets current camera parameters

        Returns:
            focal_point, position, view_up
        """
        cam1 = self.ren.GetActiveCamera()
        fp = cam1.GetFocalPoint()
        pos = cam1.GetPosition()
        vu = cam1.GetViewUp()
        return fp, pos, vu

    def set_camera(self, focal_point, position, view_up):
        """
        Sets the camera position

        Args:
            focal_point (tuple) : Focal point
            position (tuple) : Camera position
            view_up (tuple) : View up vector

        """
        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal_point)
        cam1.SetPosition(position)
        cam1.SetViewUp(view_up)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()

    @property
    def image_planes(self):
        """
        Access to the image planes array
        """
        return self.__image_planes

    @property
    def x_image(self):
        """
        Access to the image manager perpendicular to x
        """
        return self.__x_image_manager

    @property
    def y_image(self):
        """
        Access to the image manager perpendicular to y
        """
        return self.__y_image_manager

    @property
    def z_image(self):
        """
        Access to the image manager perpendicular to z
        """
        return self.__z_image_manager

    @property
    def sphere(self):
        """
        Access to the sphere
        """
        return self.__sphere

    @property
    def cortex(self):
        """
        Access to the surface manager
        """
        return self.__cortex

    def current_position(self):
        """
        Last picked position, either on the planes or on the surface

        Returns:
            Coordinates of the last picked position
        """
        if self.__active_cursor_plane:
            return self.__cursor.get_position()
        else:
            return self.cortex.get_last_picked_pos()

    @do_and_render
    def change_space(self, new_space):
        """
        Changes the current coordinate system

        Args:
            new_space (str) : New coordinate system
        """
        for im in self.image_planes:
            im.change_space(new_space, skip_render=True)
        self.cortex.set_space(new_space, skip_render=True)
        self.__current_space = new_space
        self.__cursor.set_image(self.x_image.image_plane_widget.GetInput())
        self.iren.Render()


class MeasurerViewer(object):

    """
    A viewer that allows the user to measure the distance between two points on images using a vtkMeasureWidget
    """
    camera_positions = {
        0: ((-5.5, -5.5, 4.5), (535, -5.5, 4.5), (0, 0, 1)),  # SAGITAL
        1: ((-5.5, -8, 2.8), (-5.5, 530, 2.8), (1, 0, 0)),  # CORONAL
        2: ((-3.5, 0, 10), (-3.5, 0, 550), (0, 1, 0)),  # AXIAL
    }

    def __init__(self, render_window_interactor, reader, widget):
        """
        Initializes the viewer

        Args:
            render_window_interactor (vtkRenderWindowInteractor) : The intaractor that will be used with this viewer
            widget (QObject) : Must implement *slice_change_handle*, *window_level_change_handle*
                and *distance_changed_handle*

        """
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
        self.axes = OrientationAxes()
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
        self.set_measure_axis("axial", skip_render=True)
        # state
        self.__current_subject = None
        self.__current_space = "talairach"
        self.__current_modality = None
        self.__current_class = None

        # internal data

        self.__x_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__y_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__z_image_manager = ImageManager(self.reader, self.ren, widget=widget, interactor=self.iren,
                                              picker=self.picker)
        self.__image_planes = (
            self.__x_image_manager, self.__y_image_manager, self.__z_image_manager)
        self.x_image.change_image_orientation(0, skip_render=True)
        self.y_image.change_image_orientation(1, skip_render=True)
        self.z_image.change_image_orientation(2, skip_render=True)
        # for pw in self.__image_planes:
        #    pw.image_plane_widget.InteractionOff()
        self.hide_image(skip_render=True)

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

        self.obs_id, self.obs_id2, self.obs_id3 = None, None, None

    def _restrict_points_to_plane(self, caller, event):
        """
        Restrict the measure widget points to the plane surfaces
        """
        modifiers = QApplication.keyboardModifiers()
        straight = False
        if QtCore.Qt.ControlModifier & modifiers:
            straight = True
        ax = self.__measure_axis
        slice_coords = self.image_planes[
            ax].image_plane_widget.GetSlicePosition()
        plane_point = np.zeros(3)
        plane_point[ax] = slice_coords
        pa1, pa2 = self.__pax1, self.__pax2

        representation = caller.GetRepresentation()
        r1 = representation.GetPoint1Representation()
        r2 = representation.GetPoint2Representation()
        r1i = r1.GetInteractionState()
        r2i = r2.GetInteractionState()
        camera = self.ren.GetActiveCamera()
        view_vec = np.array(camera.GetDirectionOfProjection())
        if r1i > 0 or not self.__placed:
            p1 = np.zeros(3)
            representation.GetPoint1WorldPosition(p1)
            if np.dot(view_vec, p1) != 0:
                t = (slice_coords - p1[ax]) / view_vec[ax]
                p1 = p1 + view_vec * t
            else:
                p1[ax] = slice_coords

            if straight and self.__placed:
                ref = np.zeros(3)
                representation.GetPoint2WorldPosition(ref)
                dif = np.abs(p1 - ref)
                if dif[pa1] > dif[pa2]:
                    p1[pa2] = ref[pa2]
                else:
                    p1[pa1] = ref[pa1]
            representation.SetPoint1WorldPosition(p1)
            self.__placed = True
        else:
            p2 = np.zeros(3)
            representation.GetPoint2WorldPosition(p2)
            if np.dot(view_vec, p2) != 0:
                t = (slice_coords - p2[ax]) / view_vec[ax]
                p2 = p2 + view_vec * t
            else:
                p2[ax] = slice_coords
            if straight:
                ref = np.zeros(3)
                representation.GetPoint1WorldPosition(ref)
                dif = np.abs(p2 - ref)
                if dif[pa1] > dif[pa2]:
                    p2[pa2] = ref[pa2]
                else:
                    p2[pa1] = ref[pa1]
            representation.SetPoint2WorldPosition(p2)

    def finish_initializing(self):
        """
        Finish viewer initialization, only call this after calling "show" on the widget or its parents
        """
        self.measure_widget.SetPriority(
            self.x_image.image_plane_widget.GetPriority() + 1)
        self.obs_id = self.measure_widget.AddObserver(
            vtk.vtkCommand.PlacePointEvent, self._restrict_points_to_plane)
        self.obs_id2 = self.measure_widget.AddObserver(
            vtk.vtkCommand.InteractionEvent, self._restrict_points_to_plane)
        self.obs_id3 = self.measure_widget.AddObserver(vtk.vtkCommand.InteractionEvent,
                                                       self.emit_distance_changed_signal)
        self._link_window_level()
        self.ren.ResetCameraClippingRange()
        self.ren.ResetCamera()
        self.measure_widget.On()

    def _link_window_level(self):
        """
        Link window and level of all planes

        call after initializing the planes
        """
        if self.__current_class == "IMAGE":
            self.y_image.image_plane_widget.SetLookupTable(
                self.x_image.image_plane_widget.GetLookupTable())
            self.z_image.image_plane_widget.SetLookupTable(
                self.x_image.image_plane_widget.GetLookupTable())

        def slice_movement(caller, event):
            if caller == self.x_image.image_plane_widget:
                axis = 0
            elif caller == self.y_image.image_plane_widget:
                axis = 1
            else:
                axis = 2
            sl = self.image_planes[axis].get_current_image_slice()
            if axis == self.__measure_axis and self.__placed:
                c = self.image_planes[
                    axis].image_plane_widget.GetSlicePosition()
                p1, p2 = np.zeros(3), np.zeros(3)
                self.measure_repr.GetPoint1WorldPosition(p1)
                self.measure_repr.GetPoint2WorldPosition(p2)
                p1[axis] = c
                p2[axis] = c
                self.measure_repr.SetPoint1WorldPosition(p1)
                self.measure_repr.SetPoint2WorldPosition(p2)
                # self.ren_win.Render()

        self.x_image.image_plane_widget.AddObserver(
            self.x_image.image_plane_widget.slice_change_event, slice_movement)
        self.y_image.image_plane_widget.AddObserver(
            self.y_image.image_plane_widget.slice_change_event, slice_movement)
        self.z_image.image_plane_widget.AddObserver(
            self.z_image.image_plane_widget.slice_change_event, slice_movement)

    @do_and_render
    def set_measure_axis(self, axis_str):
        """
        Set the measure plane to be perpendicular to the axis

        Args:
            axis_str (str) : "axial", "sagital" or "coronal"
        """
        axis = _axis_dict[axis_str.lower()]
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
        self.reset_camera(skip_render=True)

    @do_and_render
    def set_slice_coords(self, coords):
        """
        Move the measure plane perpendicularly

        Args:
            coords (float) : New position across the axis perpendicular to the measure plane
        """
        pw = self.image_planes[self.__measure_axis].image_plane_widget
        pw.SetSlicePosition(coords)
        pw.InvokeEvent(pw.slice_change_event)

    def emit_distance_changed_signal(self, caller, event):
        """
        Emit a Qt Signal through the associated widget
        """
        d = self.distance
        self.__widget.distance_changed_handle(d)

    @do_and_render
    def show_image(self):
        """
        Shows all planes
        """
        for im in self.__image_planes:
            im.show_image(skip_render=True)

    @do_and_render
    def hide_image(self):
        """
        Hide all planes
        """
        for im in self.__image_planes:
            im.hide_image(skip_render=True)

    @do_and_render
    def change_subject(self, subj):
        """
        Changes the subject associated to the viewer

        Args:
            new_subject : new subject id
        """
        log = logging.getLogger(__name__)
        for im in self.__image_planes:
            try:
                im.change_subject(subj, skip_render=True)
            except Exception as e:
                log.exception(e)
        self._link_window_level()

    @do_and_render
    def change_image_modality(self, image_class, mod, contrast=None):
        """
        Change image modality in all planes

        See :meth:`ImageManager.change_image_modality`


        Args:
            image_class (str): New image class, must be FMRI, IMAGE, LABEL or DTI
            mod (str): New modality name, for fMRI enter the paradigm here
            contrast (int): If modality is fMRI the index of the contrast
        """
        if mod is not None:
            mod = mod.upper()

        if image_class is not None:
            image_class = image_class.upper()

        for im in self.__image_planes:
            im.change_image_modality(image_class, mod, skip_render=True, contrast=contrast)
        self.__current_modality = mod
        self.__current_class = image_class
        self._link_window_level()

    def get_number_of_slices(self):
        """
        Get number of slices in each plane

        Returns:
            A tuple with the image dimension
        """
        n_slices = self.x_image.image_plane_widget.GetInput().GetDimensions()
        return n_slices

    def get_current_slice(self):
        """
        Get current slices of all planes

        Returns:
            A tuple with the current slice of each plane (x,y,z)
        """
        return (self.x_image.get_current_image_slice(),
                self.y_image.get_current_image_slice(),
                self.z_image.get_current_image_slice(),)

    def get_camera_parameters(self):
        """
        Gets current camera parameters

        Returns:
            focal_point, position, view_up
        """
        cam1 = self.ren.GetActiveCamera()
        fp = cam1.GetFocalPoint()
        pos = cam1.GetPosition()
        vu = cam1.GetViewUp()
        return fp, pos, vu

    @do_and_render
    def reset_camera(self):
        """
        Resets camera to the initial position
        """
        fp, pos, vu = self.camera_positions[self.__measure_axis]
        self.set_camera(fp, pos, vu, skip_render=True)

    @do_and_render
    def set_camera(self, focal_point, position, view_up):
        """
        Sets the camera position

        Args:
            focal_point (tuple) : Focal point
            position (tuple) : Camera position
            view_up (tuple) : View up vector

        """
        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal_point)
        cam1.SetPosition(position)
        cam1.SetViewUp(view_up)

        self.ren.ResetCameraClippingRange()

    @property
    def image_planes(self):
        """
        Access to the image planes array
        """
        return self.__image_planes

    @property
    def x_image(self):
        """
        Access to the image manager perpendicular to x
        """
        return self.__x_image_manager

    @property
    def y_image(self):
        """
        Access to the image manager perpendicular to y
        """
        return self.__y_image_manager

    @property
    def z_image(self):
        """
        Access to the image manager perpendicular to z
        """
        return self.__z_image_manager

    @do_and_render
    def change_space(self, new_space):
        """
        Changes the current coordinate system

        Args:
            new_space (str) : New coordinate system
        """
        for im in self.image_planes:
            im.change_space(new_space, skip_render=True)
        self.__current_space = new_space
        self.iren.Render()

    @do_and_render
    def reset_measure(self):
        """
        Reset the measure widget, remove both points from the scene
        """
        self.measure_widget.Off()
        self.measure_widget.SetWidgetStateToStart()
        self.measure_widget.On()
        self.__placed = False
        self.__widget.distance_changed_handle(np.nan)

    @property
    def distance(self):
        """
        Current distance measured by the measure widget
        """
        if not self.__placed:
            return np.nan
        else:
            return self.measure_repr.GetDistance()

    @property
    def point1(self):
        """
        Get coordinates of first measure point
        """
        if self.__placed:
            p1 = np.zeros(3)
            self.measure_repr.GetPoint1WorldPosition(p1)
            return p1
        else:
            return None

    @property
    def point2(self):
        """
        Get coordinates of second measure point
        """
        if self.__placed:
            p2 = np.zeros(3)
            self.measure_repr.GetPoint2WorldPosition(p2)
            return p2
        else:
            return None

    @do_and_render
    def set_points(self, p1, p2):
        """
        Set coordinates for both points

        Args:
            p1 (tuple) : First point coordinates
            p2 (tuple) : Second point coordinates
        """
        self.measure_repr.SetPoint1WorldPosition(p1)
        self.measure_repr.SetPoint2WorldPosition(p2)
        if not self.__placed:
            self.measure_widget.SetWidgetStateToManipulate()
            acs = vtk.vtkPropCollection()
            self.measure_repr.GetActors(acs)
            self.measure_repr.VisibilityOn()

            self.__placed = True

    @do_and_render
    def set_measure_color(self, r, g, b):
        """
        Set color of the measure widget

        Args:
            r (int) : red
            g (int) : green
            b (int) : blue
        """
        r, g, b = r / 255, g / 255, b / 255
        self.measure_repr.GetLineProperty().SetColor(r, g, b)
        self.measure_repr.GetGlyphActor().GetProperty().SetColor(r, g, b)


class AdditionalCursors(object):

    """
    An additional set of cursors to use when those included in vtkImageWidget are not flexible enough
    """

    def __init__(self, ren):
        """
        Initializes the cursors

        Args:
            ren (vtkRenderer) : Renderer into which the cursors will be drawn
        """
        self.__cursors = cursors()
        self.__cursors.SetVisibility(0)
        self.__image = None
        self.__coords = None
        self.__axis = None
        ren.AddActor(self.__cursors)

    def set_image(self, img):
        """
        Image to use as reference for the cursors

        Args:
            img (vtkImageData) : The cursors will stick to this image
        """
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
        """
        Current position of the cursors

        Returns:
            Coordinates of the last picked position (in mm)
        """
        if self.__coords is None:
            return None
        pos = np.array(self.__coords)
        org = np.array(self.__image.GetOrigin())
        sp = np.array(self.__image.GetSpacing())
        return pos * sp + org

    def get_coords(self):
        """
        Voxel coordinates of last picked position

        Returns:
            Coordinates of last picked position in voxels
        """
        return self.__coords

    def set_axis_coords(self, axis=None, coords=None):
        """
        Set position of the cursors

        Args:
            axis (int) : Axis perpendicular to the cursor, 0 for x, 1 for y and 2 for z
            coords (tuple) : Position of the cursor in voxels
        """
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
        """
        Hide cursor
        """
        self.__cursors.SetVisibility(0)


class SphereProp(object):

    """
    An sphere that can be added to any viewer to represent regions of interest
    """

    def __init__(self, ren):
        """
        Initializes the sphere prop

        Args:
            ren (vtkRenderer) : Renderer that will draw the sphere
        """
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
        self.__ren = ren
        ren.AddActor(self.__actor)

    def set_center(self, ctr):
        """
        Set the center of the sphere

        Args:
            ctr (tuple) : center
        """
        self.__source.SetCenter(*ctr)
        self.__center = ctr

    def set_radius(self, r):
        """
        Set the radius of the sphere

        Args:
            r (float) : Sphere radius
        """
        self.__source.SetRadius(r)
        self.__radius = r

    @property
    def radius(self):
        return self.__radius

    @property
    def center(self):
        return tuple(self.__center)

    @property
    def visible(self):
        return self.__actor.GetVisibility()

    def set_repr(self, rep):
        """
        Set representation of the sphere

        Args:
            rep (str): Options are ``"wireframe"`` or ``"surface"``
        """
        if rep.startswith("w"):
            self.__actor.GetProperty().SetRepresentationToWireframe()
        else:
            self.__actor.GetProperty().SetRepresentationToSurface()

    def hide(self):
        """
        Hide the sphere
        """
        self.__actor.SetVisibility(0)

    def show(self):
        """
        Show the sphere
        """
        self.__actor.SetVisibility(1)

    def set_opacity(self, opac_int):
        """
        Opacity of the sphere

        Args:
            opac_int (int) : A number from 0 to 100; where 0 is invisible and 100 is opaque
        """
        opac = opac_int / 100.0
        self.__actor.GetProperty().SetOpacity(opac)

    def set_color(self, r, g, b):
        """
        Set color of the measure widget

        Args:
            r (int) : red
            g (int) : green
            b (int) : blue
        """
        r, g, b = map(lambda x: x / 255.0, (r, g, b))
        self.__actor.GetProperty().SetColor(r, g, b)

    def remove_from_renderer(self):
        """
        Remove the sphere from the renderer
        """
        self.__ren.RemoveActor(self.__actor)


class QMeasurerWidget(QFrame):

    """
    A Qt Widget that wraps :class:`MeasurerViewer` and lets it connect naturally to Qt Applications
    """
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)
    distance_changed = pyqtSignal(float)

    def __init__(self, reader, parent):
        """
        Creates the measurer widget

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            parent (QObject) : Parent
        """
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        filt = FilterArrows(self, (QtCore.Qt.Key_C,))
        filt.key_pressed.connect(lambda e: self.event(e))
        self.__qwindow_interactor.installEventFilter(filt)
        self.__reader = reader
        self.__vtk_viewer = MeasurerViewer(
            self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        # self.subject_viewer.ren_win.Render()

        # self.__qwindow_interactor.show()

    def initialize_widget(self):
        """
        Call this function **after** calling show on the widget or a parent
        """
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        # self.__subject_viewer.show_cone()

    @property
    def orthogonal_viewer(self):
        """
        Access to the underlying class:`MeasurerViewer`
        """
        return self.__vtk_viewer

    def slice_change_handle(self, new_slice):
        """
        Emits a signal when the current image slice is changed on the vtkWidget
        """
        self.slice_changed.emit(new_slice)
        # print new_slice

    def window_level_change_handle(self, window, level):
        """
        Emits a signal when window or level are changed by interacting in the vtkWidget
        """
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)

    def distance_changed_handle(self, distance):
        """
        Emits a signal the measured distance is changed in the vtkWidget
        """
        self.distance_changed.emit(distance)


class QOrthogonalPlanesWidget(QFrame):

    """
    A Qt Widget that wraps :class:`OrthogonalPlanesViewer` and lets it connect naturally to Qt Applications
    """
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)

    def __init__(self, reader, parent):
        """
        Creates the orthogonal planes widget

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            parent (QObject) : Parent
        """
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        filt = FilterArrows(
            self, (QtCore.Qt.Key_C, QtCore.Qt.Key_O, QtCore.Qt.Key_S))
        filt.key_pressed.connect(lambda e: self.event(e))
        self.__qwindow_interactor.installEventFilter(filt)
        self.__reader = reader
        self.__vtk_viewer = OrthogonalPlanesViewer(
            self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        # self.subject_viewer.ren_win.Render()

        # self.__qwindow_interactor.show()

    def initialize_widget(self):
        """
        Call this function **after** calling show on the widget or a parent
        """
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        # self.__subject_viewer.show_cone()

    @property
    def orthogonal_viewer(self):
        """
        Access to the underlying class:`OrthogonalPlanesViewer`
        """
        return self.__vtk_viewer

    def slice_change_handle(self, new_slice):
        """
        Emits a signal when the current image slice is changed on the vtkWidget
        """
        self.slice_changed.emit(new_slice)
        # print new_slice

    def window_level_change_handle(self, window, level):
        """
        Emits a signal when window or level are changed by interacting in the vtkWidget
        """
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)


class fMRI_viewer(object):

    """
    A viewer for visualizaing fMRI data. It displays

        - Images
        - fMRI contours

    """

    def __init__(self, render_window_interactor, reader, widget):
        """
        Creates the fMRI viewer

        Args:
            render_window_interactor (vtkRenderWindowInteractor) : The intaractor that will be used with this viewer
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            widget (QObject) : Must implement *slice_change_handle*, *window_level_change_handle*
                and *cursor_move_handler*

        """
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
        self.axes = OrientationAxes()
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
        # reset camera and render
        self.reset_camera(0, skip_render=True)
        # widget, signal handling
        self.__widget = widget

    def change_orientation(self, orientation_index):
        """
        Changes the orientation of the Image Plane Widget

        Args:
            orientation_index (int) : 0 for x, 1 for y and 2 for z
        """
        # find cursor position
        pos = self.__cursor.get_coords()
        self.image.change_image_orientation(orientation_index)
        if pos is None:
            new_slice = self.image.get_number_of_image_slices() // 2
        else:
            new_slice = int(pos[orientation_index])
            self.__cursor.set_axis_coords(orientation_index, pos)
        self.image.set_image_slice(new_slice)

    def _connect_cursors(self):
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

        self.image.image_plane_widget.AddObserver(
            self.image.image_plane_widget.cursor_change_event, draw_cursor2)
        self.image.image_plane_widget.AddObserver(
            self.image.image_plane_widget.slice_change_event, slice_movement)

    def current_coords(self):
        """
        Get cursor coordinates

        Returns:
            A tuple of coordinates
        """
        return self.__cursor.get_coords()

    @do_and_render
    def set_cursor_coords(self, coords):
        """
        Set coordinates for the cursor

        Args:
            Coords (tuple) : New position for the cursor (in voxels)
        """
        axis = self.image.image_plane_widget.GetPlaneOrientation()
        self.__cursor.set_axis_coords(axis, coords)
        img_slice = coords[axis]
        self.image.set_image_slice(img_slice)

    @property
    def image(self):
        """
        Access to ImageManager
        """
        return self.__image_manager

    @property
    def contours(self):
        """
        Access to FmriContours
        """
        return self.__contours

    @do_and_render
    def change_subject(self, new_subj):
        """
        Change subject associated to the plane

        Args:
            new_subj : Id of new subject
        """
        if self.__current_subject != new_subj:
            self.__current_subject = new_subj
            self.update_view(skip_render=True)

    @do_and_render
    def change_paradigm(self, new_pdgm):
        """
        Change fMRI paradigm

        Args:
            new_pdgm (str) : Must be one of the available fMRI paradigms
        """
        if self.__current_paradigm != new_pdgm:
            self.__current_paradigm = new_pdgm
            self.update_view(skip_render=True)

    @do_and_render
    def change_contrast(self, new_contrast):
        """
        Change contrast

        Args:
            new_contrast (int) : Index of new contrast (starting at 1)
        """
        if self.__current_contrast != new_contrast:
            self.__current_contrast = new_contrast
            self.update_view(skip_render=True)

    @do_and_render
    def set_all(self, new_subject, new_pdgm, new_contrast):
        """
        Set subject, paradigm and contrast

        Args:
            new_subject : Id of new subject
            new_pdgm (str) : New paradigm, must be one of the available fMRI paradigms
            new_contrast (int) : Index of new contrast (starting at 1)
        """
        if self.__current_subject != new_subject:
            self.__current_subject = new_subject
        if self.__current_paradigm != new_pdgm:
            self.__current_paradigm = new_pdgm
        if self.__current_contrast != new_contrast:
            self.__current_contrast = new_contrast
        self.update_view(skip_render=True)

    @do_and_render
    def set_contour_value(self, value):
        """
        Set value for the fMRI contours

        Args:
            value (float) : The iso-contours will be calculated at this value
        """
        self.__contours.set_value(value)

    @do_and_render
    def set_contour_opacity(self, value):
        """
        Opacity for displaying the contours

        Args:
            value (int) : A number from 0 to 100; where 0 is invisible and 100 is opaque
        """
        opac = value / 100
        self.__contours.actor.GetProperty().SetOpacity(opac)

    @do_and_render
    def set_contour_visibility(self, value):
        """
        Set visibility of contours

        Args:
            value (bool) : If ``True`` show the contours, otherwise hide them
        """
        self.__contours.actor.SetVisibility(value)

    @do_and_render
    def update_view(self):
        """
        Resets all elements in the view
        """
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

        self.image.change_image_modality(
            "fMRI", self.__current_paradigm, contrast=self.__current_contrast)
        if not self.__image_loaded:
            self._connect_cursors()
            self.__image_loaded = True
        self.__cursor.set_image(self.image.image_plane_widget.GetInput())
        if self.image.image_plane_widget.GetEnabled():
            self.__contours.set_image(
                self.image.image_plane_widget.alternative_img)
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

    @do_and_render
    def reset_camera(self, position):
        """
        resets the current camera to standard locations.

        Args:
            position (int) :

                - 0: initial 3d view
                - 1: left
                - 2: right
                - 3: front
                - 4: back
                - 5: top
                - 6: bottom
        """

        focal, position, viewup = self.__camera_positions_dict[position]

        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal)
        cam1.SetPosition(position)
        cam1.SetViewUp(viewup)

        self.ren.ResetCameraClippingRange()

    def get_camera_parameters(self):
        """
        Gets current camera parameters

        Returs:
            focal_point, position, view_up
        """
        cam1 = self.ren.GetActiveCamera()
        fp = cam1.GetFocalPoint()
        pos = cam1.GetPosition()
        vu = cam1.GetViewUp()
        return fp, pos, vu

    def set_camera(self, focal_point, position, view_up):
        """
        Sets the camera position

        Args:
            focal_point (tuple) : Focal point
            position (tuple) : Camera position
            view_up (tuple) : View up vector

        """
        cam1 = self.ren.GetActiveCamera()
        cam1.SetFocalPoint(focal_point)
        cam1.SetPosition(position)
        cam1.SetViewUp(view_up)

        self.ren.ResetCameraClippingRange()
        self.ren_win.Render()


class FmriContours(object):

    """
    Display contours calculated over an fMRI statistic map.
    """

    def __init__(self, ren):
        """
        Initialize the contours manager

        Args:
            ren (vtkRenderer) : Renderer that will draw the contours
        """
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
        """
        Sets the value at which contours are generated

        Args:
            value (float) : Statistical value for creating contours
        """
        self.__value = value
        self.__contour_filter.SetValue(0, value)
        self.__contour_filter.SetValue(1, -1 * value)

    def set_image(self, img):
        """
        Sets the statistical map

        Args:
            img (vtkImageData) : Data used for contours generation
        """
        self.__img = img
        self.__contour_filter.SetInputData(img)
        self.__contour_filter.Update()

    def set_lut(self, lut):
        """
        Sets a lookup table for showing the contours

        Notice the contour will always have the same vale, and therefore the same color.
        However the lut will reflect the changes in the contour value.

        Args:
            lut (vtkScalarsToColors) : Table to generate contour color based on its value
        """
        self.__mapper.SetLookupTable(lut)
        self.__mapper.UseLookupTableScalarRangeOn()

    @property
    def actor(self):
        """
        Get the contours actor
        """
        return self.__actor


class QFmriWidget(QFrame):

    """
    A Qt Widget that wraps :class:`fMRI_viewer` and lets it connect naturally to Qt Applications
    """
    slice_changed = pyqtSignal(int)
    image_window_changed = pyqtSignal(float)
    image_level_changed = pyqtSignal(float)
    cursor_moved = pyqtSignal(tuple)

    def __init__(self, reader, parent):
        """
        Creates the fMRI viewer widget

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            parent (QObject) : Parent
        """
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        self.__reader = reader
        self.__vtk_viewer = fMRI_viewer(
            self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        # self.subject_viewer.ren_win.Render()

        # self.__qwindow_interactor.show()

    def initialize_widget(self):
        """
        Call this function **after** calling show on the widget or a parent
        """
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()
        # self.__subject_viewer.show_cone()

    @property
    def viewer(self):
        """
        Access to the internal fMRI_viewer
        """
        return self.__vtk_viewer

    def slice_change_handle(self, new_slice):
        """
        Emits a signal when the current image slice is changed on the vtkWidget
        """
        self.slice_changed.emit(new_slice)
        # print new_slice

    def window_level_change_handle(self, window, level):
        """
        Emits a signal when window or level are changed by interacting in the vtkWidget
        """
        self.image_window_changed.emit(window)
        self.image_level_changed.emit(level)

    def cursor_move_handler(self, coordinates):
        """
        Emits a signal when the cursor is moved
        """
        self.cursor_moved.emit(tuple(coordinates))


if __name__ == "__main__":
    import sys
    import PyQt4.QtGui as QtGui
    import braviz

    reader = braviz.readAndFilter.BravizAutoReader()
    app = QtGui.QApplication(sys.argv)
    main_window = QSubjectViewerWidget(reader, None)
    main_window.show()
    main_window.initialize_widget()

    app.exec_()
    log = logging.getLogger(__name__)
    log.info("es todo")
