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
from braviz.utilities import set_pyqt_api_2
set_pyqt_api_2()
import braviz
import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

import numpy as np
import datetime
import platform
import os

from braviz.visualization.simple_vtk import save_ren_win_picture
import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data
from braviz.interaction.qt_guis.subject_overview import Ui_subject_overview
from braviz.interaction.qt_models import SubjectsTable, SubjectDetails, StructureTreeModel, SimpleBundlesList, \
    SimpleCheckModel
from braviz.visualization.subject_viewer import QSubjectViewerWidget
from braviz.interaction.qt_dialogs import GenericVariableSelectDialog, BundleSelectionDialog, \
    SaveFibersBundleDialog, SaveScenarioDialog, LoadScenarioDialog
from braviz.applications.sample_select import SampleLoadDialog
from braviz.readAndFilter.config_file import get_config
from braviz.interaction.qt_widgets import ListValidator, ContextVariablesPanel, ImageComboBoxManager, \
    ContrastComboManager
import subprocess
from braviz.interaction.connection import MessageClient
import cPickle
import functools
import logging

__author__ = 'Diego'

# TODO only load scalar metrics if visible, lazy loading


surfaces_scalars_dict = {0: "curv", 1: "avg_curv", 2: "thickness",
                         3: "sulc", 4: "aparc", 5: "aparc.a2009s", 7: "BA", 6: "aparc.DKTatlas40"}


class SubjectOverviewApp(QMainWindow):

    def __init__(self, server_broadcast_address=None, server_receive_address=None, scenario=None, subject=None):
        # Super init
        QMainWindow.__init__(self)

        # Internal initialization
        config = get_config(__file__)
        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.__curent_subject = config.get_default_subject()
        log = logging.getLogger(__name__)
        self._messages_client = None
        if server_broadcast_address is not None or server_receive_address is not None:
            self._messages_client = MessageClient(
                server_broadcast_address, server_receive_address)
            self._messages_client.message_received.connect(
                self.receive_message)
            log.info("started messages client")

        def_vars = config.get_default_variables()
        def_var_codes = [
            braviz_tab_data.get_var_idx(x) for x in def_vars.values()]
        def_var_codes = filter(lambda x: x is not None, def_var_codes)
        initial_vars = def_var_codes
        self.__context_variables = def_var_codes
        initial_details_vars = def_var_codes

        self.vtk_widget = QSubjectViewerWidget(reader=self.reader, parent=self)
        self.vtk_viewer = self.vtk_widget.subject_viewer
        self.subjects_model = SubjectsTable(initial_vars)
        self.__demo_timer = QtCore.QTimer()
        self.__demo_timer.timeout.connect(self.go_to_next_subject)
        self.sample = braviz_tab_data.get_subjects()

        self.__frozen_subject = False
        self.__previous_subject = None

        # context panel
        self.context_frame = None

        # select first subject
        if subject is not None:
            self.__curent_subject = subject

        self.subject_details_model = SubjectDetails(initial_vars=initial_details_vars,
                                                    initial_subject=self.__curent_subject)
        # Structures model
        self.structures_tree_model = StructureTreeModel(self.reader)
        self.__structures_color = None

        # Fibers list model
        self.fibers_list_model = SimpleBundlesList()
        self.current_fibers = None
        # tracula model
        bundles = self.reader.get("TRACULA", None, index=True)
        self.tracula_model = SimpleCheckModel(bundles)
        # surfaces_state
        self.surfaces_state = dict()

        # Init gui
        self.ui = None
        self.__image_combo_manager = ImageComboBoxManager(self.reader, show_none=True)
        self.__image_contrast_manager = ContrastComboManager(self.reader)
        self.__contours_contrast_manager = ContrastComboManager(self.reader)
        self.setup_gui()

        if scenario is not None:
            scn_data = braviz_user_data.get_scenario_data_dict(scenario)
            if subject is not None:
                scn_data["subject_state"]["current_subject"] = subject
            load_scn = functools.partial(self.load_scenario, scn_data)
            QtCore.QTimer.singleShot(0, load_scn)

    def start(self):
        self.vtk_widget.initialize_widget()
        # load initial
        self.change_subject(self.__curent_subject)
        self.vtk_viewer.change_current_space("Talairach", skip_render=True)
        try:
            self.__image_combo_manager.set_image("IMAGE","MRI")
        except Exception as e:
            self.show_error(e.message)
        self.reset_image_view_controls()
        # self.vtk_viewer.show_cone()

    def setup_gui(self):
        self.ui = Ui_subject_overview()
        self.ui.setupUi(self)

        # control frame
        # view controls
        self.ui.camera_pos.activated.connect(self.position_camera)
        self.ui.space_combo.activated.connect(self.space_change)
        self.ui.space_combo.setCurrentIndex(1)

        # subject fast controls
        self.ui.subject_completer = QtGui.QCompleter(
            [str(s) for s in self.sample])
        self.ui.subject_id.setCompleter(self.ui.subject_completer)
        self.ui.subj_validator = ListValidator([str(s) for s in self.sample])
        self.ui.subject_id.setValidator(self.ui.subj_validator)
        self.ui.subject_id.editingFinished.connect(
            self.subject_from_subj_id_editor)
        self.ui.next_subject.clicked.connect(self.go_to_next_subject)
        self.ui.previus_subject.clicked.connect(self.go_to_previus_subject)

        self.ui.freeze_subject.toggled.connect(self.toggle_subject_freeze)
        self.ui.reload_last_subject.clicked.connect(self.reload_last_subject)

        # Subject selection
        self.ui.subjects_table.setModel(self.subjects_model)
        self.ui.select_subject_table_vars.clicked.connect(
            self.launch_subject_variable_select_dialog)
        self.ui.subjects_table.activated.connect(self.change_subject)
        self.ui.select_sample_button.clicked.connect(
            self.show_select_sample_dialog)

        # subject details
        self.ui.subject_details_table.setModel(self.subject_details_model)
        self.ui.select_details_button.clicked.connect(
            self.launch_details_variable_select_dialog)

        self.ui.comments_save.clicked.connect(self.save_comments)

        # image controls
        self.__image_combo_manager.setup(self.ui.image_mod_combo)
        self.__image_combo_manager.image_changed.connect(self.image_modality_change)

        # contrast
        self.__image_contrast_manager.setup(self.ui.contrast_combo)
        self.__image_contrast_manager.contrast_changed.connect(self.img_change_contrast)


        self.ui.image_orientation.activated.connect(
            self.image_orientation_change)
        self.vtk_widget.slice_changed.connect(self.ui.slice_slider.setValue)
        self.ui.slice_slider.valueChanged.connect(
            self.vtk_viewer.image.set_image_slice)
        self.vtk_widget.image_window_changed.connect(
            self.ui.image_window.setValue)
        self.vtk_widget.image_level_changed.connect(
            self.ui.image_level.setValue)
        self.ui.image_window.valueChanged.connect(
            self.vtk_viewer.image.set_image_window)
        self.ui.image_level.valueChanged.connect(
            self.vtk_viewer.image.set_image_level)
        self.ui.reset_window_level.clicked.connect(
            self.vtk_viewer.image.reset_window_level)

        # fMRI Contours controls

        available_paradigms = self.reader.get("FMRI", None, index = True)
        self.ui.fmri_paradigm_combo.clear()
        for p in available_paradigms:
            self.ui.fmri_paradigm_combo.addItem(p.title())
        self.ui.fmri_paradigm_combo.activated.connect(self.fmri_change_pdgm)

        self.__contours_contrast_manager.setup(self.ui.fmri_contrast_combo)
        self.__contours_contrast_manager.contrast_changed.connect(self.fmri_change_contrast)

        self.ui.fmri_show_contours_check.clicked.connect(
            self.fmri_update_contours)
        self.ui.fmri_show_contours_value.valueChanged.connect(
            self.fmri_update_contours)


        # segmentation controls
        self.ui.structures_tree.setModel(self.structures_tree_model)
        self.connect(self.structures_tree_model, QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"),
                     self.ui.structures_tree.dataChanged)
        self.structures_tree_model.selection_changed.connect(
            self.update_segmented_structures)
        self.ui.struct_opacity_slider.valueChanged.connect(
            self.vtk_viewer.models.set_opacity)
        self.ui.left_right_radio.toggled.connect(
            self.change_left_to_non_dominant)
        self.ui.struct_color_combo.currentIndexChanged.connect(
            self.select_structs_color)
        self.ui.struct_scalar_combo.currentIndexChanged.connect(
            self.update_segmentation_scalar)
        self.ui.export_segmentation_to_db.clicked.connect(
            self.export_segmentation_scalars_to_db)
        # tractography controls
        self.ui.fibers_from_segments_box.currentIndexChanged.connect(
            self.show_fibers_from_segment)
        self.ui.tracto_color_combo.currentIndexChanged.connect(
            self.change_tractography_color)
        self.ui.show_color_bar_check.toggled.connect(
            self.toggle_tractography_color_bar)
        self.ui.bundles_list.setModel(self.fibers_list_model)
        self.ui.add_saved_bundles.clicked.connect(
            self.add_saved_bundles_to_list)
        self.ui.save_bundle_button.clicked.connect(self.save_fibers_bundle)
        self.ui.fibers_opacity.valueChanged.connect(
            self.change_tractography_opacity)
        self.ui.bundles_list.activated.connect(self.update_current_bundle)
        self.ui.bundles_list.clicked.connect(self.update_current_bundle)
        self.ui.fibers_scalar_combo.currentIndexChanged.connect(
            self.update_fiber_scalars)
        self.ui.export_fiber_scalars_to_db.clicked.connect(
            self.export_fiber_scalars_to_db)

        # tracula panel
        self.ui.tracula_list.setModel(self.tracula_model)
        self.tracula_model.dataChanged.connect(self.update_tracula)
        self.ui.tracula_opac.valueChanged.connect(self.update_tracula_opacity)
        # surface panel
        self.ui.surface_left_check.toggled.connect(
            self.update_surfaces_from_gui)
        self.ui.surface_right_check.toggled.connect(
            self.update_surfaces_from_gui)
        self.ui.surface_select_combo.currentIndexChanged.connect(
            self.update_surfaces_from_gui)
        self.ui.surface_scalars_combo.currentIndexChanged.connect(
            self.update_surfaces_from_gui)
        self.ui.surface_color_bar_check.toggled.connect(
            self.update_surfaces_from_gui)
        self.ui.surf_opacity_slider.valueChanged.connect(
            self.update_surfaces_from_gui)
        # view frame
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
        # self.vtk_viewer.show_cone()

        # context view
        self.context_frame = ContextVariablesPanel(self.ui.splitter_2, "Context", app=self,
                                                   initial_variable_idxs=self.__context_variables)

        # menubar
        self.ui.actionSave_scenario.triggered.connect(self.save_state)
        self.ui.actionLoad_scenario.triggered.connect(
            self.load_scenario_dialog)
        self.ui.actionAuto_loop.toggled.connect(self.toggle_demo_mode)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Right:
            self.go_to_next_subject()
        elif key == QtCore.Qt.Key_Left:
            self.go_to_previus_subject()
        else:
            super(SubjectOverviewApp, self).keyPressEvent(event)

    def toggle_subject_freeze(self):
        self.__frozen_subject = self.ui.freeze_subject.isChecked()
        enable = not self.__frozen_subject
        self.ui.subject_id.setEnabled(enable)
        self.ui.next_subject.setEnabled(enable)
        self.ui.previus_subject.setEnabled(enable)

    def subject_from_subj_id_editor(self):
        new_subj = int(self.ui.subject_id.text())
        self.change_subject(new_subj)

    def reload_last_subject(self):
        if self.__previous_subject is not None:
            self.change_subject(self.__previous_subject)

    def change_subject(self, new_subject=None, broadcast_message=True):
        logger = logging.getLogger(__name__)
        if self.__frozen_subject:
            logger.info("Frozen subject, ignoring change")
            return
        if isinstance(new_subject, QtCore.QModelIndex):
            selected_index = new_subject
            subj_code_index = self.subjects_model.index(
                selected_index.row(), 0)
            new_subject = self.subjects_model.data(
                subj_code_index, QtCore.Qt.DisplayRole)

        if self._messages_client is not None and new_subject != self.__curent_subject and broadcast_message:
            self._messages_client.send_message({'subject': new_subject})
        # label
        if new_subject != self.__curent_subject:
            self.__previous_subject = self.__curent_subject

        logger.info("Changing subject to %s" % new_subject)
        self.__curent_subject = new_subject
        self.ui.subject_id.setText("%s" % new_subject)
        self.ui.subject_id2.setText("%s" % new_subject)
        self.subjects_model.highlighted_subject = int(new_subject)
        # details
        self.subject_details_model.change_subject(new_subject)
        self.reload_comments()
        # image
        image_code = new_subject

        # if len(image_code) < 3:
        #     image_code = "0" + image_code
        log = logging.getLogger(__name__)
        log.info("Image Code: %s", image_code)
        try:
            self.vtk_viewer.change_subject(image_code)
        except Exception as e:
            self.show_error("%s:%s" % (new_subject, e.message))
            log.warning(e.message)
            # raise
        else:
            self.statusBar().showMessage("%s: ok" % new_subject, 5000)

        current_img_class, current_image_name = self.__image_combo_manager.current_class_and_name
        if current_img_class == "FMRI":
            self.__image_contrast_manager.change_paradigm(new_subject, current_image_name)

        pdgm2 = unicode(self.ui.fmri_paradigm_combo.currentText())
        self.__contours_contrast_manager.change_paradigm(new_subject, pdgm2)

        self.reset_image_view_controls()
        # context
        self.update_segmentation_scalar()
        self.update_fiber_scalars()
        self.context_frame.set_subject(new_subject)

    def show_error(self, message):
        logger = logging.getLogger(__name__)
        logger.warning(message)
        self.statusBar().showMessage(message, 5000)

    def image_modality_change(self, class_and_name):
        image_class, image_name = class_and_name
        log = logging.getLogger(__name__)
        log.info("changing image mod to %s,%s" % (image_class,image_name))
        if image_class is None:
            self.vtk_viewer.image.hide_image()
            self.ui.image_orientation.setEnabled(0)
            self.ui.image_window.setEnabled(0)
            self.ui.image_level.setEnabled(0)
            self.ui.reset_window_level.setEnabled(0)
            self.ui.slice_spin.setEnabled(0)
            self.ui.slice_slider.setEnabled(0)
            self.reset_image_view_controls()
            return

        try:
            if image_class == "FMRI":
                self.__image_contrast_manager.change_paradigm(self.__curent_subject, image_name)
                contrast = self.__image_contrast_manager.get_previous_contrast(image_name)
            else:
                self.__image_contrast_manager.change_paradigm(self.__curent_subject, None)
                contrast = None
            self.vtk_viewer.image.change_image_modality(image_class, image_name, contrast=contrast)
            self.vtk_viewer.image.show_image()
        except Exception as e:
            log.warning(e.message)
            self.statusBar().showMessage(e.message, 5000)

        self.ui.image_orientation.setEnabled(1)
        self.ui.slice_spin.setEnabled(1)
        self.ui.slice_slider.setEnabled(1)
        self.ui.slice_slider.setMaximum(
            self.vtk_viewer.image.get_number_of_image_slices())
        self.ui.slice_spin.setMaximum(
            self.vtk_viewer.image.get_number_of_image_slices())
        self.reset_image_view_controls()

        window_level_control = image_class == "IMAGE"
        self.ui.image_window.setEnabled(window_level_control)
        self.ui.image_level.setEnabled(window_level_control)
        self.ui.reset_window_level.setEnabled(window_level_control)

    def img_change_contrast(self, contrast):
        image_class, image_name = self.__image_combo_manager.current_class_and_name
        self.vtk_viewer.image.change_image_modality(image_class, image_name,
                                                    contrast=contrast)

    def fmri_change_pdgm(self):
        pdgm = unicode(self.ui.fmri_paradigm_combo.currentText())
        self.__contours_contrast_manager.change_paradigm(self.__curent_subject, pdgm)
        self.fmri_change_contrast()

    def fmri_change_contrast(self, contrast = None):
        pdgm = unicode(self.ui.fmri_paradigm_combo.currentText())
        if contrast is None:
            contrast = self.__contours_contrast_manager.get_previous_contrast(pdgm)
        self.vtk_viewer.set_fmri_contours_image(pdgm, contrast)
        self.fmri_update_contours()

    def fmri_update_contours(self, dummy=None):
        visible = self.ui.fmri_show_contours_check.isChecked()
        self.vtk_viewer.set_contours_visibility(visible)
        if visible:
            value = self.ui.fmri_show_contours_value.value()
            self.vtk_viewer.contours.set_value(value)

    def image_orientation_change(self):
        orientation_dict = {"Axial": 2, "Coronal": 1, "Sagital": 0}
        logger = logging.getLogger(__name__)
        selection = str(self.ui.image_orientation.currentText())
        logger.info("Changing orientation to %s" % selection)
        self.vtk_viewer.image.change_image_orientation(
            orientation_dict[selection])
        self.reset_image_view_controls()

    def position_camera(self):
        if self.ui.camera_pos.currentIndex() == 0:
            return
        self.print_vtk_camera()
        selection = str(self.ui.camera_pos.currentText())
        camera_pos_dict = {"Default": 0, "Left": 1, "Right":
                           2, "Front": 3, "Back": 4, "Top": 5, "Bottom": 6}
        logger = logging.getLogger(__name__)
        logger.info("Changing camera to %s" % selection)
        self.vtk_viewer.reset_camera(camera_pos_dict[selection])
        self.ui.camera_pos.setCurrentIndex(0)

    def space_change(self):
        new_space = str(self.ui.space_combo.currentText())
        self.vtk_viewer.change_current_space(new_space)
        log = logging.getLogger(__name__)
        log.info(new_space)
        self.ui.slice_slider.setMaximum(
            self.vtk_viewer.image.get_number_of_image_slices())
        self.ui.slice_spin.setMaximum(
            self.vtk_viewer.image.get_number_of_image_slices())

    def print_vtk_camera(self):
        self.vtk_viewer.print_camera()

    def reset_image_view_controls(self):
        self.ui.slice_slider.setMaximum(
            self.vtk_viewer.image.get_number_of_image_slices())
        self.ui.slice_spin.setMaximum(
            self.vtk_viewer.image.get_number_of_image_slices())
        self.ui.slice_slider.setValue(
            self.vtk_viewer.image.get_current_image_slice())
        self.ui.image_level.setValue(
            self.vtk_viewer.image.get_current_image_level())
        self.ui.image_window.setValue(
            self.vtk_viewer.image.get_current_image_window())

    def launch_subject_variable_select_dialog(self):
        params = {}
        initial_selection = self.subjects_model.get_current_columns()
        dialog = GenericVariableSelectDialog(
            params, multiple=True, initial_selection_names=initial_selection)
        res = dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            new_selection = params["checked"]
            self.subjects_model.set_var_columns(new_selection)
            logger = logging.getLogger(__name__)
            logger.info("new models %s" % new_selection)

    def show_select_sample_dialog(self):
        dialog = SampleLoadDialog()
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            log.info("*sample changed*")
            self.change_sample(new_sample)
            logger = logging.getLogger(__name__)
            logger.info("new sample: %s" % new_sample)

    def change_sample(self, new_sample):
        self.sample = sorted(new_sample)

        # update subject selection widget
        self.ui.subject_completer = QtGui.QCompleter(
            [str(s) for s in self.sample])
        self.ui.subject_id.setCompleter(self.ui.subject_completer)
        self.ui.subj_validator = ListValidator([str(s) for s in self.sample])
        self.ui.subject_id.setValidator(self.ui.subj_validator)

        self.subjects_model.set_sample(self.sample)
        # update context frame
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
            logger.info("new detail variables %s" % new_selection)

    def go_to_previus_subject(self):
        current_subj_row = self.subjects_model.get_subject_index(
            self.__curent_subject)
        prev_row = (current_subj_row + self.subjects_model.rowCount() -
                    1) % self.subjects_model.rowCount()
        prev_index = self.subjects_model.index(prev_row, 0)
        self.change_subject(prev_index)

    def go_to_next_subject(self):
        try:
            current_subj_row = self.subjects_model.get_subject_index(
                self.__curent_subject)
        except KeyError:
            current_subj_row = -1
            # go to first subject
        next_row = (1 + current_subj_row) % self.subjects_model.rowCount()
        next_index = self.subjects_model.index(next_row, 0)
        self.change_subject(next_index)

    def update_segmented_structures(self):
        selected_structures = self.structures_tree_model.get_selected_structures()
        self.vtk_viewer.models.set_models(selected_structures)
        self.update_segmentation_scalar()
        self.show_fibers_from_segment(
            self.ui.fibers_from_segments_box.currentIndex())

    def update_tracula(self):
        selected = self.tracula_model.get_selected()
        self.vtk_viewer.tracula.set_bundles(selected)

    def update_tracula_opacity(self, int_opac):
        self.vtk_viewer.tracula.set_opacity(int_opac)

    def update_segmentation_scalar(self, scalar_index=None):
        metrics_dict=None
        if braviz.readAndFilter.PROJECT == "kmc40":
            metrics_dict = {"Volume": ("volume", "mm^3"),
                            "Area": ("area", "mm^2"),
                            "FA inside": ("fa_inside", ""),
                            "MD inside": ("md_inside", "e-12")}
        elif braviz.readAndFilter.PROJECT == "kmc400":
            metrics_dict = {"Volume": ("volume", "mm^3"),
                            "Area": ("area", "mm^2"),
                            "FA inside": ("fa_inside", ""),
                            "MD inside": ("md_inside", "e-5")}

        if scalar_index is None:
            scalar_index = self.ui.struct_scalar_combo.currentIndex()
        scalar_text = str(self.ui.struct_scalar_combo.itemText(scalar_index))
        metric_params = metrics_dict.get(scalar_text)
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
            new_value_text = "%.4g %s" % (new_value, units)
            self.ui.struct_scalar_value.setText(new_value_text)
            # self.ui.struct_scalar_value.setSuffix(units)

    def export_segmentation_scalars_to_db(self):
        metrics_dict = {"Volume": ("volume", "mm^3"),
                        "Area": ("area", "mm^2"),
                        "FA inside": ("fa_inside", ""),
                        "MD inside": ("md_inside", "e-5")}
        scalar_text = str(self.ui.struct_scalar_combo.currentText())
        metric_params = metrics_dict.get(scalar_text)
        if metric_params is None:
            self.show_error("Unknown metric %s" % scalar_text)
            log = logging.getLogger(__name__)
            log.error("Unknown metric %s" % scalar_text)
            return
        structures = list(self.structures_tree_model.get_selected_structures())

        scenario_data = self.get_state_dict()
        app_name = scenario_data["meta"]["application"]
        scenario_data_str = cPickle.dumps(scenario_data, 2)
        scn_id = braviz_user_data.save_scenario(app_name, scenario_name="<AUTO>",
                                                scenario_description="", scenario_data=scenario_data_str)
        self.save_screenshot(scn_id)
        # export_dialog_args = {"fibers": False, "structures_list": structures,
        #                      "metric": scalar_text,"db_id": None, "operation": None}

        # export_dialog_args = fibers metric structs
        export_dialog_args = ["%d" %
                              scn_id, "0", scalar_text] + list(structures)
        log = logging.getLogger(__name__)
        log.info(export_dialog_args)
        process_line = [
            sys.executable, "-m", "braviz.applications.export_scalar_to_db", ]
        # print process_line
        braviz.utilities.launch_sub_process(process_line + export_dialog_args)

        self.ui.export_segmentation_to_db.setEnabled(0)

        def reactivate_button():
            self.ui.export_segmentation_to_db.setEnabled(1)

        QtCore.QTimer.singleShot(2000, reactivate_button)

    def change_left_to_non_dominant(self):
        # TODO: Must deal with currently selected structures
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
            # print res.getRgb()
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
                self.vtk_viewer.tractography.set_bundle_from_checkpoints(
                    checkpoints, throug_all)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.warning(e.message)
                self.show_error(e.message)
        self.update_current_bundle()

    def change_tractography_color(self, index):
        color_codes = {0: "orient", 1: "fa_p", 2: "fa_l",
                       3: "md_p", 4: "md_l", 5: "length",
                       6: "rand", 7: "bundle"}
        color_text = color_codes.get(index)
        logger = logging.getLogger(__name__)
        logger.info("tractography color changed to: %s" % color_text)
        if color_text is not None:
            self.vtk_viewer.tractography.change_color(color_text)
        else:
            self.show_error("Not yet implemented")

    def toggle_tractography_color_bar(self, value):
        logger = logging.getLogger(__name__)
        logger.info("tractography color bar: %s" % value)
        if isinstance(value, bool):
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
            # Just activated a from segmentation model
            if (self.current_fibers is None) and (self.ui.fibers_from_segments_box.currentIndex() > 0):
                self.current_fibers = "<From Segmentation>"
                self.ui.current_bundle_tag.setText("<From Segmentation>")
            # Invalid from segmentation bundle
            else:
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
            value = self.vtk_viewer.tractography.get_scalar_from_structs(
                metric)
        else:
            value = self.vtk_viewer.tractography.get_scalar_from_db(
                metric, self.current_fibers)
        if np.isnan(value):
            self.ui.fibers_scalar_value.clear()
        else:
            self.ui.fibers_scalar_value.setText("%.4g" % value)

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
            structs = list(
                self.structures_tree_model.get_selected_structures())
            index = self.ui.fibers_from_segments_box.currentIndex()
            operation = "and" if (index == 2) else "or"
            db_id = "0"
        else:
            db_id = self.current_fibers
            structs = []
            operation = "0"
        # export_dialog_args = {"fibers": True, "structures_list": structs,
        #                      "metric": scalar_text, "db_id": db_id, "operation": operation}
        scenario_data = self.get_state_dict()
        app_name = scenario_data["meta"]["application"]
        scenario_data_str = cPickle.dumps(scenario_data, 2)
        scn_id = braviz_user_data.save_scenario(app_name, scenario_name="<AUTO>",
                                                scenario_description="", scenario_data=scenario_data_str)
        self.save_screenshot(scn_id)

        export_args = ["%d" % scn_id, "1", str(
            scalar_text), str(operation), str(db_id), ] + structs
        process_line = [
            sys.executable, "-m", "braviz.applications.export_scalar_to_db", ]
        braviz.utilities.launch_sub_process(process_line + export_args)

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
        res = dialog.exec_()
        if res == dialog.Accepted:
            log = logging.getLogger(__name__)
            log.info(selected)
            self.fibers_list_model.set_ids(selected, names_dict)
            self.vtk_viewer.tractography.set_active_db_tracts(selected)
            if isinstance(self.current_fibers, int) and self.current_fibers not in selected:
                self.update_current_bundle()

    def save_fibers_bundle(self):
        checkpoints = self.structures_tree_model.get_selected_structures()
        index = self.ui.fibers_from_segments_box.currentIndex()
        throug_all = (index == 2)
        logger = logging.getLogger(__name__)
        logger.info("saving bundles")
        dialog = SaveFibersBundleDialog(checkpoints, throug_all)
        dialog.exec_()

    def update_surfaces_from_gui(self, event=None):
        logger = logging.getLogger(__name__)
        logger.info("updating surfaces")
        left_active = self.ui.surface_left_check.isChecked()
        right_active = self.ui.surface_right_check.isChecked()
        surface = str(self.ui.surface_select_combo.currentText())
        scalars_index = self.ui.surface_scalars_combo.currentIndex()
        color_bar = self.ui.surface_color_bar_check.isChecked()
        opacity = int(self.ui.surf_opacity_slider.value())
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

        self.vtk_viewer.surface.set_hemispheres(
            left_active, right_active, skip_render=True)
        self.vtk_viewer.surface.set_surface(surface, skip_render=True)
        self.vtk_viewer.surface.set_scalars(scalars, skip_render=True)
        self.vtk_viewer.surface.set_opacity(opacity, skip_render=True)
        self.vtk_viewer.surface.show_color_bar(color_bar, skip_render=True)
        self.vtk_viewer.ren_win.Render()

    def get_state_dict(self):
        state = dict()
        # subject panel
        subject_state = dict()
        subject_state["current_subject"] = int(self.__curent_subject)
        subject_state["model_columns"] = tuple(
            self.subjects_model.get_current_column_indexes())
        subject_state["sample"] = tuple(self.sample)
        state["subject_state"] = subject_state

        # details panel
        detail_state = dict()
        detail_state["detail_vars"] = tuple(
            self.subject_details_model.get_current_variables())
        state["details_state"] = detail_state

        # images panel
        image_state = dict()
        image_state["image_class"], image_state["image_name"] = self.__image_combo_manager.current_class_and_name
        if image_state["image_class"] == "FMRI":
            image_state["contrast"] = self.__image_contrast_manager.get_previous_contrast(image_state["image_name"])
        else:
            image_state["contrast"] = None
        image_state["orientation"] = str(
            self.ui.image_orientation.currentText())
        image_state["window"] = float(self.ui.image_window.value())
        image_state["level"] = float(self.ui.image_level.value())
        image_state["slice"] = float(self.ui.slice_spin.value())
        state["image_state"] = image_state

        # contours panel
        contours_state = dict()
        contours_state["pdgm"] = str(self.ui.fmri_paradigm_combo.currentText())
        contours_state[
            "ctrst"] = self.__contours_contrast_manager.get_previous_contrast(contours_state["pdgm"])
        contours_state[
            "visible"] = self.ui.fmri_show_contours_check.isChecked()
        contours_state["value"] = self.ui.fmri_show_contours_value.value()
        state["contour_state"] = contours_state

        # segmentation panel
        segmentation_state = dict()
        segmentation_state["left_right"] = self.ui.left_right_radio.isChecked()
        segmentation_state["selected_structs"] = tuple(
            self.structures_tree_model.get_selected_structures())
        segmentation_state["color"] = self.__structures_color
        segmentation_state["opacity"] = float(
            self.vtk_viewer.models.get_opacity())
        segmentation_state["scalar"] = str(
            self.ui.struct_scalar_combo.currentText())
        state["segmentation_state"] = segmentation_state

        # tractography panel
        tractography_state = dict()
        tractography_state["bundles"] = tuple(self.fibers_list_model.get_ids())
        tractography_state["from_segment"] = str(
            self.ui.fibers_from_segments_box.currentText())
        tractography_state["color"] = str(
            self.ui.tracto_color_combo.currentText())
        tractography_state[
            "visible_color_bar"] = self.vtk_viewer.tractography.get_show_color_bar()
        tractography_state["opacity"] = float(self.ui.fibers_opacity.value())
        tractography_state["scalar"] = str(
            self.ui.fibers_scalar_combo.currentText())
        assert self.current_fibers in tractography_state[
            "bundles"] + (None, "<From Segmentation>")
        tractography_state["active_bundle"] = self.current_fibers
        state["tractography_state"] = tractography_state

        # tracula
        tracula_state = dict()
        tracula_state["bundles"] = self.vtk_viewer.tracula.active_bundles
        tracula_state["opacity"] = self.ui.tracula_opac.value()
        state["tracula_state"] = tracula_state

        # surface panel
        self.update_surfaces_from_gui()
        surfaces_state = self.surfaces_state
        state["surf_state"] = surfaces_state

        # camera panel
        camera_state = dict()
        camera_state["space"] = str(self.ui.space_combo.currentText())
        camera_state["cam_params"] = self.vtk_viewer.get_camera_parameters()
        state["camera_state"] = camera_state

        # context panel
        context_state = dict()
        context_state["variables"] = tuple(self.context_frame.get_variables())
        context_state["editable"] = tuple(self.context_frame.get_editables())
        state["context_state"] = context_state

        # meta
        meta = dict()
        meta["date"] = datetime.datetime.now()
        meta["exec"] = sys.argv
        meta["machine"] = platform.node()
        meta["application"] = os.path.splitext(os.path.basename(__file__))[0]
        state["meta"] = meta
        logger = logging.getLogger(__name__)
        logger.info("Current state %s" % state)
        return state

    def save_state(self):
        state = self.get_state_dict()
        meta = state["meta"]
        params = {}
        dialog = SaveScenarioDialog(meta["application"], state, params)
        res = dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            scn_id = params["scn_id"]
            self.save_screenshot(scn_id)

    def save_screenshot(self, scenario_index):
        file_name = "scenario_%d.png" % scenario_index
        file_path = os.path.join(
            self.reader.get_dyn_data_root(), "braviz_data", "scenarios", file_name)
        log = logging.getLogger(__name__)
        log.info(file_path)
        save_ren_win_picture(self.vtk_viewer.ren_win, file_path)

    def load_scenario_dialog(self):
        wanted_state = dict()
        my_name = os.path.splitext(os.path.basename(__file__))[0]
        dialog = LoadScenarioDialog(my_name, wanted_state)
        dialog.exec_()
        log = logging.getLogger(__name__)
        log.info(wanted_state)

        self.load_scenario(wanted_state)

    def load_scenario(self, state):

        wanted_state = state

        # camera panel
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

        # subject panel
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

        # details panel
        detail_state = wanted_state.get("details_state")
        if detail_state is not None:
            detail_state["detail_vars"] = tuple(
                self.subject_details_model.get_current_variables())

        # images panel
        image_state = wanted_state.get("image_state")
        if image_state is not None:
            image_class = image_state.get("image_class")
            if image_class is None:
                log.warning("Couldn't get image class, trying compatibility mode")
                mod = image_state.get("modality")
                image_name = str(mod).upper()
                image_class = None
                for t in ("IMAGE","LABEL","FMRI"):
                    if image_name in self.reader.get(t,None,index=True):
                        image_class = t
                        break
                if image_name == "DTI":
                    image_class = "DTI"
            else:
                image_name = image_state["image_name"]

            cont = image_state.get("contrast", 1)
            orient = image_state.get("orientation")
            self.__image_combo_manager.set_image(image_class, image_name)
            self.__image_contrast_manager.set_contrast(cont)

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
            img_ = image_state.get("slice")
            if img_ is not None:
                self.ui.slice_spin.setValue(img_)


        # fmri Contours panel
        contours_state = wanted_state.get("contour_state")
        if contours_state is not None:
            try:
                pdgm = contours_state["pdgm"]
                ctrst = contours_state["ctrst"]
                vis = contours_state["visible"]
                val = contours_state["value"]
            except KeyError:
                log.error("Bad contours data in wanted state %s" %
                          contours_state)
            else:
                idx = self.ui.fmri_paradigm_combo.findText(pdgm)
                self.ui.fmri_paradigm_combo.setCurrentIndex(idx)
                if ctrst is not None:
                    self.__contours_contrast_manager.set_contrast(ctrst)
                self.ui.fmri_show_contours_check.setChecked(vis)
                self.ui.fmri_show_contours_value.setValue(val)
                self.fmri_change_pdgm()

        # segmentation panel
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
                    # self.vtk_viewer.set_structures_color(None)
                    if self.ui.struct_color_combo.count() == 3:
                        self.ui.struct_color_combo.removeItem(2)

            opac = segmentation_state.get("opacity")
            if opac is not None:
                self.ui.struct_opacity_slider.setValue(opac)
            scal = segmentation_state.get("scalar")
            if scal is not None:
                ix = self.ui.struct_scalar_combo.findText(scal)
                self.ui.struct_scalar_combo.setCurrentIndex(ix)
                # self.update_segmentation_scalar(ix)
            selected_structs = segmentation_state.get("selected_structs")
            if selected_structs is not None:
                self.structures_tree_model.set_selected_structures(
                    selected_structs)

        # tractography panel
        tractography_state = wanted_state.get("tractography_state")
        if tractography_state is not None:
            bundles = tractography_state.get("bundles")
            if bundles is not None:
                self.fibers_list_model.set_ids(bundles)
                try:
                    self.vtk_viewer.tractography.set_active_db_tracts(bundles)
                except Exception as e:
                    log.exception(e)
            from_segment = tractography_state.get("from_segment")
            if from_segment is not None:
                idx = self.ui.fibers_from_segments_box.findText(from_segment)
                self.ui.fibers_from_segments_box.setCurrentIndex(idx)
                # self.show_fibers_from_segment(idx)
            color = tractography_state.get("color")
            if color is not None:
                idx = self.ui.tracto_color_combo.findText(color)
                self.ui.tracto_color_combo.setCurrentIndex(idx)
                # self.change_tractography_color(idx)
            visible_color_bar = tractography_state.get("visible_color_bar")
            if visible_color_bar is not None:
                self.vtk_viewer.tractography.set_show_color_bar(
                    visible_color_bar)
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
                try:
                    if isinstance(current, str):
                        self.ui.current_bundle_tag.setText(current)
                    else:
                        name = self.fibers_list_model.get_bundle_name(current)
                        self.ui.current_bundle_tag.setText(name)
                except Exception as e:
                    log.exception(e)
                    current = None
                if current is None:
                    self.ui.current_bundle_tag.setText("<No active bundle>")

                self.update_fiber_scalars()

        # tracula_panel
        tracula_state = wanted_state.get("tracula_state")
        if tracula_state is not None:
            bundles = tracula_state["bundles"]
            opac = tracula_state["opacity"]
            self.tracula_model.set_selection(bundles)
            self.ui.tracula_opac.setValue(opac)
            self.vtk_viewer.tracula.set_opacity(opac)
            self.vtk_viewer.ren.Render()

        # surface panel
        surface_state = wanted_state.get("surf_state")
        if surface_state is not None:
            self.surfaces_state = dict(surface_state)

            # update gui
            try:
                left_active = surface_state["left"]
                self.ui.surface_left_check.setChecked(left_active)
                right_active = surface_state["right"]
                self.ui.surface_right_check.setChecked(right_active)
                surface = surface_state["surf"]
                index = self.ui.surface_select_combo.findText(surface)
                self.ui.surface_select_combo.setCurrentIndex(index)
                scalar_index = surface_state["scalar_idx"]
                self.ui.surface_scalars_combo.setCurrentIndex(scalar_index)
                color_bar = surface_state["color_bar"]
                self.ui.surface_color_bar_check.setChecked(color_bar)
                opacity = surface_state["opacity"]
                self.ui.surf_opacity_slider.setValue(opacity)
                self.surfaces_state = surface_state

            except KeyError:
                pass
            else:
                self.__update_surfaces()

        # context panel
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

    def receive_message(self, msg):
        log = logging.getLogger(__file__)
        log.info("RECEIVED: %s" % msg)
        subj = msg.get("subject")
        if subj is not None:
            self.change_subject(subj, broadcast_message=False)

    def reload_comments(self):
        comment = braviz_user_data.get_comment(self.__curent_subject)
        if len(comment) == 0:
            self.ui.comments_box.clear()
        else:
            self.ui.comments_box.setPlainText(comment)

    def save_comments(self):
        comment = unicode(self.ui.comments_box.toPlainText())
        braviz_user_data.update_comment(self.__curent_subject, comment)
        self.statusBar().showMessage("comments saved", 2000)

    def toggle_demo_mode(self, active):
        if active:
            interval = (QtGui.QInputDialog.getInt(self, "Set loop interval",
                                                  "Interval (s):", 20, 0, 1000))
            if interval[1] is True:
                self.__demo_timer.start(interval[0] * 1000)
            else:
                self.ui.actionAuto_loop.setChecked(False)
        else:
            self.__demo_timer.stop()


def run(server_broadcast=None, server_receive=None, scenario=None, subject=None):
    """
    Launches the subject_overview application

    Args:
        server_broadcast (str) : The address used by a message broker to broadcast message
        server_receive (str) : The address used by a message broker to receive messages
        scenario (int) : The scenario id to load at startup
        subject : The subject id to load at startup
    """
    app = QtGui.QApplication([])
    main_window = SubjectOverviewApp(
        server_broadcast, server_receive, scenario, subject)
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
    # args: [scenario] [server_broadcast] [server_receive] [subject]
    import sys

    from braviz.utilities import configure_logger_from_conf
    configure_logger_from_conf("subject_overview")
    # configure_logger("subject_overview")
    log = logging.getLogger(__name__)
    log.info(sys.argv)
    scenario = None

    server_broadcast = None
    server_receive = None
    subject = None
    if len(sys.argv) >= 2:
        maybe_scene = int(sys.argv[1])
        if maybe_scene > 0:
            scenario = maybe_scene
        if len(sys.argv) >= 3:
            server_broadcast = sys.argv[2]
            if len(sys.argv) >= 4:
                server_receive = sys.argv[3]
                if len(sys.argv) >= 5:
                    subject = sys.argv[4]

    run(server_broadcast, server_receive, scenario, subject)
