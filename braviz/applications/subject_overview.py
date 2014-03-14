from __future__ import division

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
from PyQt4.QtGui import QMainWindow

import braviz
from braviz.interaction.qt_guis.subject_overview import Ui_subject_overview
from braviz.interaction.qt_models import SubjectsTable
from braviz.visualization.subject_viewer import QSuvjectViwerWidget


class SubjectOverviewApp(QMainWindow):
    def __init__(self, initial_vars=None):
        #Super init
        QMainWindow.__init__(self)
        #Internal initialization
        self.reader = braviz.readAndFilter.kmc40AutoReader()
        if initial_vars is None:
            #GENRE LAT Weight at birth VCIIQ
            initial_vars = (11, 6, 17, 1)
        self.clinical_vars = initial_vars
        self.vtk_widget = QSuvjectViwerWidget(reader=self.reader)
        self.vtk_viewer = self.vtk_widget.subject_viewer
        self.subjects_model = SubjectsTable(initial_vars)
        #Init gui
        self.ui = None
        self.setup_gui()

        #load initial image
        self.image_modality_change()
        #self.vtk_viewer.show_cone()

    def setup_gui(self):
        self.ui = Ui_subject_overview()
        self.ui.setupUi(self)

        #control frame
        #view controls
        self.ui.camera_pos.activated.connect(self.position_camera)
        self.ui.space_combo.activated.connect(self.space_change)

        #image controls
        self.ui.image_mod_combo.activated.connect(self.image_modality_change)
        self.ui.image_orientation.activated.connect(self.image_orientation_change)
        self.vtk_widget.slice_changed.connect(self.ui.slice_slider.setValue)
        self.ui.slice_slider.valueChanged.connect(self.vtk_viewer.set_image_slice)
        self.vtk_widget.image_window_changed.connect(self.ui.image_window.setValue)
        self.vtk_widget.image_level_changed.connect(self.ui.image_level.setValue)
        self.ui.image_window.valueChanged.connect(self.vtk_viewer.set_image_window)
        self.ui.reset_window_level.pressed.connect(self.vtk_viewer.reset_window_level)

        #Subject selection
        self.ui.subjects_table.setModel(self.subjects_model)

        #view frame
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)

    def image_modality_change(self):
        selection = str(self.ui.image_mod_combo.currentText())
        if selection == "None":
            self.vtk_viewer.hide_image()
            self.ui.image_orientation.setEnabled(0)
            self.ui.image_window.setEnabled(0)
            self.ui.image_level.setEnabled(0)
            self.ui.reset_window_level.setEnabled(0)
            self.ui.slice_spin.setEnabled(0)
            self.ui.slice_slider.setEnabled(0)
            self.ui.slice_slider.setMaximum(self.vtk_viewer.get_number_of_image_slices())
            self.reset_image_view_controls()
            return

        if selection in ("MRI", "FA", "APARC"):
            self.vtk_viewer.change_image_modality(selection)
        else:
            try:
                self.vtk_viewer.change_image_modality("FMRI", selection)
            except Exception as e:
                print e.message
                self.statusBar().showMessage(e.message, 5000)

        self.ui.image_orientation.setEnabled(1)
        self.ui.slice_spin.setEnabled(1)
        self.ui.slice_slider.setEnabled(1)
        self.reset_image_view_controls()

        window_level_control = 1 if selection in ("MRI", "FA") else 0
        self.ui.image_window.setEnabled(window_level_control)
        self.ui.image_level.setEnabled(window_level_control)
        self.ui.reset_window_level.setEnabled(window_level_control)

    def image_orientation_change(self):
        orientation_dict = {"Axial": 2, "Coronal": 1, "Sagital": 0}
        selection = str(self.ui.image_orientation.currentText())
        self.vtk_viewer.change_image_orientation(orientation_dict[selection])
        self.reset_image_view_controls()

    def position_camera(self):
        self.print_vtk_camera()
        selection = str(self.ui.camera_pos.currentText())
        camera_pos_dict = {"Default": 0, "Left": 1, "Right": 2, "Front": 3, "Back": 4, "Top": 5, "Bottom": 6}
        self.vtk_viewer.reset_camera(camera_pos_dict[selection])

    def space_change(self):
        new_space = str(self.ui.space_combo.currentText())
        self.vtk_viewer.change_current_space(new_space)
        print new_space

    def print_vtk_camera(self):
        self.vtk_viewer.print_camera()

    def reset_image_view_controls(self):
        self.ui.slice_slider.setMaximum(self.vtk_viewer.get_number_of_image_slices())
        self.ui.slice_spin.setMaximum(self.vtk_viewer.get_number_of_image_slices())
        self.ui.slice_slider.setValue(self.vtk_viewer.get_current_image_slice())
        self.ui.image_level.setValue(self.vtk_viewer.get_current_image_level())
        self.ui.image_window.setValue(self.vtk_viewer.get_current_image_window())



def run():
    import sys

    app = QtGui.QApplication(sys.argv)
    main_window = SubjectOverviewApp()
    main_window.show()
    app.exec_()


if __name__ == '__main__':
    run()