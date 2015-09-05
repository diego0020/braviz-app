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


import logging

import vtk
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt4.QtGui import QFrame, QHBoxLayout
from PyQt4.QtCore import pyqtSignal

from braviz.visualization.simple_vtk import OrientationAxes, persistentImagePlane, get_window_level
from braviz.visualization.subject_viewer import do_and_render


__author__ = 'Diego'


class CheckboardView(object):

    """
    Viewer to compare two images
    """

    def __init__(self, render_window_interactor, reader, widget):
        """
        Construct the viewer

        Args:
            render_window_interactor (vtkRenderWindowInteractor) : Interactor for the image plane widget
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            widget (QObject) : Must implement *slice_change_handle*
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

        self.reader = reader
        self.widget = widget

        # pipeline
        # img1 -> map_colors -------------- |checkboard view ---> plane widget
        # img2 -> reslice ->  map_colors -> |

        self.__img1 = None
        self.__img2 = None

        self.__color_wl1 = vtk.vtkImageMapToWindowLevelColors()
        self.__color_wl2 = vtk.vtkImageMapToWindowLevelColors()
        self.__color_wl1.SetOutputFormatToRGB()
        self.__color_wl2.SetOutputFormatToRGB()
        self.__lut = self.reader.get("LABEL", None, lut=True, name="APARC")
        self.__color_labels1 = vtk.vtkImageMapToColors()
        self.__color_labels2 = vtk.vtkImageMapToColors()
        self.__color_labels1.SetLookupTable(self.__lut)
        self.__color_labels2.SetLookupTable(self.__lut)
        self.__color_labels1.SetOutputFormatToRGB()
        self.__color_labels2.SetOutputFormatToRGB()

        # WL : Window Level, NOM: Nominal, PT: Pass Throug (no lut)
        self.__color1_type = "WL"
        self.__color2_type = "WL"

        self.__reslice2 = vtk.vtkImageReslice()
        self.__checkboard_view = vtk.vtkImageCheckerboard()
        self.__plane_widget = None
        self.__current_space = "subject"
        self.__orientation = 2
        self.__divs = 3
        self.__img1_params = (None, "None", None)
        self.__img2_params = (None, "None", None)

        self.__outline = vtk.vtkOutlineFilter()
        self.__outline_mapper = vtk.vtkPolyDataMapper()
        self.__outline_mapper.SetInputConnection(
            self.__outline.GetOutputPort())
        self.__outline_actor = vtk.vtkActor()
        self.__outline_actor.SetMapper(self.__outline_mapper)
        self.ren.AddActor(self.__outline_actor)
        self.reset_camera(0, skip_render=True)
        self.set_number_of_divisions(self.__divs, skip_render=True)

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

    def update_pipeline(self):
        """
        Updates the whole visualization pipeline
        """
        if self.__plane_widget is None:
            self._create_image_plane_widget()

        if self.__img1 is None and self.__img2 is None:
            self.__plane_widget.Off()
            return
        else:
            self.__plane_widget.On()

        if self.__img1 is not None:
            self.__outline.SetInputData(self.__img1)
            if self.__color1_type == "NOM":
                self.__color_labels1.SetInputData(self.__img1)
                if self.__img2 is None:
                    self.__color_labels1.Update()
                    self.__plane_widget.SetInputData(
                        self.__color_labels1.GetOutput())
                else:
                    self.__color_labels1.Update()
                    self.__checkboard_view.SetInput1Data(
                        self.__color_labels1.GetOutput())
            elif self.__color1_type == "WL":
                self.__color_wl1.SetInputData(self.__img1)
                w, l = get_window_level(self.__img1)
                self.__color_wl1.SetWindow(w)
                self.__color_wl1.SetLevel(l)
                if self.__img2 is None:
                    self.__color_wl1.Update()
                    self.__plane_widget.SetInputData(
                        self.__color_wl1.GetOutput())
                    # self.__plane_widget.SetInputConnection(self.__color_wl1.GetOutputPort())
                else:
                    self.__color_wl1.Update()
                    self.__checkboard_view.SetInput1Data(
                        self.__color_wl1.GetOutput())
            elif self.__color1_type == "PT":
                if self.__img2 is None:
                    self.__plane_widget.SetInputData(self.__img1)
                else:
                    self.__checkboard_view.SetInput1Data(self.__img1)
            else:
                raise ValueError

        if self.__img2 is not None:
            if self.__img1 is not None:
                self.__reslice2.SetOutputOrigin(self.__img1.GetOrigin())
                self.__reslice2.SetOutputSpacing(self.__img1.GetSpacing())
                self.__reslice2.SetOutputExtent(self.__img1.GetExtent())
                if self.__color2_type:
                    self.__reslice2.SetInterpolationModeToNearestNeighbor()
                else:
                    self.__reslice2.SetInterpolationModeToCubic()
                self.__reslice2.SetInputData(self.__img2)
            else:
                self.__outline.SetInputData(self.__img2)

            #----------------------------------
            if self.__color2_type == "NOM":
                if self.__img1 is None:
                    self.__color_labels2.SetInputData(self.__img2)
                    self.__color_labels2.Update()
                    self.__plane_widget.SetInputData(
                        self.__color_labels2.GetOutput())
                else:
                    self.__color_labels2.SetInputConnection(
                        self.__reslice2.GetOutputPort())
                    self.__color_labels2.Update()
                    self.__checkboard_view.SetInput2Data(
                        self.__color_labels2.GetOutput())
            elif self.__color2_type == "WL":
                w, l = get_window_level(self.__img2)
                self.__color_wl2.SetWindow(w)
                self.__color_wl2.SetLevel(l)
                if self.__img1 is None:
                    self.__color_wl2.SetInputData(self.__img2)
                    self.__color_wl2.Update()
                    self.__plane_widget.SetInputData(
                        self.__color_wl2.GetOutput())
                else:
                    self.__color_wl2.SetInputConnection(
                        self.__reslice2.GetOutputPort())
                    self.__color_wl2.Update()
                    self.__checkboard_view.SetInput2Data(
                        self.__color_wl2.GetOutput())
            elif self.__color2_type == "PT":
                if self.__img1 is None:
                    self.__plane_widget.SetInputData(self.__img2)
                else:
                    self.__reslice2.Update()
                    self.__checkboard_view.SetInput2Data(
                        self.__reslice2.GetOutput())

            else:
                raise ValueError
        if self.__img1 is not None and self.__img2 is not None:
            self.__checkboard_view.Update()
            # print self.__checkboard_view.GetOutput()
            self.__plane_widget.SetInputData(
                self.__checkboard_view.GetOutput())

    def _create_image_plane_widget(self):
        """
        Creates the internal vtkImagePlaneWidget
        """
        if self.__plane_widget is None:
            self.__plane_widget = persistentImagePlane(self.__orientation)
            self.__plane_widget.SetInteractor(self.iren)
            self.__plane_widget.GetColorMap().SetLookupTable(None)
            self.__plane_widget.On()

            def slice_change_handler(source, event):
                new_slice = self.__plane_widget.GetSliceIndex()
                self.widget.slice_change_handle(new_slice)
            self.__plane_widget.AddObserver(
                self.__plane_widget.slice_change_event, slice_change_handler)

    @do_and_render
    def set_img1(self, subj, img_class, img_name, contrast=1, force=False):
        """
        Sets the first image

        Args:
            subj : Subject image code
            img_class (str) : image class (see :meth:`braviz.visualization.subject_viewer.ImageManager.change_image_modality`)
            img_name (str) : image name (see :meth:`braviz.visualization.subject_viewer.ImageManager.change_image_modality`)
            contrast (int) : contrast for fMRI images
            force (bool) : if ``True`` force reloading the data
        """
        if img_class is not None:
            img_class = img_class.upper()
        img_name = img_name.upper()
        params = (subj, img_class, img_name, contrast)
        if params == self.__img1_params and not force:
            return
        self.__img1_params = params
        if img_class is None:
            self.__img1 = None
        else:
            try:
                self.__img1 = self.reader.get(img_class, subj, format="vtk",
                                              space=self.__current_space, name=img_name)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.exception(e)
                self.__img1 = None

        if img_class == "LABEL":
            self.__color1_type = "NOM"
        elif img_class == "DTI":
            self.__color1_type = "PT"
        elif img_class == "IMAGE":
            self.__color1_type = "WL"
        elif img_class is None:
            pass
        else:
            raise NotImplementedError

        self.update_pipeline()

    @do_and_render
    def set_img2(self, subj, img_class, img_name, contrast=None, force=False):
        """
        Sets the second image

        Args:
            subj : Subject image code
            img_class (str) : image class (see :meth:`braviz.visualization.subject_viewer.ImageManager.change_image_modality`)
            img_name (str) : image name (see :meth:`braviz.visualization.subject_viewer.ImageManager.change_image_modality`)
            contrast (int) : contrast for fMRI images
            force (bool) : if ``True`` force reloading the data
        """
        if img_class is not None:
            img_class = img_class.upper()
        img_name = img_name.upper()
        params = (subj, img_class, img_name, contrast)
        if params == self.__img1_params and not force:
            return
        self.__img2_params = params
        if img_class is None:
            self.__img2 = None
        else:
            try:
                self.__img2 = self.reader.get(img_class, subj, format="vtk",
                                              space=self.__current_space, name=img_name)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.exception(e)
                self.__img2 = None

        if img_class == "LABEL":
            self.__color2_type = "NOM"
        elif img_class == "DTI":
            self.__color2_type = "PT"
        elif img_class == "IMAGE":
            self.__color2_type = "WL"
        else:
            raise NotImplementedError

        self.update_pipeline()

    @do_and_render
    def set_number_of_divisions(self, divs):
        """
        Set number of divisions in the checkboard pattern

        Args:
            divs (int) : Number of divisions
        """
        divs_ar = [divs] * 3
        divs_ar[self.__orientation] = 1
        self.__checkboard_view.SetNumberOfDivisions(divs_ar)
        self.__divs = divs
        if self.__img1 is not None and self.__img2 is not None:
            self.__checkboard_view.Update()
            self.__plane_widget.SetInputData(
                self.__checkboard_view.GetOutput())

    @do_and_render
    def set_orientation(self, orientation_int):
        """
        Sets orientation of the plane widget

        Args:
            orientation_int (int) : 0 is x, 1 is y, 2 is z
        """
        self.__plane_widget.set_orientation(orientation_int)
        self.__orientation = orientation_int
        self.set_number_of_divisions(self.__divs, skip_render=True)

    def _load_test_view(self):
        """
        Test
        """
        self.set_img1(119, "IMAGE", "MRI")
        self.set_img2(119, "LABEL", "APARC")

    @do_and_render
    def change_space(self, new_space):
        """
        Change current coordinate system

        new_space (str) : new coordinate system, see :meth:`~braviz.readAndFilter.base_reader.BaseReader.get`
        """
        self.__current_space = new_space
        p1 = self.__img1_params
        p2 = self.__img2_params
        self.set_img1(*p1, force=True, skip_render=True)
        self.set_img2(*p2, force=True, skip_render=True)

    @do_and_render
    def set_image_slice(self, new_slice):
        """
        Set plane widget slice

        Args:
            new_slice (int) : Index of desired slice
        """
        if self.__plane_widget is None:
            return
        self.__plane_widget.SetSliceIndex(int(new_slice))
        self.__plane_widget.InvokeEvent(self.__plane_widget.slice_change_event)

    def get_number_of_image_slices(self):
        """
        Gets the number of slices available in the current direction

        Returns:
            The number of available slices
        """
        if self.__plane_widget is None:
            return 0
        img = self.__plane_widget.GetInput()
        if img is None:
            return 0
        dimensions = img.GetDimensions()

        return dimensions[self.__orientation]


class QCheckViewer(QFrame):

    """
    Wraps the :class:`CheckboardView` so that in can be connected to Qt applications.
    """
    slice_changed = pyqtSignal(int)

    def __init__(self, reader, parent):
        """
        Constructs the widget

        Args:
            reader (braviz.visualization.base_reader.BaseReader) : Braviz reader
            parent (QObject) : Parent
        """
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        self.__reader = reader
        self.__vtk_viewer = CheckboardView(
            self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

    def initialize_widget(self):
        """
        Call this function **after** calling show on the widget or a parent
        """
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()

    @property
    def viewer(self):
        """
        Access to internal :class:`CheckboardView` object
        """
        return self.__vtk_viewer

    def slice_change_handle(self, new_slice):
        """
        Emits a qt signal when the current slice is changed from vtk
        """
        self.slice_changed.emit(new_slice)
