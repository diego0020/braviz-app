from __future__ import division
import logging
from functools import partial as partial_f

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QMainWindow
import vtk

import braviz
from braviz.interaction.qt_guis.roi_builder import Ui_RoiBuildApp
from braviz.visualization.subject_viewer import QOrthogonalPlanesWidget
from braviz.readAndFilter.filter_fibers import FilterBundleWithSphere
from braviz.interaction.qt_models import SubjectCheclist

__author__ = 'Diego'

AXIAL = 2
SAGITAL = 0
CORONAL = 1

class BuildRoiApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = None
        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.__subjects_list = self.reader.get("ids")
        self.__current_subject = self.__subjects_list[0]
        self.__current_image_mod = "MRI"
        self.__curent_space = "World"
        self.vtk_widget = QOrthogonalPlanesWidget(self.reader, parent=self)
        self.vtk_viewer = self.vtk_widget.orthogonal_viewer

        self.__fibers_map = None
        self.__fibers_ac = None
        self.__filetred_pd = None
        self.__full_pd = None
        self.__fibers_filterer = None

        self.__subjects_check_model = SubjectCheclist(self.__subjects_list)

        self.setup_ui()
        self.new_sphere()

    def setup_ui(self):
        self.ui = Ui_RoiBuildApp()
        self.ui.setupUi(self)
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.ui.axial_check.stateChanged.connect(partial_f(self.show_image, AXIAL))
        self.ui.coronal_check.stateChanged.connect(partial_f(self.show_image, CORONAL))
        self.ui.sagital_check.stateChanged.connect(partial_f(self.show_image, SAGITAL))
        self.ui.axial_slice.valueChanged.connect(partial_f(self.set_slice,AXIAL))
        self.ui.coronal_slice.valueChanged.connect(partial_f(self.set_slice,CORONAL))
        self.ui.sagital_slice.valueChanged.connect(partial_f(self.set_slice,SAGITAL))
        self.vtk_widget.slice_changed.connect(self.update_slice_controls)

        self.ui.sphere_radius.valueChanged.connect(self.update_sphere_radius)
        self.ui.sphere_x.valueChanged.connect(self.update_sphere_center)
        self.ui.sphere_y.valueChanged.connect(self.update_sphere_center)
        self.ui.sphere_z.valueChanged.connect(self.update_sphere_center)
        self.ui.copy_from_cursor_button.clicked.connect(self.copy_coords_from_cursor)
        self.ui.sphere_rep.currentIndexChanged.connect(self.set_sphere_representation)
        self.ui.sphere_opac.valueChanged.connect(self.set_sphere_opac)

        self.ui.show_fibers_check.stateChanged.connect(self.show_fibers)

        self.ui.subjects_list.setModel(self.__subjects_check_model)
        self.ui.subjects_list.activated.connect(self.select_subject)
        self.ui.subject_sphere_label.setText("Subject %s"%self.__current_subject)

    def start(self):
        self.vtk_widget.initialize_widget()
        self.set_image("MRI")
        self.vtk_viewer.finish_initializing()

    def set_image(self,modality):
        self.vtk_viewer.change_image_modality(modality)
        dims = self.vtk_viewer.get_number_of_slices()
        self.ui.axial_slice.setMaximum(dims[AXIAL])
        self.ui.coronal_slice.setMaximum(dims[CORONAL])
        self.ui.sagital_slice.setMaximum(dims[SAGITAL])
        self.update_slice_controls()

    def update_slice_controls(self,new_slice=None):
        curr_slices = self.vtk_viewer.get_current_slice()
        self.ui.axial_slice.setValue(curr_slices[AXIAL])
        self.ui.coronal_slice.setValue(curr_slices[CORONAL])
        self.ui.sagital_slice.setValue(curr_slices[SAGITAL])

    def set_slice(self,axis,index):
        self.vtk_viewer.image_planes[axis].set_image_slice(index)
        self.vtk_viewer.ren_win.Render()

    def show_image(self, axis, state):
        if state == QtCore.Qt.Checked:
            self.vtk_viewer.image_planes[axis].show_image()
        elif state == QtCore.Qt.Unchecked:
            self.vtk_viewer.image_planes[axis].hide_image()
        self.vtk_viewer.ren_win.Render()

    def new_sphere(self):
        self.vtk_viewer.sphere.show()
        self.update_sphere_center()
        self.update_sphere_radius(self.ui.sphere_radius.value())
        self.vtk_viewer.ren_win.Render()

    def update_sphere_center(self,dummy=None):
        ctr = (self.ui.sphere_x.value(),self.ui.sphere_y.value(),self.ui.sphere_z.value())
        self.vtk_viewer.sphere.set_center(ctr)
        self.show_fibers()
        self.vtk_viewer.ren_win.Render()

    def update_sphere_radius(self,r=None):
        self.vtk_viewer.sphere.set_radius(r)
        self.show_fibers()
        self.vtk_viewer.ren_win.Render()

    def set_sphere_representation(self,index):
        if index == 0:
            rep = "solid"
        else:
            rep = "wire"
        self.vtk_viewer.sphere.set_repr(rep)
        self.vtk_viewer.ren_win.Render()

    def set_sphere_opac(self,opac_val):
        self.vtk_viewer.sphere.set_opacity(opac_val)
        self.vtk_viewer.ren_win.Render()

    def copy_coords_from_cursor(self):
        coords = self.vtk_viewer.current_position()
        if coords is None:
            return
        cx,cy,cz = coords
        self.ui.sphere_x.setValue(cx)
        self.ui.sphere_y.setValue(cy)
        self.ui.sphere_z.setValue(cz)

    def show_fibers(self,event=None):
        if self.ui.show_fibers_check.checkState()!=QtCore.Qt.Checked:
            if self.__fibers_ac is not None:
                self.__fibers_ac.SetVisibility(0)
                if event is not None:
                    self.vtk_viewer.ren_win.Render()
            return
        if self.__fibers_ac is None:
            self.__fibers_ac = vtk.vtkActor()
            self.__fibers_map = vtk.vtkPolyDataMapper()
            self.vtk_viewer.ren.AddActor(self.__fibers_ac)
            self.__fibers_ac.SetMapper(self.__fibers_map)
            self.__fibers_ac.SetVisibility(0)

        assert self.__fibers_map is not None
        if self.__fibers_filterer is None:
            self.__fibers_filterer = FilterBundleWithSphere()
        if self.__full_pd is None:
            self.__full_pd = self.reader.get("fibers",self.__current_subject,space=self.__curent_space)
            self.__fibers_filterer.set_bundle(self.__full_pd)

        ctr = (self.ui.sphere_x.value(),self.ui.sphere_y.value(),self.ui.sphere_z.value())
        r = self.ui.sphere_radius.value()
        self.__filetred_pd = self.__fibers_filterer.filter_bundle_with_sphere(ctr,r)
        self.__fibers_map.SetInputData(self.__filetred_pd)
        self.__fibers_ac.SetVisibility(1)
        if event is not None:
            self.vtk_viewer.ren_win.Render()

    def select_subject(self,index):
        subj = self.__subjects_check_model.data(index,QtCore.Qt.DisplayRole)
        self.change_subject(subj)

    def change_subject(self,new_subject):
        self.__current_subject = new_subject
        self.ui.subject_sphere_label.setText("Subject %s"%self.__current_subject)
        self.vtk_viewer.change_subject(new_subject)
        self.__full_pd = None
        self.show_fibers()
        print new_subject

def run():
    import sys
    from braviz.utilities import configure_console_logger

    # configure_logger("build_roi")
    configure_console_logger("build_roi")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = BuildRoiApp()
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()