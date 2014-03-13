from __future__ import division
__author__ = 'Diego'

import PyQt4.QtGui as QtGui
from PyQt4.QtGui import QMainWindow
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

import braviz
from braviz.interaction.qt_guis.subject_overview import Ui_subject_overview
from braviz.visualization.subject_viewer import SubjectViewer


class SubjectOverviewApp(QMainWindow):
    def __init__(self,initial_vars=None):
        #Super init
        QMainWindow.__init__(self)
        #Internal initialization
        self.reader=braviz.readAndFilter.kmc40AutoReader()
        if initial_vars is None:
            #GENRE LAT Weight at birth VCIIQ
            initial_vars=(11,6,17,1)
        self.clinical_vars=initial_vars
        self.vtk_widget=QVTKRenderWindowInteractor()
        self.vtk_viewer=SubjectViewer(self.vtk_widget,self.reader)
        #Init gui
        self.ui=None
        self.setup_gui()

        #load initial image
        self.image_modality_change()
        #self.vtk_viewer.show_cone()

    def setup_gui(self):
        self.ui=Ui_subject_overview()
        self.ui.setupUi(self)

        #control frame
        #view controls
        self.ui.camera_pos.activated.connect(self.position_camera)
        self.ui.space_combo.activated.connect(self.space_change)

        #image controls
        self.ui.image_mod_combo.activated.connect(self.image_modality_change)
        self.ui.image_orientation.activated.connect(self.image_orientation_change)

        #view frame
        self.ui.vtk_frame_layout=QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0,0,0,0)



    def image_modality_change(self):
        selection=str(self.ui.image_mod_combo.currentText())
        if selection=="None":
            self.vtk_viewer.hide_image()
            self.ui.image_orientation.setEnabled(0)
            self.ui.image_window.setEnabled(0)
            self.ui.image_level.setEnabled(0)
            self.ui.reset_window_level.setEnabled(0)
            self.ui.slice_spin.setEnabled(0)
            self.ui.slice_slider.setEnabled(0)
            return

        if selection in ("MRI","FA","APARC"):
            self.vtk_viewer.change_image_modality(selection)
        else:
            try:
                self.vtk_viewer.change_image_modality("FMRI",selection)
            except Exception as e:
                print e.message
                self.statusBar().showMessage(e.message,5000)

        self.ui.image_orientation.setEnabled(1)
        self.ui.slice_spin.setEnabled(1)
        self.ui.slice_slider.setEnabled(1)

        window_level_control=1 if selection in ("MRI","FA") else 0
        self.ui.image_window.setEnabled(window_level_control)
        self.ui.image_level.setEnabled(window_level_control)
        self.ui.reset_window_level.setEnabled(window_level_control)

    def image_orientation_change(self):
        orientation_dict={"Axial":2 , "Coronal":1, "Sagital":0}
        selection=str(self.ui.image_orientation.currentText())
        self.vtk_viewer.change_image_orientation(orientation_dict[selection])


    def position_camera(self):
        self.print_vtk_camera()
        selection=str(self.ui.camera_pos.currentText())
        camera_pos_dict={"Default":0,"Left":1,"Right":2,"Front":3,"Back":4,"Top":5,"Bottom":6}
        self.vtk_viewer.reset_camera(camera_pos_dict[selection])

    def space_change(self):
        new_space=str(self.ui.space_combo.currentText())
        self.vtk_viewer.change_current_space(new_space)
        print new_space

    def print_vtk_camera(self):
        self.vtk_viewer.print_camera()



def run():
    import sys
    app = QtGui.QApplication(sys.argv)
    main_window = SubjectOverviewApp()
    main_window.show()
    app.exec_()

if __name__ == '__main__':
    run()