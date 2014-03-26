from __future__ import division

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

import numpy as np
import multiprocessing
import datetime
import sys
import platform
import os

import braviz
import braviz.readAndFilter.tabular_data as braviz_tab_data
from braviz.interaction.qt_guis.subject_overview import Ui_subject_overview
from braviz.interaction.qt_models import SubjectsTable, SubjectDetails, StructureTreeModel, SimpleBundlesList
from braviz.visualization.subject_viewer import QSuvjectViwerWidget
from braviz.interaction.qt_dialogs import GenericVariableSelectDialog, ContextVariablesPanel, BundleSelectionDialog, \
    SaveFibersBundleDialog, SaveScenarioDialog, LoadScenarioDialog
from braviz.applications import export_scalar_to_db


class SubjectOverviewApp(QMainWindow):
    def __init__(self, pipe = None):
        #Super init
        QMainWindow.__init__(self)
        #Internal initialization
        self.reader = braviz.readAndFilter.kmc40AutoReader()
        self.__curent_subject = None
        self.__pipe = pipe
        if pipe is not None:
            self.__pipe_check_timer=QtCore.QTimer()
            self.__pipe_check_timer.timeout.connect(self.poll_from_pipe)
            self.__pipe_check_timer.start(200)
        else:
            self.__pipe_check_timer = None

        initial_vars = (11, 17, 1)

        self.vtk_widget = QSuvjectViwerWidget(reader=self.reader)
        self.vtk_viewer = self.vtk_widget.subject_viewer
        self.subjects_model = SubjectsTable(initial_vars)
        self.active_children_check_timer = QtCore.QTimer()
        self.active_children_check_timer.timeout.connect(self.check_active_children)

        #context panel
        self.context_frame = None
        self.__context_variables = [11, 6, 17, 1]

        #select first subject
        index = self.subjects_model.index(0, 0)
        self.__curent_subject = self.subjects_model.data(index, QtCore.Qt.DisplayRole)

        initial_details_vars = [6, 11, 248, 249, 250, 251, 252, 253, 254, 255]
        self.subject_details_model = SubjectDetails(initial_vars=initial_details_vars,
                                                    initial_subject=self.__curent_subject)
        #Structures model
        self.structures_tree_model = StructureTreeModel(self.reader)
        self.__structures_color = None

        #Fibers list model
        self.fibers_list_model = SimpleBundlesList()
        self.current_fibers = None

        #Init gui
        self.ui = None
        self.setup_gui()

    def start(self):
        self.vtk_widget.initialize_widget()
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
        self.ui.image_level.valueChanged.connect(self.vtk_viewer.set_image_level)
        self.ui.reset_window_level.pressed.connect(self.vtk_viewer.reset_window_level)
        #segmentation controls
        self.ui.structures_tree.setModel(self.structures_tree_model)
        self.connect(self.structures_tree_model, QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"),
                     self.ui.structures_tree.dataChanged)
        self.structures_tree_model.selection_changed.connect(self.update_segmented_structures)
        self.ui.struct_opacity_slider.valueChanged.connect(self.vtk_viewer.set_structures_opacity)
        self.ui.left_right_radio.toggled.connect(self.change_left_to_non_dominant)
        self.ui.struct_color_combo.currentIndexChanged.connect(self.select_structs_color)
        self.ui.struct_scalar_combo.currentIndexChanged.connect(self.update_segmentation_scalar)
        self.ui.export_segmentation_to_db.pressed.connect(self.export_segmentation_scalars_to_db)
        #tractography controls
        self.ui.fibers_from_segments_box.currentIndexChanged.connect(self.show_fibers_from_segment)
        self.ui.tracto_color_combo.currentIndexChanged.connect(self.change_tractography_color)
        self.ui.bundles_list.setModel(self.fibers_list_model)
        self.ui.add_saved_bundles.pressed.connect(self.add_saved_bundles_to_list)
        self.ui.save_bundle_button.pressed.connect(self.save_fibers_bundle)
        self.ui.fibers_opacity.valueChanged.connect(self.change_tractography_opacity)
        self.ui.bundles_list.activated.connect(self.update_current_bundle)
        self.ui.fibers_scalar_combo.currentIndexChanged.connect(self.update_fiber_scalars)
        self.ui.export_fiber_scalars_to_db.pressed.connect(self.export_fiber_scalars_to_db)

        #view frame
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
        #self.vtk_viewer.show_cone()

        #context view
        self.context_frame = ContextVariablesPanel(self.ui.splitter_2, "Context")

        #menubar
        self.ui.actionSave_scenario.triggered.connect(self.save_state)
        self.ui.actionLoad_scenario.triggered.connect(self.load_scenario)


    def change_subject(self, new_subject=None):
        if isinstance(new_subject, QtCore.QModelIndex):
            selected_index = new_subject
            subj_code_index = self.subjects_model.index(selected_index.row(), 0)
            new_subject = self.subjects_model.data(subj_code_index, QtCore.Qt.DisplayRole)

        if self.__pipe is not None:
            self.__pipe.send({'subject': str(new_subject)})
        #label
        self.__curent_subject = new_subject
        self.ui.subject_id.setText("%s" % new_subject)
        self.ui.subject_id2.setText("%s" % new_subject)
        #details
        self.subject_details_model.change_subject(new_subject)
        #image
        image_code = str(braviz_tab_data.get_var_value(braviz_tab_data.IMAGE_CODE, new_subject))
        if len(image_code) < 3:
            image_code = "0" + image_code
        print "Image Code: ", image_code
        try:
            self.vtk_viewer.change_subject(image_code)
        except Exception as e:
            self.show_error(e.message)
            #raise
        self.reset_image_view_controls()
        #context
        self.update_segmentation_scalar()
        self.update_fiber_scalars()
        self.context_frame.set_subject(new_subject)


    def show_error(self, message):
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
        if self.ui.camera_pos.currentIndex() == 0:
            return
        self.print_vtk_camera()
        selection = str(self.ui.camera_pos.currentText())
        camera_pos_dict = {"Default": 0, "Left": 1, "Right": 2, "Front": 3, "Back": 4, "Top": 5, "Bottom": 6}
        self.vtk_viewer.reset_camera(camera_pos_dict[selection])
        self.ui.camera_pos.setCurrentIndex(0)

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
        initial_selection = self.subjects_model.get_current_columns()
        dialog = GenericVariableSelectDialog(params, multiple=True, initial_selection_names=initial_selection)
        res=dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            new_selection = params["checked"]
            self.subjects_model.set_var_columns(new_selection)


    def launch_details_variable_select_dialog(self):
        params = {}
        initial_selection = self.subject_details_model.get_current_variables()
        dialog = GenericVariableSelectDialog(params, multiple=True, initial_selection_idx=initial_selection)
        dialog.exec_()
        new_selection = params.get("checked")
        if new_selection is not None:
            self.subject_details_model.set_variables(sorted(new_selection))


    def go_to_previus_subject(self):
        current_subj_row = self.subjects_model.get_subject_index(self.__curent_subject)
        prev_row = (current_subj_row + self.subjects_model.rowCount() - 1) % self.subjects_model.rowCount()
        prev_index = self.subjects_model.index(prev_row, 0)
        self.change_subject(prev_index)

    def go_to_next_subject(self):
        current_subj_row = self.subjects_model.get_subject_index(self.__curent_subject)
        next_row = (1 + current_subj_row) % self.subjects_model.rowCount()
        next_index = self.subjects_model.index(next_row, 0)
        self.change_subject(next_index)

    def update_segmented_structures(self):
        selected_structures = self.structures_tree_model.get_selected_structures()
        self.vtk_viewer.set_structures(selected_structures)
        self.update_segmentation_scalar()

    metrics_dict = {"Volume": ("volume", "mm^3"),
                    "Area": ("area", "mm^2"),
                    "FA inside": ("fa_inside", ""),
                    "MD inside": ("md_inside", "*1e-12")}

    def update_segmentation_scalar(self, scalar_index=None):

        if scalar_index is None:
            scalar_index = self.ui.struct_scalar_combo.currentIndex()
        scalar_text = str(self.ui.struct_scalar_combo.itemText(scalar_index))
        metric_params = self.metrics_dict.get(scalar_text)
        if metric_params is None:
            self.ui.struct_scalar_value.clear()
            self.show_error("Unknown metric %s" % scalar_text)
            return
        metric_code, units = metric_params
        new_value = self.vtk_viewer.get_structures_scalar(metric_code)
        if np.isnan(new_value):
            self.ui.struct_scalar_value.clear()
        else:
            self.ui.struct_scalar_value.setValue(new_value)
            self.ui.struct_scalar_value.setSuffix(units)

    def export_segmentation_scalars_to_db(self):

        scalar_text = str(self.ui.struct_scalar_combo.currentText())
        metric_params = self.metrics_dict.get(scalar_text)
        if metric_params is None:
            self.show_error("Unknown metric %s" % scalar_text)
            return
        structures = tuple(self.structures_tree_model.get_selected_structures())
        export_dialog_args = {"fibers": False, "structures_list": structures,
                              "metric": scalar_text}
        export_dialog = multiprocessing.Process(target=export_scalar_to_db.run, kwargs=export_dialog_args)
        export_dialog.start()
        self.active_children_check_timer.start(100000)
        self.ui.export_segmentation_to_db.setEnabled(0)

        def reactivate_button():
            self.ui.export_segmentation_to_db.setEnabled(1)

        QtCore.QTimer.singleShot(2000, reactivate_button)


    def check_active_children(self):
        sub_processes = multiprocessing.active_children()
        print "checking kids:", sub_processes
        if len(sub_processes) == 0:
            self.active_children_check_timer.stop()
            print "all sub processes finished"

    def change_left_to_non_dominant(self):
        if self.ui.left_right_radio.isChecked():
            left_right = True
        else:
            left_right = False
        self.structures_tree_model.reload_hierarchy(dominant=not left_right)


    def select_structs_color(self, index):
        if index == 1:
            print "launch choose color dialog"
            color_dialog = QtGui.QColorDialog()
            res = color_dialog.getColor()
            new_color = res.getRgb()[:3]
            new_float_color = [x / 255 for x in new_color]
            self.vtk_viewer.set_structures_color(new_float_color)
            self.__structures_color = new_float_color
            #print res.getRgb()
            if self.ui.struct_color_combo.count() < 3:
                self.ui.struct_color_combo.addItem("Custom")
            self.ui.struct_color_combo.setCurrentIndex(2)
        if index == 0:
            self.vtk_viewer.set_structures_color(None)
            self.__structures_color = None
            if self.ui.struct_color_combo.count() == 3:
                self.ui.struct_color_combo.removeItem(2)

    def show_fibers_from_segment(self, index):
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
                self.vtk_viewer.show_fibers_from_checkpoints(checkpoints, throug_all)
            except Exception as e:
                self.show_error(e.message)
        self.update_current_bundle()

    def change_tractography_color(self, index):
        color_codes = {0: "orient", 1: "fa", 5: "rand", 6: "bundle"}
        color_text = color_codes.get(index)
        if color_text is not None:
            self.vtk_viewer.change_tractography_color(color_text)
        else:
            self.show_error("Not yet implemented")

    def change_tractography_opacity(self, value):
        float_value = value / 100
        self.vtk_viewer.set_tractography_opacity(float_value)


    def update_current_bundle(self, index=None):
        self.ui.export_fiber_scalars_to_db.setEnabled(1)
        if index is None:
            if (self.current_fibers is None) and (self.ui.fibers_from_segments_box.currentIndex() > 0):
                self.current_fibers = "<From Segmentation>"
                self.ui.current_bundle_tag.setText("<From Segmentation>")
            if (self.current_fibers == "<From Segmentation>") and (
                        self.ui.fibers_from_segments_box.currentIndex() == 0):
                self.current_fibers = None
                self.ui.current_bundle_tag.setText("<No active bundle>")
                self.ui.export_fiber_scalars_to_db.setEnabled(0)
        else:
            name = self.fibers_list_model.data(index, QtCore.Qt.DisplayRole)
            self.ui.current_bundle_tag.setText(name)
            bid = self.fibers_list_model.data(index, QtCore.Qt.UserRole)
            if bid is None:
                self.ui.current_bundle_tag.setText("<From Segmentation>")
                self.current_fibers = "<From Segmentation>"
            else:
                self.current_fibers = bid
        self.update_fiber_scalars()

    fiber_metrics_dict = {"Count": "number",
                          "Mean L": "mean_length",
                          "Mean FA": "mean_fa"}

    def update_fiber_scalars(self, index=None):
        print self.current_fibers
        if index is None:
            index = self.ui.fibers_scalar_combo.currentIndex()
        text = str(self.ui.fibers_scalar_combo.itemText(index))

        metric = self.fiber_metrics_dict.get(text)
        if metric is None:
            self.ui.fibers_scalar_value.clear()
            self.show_error("%s not yet implemented" % text)
            return
        if self.current_fibers is None:
            value = float("nan")
        elif type(self.current_fibers) is str:
            value = self.vtk_viewer.get_fibers_scalar_from_segmented(metric)
        else:
            value = self.vtk_viewer.get_fibers_scalar_from_db(metric, self.current_fibers)
        if np.isnan(value):
            self.ui.fibers_scalar_value.clear()
        else:
            self.ui.fibers_scalar_value.setValue(value)

    def export_fiber_scalars_to_db(self):
        if self.current_fibers is None:
            return
        scalar_text = str(self.ui.fibers_scalar_combo.currentText())
        metric_params = self.fiber_metrics_dict.get(scalar_text)
        if metric_params is None:
            self.show_error("Unknown metric %s" % scalar_text)
            return
        if type(self.current_fibers) is str:
            structs = tuple(self.structures_tree_model.get_selected_structures())
            index = self.ui.fibers_from_segments_box.currentIndex()
            operation = "and" if (index == 2) else "or"
            db_id = None
        else:
            db_id = self.current_fibers
            structs = None
            operation = None
        export_dialog_args = {"fibers": True, "structures_list": structs,
                              "metric": scalar_text, "db_id": db_id, "operation": operation}
        export_dialog = multiprocessing.Process(target=export_scalar_to_db.run, kwargs=export_dialog_args)
        export_dialog.start()
        #to avoid zombie processes
        self.active_children_check_timer.start(10000)
        self.ui.export_fiber_scalars_to_db.setEnabled(0)

        def reactivate_button():
            self.ui.export_fiber_scalars_to_db.setEnabled(1)

        QtCore.QTimer.singleShot(2000, reactivate_button)
        print "launching"

    def add_saved_bundles_to_list(self):
        selected = set(self.fibers_list_model.get_ids())
        names_dict = {}
        dialog = BundleSelectionDialog(selected, names_dict)
        dialog.exec_()
        print selected
        self.fibers_list_model.set_ids(selected, names_dict)
        self.vtk_viewer.set_fibers_from_db(selected)

    def save_fibers_bundle(self):
        checkpoints = self.structures_tree_model.get_selected_structures()
        index = self.ui.fibers_from_segments_box.currentIndex()
        operation = self.ui.fibers_from_segments_box.itemText(index)
        throug_all = (index == 2)
        dialog = SaveFibersBundleDialog(operation, checkpoints, throug_all)
        dialog.exec_()

    def save_state(self):
        state = dict()
        #subject panel
        subject_state = dict()
        subject_state["current_subject"] = int(self.__curent_subject)
        subject_state["model_columns"] = tuple(self.subjects_model.get_current_column_indexes())
        state["subject_state"] = subject_state

        #details panel
        detail_state = dict()
        detail_state["detail_vars"] = tuple(self.subject_details_model.get_current_variables())
        state["details_state"] = detail_state

        #images panel
        image_state = dict()
        image_state["modality"] = str(self.ui.image_mod_combo.currentText())
        image_state["orientation"] = str(self.ui.image_orientation.currentText())
        image_state["window"] = float(self.ui.image_window.value())
        image_state["level"] = float(self.ui.image_level.value())
        image_state["slice"] = float(self.ui.slice_spin.value())
        state["image_state"] = image_state

        #segmentation panel
        segmentation_state = dict()
        segmentation_state["left_right"] = self.ui.left_right_radio.isChecked()
        segmentation_state["selected_structs"] = tuple(self.structures_tree_model.get_selected_structures())
        segmentation_state["color"] = self.__structures_color
        segmentation_state["opacity"] = float(self.vtk_viewer.get_structures_opacity())
        segmentation_state["scalar"] = str(self.ui.struct_scalar_combo.currentText())
        state["segmentation_state"] = segmentation_state

        #tractography panel
        tractography_state = dict()
        tractography_state["bundles"] = tuple(self.fibers_list_model.get_ids())
        tractography_state["from_segment"] = str(self.ui.fibers_from_segments_box.currentText())
        tractography_state["color"] = str(self.ui.tracto_color_combo.currentText())
        tractography_state["opacity"] = float(self.ui.fibers_opacity.value())
        tractography_state["scalar"] = str(self.ui.fibers_scalar_combo.currentText())
        tractography_state["active_bundle"] = self.current_fibers
        state["tractography_state"] = tractography_state

        #camera panel
        camera_state = dict()
        camera_state["space"] = str(self.ui.space_combo.currentText())
        camera_state["cam_params"] = self.vtk_viewer.get_camera_parameters()
        state["camera_state"] = camera_state

        #context panel
        context_state = dict()
        context_state["variables"] = tuple(self.context_frame.get_variables())
        context_state["editable"] = tuple(self.context_frame.get_editables())
        state["context_state"] = context_state

        #meta
        meta = dict()
        meta["date"] = datetime.datetime.now()
        meta["exec"] = sys.argv
        meta["machine"] = platform.node()
        meta["application"] = os.path.basename(__file__)[:-3]  # remove .py
        state["meta"] = meta

        print state

        dialog = SaveScenarioDialog(meta["application"],state)
        dialog.exec_()

    def load_scenario(self):
        wanted_state = dict()
        my_name = os.path.splitext(os.path.basename(__file__))[0]
        dialog = LoadScenarioDialog(my_name,wanted_state)
        dialog.exec_()
        print wanted_state

        #subject panel
        subject_state = wanted_state.get("subject_state")
        if subject_state is not None:
            subject = subject_state.get("current_subject")
            if subject is not None:
                self.change_subject(subject)
            model_cols = subject_state.get("model_columns")
            if model_cols is not None:
                self.subjects_model.set_var_columns(model_cols)


        #details panel
        detail_state = wanted_state.get("details_state")
        if detail_state is not None:
            detail_state["detail_vars"] = tuple(self.subject_details_model.get_current_variables())

        #images panel
        image_state = wanted_state.get("image_state")
        if image_state is not None:
            mod = image_state.get("modality")
            if mod is not None:
                ix=self.ui.image_mod_combo.findText(mod)
                self.ui.image_mod_combo.setCurrentIndex(ix)
                self.image_modality_change()
            orient = image_state.get("orientation")
            if orient is not None:
                ix = self.ui.image_orientation.findText(orient)
                self.ui.image_orientation.setCurrentIndex(ix)
                self.image_orientation_change()
            window= image_state.get("window")
            if window is not None:
                self.ui.image_window.setValue(window)
            level= image_state.get("level")
            if level is not None:
                self.ui.image_level.setValue(level)
            slice = image_state.get("slice")
            if slice is not None:
                self.ui.slice_spin.setValue(slice)

        #segmentation panel
        segmentation_state =wanted_state.get("segmentation_state")
        if segmentation_state is not None:
            left_right = segmentation_state.get("left_right")
            if left_right is not None:
                self.ui.left_right_radio.setChecked(left_right)
                self.ui.dom_nondom_radio.setChecked(not left_right)
            color = segmentation_state.get("color",False)
            if color is not False:
                self.__structures_color = color
                if color is not None:
                    if self.ui.struct_color_combo.count() < 3:
                        self.ui.struct_color_combo.addItem("Custom")
                    self.ui.struct_color_combo.setCurrentIndex(2)
                    self.vtk_viewer.set_structures_color(color)
                else:
                    self.ui.struct_color_combo.setCurrentIndex(0)
                    #self.vtk_viewer.set_structures_color(None)
                    if self.ui.struct_color_combo.count() == 3:
                        self.ui.struct_color_combo.removeItem(2)

            opac = segmentation_state.get("opacity")
            if opac is not None:
                self.ui.struct_opacity_slider.setValue(opac)
            scal = segmentation_state.get("scalar")
            if scal is not None:
                ix = self.ui.struct_scalar_combo.findText(scal)
                self.ui.struct_scalar_combo.setCurrentIndex(ix)
                #self.update_segmentation_scalar(ix)
            selected_structs=segmentation_state.get("selected_structs")
            if selected_structs is not None:
                self.structures_tree_model.set_selected_structures(selected_structs)

        #tractography panel
        tractography_state = wanted_state.get("tractography_state")
        if tractography_state is not None:
            bundles = tractography_state.get("bundles")
            if bundles is not None:
                self.fibers_list_model.set_ids(bundles)
                self.vtk_viewer.set_fibers_from_db(bundles)
            from_segment = tractography_state.get("from_segment")
            if from_segment is not None:
                idx = self.ui.fibers_from_segments_box.findText(from_segment)
                self.ui.fibers_from_segments_box.setCurrentIndex(idx)
                #self.show_fibers_from_segment(idx)
            color = tractography_state.get("color")
            if color is not None:
                idx = self.ui.tracto_color_combo.findText(color)
                self.ui.tracto_color_combo.setCurrentIndex(idx)
                #self.change_tractography_color(idx)
            opac = tractography_state.get("opacity")
            if opac is not None:
                self.ui.fibers_opacity.setValue(opac)
            scal = tractography_state["scalar"]
            if scal is not None:
                idx=self.ui.fibers_scalar_combo.findText(scal)
                self.ui.fibers_scalar_combo.setCurrentIndex(idx)
                self.update_fiber_scalars(idx)
            current = tractography_state.get("active_bundle",False)
            if current is not False:
                self.current_fibers = current
                if current is None:
                    self.ui.current_bundle_tag.setText("<No active bundle>")
                elif isinstance(current,str):
                    self.ui.current_bundle_tag.setText(current)
                else:
                    name = self.fibers_list_model.get_bundle_name(current)
                    self.ui.current_bundle_tag.setText(name)
                self.update_fiber_scalars()

        #camera panel
        camera_state = wanted_state.get("camera_state")
        if camera_state is not  None:
            space = camera_state.get("space")
            if space is not None:
                idx = self.ui.space_combo.findText(space)
                self.ui.space_combo.setCurrentIndex(idx)
                self.space_change()
            cam = camera_state.get("cam_params")
            if cam is not None:
                fp,pos,vu = cam
                self.vtk_viewer.set_camera(fp,pos,vu)

        #context panel
        context_state = wanted_state.get("context_state")
        if context_state is not None:
            variables = context_state.get("variables")
            if variables is not None:
                editables = context_state.get("editable")
                if editables is not None:
                    editables = dict(editables)
                self.context_frame.set_variables(variables,editables)
                self.context_frame.set_subject(self.__curent_subject)
        return

    def poll_from_pipe(self):
        if self.__pipe is not None:
            if self.__pipe.poll():
                message = self.__pipe.recv()
                subj = message.get('subject')
                self.change_subject(subj)


def run(pipe=None):
    import sys

    app = QtGui.QApplication(sys.argv)
    main_window = SubjectOverviewApp(pipe)
    main_window.show()
    main_window.start()
    app.exec_()


if __name__ == '__main__':
    run()