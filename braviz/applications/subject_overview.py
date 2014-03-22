from __future__ import division

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

import braviz
from braviz.interaction.qt_guis.subject_overview import Ui_subject_overview
from braviz.interaction.qt_models import SubjectsTable, SubjectDetails, StructureTreeModel, SimpleBundlesList
from braviz.visualization.subject_viewer import QSuvjectViwerWidget
from braviz.interaction.qt_dialogs import GenericVariableSelectDialog, ContextVariablesPanel, BundleSelectionDialog, \
    SaveFibersBundleDialog


class SubjectOverviewApp(QMainWindow):
    def __init__(self,):
        #Super init
        QMainWindow.__init__(self)
        #Internal initialization
        self.reader = braviz.readAndFilter.kmc40AutoReader()
        self.__curent_subject = None

        initial_vars = (11, 17, 1)

        self.vtk_widget = QSuvjectViwerWidget(reader=self.reader)
        self.vtk_viewer = self.vtk_widget.subject_viewer
        self.subjects_model = SubjectsTable(initial_vars)

        #context panel
        self.context_frame=None
        self.__context_variables=[11, 6, 17, 1]

        #select first subject
        index=self.subjects_model.index(0,0)
        self.__curent_subject = self.subjects_model.data(index,QtCore.Qt.DisplayRole)

        initial_details_vars=[6,11,248,249,250,251,252,253,254,255]
        self.subject_details_model=SubjectDetails(initial_vars=initial_details_vars,
                                                  initial_subject=self.__curent_subject)
        #Structures model
        self.structures_tree_model = StructureTreeModel(self.reader)

        #Fibers list model
        self.fibers_list_model = SimpleBundlesList()

        #Init gui
        self.ui = None
        self.setup_gui()

        #load initial
        self.vtk_viewer.change_image_modality("MRI")
        self.change_subject(self.__curent_subject)
        #self.vtk_viewer.show_cone()


    def setup_gui(self):
        self.ui = Ui_subject_overview()
        self.ui.setupUi(self)

        #control frame
        #view controls
        self.ui.camera_pos.activated.connect(self.position_camera)
        self.ui.space_combo.activated.connect(self.space_change)

        #Subject selection
        self.ui.subjects_table.setModel(self.subjects_model)
        self.ui.select_subject_table_vars.pressed.connect(self.launch_subject_variable_select_dialog)
        self.ui.subjects_table.activated.connect(self.change_subject)
        self.ui.next_subject.pressed.connect(self.go_to_next_subject)
        self.ui.previus_subject.pressed.connect(self.go_to_previus_subject)

        #subject details
        self.ui.subject_details_table.setModel(self.subject_details_model)
        self.ui.select_details_button.pressed.connect(self.launch_details_variable_select_dialog)
        #image controls
        self.ui.image_mod_combo.activated.connect(self.image_modality_change)
        self.ui.image_orientation.activated.connect(self.image_orientation_change)
        self.vtk_widget.slice_changed.connect(self.ui.slice_slider.setValue)
        self.ui.slice_slider.valueChanged.connect(self.vtk_viewer.set_image_slice)
        self.vtk_widget.image_window_changed.connect(self.ui.image_window.setValue)
        self.vtk_widget.image_level_changed.connect(self.ui.image_level.setValue)
        self.ui.image_window.valueChanged.connect(self.vtk_viewer.set_image_window)
        self.ui.reset_window_level.pressed.connect(self.vtk_viewer.reset_window_level)
        #segmentation controls
        self.ui.structures_tree.setModel(self.structures_tree_model)
        self.connect(self.structures_tree_model,QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"),
                     self.ui.structures_tree.dataChanged)
        self.structures_tree_model.selection_changed.connect(self.update_segmented_structures)
        self.ui.struct_opacity_slider.valueChanged.connect(self.vtk_viewer.set_structures_opacity)
        self.ui.left_right_radio.toggled.connect(self.change_left_to_non_dominant)
        self.ui.struct_color_combo.currentIndexChanged.connect(self.select_structs_color)
        #tractography controls
        self.ui.fibers_from_segments_box.currentIndexChanged.connect(self.show_fibers_from_segment)
        self.ui.tracto_color_combo.currentIndexChanged.connect(self.change_tractography_color)
        self.ui.bundles_list.setModel(self.fibers_list_model)
        self.ui.add_saved_bundles.pressed.connect(self.add_saved_bundles_to_list)
        self.ui.save_bundle_button.pressed.connect(self.save_fibers_bundle)
        self.ui.fibers_opacity.valueChanged.connect(self.change_tractography_opacity)

        #view frame
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)

        #context view
        self.context_frame=ContextVariablesPanel(self.ui.splitter_2,"Context")

    def change_subject(self, new_subject=None):
        if isinstance(new_subject, QtCore.QModelIndex):
            selected_index = new_subject
            subj_code_index = self.subjects_model.index(selected_index.row(), 0)
            new_subject = self.subjects_model.data(subj_code_index, QtCore.Qt.DisplayRole)
        #label
        self.__curent_subject = new_subject
        self.ui.subject_id.setText("%s" % new_subject)
        self.ui.subject_id2.setText("%s" % new_subject)
        #details
        self.subject_details_model.change_subject(new_subject)
        #image
        try:
            self.vtk_viewer.change_subject(new_subject)
        except Exception as e:
            self.show_error(e.message)
            #raise
        self.reset_image_view_controls()
        #context
        self.context_frame.set_subject(new_subject)
    def show_error(self,message):
        self.statusBar().showMessage(message, 5000)
    def image_modality_change(self):
        selection = str(self.ui.image_mod_combo.currentText())
        if selection == "None":
            self.vtk_viewer.change_image_modality(None)
            self.ui.image_orientation.setEnabled(0)
            self.ui.image_window.setEnabled(0)
            self.ui.image_level.setEnabled(0)
            self.ui.reset_window_level.setEnabled(0)
            self.ui.slice_spin.setEnabled(0)
            self.ui.slice_slider.setEnabled(0)
            self.reset_image_view_controls()
            return

        if selection in ("MRI", "FA", "APARC", "MD", "DTI"):
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
        self.ui.slice_slider.setMaximum(self.vtk_viewer.get_number_of_image_slices())
        self.reset_image_view_controls()

        window_level_control = 1 if selection in ("MRI", "FA", "MD") else 0
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

    def launch_subject_variable_select_dialog(self):
        params = {}
        initial_selection=self.subjects_model.get_current_columns()
        dialog = GenericVariableSelectDialog(params, multiple=True, initial_selection_names=initial_selection)
        dialog.exec_()
        new_selection = params["checked"]
        self.subjects_model.set_var_columns(new_selection)

        print "returning"

    def launch_details_variable_select_dialog(self):
        params = {}
        initial_selection=self.subject_details_model.get_current_variables()
        dialog = GenericVariableSelectDialog(params, multiple=True, initial_selection_idx=initial_selection)
        dialog.exec_()
        new_selection = params.get("checked")
        if new_selection is not None:
            self.subject_details_model.set_variables(sorted(new_selection))

        print "returning"

    def go_to_previus_subject(self):
        current_subj_row=self.subjects_model.get_subject_index(self.__curent_subject)
        prev_row=(current_subj_row+self.subjects_model.rowCount()-1)%self.subjects_model.rowCount()
        prev_index=self.subjects_model.index(prev_row,0)
        self.change_subject(prev_index)

    def go_to_next_subject(self):
        current_subj_row=self.subjects_model.get_subject_index(self.__curent_subject)
        next_row=(1+current_subj_row)%self.subjects_model.rowCount()
        next_index=self.subjects_model.index(next_row,0)
        self.change_subject(next_index)

    def update_segmented_structures(self):
        selected_structures = self.structures_tree_model.get_selected_structures()
        self.vtk_viewer.set_structures(selected_structures)

    def change_left_to_non_dominant(self):
        if self.ui.left_right_radio.isChecked():
            left_right=True
        else:
            left_right=False
        self.structures_tree_model.reload_hierarchy(dominant=not left_right)
        print "Que mas?"

    def select_structs_color(self,index):
        print "mamamia"
        if index==1:
            print "launch choose color dialog"
            color_dialog=QtGui.QColorDialog()
            res=color_dialog.getColor()
            new_color=res.getRgb()[:3]
            new_float_color = [x/255 for x in new_color]
            self.vtk_viewer.set_structures_color(new_float_color)
            #print res.getRgb()
            if self.ui.struct_color_combo.count() < 3:
                self.ui.struct_color_combo.addItem("Custom")
            self.ui.struct_color_combo.setCurrentIndex(2)
        if index == 0:
            self.vtk_viewer.set_structures_color(None)
            if self.ui.struct_color_combo.count() == 3:
                self.ui.struct_color_combo.removeItem(2)

    def show_fibers_from_segment(self,index):
        if index == 0:
            self.vtk_viewer.hide_fibers_from_checkpoints()
            self.fibers_list_model.set_show_special(False)
            self.ui.save_bundle_button.setEnabled(False)
        else:
            checkpoints = self.structures_tree_model.get_selected_structures()
            self.fibers_list_model.set_show_special(True)
            throug_all = (index == 2)
            self.ui.save_bundle_button.setEnabled(True)
            try:
                self.vtk_viewer.show_fibers_from_checkpoints(checkpoints,throug_all)
            except Exception as e:
                self.show_error(e.message)

    def change_tractography_color(self,index):
        color_codes = {0: "orient", 1 : "fa", 5:"rand",6:"bundle"}
        color_text = color_codes.get(index)
        if color_text is not None:
            self.vtk_viewer.change_tractography_color(color_text)
        else:
            self.show_error("Not yet implemented")

    def change_tractography_opacity(self,value):
        float_value = value/100
        self.vtk_viewer.set_tractography_opacity(float_value)


    def add_saved_bundles_to_list(self):
        selected =set(self.fibers_list_model.get_ids())
        names_dict = {}
        dialog = BundleSelectionDialog(selected,names_dict)
        dialog.exec_()
        print selected
        self.fibers_list_model.restart_structures()
        for b in selected:
            self.fibers_list_model.add_bundle(b,names_dict[b])
        self.vtk_viewer.set_fibers_from_db(selected)

    def save_fibers_bundle(self):
        checkpoints = self.structures_tree_model.get_selected_structures()
        index = self.ui.fibers_from_segments_box.currentIndex()
        operation = self.ui.fibers_from_segments_box.itemText(index)
        throug_all = (index == 2)
        dialog = SaveFibersBundleDialog(operation,checkpoints,throug_all)
        dialog.exec_()

def run():
    import sys

    app = QtGui.QApplication(sys.argv)
    main_window = SubjectOverviewApp()
    main_window.show()
    app.exec_()


if __name__ == '__main__':
    run()