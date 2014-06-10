from __future__ import division

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

import numpy as np
import datetime
import platform
import os

import braviz
import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data
from braviz.interaction.qt_guis.subject_overview import Ui_subject_overview
from braviz.interaction.qt_models import SubjectsTable, SubjectDetails, StructureTreeModel, SimpleBundlesList
from braviz.visualization.subject_viewer import QSubjectViwerWidget
from braviz.interaction.qt_dialogs import GenericVariableSelectDialog, ContextVariablesPanel, BundleSelectionDialog, \
    SaveFibersBundleDialog, SaveScenarioDialog, LoadScenarioDialog
from braviz.interaction.qt_sample_select_dialog import SampleLoadDialog
import subprocess
import multiprocessing.connection
import binascii
import cPickle
import functools
import logging

#TODO only load scalar metrics if visible

surfaces_scalars_dict={0 : "curv", 1 : "avg_curv", 2: "thickness",
                         3: "sulc", 4: "aparc", 5: "aparc.a2009s", 6: "BA"}

class SubjectOverviewApp(QMainWindow):
    def __init__(self, pipe_key=None,scenario=None):
        #Super init
        QMainWindow.__init__(self)
        #Internal initialization
        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.__curent_subject = None
        self.__pipe = pipe_key
        log = logging.getLogger(__name__)
        if pipe_key is not None:
            log.info("Got pipe key")
            log.info(pipe_key)
            pipe_key_bin = binascii.a2b_hex(pipe_key)

            address = ("localhost", 6001)
            self.__pipe = multiprocessing.connection.Client(address, authkey=pipe_key_bin)
            self.__pipe_check_timer = QtCore.QTimer()
            self.__pipe_check_timer.timeout.connect(self.poll_from_pipe)
            self.__pipe_check_timer.start(200)
        else:
            self.__pipe_check_timer = None

        initial_vars = (11, 17, 1)

        self.vtk_widget = QSubjectViwerWidget(reader=self.reader, parent=self)
        self.vtk_viewer = self.vtk_widget.subject_viewer
        self.subjects_model = SubjectsTable(initial_vars)
        self.sample = braviz_tab_data.get_subjects()

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

        #surfaces_state
        self.surfaces_state = dict()

        #Init gui
        self.ui = None
        self.setup_gui()

        if scenario is not None:
            scn_data_str=braviz_user_data.get_scenario_data(scenario)
            scn_data = cPickle.loads(str(scn_data_str))
            load_scn = functools.partial(self.load_scenario,scn_data)
            QtCore.QTimer.singleShot(0,load_scn)

    def start(self):
        self.vtk_widget.initialize_widget()
        #load initial
        self.vtk_viewer.image.change_image_modality("MRI")
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
        self.ui.select_subject_table_vars.clicked.connect(self.launch_subject_variable_select_dialog)
        self.ui.subjects_table.activated.connect(self.change_subject)
        self.ui.next_subject.clicked.connect(self.go_to_next_subject)
        self.ui.previus_subject.clicked.connect(self.go_to_previus_subject)
        self.ui.select_sample_button.clicked.connect(self.show_select_sample_dialog)

        #subject details
        self.ui.subject_details_table.setModel(self.subject_details_model)
        self.ui.select_details_button.clicked.connect(self.launch_details_variable_select_dialog)
        #image controls
        self.ui.image_mod_combo.activated.connect(self.image_modality_change)
        self.ui.image_orientation.activated.connect(self.image_orientation_change)
        self.vtk_widget.slice_changed.connect(self.ui.slice_slider.setValue)
        self.ui.slice_slider.valueChanged.connect(self.vtk_viewer.image.set_image_slice)
        self.vtk_widget.image_window_changed.connect(self.ui.image_window.setValue)
        self.vtk_widget.image_level_changed.connect(self.ui.image_level.setValue)
        self.ui.image_window.valueChanged.connect(self.vtk_viewer.image.set_image_window)
        self.ui.image_level.valueChanged.connect(self.vtk_viewer.image.set_image_level)
        self.ui.reset_window_level.clicked.connect(self.vtk_viewer.image.reset_window_level)
        fmri_paradigms = self.reader.get("fmri",None,index=True)
        for pdg in fmri_paradigms:
            self.ui.image_mod_combo.addItem(pdg)
        #MRI
        self.ui.image_mod_combo.setCurrentIndex(1)
        #segmentation controls
        self.ui.structures_tree.setModel(self.structures_tree_model)
        self.connect(self.structures_tree_model, QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"),
                     self.ui.structures_tree.dataChanged)
        self.structures_tree_model.selection_changed.connect(self.update_segmented_structures)
        self.ui.struct_opacity_slider.valueChanged.connect(self.vtk_viewer.models.set_opacity)
        self.ui.left_right_radio.toggled.connect(self.change_left_to_non_dominant)
        self.ui.struct_color_combo.currentIndexChanged.connect(self.select_structs_color)
        self.ui.struct_scalar_combo.currentIndexChanged.connect(self.update_segmentation_scalar)
        self.ui.export_segmentation_to_db.clicked.connect(self.export_segmentation_scalars_to_db)
        #tractography controls
        self.ui.fibers_from_segments_box.currentIndexChanged.connect(self.show_fibers_from_segment)
        self.ui.tracto_color_combo.currentIndexChanged.connect(self.change_tractography_color)
        self.ui.show_color_bar_check.toggled.connect(self.toggle_tractography_color_bar)
        self.ui.bundles_list.setModel(self.fibers_list_model)
        self.ui.add_saved_bundles.clicked.connect(self.add_saved_bundles_to_list)
        self.ui.save_bundle_button.clicked.connect(self.save_fibers_bundle)
        self.ui.fibers_opacity.valueChanged.connect(self.change_tractography_opacity)
        self.ui.bundles_list.activated.connect(self.update_current_bundle)
        self.ui.bundles_list.clicked.connect(self.update_current_bundle)
        self.ui.fibers_scalar_combo.currentIndexChanged.connect(self.update_fiber_scalars)
        self.ui.export_fiber_scalars_to_db.clicked.connect(self.export_fiber_scalars_to_db)
        #surface panel
        self.ui.surface_left_check.toggled.connect(self.update_surfaces_from_gui)
        self.ui.surface_right_check.toggled.connect(self.update_surfaces_from_gui)
        self.ui.surface_select_combo.currentIndexChanged.connect(self.update_surfaces_from_gui)
        self.ui.surface_scalars_combo.currentIndexChanged.connect(self.update_surfaces_from_gui)
        self.ui.surface_color_bar_check.toggled.connect(self.update_surfaces_from_gui)
        self.ui.surf_opacity_slider.valueChanged.connect(self.update_surfaces_from_gui)
        #view frame
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
        #self.vtk_viewer.show_cone()

        #context view
        self.context_frame = ContextVariablesPanel(self.ui.splitter_2, "Context",app=self)

        #menubar
        self.ui.actionSave_scenario.triggered.connect(self.save_state)
        self.ui.actionLoad_scenario.triggered.connect(self.load_scenario_dialog)


    def change_subject(self, new_subject=None):
        if isinstance(new_subject, QtCore.QModelIndex):
            selected_index = new_subject
            subj_code_index = self.subjects_model.index(selected_index.row(), 0)
            new_subject = self.subjects_model.data(subj_code_index, QtCore.Qt.DisplayRole)

        if self.__pipe is not None:
            self.__pipe.send({'subject': str(new_subject)})
        #label
        logger = logging.getLogger(__name__)
        logger.info("Changing subject to %s"%new_subject)
        self.__curent_subject = new_subject
        self.ui.subject_id.setText("%s" % new_subject)
        self.ui.subject_id2.setText("%s" % new_subject)
        #details
        self.subject_details_model.change_subject(new_subject)
        #image
        image_code = str(braviz_tab_data.get_var_value(braviz_tab_data.IMAGE_CODE, int(new_subject)))
        if len(image_code) < 3:
            image_code = "0" + image_code
        log = logging.getLogger(__name__)
        log.info("Image Code: %s", image_code)
        try:
            self.vtk_viewer.change_subject(image_code)
        except Exception as e:
            self.show_error(e.message)
            log.warning(e.message)
            #raise
        self.reset_image_view_controls()
        #context
        self.update_segmentation_scalar()
        self.update_fiber_scalars()
        self.context_frame.set_subject(new_subject)


    def show_error(self, message):
        logger = logging.getLogger(__name__)
        logger.warning(message)
        self.statusBar().showMessage(message, 5000)

    def image_modality_change(self):
        selection = str(self.ui.image_mod_combo.currentText())
        log = logging.getLogger(__name__)
        log.info("changing image mod to %s"%selection)
        if selection == "None":
            self.vtk_viewer.image.hide_image()
            self.ui.image_orientation.setEnabled(0)
            self.ui.image_window.setEnabled(0)
            self.ui.image_level.setEnabled(0)
            self.ui.reset_window_level.setEnabled(0)
            self.ui.slice_spin.setEnabled(0)
            self.ui.slice_slider.setEnabled(0)
            self.reset_image_view_controls()
            return

        self.vtk_viewer.image.show_image()
        if selection in ("MRI", "FA", "APARC", "MD", "DTI"):
            self.vtk_viewer.image.change_image_modality(selection)
        else:
            try:
                self.vtk_viewer.image.change_image_modality("FMRI", selection)
            except Exception as e:
                log.warning(e.message)
                self.statusBar().showMessage(e.message, 5000)

        self.ui.image_orientation.setEnabled(1)
        self.ui.slice_spin.setEnabled(1)
        self.ui.slice_slider.setEnabled(1)
        self.ui.slice_slider.setMaximum(self.vtk_viewer.image.get_number_of_image_slices())
        self.reset_image_view_controls()

        window_level_control = 1 if selection in ("MRI", "FA", "MD","Precision","Power") else 0
        self.ui.image_window.setEnabled(window_level_control)
        self.ui.image_level.setEnabled(window_level_control)
        self.ui.reset_window_level.setEnabled(window_level_control)

    def image_orientation_change(self):
        orientation_dict = {"Axial": 2, "Coronal": 1, "Sagital": 0}
        logger = logging.getLogger(__name__)
        selection = str(self.ui.image_orientation.currentText())
        logger.info("Changing orientation to %s"%selection)
        self.vtk_viewer.image.change_image_orientation(orientation_dict[selection])
        self.reset_image_view_controls()

    def position_camera(self):
        if self.ui.camera_pos.currentIndex() == 0:
            return
        self.print_vtk_camera()
        selection = str(self.ui.camera_pos.currentText())
        camera_pos_dict = {"Default": 0, "Left": 1, "Right": 2, "Front": 3, "Back": 4, "Top": 5, "Bottom": 6}
        logger = logging.getLogger(__name__)
        logger.info("Changing camera to %s"%selection)
        self.vtk_viewer.reset_camera(camera_pos_dict[selection])
        self.ui.camera_pos.setCurrentIndex(0)

    def space_change(self):
        new_space = str(self.ui.space_combo.currentText())
        self.vtk_viewer.change_current_space(new_space)
        log = logging.getLogger(__name__)
        log.info(new_space)

    def print_vtk_camera(self):
        self.vtk_viewer.print_camera()


    def reset_image_view_controls(self):
        self.ui.slice_slider.setMaximum(self.vtk_viewer.image.get_number_of_image_slices())
        self.ui.slice_spin.setMaximum(self.vtk_viewer.image.get_number_of_image_slices())
        self.ui.slice_slider.setValue(self.vtk_viewer.image.get_current_image_slice())
        self.ui.image_level.setValue(self.vtk_viewer.image.get_current_image_level())
        self.ui.image_window.setValue(self.vtk_viewer.image.get_current_image_window())

    def launch_subject_variable_select_dialog(self):
        params = {}
        initial_selection = self.subjects_model.get_current_columns()
        dialog = GenericVariableSelectDialog(params, multiple=True, initial_selection_names=initial_selection)
        res = dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            new_selection = params["checked"]
            self.subjects_model.set_var_columns(new_selection)
            logger = logging.getLogger(__name__)
            logger.info("new models %s"%new_selection)

    def show_select_sample_dialog(self):
        dialog = SampleLoadDialog()
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            log.info("*sample changed*")
            self.change_sample(new_sample)
            logger = logging.getLogger(__name__)
            logger.info("new sample: %s"%new_sample)

    def change_sample(self,new_sample):
        self.sample = sorted(new_sample)
        self.subjects_model.set_sample(self.sample)
        self.context_frame.set_sample(self.sample)

    def launch_details_variable_select_dialog(self):
        params = {}
        initial_selection = self.subject_details_model.get_current_variables()
        dialog = GenericVariableSelectDialog(params, multiple=True, initial_selection_idx=initial_selection,
                                             sample=self.sample)
        dialog.exec_()
        new_selection = params.get("checked")
        if new_selection is not None:
            self.subject_details_model.set_variables(sorted(new_selection))
            logger = logging.getLogger(__name__)
            logger.info("new detail variables %s"%new_selection)


    def go_to_previus_subject(self):
        current_subj_row = self.subjects_model.get_subject_index(self.__curent_subject)
        prev_row = (current_subj_row + self.subjects_model.rowCount() - 1) % self.subjects_model.rowCount()
        prev_index = self.subjects_model.index(prev_row, 0)
        self.change_subject(prev_index)

    def go_to_next_subject(self):
        try:
            current_subj_row = self.subjects_model.get_subject_index(self.__curent_subject)
        except KeyError:
            current_subj_row = -1
            #go to first subject
        next_row = (1 + current_subj_row) % self.subjects_model.rowCount()
        next_index = self.subjects_model.index(next_row, 0)
        self.change_subject(next_index)

    def update_segmented_structures(self):
        selected_structures = self.structures_tree_model.get_selected_structures()
        self.vtk_viewer.models.set_models(selected_structures)
        self.update_segmentation_scalar()
        self.show_fibers_from_segment(self.ui.fibers_from_segments_box.currentIndex())

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
            log = logging.getLogger(__name__)
            log.error("Unknown metric %s" % scalar_text)
            return
        metric_code, units = metric_params
        new_value = self.vtk_viewer.models.get_scalar_metrics(metric_code)
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
            log = logging.getLogger(__name__)
            log.error("Unknown metric %s" % scalar_text)
            return
        structures = list(self.structures_tree_model.get_selected_structures())

        scenario_data = self.get_state_dict()
        app_name = scenario_data["meta"]["application"]
        scenario_data_str = cPickle.dumps(scenario_data,2)
        scn_id = braviz_user_data.save_scenario(app_name, scenario_name="<AUTO>",
                                                scenario_description="", scenario_data=scenario_data_str)
        self.save_screenshot(scn_id)
        #export_dialog_args = {"fibers": False, "structures_list": structures,
        #                      "metric": scalar_text,"db_id": None, "operation": None}

        #export_dialog_args = fibers metric structs
        export_dialog_args = ["%d" % scn_id, "0", scalar_text] + list(structures)
        log = logging.getLogger(__name__)
        log.info(export_dialog_args)
        process_line = [sys.executable, "-m", "braviz.applications.export_scalar_to_db", ]
        #print process_line
        subprocess.Popen(process_line + export_dialog_args)

        self.ui.export_segmentation_to_db.setEnabled(0)

        def reactivate_button():
            self.ui.export_segmentation_to_db.setEnabled(1)

        QtCore.QTimer.singleShot(2000, reactivate_button)


    def change_left_to_non_dominant(self):
        #TODO: Must deal with currently selected structures
        if self.ui.left_right_radio.isChecked():
            left_right = True
        else:
            left_right = False
        self.vtk_viewer.models.set_models(tuple())
        self.structures_tree_model.reload_hierarchy(dominant=not left_right)


    def select_structs_color(self, index):
        log = logging.getLogger(__name__)
        if index == 1:
            log.info("launch choose color dialog")
            color_dialog = QtGui.QColorDialog()
            res = color_dialog.getColor()
            new_color = res.getRgb()[:3]
            new_float_color = [x / 255 for x in new_color]
            self.vtk_viewer.models.set_color(new_float_color)
            self.__structures_color = new_float_color
            #print res.getRgb()
            if self.ui.struct_color_combo.count() < 3:
                self.ui.struct_color_combo.addItem("Custom")
            self.ui.struct_color_combo.setCurrentIndex(2)
        if index == 0:
            self.vtk_viewer.models.set_color(None)
            self.__structures_color = None
            if self.ui.struct_color_combo.count() == 3:
                self.ui.struct_color_combo.removeItem(2)

    def show_fibers_from_segment(self, index):
        if index == 0:
            self.vtk_viewer.tractography.hide_checkpoints_bundle()
            self.fibers_list_model.set_show_special(False)
            self.ui.save_bundle_button.setEnabled(False)
        else:
            checkpoints = self.structures_tree_model.get_selected_structures()
            self.fibers_list_model.set_show_special(True)
            throug_all = (index == 2)
            self.ui.save_bundle_button.setEnabled(True)
            try:
                self.vtk_viewer.tractography.set_bundle_from_checkpoints(checkpoints, throug_all)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.warning(e.message)
                self.show_error(e.message)
        self.update_current_bundle()

    def change_tractography_color(self, index):
        color_codes = {0: "orient", 1: "fa_p",2:"fa_l",
                       3 : "md_p", 4: "md_l" , 5:"length",
                       6: "rand", 7: "bundle"}
        color_text = color_codes.get(index)
        logger = logging.getLogger(__name__)
        logger.info("tractography color changed to: %s"%color_text)
        if color_text is not None:
            self.vtk_viewer.tractography.change_color(color_text)
        else:
            self.show_error("Not yet implemented")

    def toggle_tractography_color_bar(self,value):
        logger = logging.getLogger(__name__)
        logger.info("tractography color bar: %s"%value)
        if isinstance(value,bool):
            self.vtk_viewer.tractography.set_show_color_bar(value)
            return
        else:
            if value == QtCore.Qt.Checked:
                self.vtk_viewer.tractography.set_show_color_bar(True)
            else:
                self.vtk_viewer.tractography.set_show_color_bar(False)

    def change_tractography_opacity(self, value):
        float_value = value / 100
        self.vtk_viewer.tractography.set_opacity(float_value)


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
                          "Mean FA": "mean_fa",
                          "Mean MD": "mean_md"}

    def update_fiber_scalars(self, index=None):
        log = logging.getLogger(__name__)
        log.info(self.current_fibers)
        if index is None:
            index = self.ui.fibers_scalar_combo.currentIndex()
        text = str(self.ui.fibers_scalar_combo.itemText(index))

        metric = self.fiber_metrics_dict.get(text)
        if metric is None:
            self.ui.fibers_scalar_value.clear()
            self.show_error("%s not yet implemented" % text)
            log = logging.getLogger(__name__)
            log.error("%s not yet implemented" % text)
            return
        if self.current_fibers is None:
            value = float("nan")
        elif type(self.current_fibers) is str:
            value = self.vtk_viewer.tractography.get_scalar_from_structs(metric)
        else:
            value = self.vtk_viewer.tractography.get_scalar_from_db(metric, self.current_fibers)
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
            log = logging.getLogger(__name__)
            log.error("Unknown metric %s" % scalar_text)
            return
        if type(self.current_fibers) is str:
            structs = list(self.structures_tree_model.get_selected_structures())
            index = self.ui.fibers_from_segments_box.currentIndex()
            operation = "and" if (index == 2) else "or"
            db_id = "0"
        else:
            db_id = self.current_fibers
            structs = []
            operation = "0"
        #export_dialog_args = {"fibers": True, "structures_list": structs,
        #                      "metric": scalar_text, "db_id": db_id, "operation": operation}
        scenario_data = self.get_state_dict()
        app_name = scenario_data["meta"]["application"]
        scenario_data_str = cPickle.dumps(scenario_data,2)
        scn_id = braviz_user_data.save_scenario(app_name, scenario_name="<AUTO>",
                                                scenario_description="", scenario_data=scenario_data_str)
        self.save_screenshot(scn_id)

        export_args = ["%d" % scn_id, "1", str(scalar_text), str(operation), str(db_id), ] + structs
        process_line = [sys.executable, "-m", "braviz.applications.export_scalar_to_db", ]
        subprocess.Popen(process_line + export_args)

        self.ui.export_fiber_scalars_to_db.setEnabled(0)

        def reactivate_button():
            self.ui.export_fiber_scalars_to_db.setEnabled(1)

        QtCore.QTimer.singleShot(2000, reactivate_button)
        log = logging.getLogger(__name__)
        log.info("launching")

    def add_saved_bundles_to_list(self):
        selected = set(self.fibers_list_model.get_ids())
        names_dict = {}
        dialog = BundleSelectionDialog(selected, names_dict)
        dialog.exec_()
        log = logging.getLogger(__name__)
        log.info(selected)
        self.fibers_list_model.set_ids(selected, names_dict)
        self.vtk_viewer.tractography.set_active_db_tracts(selected)

    def save_fibers_bundle(self):
        checkpoints = self.structures_tree_model.get_selected_structures()
        index = self.ui.fibers_from_segments_box.currentIndex()
        operation = self.ui.fibers_from_segments_box.itemText(index)
        throug_all = (index == 2)
        logger = logging.getLogger(__name__)
        logger.info("saving bundles")
        dialog = SaveFibersBundleDialog(operation, checkpoints, throug_all)
        dialog.exec_()

    def update_surfaces_from_gui(self,event=None):
        logger = logging.getLogger(__name__)
        logger.info("updating surfaces")
        left_active = self.ui.surface_left_check.isChecked()
        right_active = self.ui.surface_right_check.isChecked()
        surface = str(self.ui.surface_select_combo.currentText())
        scalars_index = self.ui.surface_scalars_combo.currentIndex()
        color_bar = self.ui.surface_color_bar_check.isChecked()
        opacity  = int(self.ui.surf_opacity_slider.value())
        # print "========="
        # print "left", left_active
        # print "right", right_active
        # print "surface", surface
        # print "scalars", scalars
        # print "color bar", color_bar
        # print "opacity = ", opacity



        self.surfaces_state["left"] = left_active
        self.surfaces_state["right"] = right_active
        self.surfaces_state["surf"] = surface
        self.surfaces_state["scalar_idx"] = scalars_index
        self.surfaces_state["color_bar"] = color_bar
        self.surfaces_state["opacity"] = opacity
        log = logging.getLogger(__name__)
        log.debug(self.surfaces_state)
        self.__update_surfaces()

    def __update_surfaces(self):
        left_active = self.surfaces_state["left"]
        right_active = self.surfaces_state["right"]
        surface = self.surfaces_state["surf"]
        scalars_index = self.surfaces_state["scalar_idx"]
        scalars = surfaces_scalars_dict[scalars_index]
        color_bar = self.surfaces_state["color_bar"]
        opacity = self.surfaces_state["opacity"]

        self.vtk_viewer.surface.set_hemispheres(left_active,right_active,skip_render=True)
        self.vtk_viewer.surface.set_surface(surface,skip_render=True)
        self.vtk_viewer.surface.set_scalars(scalars,skip_render=True)
        self.vtk_viewer.surface.set_opacity(opacity,skip_render=True)
        self.vtk_viewer.surface.show_color_bar(color_bar,skip_render=True)
        self.vtk_viewer.ren_win.Render()



    def get_state_dict(self):
        state = dict()
        #subject panel
        subject_state = dict()
        subject_state["current_subject"] = int(self.__curent_subject)
        subject_state["model_columns"] = tuple(self.subjects_model.get_current_column_indexes())
        subject_state["sample"] = tuple(self.sample)
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
        segmentation_state["opacity"] = float(self.vtk_viewer.models.get_opacity())
        segmentation_state["scalar"] = str(self.ui.struct_scalar_combo.currentText())
        state["segmentation_state"] = segmentation_state

        #tractography panel
        tractography_state = dict()
        tractography_state["bundles"] = tuple(self.fibers_list_model.get_ids())
        tractography_state["from_segment"] = str(self.ui.fibers_from_segments_box.currentText())
        tractography_state["color"] = str(self.ui.tracto_color_combo.currentText())
        tractography_state["visible_color_bar"] = self.vtk_viewer.tractography.get_show_color_bar()
        tractography_state["opacity"] = float(self.ui.fibers_opacity.value())
        tractography_state["scalar"] = str(self.ui.fibers_scalar_combo.currentText())
        tractography_state["active_bundle"] = self.current_fibers
        state["tractography_state"] = tractography_state

        #surface panel
        surfaces_state = self.surfaces_state
        state["surf_state"] = surfaces_state

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
        meta["application"] = os.path.splitext(os.path.basename(__file__))[0]
        state["meta"] = meta
        logger = logging.getLogger(__name__)
        logger.info("Current state %s"%state)
        return state

    def save_state(self):
        state = self.get_state_dict()
        meta = state["meta"]
        params={}
        dialog = SaveScenarioDialog(meta["application"], state,params)
        res=dialog.exec_()
        if res==QtGui.QDialog.Accepted:
            scn_id = params["scn_id"]
            self.save_screenshot(scn_id)


    def save_screenshot(self,scenario_index):
        file_name = "scenario_%d.png"%scenario_index
        file_path = os.path.join(self.reader.getDynDataRoot(), "braviz_data","scenarios",file_name)
        log = logging.getLogger(__name__)
        log.info(file_path)
        braviz.visualization.save_ren_win_picture(self.vtk_viewer.ren_win,file_path)


    def load_scenario_dialog(self):
        wanted_state = dict()
        my_name = os.path.splitext(os.path.basename(__file__))[0]
        dialog = LoadScenarioDialog(my_name, wanted_state, self.reader)
        dialog.exec_()
        log = logging.getLogger(__name__)
        log.info(wanted_state)

        self.load_scenario(wanted_state)

    def load_scenario(self, state):

        wanted_state = state

        #camera panel
        camera_state = wanted_state.get("camera_state")
        log = logging.getLogger(__name__)
        log.info("setting camera")
        if camera_state is not None:
            space = camera_state.get("space")
            if space is not None:
                idx = self.ui.space_combo.findText(space)
                self.ui.space_combo.setCurrentIndex(idx)
                self.space_change()
            cam = camera_state.get("cam_params")
            if cam is not None:
                fp, pos, vu = cam
                self.vtk_viewer.set_camera(fp, pos, vu)

        #subject panel
        subject_state = wanted_state.get("subject_state")
        if subject_state is not None:
            subject = subject_state.get("current_subject")
            if subject is not None:
                self.change_subject(subject)
            model_cols = subject_state.get("model_columns")
            if model_cols is not None:
                self.subjects_model.set_var_columns(model_cols)
            sample = subject_state.get("sample")
            if sample is not None:
                self.change_sample(sample)

        #details panel
        detail_state = wanted_state.get("details_state")
        if detail_state is not None:
            detail_state["detail_vars"] = tuple(self.subject_details_model.get_current_variables())

        #images panel
        image_state = wanted_state.get("image_state")
        if image_state is not None:
            mod = image_state.get("modality")
            if mod is not None:
                ix = self.ui.image_mod_combo.findText(mod)
                self.ui.image_mod_combo.setCurrentIndex(ix)
                self.image_modality_change()
            orient = image_state.get("orientation")
            if orient is not None:
                ix = self.ui.image_orientation.findText(orient)
                self.ui.image_orientation.setCurrentIndex(ix)
                self.image_orientation_change()
            window = image_state.get("window")
            if window is not None:
                self.ui.image_window.setValue(window)
            level = image_state.get("level")
            if level is not None:
                self.ui.image_level.setValue(level)
            slice = image_state.get("slice")
            if slice is not None:
                self.ui.slice_spin.setValue(slice)

        #segmentation panel
        segmentation_state = wanted_state.get("segmentation_state")
        if segmentation_state is not None:
            left_right = segmentation_state.get("left_right")
            if left_right is not None:
                self.ui.left_right_radio.setChecked(left_right)
                self.ui.dom_nondom_radio.setChecked(not left_right)
            color = segmentation_state.get("color", False)
            if color is not False:
                self.__structures_color = color
                if color is not None:
                    if self.ui.struct_color_combo.count() < 3:
                        self.ui.struct_color_combo.addItem("Custom")
                    self.ui.struct_color_combo.setCurrentIndex(2)
                    self.vtk_viewer.models.set_color(color)
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
            selected_structs = segmentation_state.get("selected_structs")
            if selected_structs is not None:
                self.structures_tree_model.set_selected_structures(selected_structs)

        #tractography panel
        tractography_state = wanted_state.get("tractography_state")
        if tractography_state is not None:
            bundles = tractography_state.get("bundles")
            if bundles is not None:
                self.fibers_list_model.set_ids(bundles)
                self.vtk_viewer.tractography.set_active_db_tracts(bundles)
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
            visible_color_bar = tractography_state.get("visible_color_bar")
            if visible_color_bar is not None:
                self.vtk_viewer.tractography.set_show_color_bar(visible_color_bar)
            opac = tractography_state.get("opacity")
            if opac is not None:
                self.ui.fibers_opacity.setValue(opac)
            scal = tractography_state["scalar"]
            if scal is not None:
                idx = self.ui.fibers_scalar_combo.findText(scal)
                self.ui.fibers_scalar_combo.setCurrentIndex(idx)
                self.update_fiber_scalars(idx)
            current = tractography_state.get("active_bundle", False)
            if current is not False:
                self.current_fibers = current
                if current is None:
                    self.ui.current_bundle_tag.setText("<No active bundle>")
                elif isinstance(current, str):
                    self.ui.current_bundle_tag.setText(current)
                else:
                    name = self.fibers_list_model.get_bundle_name(current)
                    self.ui.current_bundle_tag.setText(name)
                self.update_fiber_scalars()

        #surface panel
        surface_state = wanted_state.get("surf_state")
        if surface_state is not None:
            self.surfaces_state = surface_state

            #update gui
            left_active = self.surfaces_state["left"]
            self.ui.surface_left_check.setChecked(left_active)
            right_active = self.surfaces_state["right"]
            self.ui.surface_right_check.setChecked(right_active)
            surface = self.surfaces_state["surf"]
            index = self.ui.surface_select_combo.findText(surface)
            self.ui.surface_select_combo.setCurrentIndex(index)
            scalar_index = self.surfaces_state["scalar_idx"]
            self.ui.surface_scalars_combo.setCurrentIndex(scalar_index)
            color_bar = self.surfaces_state["color_bar"]
            self.ui.surface_color_bar_check.setChecked(color_bar)
            opacity = self.surfaces_state["opacity"]
            self.ui.surf_opacity_slider.setValue(opacity)
            self.__update_surfaces()

        #context panel
        context_state = wanted_state.get("context_state")
        if context_state is not None:
            variables = context_state.get("variables")
            if variables is not None:
                editables = context_state.get("editable")
                if editables is not None:
                    editables = dict(editables)
                self.context_frame.set_variables(variables, editables)
                self.context_frame.set_subject(self.__curent_subject)
        return

    def poll_from_pipe(self):
        if self.__pipe is not None:
            if self.__pipe.poll():
                message = self.__pipe.recv()
                subj = message.get('subject')
                self.change_subject(subj)
                scenario = message.get("scenario")
                if scenario is not None:
                    scn_str = braviz_user_data.get_scenario_data(scenario)
                    scn_dict = cPickle.loads(str(scn_str))
                    try:
                        scn_dict["subject_state"].pop("current_subject")
                    except KeyError:
                        pass
                    self.load_scenario(scn_dict)


def run(pipe_key,scenario):
    app = QtGui.QApplication([])
    main_window = SubjectOverviewApp(pipe_key,scenario)
    main_window.show()
    main_window.start()
    log = logging.getLogger(__name__)
    log.info("before exec")
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    #args: [scenario] [pipe_key]
    import sys

    from braviz.utilities import configure_logger
    configure_logger("subject_overview")
    log = logging.getLogger(__name__)
    print "ya"
    log.info(sys.argv)
    scenario = None
    if len(sys.argv)>=2 :
        maybe_scene = int(sys.argv[1])
        if maybe_scene > 0:
            scenario = maybe_scene


    if len(sys.argv) >= 3:
        key = sys.argv[2]
    else:
        key = None
    run(key,scenario)