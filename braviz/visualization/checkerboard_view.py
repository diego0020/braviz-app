import vtk
import braviz
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PyQt4 import QtCore
from PyQt4.QtGui import QFrame, QHBoxLayout, QApplication
from PyQt4.QtCore import pyqtSignal
import logging

from braviz.visualization.subject_viewer import do_and_render

__author__ = 'Diego'

_NOMINAL_MODS={"APARC","WMPARC"}
_COLORED_MODS={"DTI","NONE"}
_WL_MODS={"MRI","FA","MD"}

class CheckbordView(object):
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

        self.reader = reader
        self.widget = widget

        #pipeline
        # img1 -> map_colors -------------- |checkboard view ---> plane widget
        # img2 -> reslice ->  map_colors -> |

        self.__img1 = None
        self.__img2 = None


        self.__color_wl1 = vtk.vtkImageMapToWindowLevelColors()
        self.__color_wl2 = vtk.vtkImageMapToWindowLevelColors()
        self.__color_wl1.SetOutputFormatToRGB()
        self.__color_wl2.SetOutputFormatToRGB()
        self.__lut = self.reader.get("APARC",None,lut=True)
        self.__color_labels1 = vtk.vtkImageMapToColors()
        self.__color_labels2 = vtk.vtkImageMapToColors()
        self.__color_labels1.SetLookupTable(self.__lut)
        self.__color_labels2.SetLookupTable(self.__lut)
        self.__color_labels1.SetOutputFormatToRGB()
        self.__color_labels2.SetOutputFormatToRGB()

        #WL : Window Level, NOM: Nominal, PT: Pass Throug (no lut)
        self.__color1_type = "WL"
        self.__color2_type = "WL"


        self.__reslice2 = vtk.vtkImageReslice()
        self.__checkboard_view = vtk.vtkImageCheckerboard()
        self.__plane_widget = None
        self.__current_space = "World"
        self.__orientation = 2
        self.__divs = 3
        self.__img1_params=(None,"None",None)
        self.__img2_params=(None,"None",None)

        self.__outline = vtk.vtkOutlineFilter()
        self.__outline_mapper = vtk.vtkPolyDataMapper()
        self.__outline_mapper.SetInputConnection(self.__outline.GetOutputPort())
        self.__outline_actor= vtk.vtkActor()
        self.__outline_actor.SetMapper(self.__outline_mapper)
        self.ren.AddActor(self.__outline_actor)
        self.reset_camera(0,skip_render=True)
        self.set_number_of_divisions(self.__divs,skip_render=True)

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


    def update_pipeline(self):
        if self.__plane_widget is None:
            self.create_image_plane_widget()

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
                    self.__plane_widget.SetInputData(self.__color_labels1.GetOutput())
                else:
                    self.__color_labels1.Update()
                    self.__checkboard_view.SetInput1Data(self.__color_labels1.GetOutput())
            elif self.__color1_type == "WL":
                self.__color_wl1.SetInputData(self.__img1)
                w,l = get_window_level(self.__img1)
                self.__color_wl1.SetWindow(w)
                self.__color_wl1.SetLevel(l)
                if self.__img2 is None:
                    self.__color_wl1.Update()
                    self.__plane_widget.SetInputData(self.__color_wl1.GetOutput())
                    #self.__plane_widget.SetInputConnection(self.__color_wl1.GetOutputPort())
                else:
                    self.__color_wl1.Update()
                    self.__checkboard_view.SetInput1Data(self.__color_wl1.GetOutput())
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
                    self.__plane_widget.SetInputData(self.__color_labels2.GetOutput())
                else:
                    self.__color_labels2.SetInputConnection(self.__reslice2.GetOutputPort())
                    self.__color_labels2.Update()
                    self.__checkboard_view.SetInput2Data(self.__color_labels2.GetOutput())
            elif self.__color2_type == "WL":
                w,l = get_window_level(self.__img2)
                self.__color_wl2.SetWindow(w)
                self.__color_wl2.SetLevel(l)
                if self.__img1 is None:
                    self.__color_wl2.SetInputData(self.__img2)
                    self.__color_wl2.Update()
                    self.__plane_widget.SetInputData(self.__color_wl2.GetOutput())
                else:
                    self.__color_wl2.SetInputConnection(self.__reslice2.GetOutputPort())
                    self.__color_wl2.Update()
                    self.__checkboard_view.SetInput2Data(self.__color_wl2.GetOutput())
            elif self.__color2_type == "PT":
                if self.__img1 is None:
                    self.__plane_widget.SetInputData(self.__img2)
                else:
                    self.__reslice2.Update()
                    self.__checkboard_view.SetInput2Data(self.__reslice2.GetOutput())

            else:
                raise ValueError
        if self.__img1 is not None and self.__img2 is not None:
            self.__checkboard_view.Update()
            #print self.__checkboard_view.GetOutput()
            self.__plane_widget.SetInputData(self.__checkboard_view.GetOutput())


    def create_image_plane_widget(self):
        if self.__plane_widget is None:
            self.__plane_widget = braviz.visualization.persistentImagePlane(self.__orientation)
            self.__plane_widget.SetInteractor(self.iren)
            self.__plane_widget.GetColorMap().SetLookupTable(None)
            self.__plane_widget.On()
            def slice_change_handler(source, event):
                new_slice = self.__plane_widget.GetSliceIndex()
                self.widget.slice_change_handle(new_slice)
            self.__plane_widget.AddObserver(self.__plane_widget.slice_change_event, slice_change_handler)


    @do_and_render
    def set_img1(self,subj,mod,contrast=None,force=False):
        params = (subj,mod.upper(),contrast)
        if params == self.__img1_params and not force:
            return
        self.__img1_params = params
        modality = params[1]
        if modality == "NONE":
            self.__img1 = None
        elif contrast is not None:
            raise NotImplementedError
        else:
            try:
                self.__img1 = self.reader.get(mod,subj,format="vtk",space=self.__current_space)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.exception(e)
                self.__img1 = None

        if modality in _NOMINAL_MODS:
            self.__color1_type = "NOM"
        elif modality in _COLORED_MODS:
            self.__color1_type = "PT"
        elif modality in _WL_MODS:
            self.__color1_type = "WL"
        else:
            raise  NotImplementedError

        self.update_pipeline()


    @do_and_render
    def set_img2(self,subj,mod,contrast=None, force=False):
        params = (subj,mod.upper(),contrast)
        if params == self.__img2_params and not force:
            return
        self.__img2_params = params
        modality = params[1]
        if modality == "NONE":
            self.__img2 = None
        elif contrast is not None:
            raise NotImplementedError
        else:
            try:
                self.__img2 = self.reader.get(mod,subj,format="vtk",space=self.__current_space)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.exception(e)
                self.__img1 = None

        if modality in _NOMINAL_MODS:
            self.__color2_type = "NOM"
        elif modality in _COLORED_MODS:
            self.__color2_type = "PT"
        elif modality in _WL_MODS:
            self.__color2_type = "WL"
        else:
            raise  NotImplementedError

        self.update_pipeline()


    def set_orientation(self,orientation_int):
        pass

    @do_and_render
    def set_number_of_divisions(self,divs):
        divs_ar = [divs]*3
        divs_ar[self.__orientation]=1
        self.__checkboard_view.SetNumberOfDivisions(divs_ar)
        self.__divs = divs
        if self.__img1 is not None and self.__img2 is not None:
            self.__checkboard_view.Update()
            self.__plane_widget.SetInputData(self.__checkboard_view.GetOutput())

    @do_and_render
    def set_orientation(self,orientation_int):
        self.__plane_widget.set_orientation(orientation_int)
        self.__orientation = orientation_int
        self.set_number_of_divisions(self.__divs,skip_render=True)

    def load_test_view(self):
        self.set_img1(119,"MRI")
        self.set_img2(119,"APARC")

    @do_and_render
    def change_space(self,new_space):
        self.__current_space=new_space
        p1=self.__img1_params
        p2=self.__img2_params
        self.set_img1(*p1,force=True,skip_render=True)
        self.set_img2(*p2,force=True,skip_render=True)

    @do_and_render
    def set_image_slice(self, new_slice):
        if self.__plane_widget is None:
            return
        self.__plane_widget.SetSliceIndex(int(new_slice))
        self.__plane_widget.InvokeEvent(self.__plane_widget.slice_change_event)

    def get_number_of_image_slices(self):
        if self.__plane_widget is None:
            return 0
        img = self.__plane_widget.GetInput()
        if img is None:
            return 0
        dimensions = img.GetDimensions()

        return dimensions[self.__orientation]


def get_window_level(img):
    stats = vtk.vtkImageHistogramStatistics()
    stats.SetInputData(img)
    stats.Update()
    _,w = stats.GetAutoRange()
    return w,w/2



class QCheckViewer(QFrame):
    slice_changed = pyqtSignal(int)

    def __init__(self, reader, parent):
        QFrame.__init__(self, parent)
        self.__qwindow_interactor = QVTKRenderWindowInteractor(self)
        self.__reader = reader
        self.__vtk_viewer = CheckbordView(self.__qwindow_interactor, self.__reader, self)
        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__qwindow_interactor)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)
    def initialize_widget(self):
        """call after showing the interface"""
        self.__qwindow_interactor.Initialize()
        self.__qwindow_interactor.Start()

    @property
    def viewer(self):
        return self.__vtk_viewer

    def slice_change_handle(self, new_slice):
        self.slice_changed.emit(new_slice)
