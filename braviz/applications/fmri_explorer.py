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


from __future__ import division, print_function
from braviz.utilities import set_pyqt_api_2
set_pyqt_api_2()

from itertools import izip, repeat
import logging

from PyQt4 import QtCore, QtGui
import pandas as pd
import seaborn as sns
import numpy as np

import braviz
from braviz.interaction.qt_widgets import ListValidator, ContrastComboManager
from braviz.interaction.sample_select import SampleManager
import braviz.visualization.subject_viewer
import braviz.visualization.fmri_timeseries
from braviz.readAndFilter import tabular_data as braviz_tab_data
from braviz.interaction.qt_models import DataFrameModel
from braviz.interaction import qt_dialogs
from braviz.interaction.connection import MessageClient
from braviz.interaction.qt_guis.fmri_explore import Ui_fMRI_Explorer
from braviz.readAndFilter.config_file import get_config


__author__ = 'Diego'


class FmriExplorer(QtGui.QMainWindow):

    def __init__(self, scenario, server_broadcast_address, server_receive_address):
        super(FmriExplorer, self).__init__()
        log = logging.getLogger(__name__)
        config = get_config(__file__)

        self.__reader = braviz.readAndFilter.BravizAutoReader()

        self.__current_subject = config.get_default_subject()
        self.__current_paradigm = None
        self.__current_contrast = 1

        self.__frozen_points = pd.DataFrame(
            columns=["Subject", "Coordinates", "Contrast", "T Stat"], index=[])
        self.__frozen_model = DataFrameModel(
            self.__frozen_points, string_columns=(1, 2), index_as_column=False)

        self.ui = None
        self.__contrast_combo_manager = None
        self.three_d_widget = None
        self.image_view = None
        self.time_plot = None

        self._messages_client = None
        if server_broadcast_address is not None or server_receive_address is not None:
            self._messages_client = MessageClient(
                server_broadcast_address, server_receive_address)
            self._messages_client.message_received.connect(
                self.receive_message)
            log.info("started messages client")

        all_subjs =  frozenset(str(i)
                                     for i in braviz_tab_data.get_subjects())
        self.sample_manager = SampleManager(parent=self, initial_sample=all_subjs, message_client=self._messages_client)
        self.sample_manager.sample_changed.connect(self.change_sample)

        self.start_ui()

        if scenario is None or scenario == 0:
            QtCore.QTimer.singleShot(0, self.load_initial_view)
        else:
            log.info("Got scenario")
            log.info(scenario)

    def start_ui(self):
        self.ui = Ui_fMRI_Explorer()
        self.ui.setupUi(self)

        # image frame
        self.three_d_widget = braviz.visualization.subject_viewer.QFmriWidget(
            self.__reader, self.ui.vtk_frame)
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout(self.ui.vtk_frame)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.addWidget(self.three_d_widget)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.image_view = self.three_d_widget.viewer
        self.three_d_widget.cursor_moved.connect(self.handle_cursor_move)

        # timeseries frame
        self.time_plot = braviz.visualization.fmri_timeseries.TimeseriesPlot(
            self.ui.timeline_frame)
        self.ui.timeline_frame_layout = QtGui.QVBoxLayout(
            self.ui.timeline_frame)
        self.ui.timeline_frame.setLayout(self.ui.timeline_frame_layout)
        self.ui.timeline_frame_layout.addWidget(self.time_plot)
        self.ui.timeline_frame_layout.setContentsMargins(0, 0, 0, 0)

        # controls
        paradigms = sorted(self.__reader.get("fmri", None, index=True))
        for p in paradigms:
            self.ui.paradigm_combo.addItem(p)
        self.ui.paradigm_combo.setCurrentIndex(0)
        self.ui.paradigm_combo.activated.connect(self.update_fmri_data_view)

        self.__contrast_combo_manager = ContrastComboManager(self.__reader)
        self.__contrast_combo_manager.setup(self.ui.contrast_combo)
        self.__contrast_combo_manager.contrast_changed.connect(self.update_fmri_data_view)

        # subject
        self.ui.subj_completer = QtGui.QCompleter([str(i) for i in self.sample_manager.current_sample])
        self.ui.subject_edit.setCompleter(self.ui.subj_completer)
        self.ui.subj_validator = ListValidator([str(i) for i in self.sample_manager.current_sample])
        self.ui.subject_edit.setValidator(self.ui.subj_validator)
        self.ui.subject_edit.editingFinished.connect(
            self.update_fmri_data_view)

        # image
        self.three_d_widget.slice_changed.connect(
            self.ui.slice_slider.setValue)
        self.ui.slice_slider.valueChanged.connect(
            self.image_view.image.set_image_slice)
        self.ui.slice_spin.setMinimum(0)
        self.ui.slice_slider.setMinimum(0)

        self.ui.image_orientation_combo.setCurrentIndex(2)
        self.ui.image_orientation_combo.activated.connect(
            self.change_image_orientation)

        # contours
        self.ui.show_contours_value.valueChanged.connect(
            self.change_contour_value)
        self.ui.show_contours_check.clicked.connect(
            self.change_contour_visibility)
        self.ui.contour_opacity_slider.valueChanged.connect(
            self.change_contour_opacity)

        # Frozen
        self.ui.frozen_points_table.setModel(self.__frozen_model)
        self.ui.freeze_point_button.clicked.connect(self.freeze_point)
        self.ui.clear_button.clicked.connect(self.clear_frozen)
        self.ui.frozen_points_table.customContextMenuRequested.connect(
            self.get_frozen_context_menu)
        self.ui.frozen_points_table.activated.connect(self.highlight_frozen)
        self.ui.frozen_points_table.clicked.connect(self.highlight_frozen)
        self.ui.for_all_subjects.clicked.connect(self.add_point_for_all)

        # timelines
        self.ui.time_color_combo.insertSeparator(1)
        self.ui.time_color_combo.addItem("Select group variable")
        self.ui.time_color_combo.addItem("Group by location")
        self.ui.time_color_combo.activated.connect(self.select_time_color)
        self.ui.time_aggregrate_combo.activated.connect(
            self.timeline_aggregrate_combo)

        # menu
        self.ui.actionSelect_Sample.triggered.connect(self.sample_manager.load_sample)
        self.ui.actionSave_scenario.triggered.connect(self.save_scenario)
        self.ui.actionLoad_scenario.triggered.connect(self.load_scenario)
        self.ui.actionFrozen_Table.triggered.connect(self.export_frozen_table)
        self.ui.actionGraph.triggered.connect(self.export_time_plot)
        self.ui.actionSignals.triggered.connect(self.export_signals)

        self.sample_manager.configure_sample_policy_menu(self.ui.menuAccept_Samples)

    def start(self):
        self.three_d_widget.initialize_widget()

    def change_image_orientation(self):
        orientation_dict = {"Axial": 2, "Coronal": 1, "Sagital": 0}
        selection = str(self.ui.image_orientation_combo.currentText())
        orientation_index = orientation_dict[selection]
        self.image_view.change_orientation(orientation_index)
        self.update_slice_controls()

    def load_initial_view(self):

        self.ui.subject_edit.setText(str(self.__current_subject))
        self.update_fmri_data_view()

    def update_fmri_data_view(self, dummy = None, broadcast_message = True):
        log = logging.getLogger(__name__)
        subj = str(self.ui.subject_edit.text())
        if subj in self.sample_manager.current_sample:
            if self._messages_client is not None and subj != self.__current_subject and broadcast_message:
                self._messages_client.send_message({'subject': subj})
            self.__current_subject = subj
        new_paradigm = str(self.ui.paradigm_combo.currentText())
        if new_paradigm != self.__current_paradigm:
            res = self.warn_and_remove_frozen()
            if not res:
                # operation cancelled
                ix = self.ui.paradigm_combo.findText(self.__current_paradigm)
                self.ui.paradigm_combo.setCurrentIndex(ix)
                return
        image_code = self.__current_subject
        self.__current_paradigm = new_paradigm
        self.__contrast_combo_manager.change_paradigm(self.__current_subject, new_paradigm)
        self.__current_contrast = self.__contrast_combo_manager.get_previous_contrast(new_paradigm)

        try:
            spm_data = self.__reader.get(
                "fmri", image_code, name=self.__current_paradigm, spm=True)
        except Exception:
            log.warning("Couldn't read spm file")
            spm_data = None

        try:
            self.image_view.set_all(
                image_code, self.__current_paradigm, self.__current_contrast)
            bold_image = self.__reader.get(
                "BOLD", image_code, name=self.__current_paradigm)
        except Exception:
            message = "%s not available for subject %s" % (
                self.__current_paradigm, self.__current_subject)
            log.warning(message)
            self.statusBar().showMessage(message, 500)
            bold_image = None
            # raise

        self.update_slice_controls()
        self.time_plot.clear()
        self.time_plot.set_spm_and_bold(spm_data, bold_image)
        self.time_plot.set_contrast(self.__current_contrast)
        self.time_plot.draw_bold_signal(self.image_view.current_coords())

    def update_slice_controls(self):
        n_slices = self.image_view.image.get_number_of_image_slices()
        self.ui.slice_spin.setMaximum(n_slices)
        self.ui.slice_slider.setMaximum(n_slices)

    def handle_cursor_move(self, coords):
        cx, cy, cz = map(int, coords)
        stat = self.image_view.image.image_plane_widget.alternative_img.GetScalarComponentAsDouble(
            cx, cy, cz, 0)
        self.statusBar().showMessage("(%d,%d,%d) : %.4g" % (cx, cy, cz, stat))
        self.time_plot.draw_bold_signal(coords)

    def change_contour_value(self, value):
        self.image_view.set_contour_value(value)

    def change_contour_visibility(self):
        checked = self.ui.show_contours_check.isChecked()
        self.image_view.set_contour_visibility(checked)

    def change_contour_opacity(self, value):
        self.image_view.set_contour_opacity(value)

    def freeze_point(self):
        # todo should include contrast?
        coords = self.image_view.current_coords()
        if coords is None:
            return
        cx, cy, cz = (int(x) for x in coords)
        s = int(self.__current_subject)
        contrast = str(self.ui.contrast_combo.currentText())
        stat = self.image_view.image.image_plane_widget.alternative_img.GetScalarComponentAsDouble(
            cx, cy, cz, 0)
        i = (s, cx, cy, cz)
        if i in self.__frozen_points.index:
            return
        df2 = pd.DataFrame({"Subject": [s],
                            "Coordinates": [(cx, cy, cz)], "Contrast": [contrast],
                            "T Stat": [stat]},
                           index=[i])
        self.__frozen_points = self.__frozen_points.append(df2)
        self.__frozen_model.set_df(self.__frozen_points)
        self.time_plot.add_frozen_bold_signal(i, (cx, cy, cz))

    def clear_frozen(self):
        self.__frozen_points = pd.DataFrame(
            columns=["Subject", "Coordinates", "T Stat"])
        self.__frozen_model.set_df(self.__frozen_points)
        self.time_plot.clear_frozen_bold_signals()

    def warn_and_remove_frozen(self):
        """When paradigm changes"""
        if len(self.__frozen_points) > 0:
            dialog = QtGui.QMessageBox()
            dialog.setText(
                "Changing paradigm will delete the current frozen points")
            dialog.setInformativeText("Do you want to clear frozen points?")
            dialog.setStandardButtons(dialog.Discard | dialog.Cancel)
            dialog.setIcon(dialog.Question)
            res = dialog.exec_()
            if res == dialog.Discard:
                self.clear_frozen()
                return True
            else:
                return False
        return True

    def get_frozen_context_menu(self, pos):
        item = self.ui.frozen_points_table.currentIndex()
        if not item.isValid():
            return

        def delete_item():
            item_index = self.__frozen_model.get_item_index(item)
            self.__frozen_points = self.__frozen_points.drop(item_index)
            self.__frozen_model.set_df(self.__frozen_points)
            self.time_plot.remove_frozen_bold_signal(item_index)

        menu = QtGui.QMenu(self.ui.frozen_points_table)
        remove_action = QtGui.QAction("Remove", None)
        menu.addAction(remove_action)
        remove_action.triggered.connect(delete_item)
        global_pos = self.ui.frozen_points_table.mapToGlobal(pos)
        menu.exec_(global_pos)

    def highlight_frozen(self, item):
        item_index = self.__frozen_model.get_item_index(item)
        location = item_index[1:]
        if location != self.image_view.current_coords:
            self.image_view.set_cursor_coords(location)
        self.time_plot.highlight_frozen_bold(item_index)

    def batch_add_points(self, subj_coords, contrast):
        log = logging.getLogger(__name__)
        self.ui.clear_button.setEnabled(0)
        self.ui.freeze_point_button.setEnabled(0)
        self.ui.for_all_subjects.setEnabled(0)
        self.ui.time_color_combo.setEnabled(0)
        self.ui.time_aggregrate_combo.setEnabled(0)
        self.ui.progressBar.setValue(0)
        if isinstance(contrast, basestring):
            iterator = izip(subj_coords, repeat(contrast))
        else:
            iterator = izip(subj_coords, contrast)
        for j, each in enumerate(iterator):
            i, cont = each
            i = tuple(map(int, i))
            cont_number = self.ui.contrast_combo.findText(cont) + 1
            sbj = int(i[0])
            cx, cy, cz = i[1:4]
            s_img = sbj
            progress = j / (len(self.sample_manager.current_sample)) * 100
            self.ui.progressBar.setValue(progress)
            QtCore.QCoreApplication.instance().processEvents()
            if i not in self.__frozen_points.index:
                try:
                    fmri = self.__reader.get("fMRI", s_img, name=self.__current_paradigm,
                                             contrast=cont_number,
                                             space="fmri-%s" % self.__current_paradigm)
                    bold = self.__reader.get(
                        "bold", s_img, name=self.__current_paradigm)
                except Exception:
                    log.warning("%s not found for subject %s" %
                                (self.__current_paradigm, s_img))
                else:
                    stat = fmri.get_data()[cx, cy, cz]
                    df2 = pd.DataFrame({"Subject": [sbj], "Coordinates": [(cx, cy, cz)],
                                        "Contrast": [cont],
                                        "T Stat": [stat]},
                                       index=[i])
                    self.__frozen_points = self.__frozen_points.append(df2)
                    self.__frozen_model.set_df(self.__frozen_points)
                    self.time_plot.add_frozen_bold_signal(
                        i, (cx, cy, cz), bold.get_data())
        self.ui.progressBar.setValue(100)
        self.ui.clear_button.setEnabled(1)
        self.ui.freeze_point_button.setEnabled(1)
        self.ui.for_all_subjects.setEnabled(1)
        self.ui.time_color_combo.setEnabled(1)
        self.ui.time_aggregrate_combo.setEnabled(1)

    def add_point_for_all(self):
        coords = self.image_view.current_coords()
        x, y, z = coords
        contrast = str(self.ui.contrast_combo.currentText())
        if coords is None:
            return
        subjs = self.sample_manager.current_sample
        subj_coords = izip(subjs, repeat(x), repeat(y), repeat(z))
        self.batch_add_points(subj_coords, contrast)

    def select_time_color(self):
        if self.ui.time_color_combo.currentIndex() == self.ui.time_color_combo.count() - 2:
            params = {}
            dialog = qt_dialogs.SelectOneVariableWithFilter(
                params, accept_real=False, sample=self.sample_manager.current_sample)
            res = dialog.exec_()
            if res == dialog.Accepted:
                var_name = params.get("selected_outcome")
                if var_name is not None:
                    self.ui.time_color_combo.insertItem(
                        1, "Color by %s" % var_name)
                    self.set_timeline_colors(var_name)
                    self.ui.time_color_combo.setCurrentIndex(1)
        if self.ui.time_color_combo.currentIndex() == self.ui.time_color_combo.count() - 1:
            self.set_timeline_colors_by_location()
        elif self.ui.time_color_combo.currentIndex() == 0:
            self.set_timeline_colors(None)
        else:
            var_name = str(self.ui.time_color_combo.currentText())
            self.set_timeline_colors(var_name[9:])  # len("Color by ")

    def set_timeline_colors(self, var_name):
        log = logging.getLogger(__name__)
        log.info("Coloring by %s", var_name)
        if var_name is None:
            self.time_plot.set_frozen_groups_and_colors(None, None)
            self.time_plot.set_frozen_colors(None)
        else:
            df = braviz_tab_data.get_data_frame_by_name(var_name)
            df = df.set_index(df.index.astype(int))
            df = df.loc[self.sample_manager.current_sample]
            series = df[var_name].astype(int)
            values = set(series.astype(int))
            values.add(None)
            n_values = len(values)
            color_palette = sns.color_palette("Dark2", n_values)
            color_dict = dict(
                ((v, color_palette[i]) for i, v in enumerate(values)))
            color_dict[-1] = "#FF00E6"  # nan

            def color_fun(url):
                subj = int(url[0])
                val = series.get(subj)
                color = color_dict[val]
                return color

            def group_function(url):
                subj = int(url[0])
                val = series.get(subj, -1)
                if np.isnan(val):
                    val = -1
                return int(val)

            self.time_plot.set_frozen_groups_and_colors(
                group_function, color_dict)
            self.time_plot.set_frozen_colors(color_fun)

    def set_timeline_colors_by_location(self):
        locations = [t for t in self.__frozen_points["Coordinates"]]
        unique_locs = set(locations)
        colors = sns.color_palette("Dark2", len(unique_locs))
        loc_indexes = dict(((l, i) for i, l in enumerate(unique_locs)))
        color_dict = dict(((i, c) for i, c in enumerate(colors)))

        def color_fun(url):
            location = tuple(url[1:])
            l_i = loc_indexes[location]
            color = color_dict[l_i]
            return color

        def group_function(url):
            location = tuple(url[1:])
            return loc_indexes[location]

        self.time_plot.set_frozen_groups_and_colors(group_function, color_dict)
        self.time_plot.set_frozen_colors(color_fun)

    def timeline_aggregrate_combo(self):
        aggregrate = self.ui.time_aggregrate_combo.currentIndex() > 0
        self.set_timeline_aggregate(aggregrate)

    def set_timeline_aggregate(self, aggregate=False):
        self.time_plot.set_frozen_aggregration(aggregate)

    def get_state(self):
        import datetime
        import sys
        import platform
        import os

        state = {"sample": list(self.sample_manager.current_sample)}
        # sample

        # fMRI
        fmri_state = {"subject": self.__current_subject, "paradigm": self.__current_paradigm,
                      "contrast": self.__current_contrast,
                      "image_orientation": self.image_view.image.image_plane_widget.GetPlaneOrientation(),
                      "image_slice": self.image_view.image.get_current_image_slice(),
                      "contours_active": self.ui.show_contours_check.isChecked(), "contours_threshold": float(
            self.ui.show_contours_value.value()), "contours_opacity": int(
            self.ui.contour_opacity_slider.value()), "camera": self.image_view.get_camera_parameters()}
        state["fmri"] = fmri_state
        # Timelines
        timeline_state = {"frozen": zip(
            self.__frozen_points.index, self.__frozen_points["Contrast"])}
        if self.ui.time_color_combo.currentIndex() == 0:
            color = "<uniform>"
        elif self.ui.time_color_combo.currentIndex() == self.ui.time_color_combo.count() - 1:
            color = "<location>"
        else:
            color = str(self.ui.time_color_combo.currentText())[9:]
        timeline_state["color"] = color
        timeline_state[
            "aggregate"] = self.ui.time_aggregrate_combo.currentIndex() > 0

        state["timeline"] = timeline_state
        # meta
        meta = {"date": datetime.datetime.now(), "exec": sys.argv, "machine": platform.node(),
                "application": os.path.splitext(os.path.basename(__file__))[0]}
        state["meta"] = meta
        return state

    def save_scenario(self):
        import functools
        state = self.get_state()
        app_name = state["meta"]["application"]
        params = {}
        dialog = braviz.interaction.qt_dialogs.SaveScenarioDialog(
            app_name, state, params)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == QtGui.QDialog.Accepted:
            scn_id = params["scn_id"]
            log.info("scenario saved with id %d" % scn_id)
            take_screen = functools.partial(self.take_screenshot, scn_id)
            QtCore.QTimer.singleShot(500, take_screen)

    def load_scenario(self):
        new_state = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(
            "fmri_explorer", new_state)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == QtGui.QDialog.Accepted:
            log.info("New state : ")
            log.info(new_state)
            self.load_state(new_state)

    def load_state(self, wanted_state):
        # fmri
        sample = wanted_state["sample"]
        if sample is not None:
            self.sample_manager.current_sample = sample

        fmri_state = wanted_state["fmri"]
        subj = fmri_state.get("subject")
        if subj is not None:
            self.ui.subject_edit.setText(str(subj))
        pdgm = fmri_state["paradigm"]
        if pdgm is not None:
            ix = self.ui.paradigm_combo.findText(pdgm)
            if ix >= 0:
                self.ui.paradigm_combo.setCurrentIndex(ix)
        cont = fmri_state.get("contrast")
        self.update_fmri_data_view()
        self.ui.contrast_combo.setCurrentIndex(cont - 1)
        self.update_fmri_data_view()

        img_or = fmri_state.get("image_orientation")
        if img_or is not None:
            orientation_dict = {2: "Axial", 1: "Coronal", 0: "Sagital"}
            name = orientation_dict.get(img_or)
            ix = self.ui.image_orientation_combo.findText(name)
            if ix >= 0:
                self.ui.image_orientation_combo.setCurrentIndex(ix)
                self.change_image_orientation()
        image_slice = fmri_state.get("image_slice")
        if image_slice is not None:
            self.ui.slice_spin.setValue(image_slice)
            self.image_view.image.set_image_slice(image_slice)
        cont_act = fmri_state.get("contours_active")
        if cont_act is not None:
            self.ui.show_contours_check.setChecked(cont_act)
            self.change_contour_visibility()
        cont_thr = fmri_state.get("contours_threshold")
        if cont_thr is not None:
            self.ui.show_contours_value.setValue(cont_thr)
            self.change_contour_value(cont_thr)
        cont_opac = fmri_state.get("contours_opacity")
        if cont_opac is not None:
            self.ui.contour_opacity_slider.setValue(cont_opac)
            self.change_contour_opacity(cont_opac)
        camera = fmri_state.get("camera")
        if camera is not None:
            self.image_view.set_camera(*camera)

        timeline_state = wanted_state["timeline"]
        color = timeline_state.get("color")
        if color is not None:
            if color == "<uniform>":
                self.ui.time_color_combo.setCurrentIndex(0)
                self.set_timeline_colors(None)
            elif color == "<location>":
                self.ui.time_color_combo.setCurrentIndex(
                    self.ui.time_color_combo.count() - 1)
                self.set_timeline_colors_by_location()
            else:
                full_text = "Color by %s" % color
                ix = self.ui.time_color_combo.findText(full_text)
                if ix >= 0:
                    self.ui.time_color_combo.setCurrentIndex(ix)
                else:
                    self.ui.time_color_combo.insertItem(1, full_text)
                    self.ui.time_color_combo.setCurrentIndex(1)
                self.set_timeline_colors(color)
        agg = timeline_state.get("aggregate")
        if agg is not None:
            if agg:
                self.ui.time_aggregrate_combo.setCurrentIndex(1)
            else:
                self.ui.time_aggregrate_combo.setCurrentIndex(0)
            self.set_timeline_aggregate(agg)

        frozen = timeline_state.get("frozen")
        if frozen is not None and len(frozen)>0:
            self.clear_frozen()
            ixs, conts = izip(*frozen)
            self.batch_add_points(ixs, conts)

    def take_screenshot(self, scenario_index):
        import os
        geom = self.geometry()
        pixmap = QtGui.QPixmap.grabWindow(QtGui.QApplication.desktop().winId(), geom.x(), geom.y(), geom.width(),
                                          geom.height())
        file_name = "scenario_%d.png" % scenario_index
        file_path = os.path.join(
            self.__reader.get_dyn_data_root(), "braviz_data", "scenarios", file_name)
        pixmap.save(file_path, "png")
        log = logging.getLogger(__name__)
        log.info("chick %s" % file_path)

    def receive_message(self, msg):
        log = logging.getLogger(__name__)
        subj = msg.get("subject")
        if subj is not None and subj in self.sample_manager.current_sample and subj != self.__current_subject:
            self.ui.subject_edit.setText(subj)
            log.info("Changing to subj %s" % subj)
            self.update_fmri_data_view(broadcast_message=False)
        if "sample" in msg:
            self.sample_manager.process_sample_message(msg)

    def change_sample(self, new_sample):
        log = logging.getLogger(__name__)
        log.info("*sample changed*")
        valid_ids = {"%s" % s for s in new_sample}
        logger = logging.getLogger(__name__)
        logger.info("new sample: %s" % new_sample)
        self.ui.subj_completer = QtGui.QCompleter(list(valid_ids))
        self.ui.subject_edit.setCompleter(self.ui.subj_completer)
        self.ui.subj_validator = ListValidator(valid_ids)
        self.ui.subject_edit.setValidator(self.ui.subj_validator)


    def export_time_plot(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(
            self, "Save Timeline Plot", ".", "PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.time_plot.fig.savefig(filename)

    def export_signals(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(
            self, "Save Signals", ".", "matlab (*.mat)"))
        self.time_plot.export_frozen_signals(filename)
        pass

    def export_frozen_table(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(
            self, "Save Signals", ".", "table (*.csv)"))
        self.__frozen_points.to_csv(filename)


def run():
    import sys
    from braviz.utilities import configure_logger_from_conf

    configure_logger_from_conf("fmri")
    args = sys.argv
    scenario = None
    server_broadcast_address = None
    server_receive_address = None
    if len(args) > 1:
        scenario = int(args[1])
        if len(args) > 2:
            server_broadcast_address = args[2]
            if len(args) > 3:
                server_receive_address = args[3]
    qt_args = args[4:]
    app = QtGui.QApplication(qt_args)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = FmriExplorer(
        scenario, server_broadcast_address, server_receive_address)
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()
