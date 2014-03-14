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
        self.__current_subject = "093"
        self.__current_space = "world"
        self.__current_image = None
        self.__current_image_orientation = 0
        self.__curent_fmri_paradigm = None

        #internal data
        self.__image_plane_widget = None
        self.__mri_lut = None
        self.__fmri_blender = braviz.visualization.fMRI_blender()

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

    def hide_image(self):
        if self.__image_plane_widget is not None:
            self.__image_plane_widget.Off()
            #self.image_plane_widget.SetVisibility(0)

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

        self.__image_plane_widget.AddObserver(self.__image_plane_widget.slice_change_event, slice_change_handler)

    def change_image_modality(self, modality, paradigm=None, force_reload=False):
        """Changes the modality of the current image
        to hide the image call hide_image
        in the case of fMRI modality should be fMRI and paradigm the name of the paradigm"""

        modality = modality.upper()
        if (modality == self.__current_image) and (paradigm == self.__curent_fmri_paradigm) and \
                self.__image_plane_widget.GetEnabled() and not force_reload:
            #nothing to do
            return

        if self.__image_plane_widget is None:
            self.create_image_plane_widget()
        self.__image_plane_widget.On()

        #update image labels:
        aparc_img = self.reader.get("APARC", self.__current_subject, format="VTK", space=self.__current_space)
        aparc_lut = self.reader.get("APARC", self.__current_subject, lut=True)
        self.__image_plane_widget.addLabels(aparc_img)
        self.__image_plane_widget.setLabelsLut(aparc_lut)

        if modality == "FMRI":
            mri_image = self.reader.get("MRI", self.__current_subject, format="VTK", space=self.__current_space)
            fmri_image = self.reader.get("fMRI", self.__current_subject, format="VTK", space=self.__current_space,
                                         name=paradigm)
            if fmri_image is None:
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
        elif modality == "FA":
            lut = self.reader.get("FA", self.__current_subject, lut=True)
            self.__image_plane_widget.SetLookupTable(lut)
            self.__image_plane_widget.SetResliceInterpolateToCubic()
        elif modality == "APARC":
            lut = self.reader.get("APARC", self.__current_subject, lut=True)
            self.__image_plane_widget.SetLookupTable(lut)
            #Important:
            self.__image_plane_widget.SetResliceInterpolateToNearestNeighbour()
        self.__current_image = modality
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

    def set_image_slice(self,new_slice):
        if self.__image_plane_widget is None:
            return
        self.__image_plane_widget.SetSliceIndex(new_slice)
        self.ren_win.Render()

    def change_current_space(self, new_space):
        if self.__current_space == new_space:
            return
        self.__current_space = new_space
        if self.__image_plane_widget is not None and self.__image_plane_widget.GetEnabled():
            self.change_image_modality(self.__current_image, self.__curent_fmri_paradigm, force_reload=True)

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

class QSuvjectViwerWidget(QFrame):
    slice_changed = pyqtSignal(int)
    window_level_changed = pyqtSignal(float, float)

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

