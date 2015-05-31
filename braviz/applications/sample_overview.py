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

__author__ = 'diego'

import logging
import vtk
from PyQt4 import QtGui
from PyQt4 import QtCore
import braviz
from braviz.visualization.subject_viewer import QSubjectViewerWidget
from braviz.interaction.qt_guis.sample_overview import Ui_SampleOverview
import braviz.interaction.qt_dialogs
from braviz.readAndFilter.config_file import get_apps_config
import braviz.applications.sample_select
from braviz.visualization.matplotlib_qt_widget import MatplotWidget
from braviz.readAndFilter import tabular_data as braviz_tab_data
from braviz.readAndFilter import user_data as braviz_user_data
from itertools import izip
import numpy as np
import platform

from collections import Counter
import os
import datetime
import functools

from braviz.interaction.connection import MessageClient, MessageServer

if braviz.readAndFilter.PROJECT == "kmc40":
    SAMPLE_SIZE = 0.3
else:
    SAMPLE_SIZE = 0.1


class SampleOverview(QtGui.QMainWindow):

    def __init__(self, server_broadcast_address=None, server_receive_address=None, initial_scenario=None):
        super(SampleOverview, self).__init__()
        self.reader = braviz.readAndFilter.BravizAutoReader()
        log = logging.getLogger(__name__)
        self.plot_widget = None
        self.sample = braviz_tab_data.get_subjects()
        self.viewers_dict = {}
        self.widgets_dict = {}
        self.widget_observers = {}
        self.current_space = "Talairach"

        self.sample_message_policy = "ask"

        self.inside_layouts = dict()
        self.row_scroll_widgets = dict()
        self.row_widget_contents = dict()
        self.row_labels = dict()
        self.row_frames = dict()
        self.row_frame_lays = dict()

        self.scalar_data = None
        self.nominal_name = None
        self.nominal_index = None
        self.rational_index = None
        self.rational_name = None
        self.labels_dict = {}

        self.current_selection = None
        self.current_scenario = None

        if server_broadcast_address is not None or server_receive_address is not None:
            self._message_client = MessageClient(
                server_broadcast_address, server_receive_address)
            self._message_client.message_received.connect(self.receive_message)
            log.info("started messages client")
        else:
            self._message_client = None

        self.ui = None
        self.context_menu_opened_recently = False
        cfg = get_apps_config()
        def_vars = cfg.get_default_variables()
        ratio_var = braviz_tab_data.get_var_idx(def_vars["ratio1"])
        nom_var = braviz_tab_data.get_var_idx(def_vars["nom1"])
        self.rational_name = def_vars["ratio1"]
        self.nominal_name = def_vars["nom1"]

        self.setup_gui()
        if initial_scenario is None:
            self.take_random_sample()

            self.load_scalar_data(ratio_var, nom_var)
            QtCore.QTimer.singleShot(100, self.add_subject_viewers)
        else:
            self.sample = []
            state = braviz_user_data.get_scenario_data_dict(initial_scenario)
            load_scn_funct = functools.partial(
                self.load_scenario, state, False)
            QtCore.QTimer.singleShot(100, load_scn_funct)

    def setup_gui(self):
        self.ui = Ui_SampleOverview()
        self.ui.setupUi(self)
        self.plot_widget = MatplotWidget(self.ui.plot_1)
        self.plot_widget.point_picked.connect(self.select_from_bar)
        self.ui.plot_1_layout = QtGui.QHBoxLayout()
        self.ui.plot_1_layout.addWidget(self.plot_widget)
        self.ui.plot_1.setLayout(self.ui.plot_1_layout)
        self.ui.row_layout = QtGui.QVBoxLayout(self.ui.row_container)
        self.ui.row_container.setLayout(self.ui.row_layout)
        self.ui.row_layout.setContentsMargins(0, 0, 0, 0)
        self.ui.row_layout.setSpacing(0)
        self.ui.progress_bar = QtGui.QProgressBar()
        self.ui.camera_combo.currentIndexChanged.connect(
            self.camera_combo_handle)
        self.ui.space_combo.currentIndexChanged.connect(
            self.set_space_from_menu)
        self.ui.space_combo.setCurrentIndex(1)

        self.ui.action_load_visualization.triggered.connect(
            self.load_visualization)
        self.ui.nomina_combo.addItem(
            self.nominal_name)
        self.ui.nomina_combo.setCurrentIndex(1)
        self.ui.nomina_combo.currentIndexChanged.connect(
            self.select_nominal_variable)
        self.ui.rational_combo.addItem(
            self.rational_name)
        self.ui.rational_combo.setCurrentIndex(1)
        self.ui.rational_combo.currentIndexChanged.connect(
            self.select_rational_variable)
        self.ui.action_save_scenario.triggered.connect(self.save_scenario)
        self.ui.action_load_scenario.triggered.connect(
            self.load_scenario_dialog)

        self.ui.actionSelect_sample.triggered.connect(
            self.load_sample)
        self.ui.actionModify_sample.triggered.connect(self.modify_sample)
        self.ui.actionAsk.triggered.connect(lambda: self.update_samples_policy("ask"))
        self.ui.actionNever.triggered.connect(lambda: self.update_samples_policy("never"))
        self.ui.actionAlways.triggered.connect(lambda: self.update_samples_policy("always"))
        self.ui.actionSend_sample.triggered.connect(self.send_sample)


        self.ui.progress_bar.setValue(0)

    def change_nominal_variable(self, new_var_index):
        self.load_scalar_data(self.rational_index, new_var_index)
        logger = logging.getLogger(__name__)
        logger.info("Changed nominal variable to %s" % new_var_index)
        self.re_arrange_viewers()

    def change_rational_variable(self, new_var_index):
        self.load_scalar_data(new_var_index, self.nominal_index)
        logger = logging.getLogger(__name__)
        logger.info("Changed rational variable to %s" % new_var_index)
        self.re_arrange_viewers()

    def re_arrange_viewers(self):
        # reorganize rows
        unique_levels = sorted(self.scalar_data[self.nominal_name].unique())

        new_scrolls_dict = dict()
        new_contents_dict = dict()
        new_layouts_dict = dict()
        new_labels = dict()
        new_row_frames = dict()
        new_row_lays = dict()
        old_levels = sorted(self.row_scroll_widgets.keys())
        log = logging.getLogger(__name__)
        log.debug("Unique nominal levels:")
        log.debug(unique_levels)
        # reuse existing rows
        for nl, ol in izip(unique_levels, old_levels):
            if np.isnan(nl):
                nl = "nan"
            new_scrolls_dict[nl] = self.row_scroll_widgets[ol]
            new_contents_dict[nl] = self.row_widget_contents[ol]
            new_layouts_dict[nl] = self.inside_layouts[ol]
            new_labels[nl] = self.row_labels[ol]
            level_name = self.labels_dict.get(nl, "<?>")
            if level_name is None or len(level_name) == 0:
                level_name = "Level %s" % nl
            new_labels[nl].setText(level_name)
            new_labels[nl].set_color(
                self.plot_widget.colors_dict.get(nl, "#EA7AE3"))
            new_row_frames[nl] = self.row_frames[ol]
            new_row_lays[nl] = self.row_frame_lays[ol]

        for nl in unique_levels[len(old_levels):]:
            if np.isnan(nl):
                nl = "nan"
            # create new rows
            row_frame = QtGui.QFrame(self.ui.view)
            self.ui.row_layout.addWidget(row_frame, 1)
            row_lay = QtGui.QHBoxLayout()
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_frame.setContentsMargins(0, 0, 0, 0)
            row_frame.setLayout(row_lay)
            row_frame.setLineWidth(0)
            row_frame.setMidLineWidth(0)
            # add label
            level_name = self.labels_dict.get(nl)
            if level_name is None:
                level_name = "Level %s" % nl
            label = self.get_rotated_label(
                row_frame, level_name, self.plot_widget.colors_dict.get(nl))
            row_lay.addWidget(label)
            new_labels[nl] = label
            new_row_frames[nl] = row_frame
            new_row_lays[nl] = row_lay

            scroll = QtGui.QScrollArea(row_frame)
            row_lay.addWidget(scroll, 1)
            new_scrolls_dict[nl] = scroll
            scroll.setWidgetResizable(True)
            contents = QtGui.QWidget()
            new_contents_dict[nl] = contents
            inside_lay = QtGui.QGridLayout(contents)
            inside_lay.setContentsMargins(0, 0, 0, 0)
            new_layouts_dict[nl] = inside_lay
            contents.setLayout(inside_lay)
            scroll.setWidget(contents)

            log.debug("new row created, level %s" % nl)

        # set to 0 column widths
        for nl in unique_levels:
            if np.isnan(nl):
                nl = "nan"
            lay = new_layouts_dict[nl]
            for i in xrange(0, lay.columnCount()):
                lay.setColumnMinimumWidth(i, 0)
        cnt = Counter()
        for subj in self.sample:
            viewer = self.widgets_dict[subj]
            level = self.scalar_data.ix[subj, self.nominal_name]
            if np.isnan(level):
                level = "nan"
            i = cnt[level]
            new_layouts_dict[level].addWidget(viewer, 0, i)
            new_layouts_dict[level].setColumnMinimumWidth(i, 400)
            cnt[level] += 1

        # log.debug(cnt)
        # for nl in unique_levels:
        #    log.debug("%s %s"%(nl, new_layouts_dict[nl].columnCount()))

        # delete useless rows
        for ol in old_levels[len(unique_levels):]:
            log.debug("adios row %s" % ol)
            self.row_frames[ol].deleteLater()
            self.row_frame_lays[ol].deleteLater()
            self.inside_layouts[ol].deleteLater()
            self.row_scroll_widgets[ol].deleteLater()
            self.row_labels[ol].deleteLater()

        # set dictionaries
        self.row_scroll_widgets = new_scrolls_dict
        self.row_widget_contents = new_contents_dict
        self.inside_layouts = new_layouts_dict
        self.row_labels = new_labels
        self.row_frames = new_row_frames
        self.row_frame_lays = new_row_lays

    def take_random_sample(self):
        sample = braviz_tab_data.get_subjects()
        self.sample = list(
            np.random.choice(sample, np.ceil(len(sample) * SAMPLE_SIZE), replace=False))

    def callback_maker(self, subj):
        def cb(obj, event):
            self.select_from_viewer(subj)

        return cb

    def add_subject_viewers(self, scenario=None):
        # create parents:
        levels = self.scalar_data[self.nominal_name].unique()
        log = logging.getLogger(__name__)
        log.info(levels)
        for level in levels:
            if np.isnan(level):
                level = "nan"
            row_frame = QtGui.QFrame(self.ui.view)
            self.ui.row_layout.addWidget(row_frame, 1)
            row_lay = QtGui.QHBoxLayout()
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_frame.setContentsMargins(0, 0, 0, 0)
            row_frame.setLayout(row_lay)
            row_frame.setLineWidth(0)
            row_frame.setMidLineWidth(0)
            # add label
            level_name = self.labels_dict.get(level)
            if level_name is None:
                level_name = "Level %s" % level
            label = self.get_rotated_label(
                row_frame, level_name, self.plot_widget.colors_dict.get(level))
            row_lay.addWidget(label)
            self.row_labels[level] = label
            self.row_frames[level] = row_frame
            self.row_frame_lays[level] = row_lay

            scroll = QtGui.QScrollArea(row_frame)
            row_lay.addWidget(scroll, 1)
            self.row_scroll_widgets[level] = scroll
            scroll.setWidgetResizable(True)
            contents = QtGui.QWidget()
            self.row_widget_contents[level] = contents
            #contents.setGeometry(QtCore.QRect(0, 0, 345, 425))
            inside_lay = QtGui.QGridLayout(contents)
            inside_lay.setContentsMargins(0, 0, 0, 0)
            self.inside_layouts[level] = inside_lay
            contents.setLayout(inside_lay)
            scroll.setWidget(contents)

        for subj in self.sample:
            level = self.scalar_data.ix[subj, self.nominal_name]
            if np.isnan(level):
                level = "nan"
            contents = self.row_widget_contents[level]
            viewer = self.__create_viewer(subj, contents)
            self.viewers_dict[subj] = viewer.subject_viewer
            self.widgets_dict[subj] = viewer
            QtGui.QApplication.instance().processEvents()

        # add viewers to rows
        for subj in self.sample:
            viewer = self.widgets_dict[subj]
            level = self.scalar_data.ix[subj, self.nominal_name]
            if np.isnan(level):
                level = "nan"
            i = self.inside_layouts[level].columnCount()
            self.inside_layouts[level].addWidget(viewer, 0, i)
            self.inside_layouts[level].setColumnMinimumWidth(i, 400)

        for widget in self.widgets_dict.values():
            widget.initialize_widget()
            QtGui.QApplication.instance().processEvents()

        self.reload_viewers(scenario)

    def get_rotated_label(self, parent, text, color):
        from braviz.interaction.qt_widgets import RotatedLabel

        label = RotatedLabel(parent)
        label.set_color(color)
        label.setFixedWidth(30)
        label.setText(text)
        return label

    def reload_viewers(self, scenario=None):
        self.ui.statusbar.addPermanentWidget(self.ui.progress_bar)
        self.ui.progress_bar.show()
        log = logging.getLogger(__name__)
        for i, (subj, viewer) in enumerate(self.viewers_dict.iteritems()):
            self.ui.progress_bar.setValue(i / len(self.sample) * 100)
            log.info("loading viewer %d " % subj)
            try:
                if scenario is None:
                    self.load_initial_view(subj, viewer)
                else:
                    self.load_scenario_in_viewer(viewer, scenario, subj)
            except Exception as e:
                log.exception(e)
                self.statusBar().showMessage(e.message, 1000)
            QtGui.QApplication.instance().processEvents()
        self.ui.progress_bar.setValue(100)
        self.ui.statusbar.removeWidget(self.ui.progress_bar)
        self.ui.statusbar.showMessage("Loading complete")

    def load_initial_view(self, subject, viewer):
        log = logging.getLogger(__name__)
        img_code = subject
        try:
            viewer.change_subject(img_code)
        except Exception as e:
            log.warning(e.message)

    def locate_subj(self, subj):
        # restore previous
        subj = int(subj)
        if not subj in self.sample:
            return
        if self.current_selection is not None:
            i_widget = self.widgets_dict[self.current_selection]
            i_widget.setFrameStyle(QtGui.QFrame.NoFrame)

        # new selection
        i_widget = self.widgets_dict[subj]
        level = self.scalar_data.ix[subj, self.nominal_name]
        if np.isnan(level):
            level = "nan"
        self.row_scroll_widgets[level].ensureWidgetVisible(i_widget)
        i_widget.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Plain)
        i_widget.setLineWidth(10)
        i_widget.setMidLineWidth(1)

        self.current_selection = subj

        # locate in bar plot
        self.plot_widget.highlight_id(int(subj))
        self.ui.camera_combo.setItemText(
            2, "Copy from %s" % self.current_selection)

    def load_scalar_data(self, rational_var_index, nominal_var_index, force=False):
        if not force and (self.rational_index == rational_var_index) and (self.nominal_index == nominal_var_index):
            return
        log = logging.getLogger(__name__)
        self.rational_index = rational_var_index
        self.nominal_index = nominal_var_index
        self.scalar_data = braviz_tab_data.get_data_frame_by_index(
            (rational_var_index, nominal_var_index), self.reader)
        self.rational_name = self.scalar_data.columns[0]
        self.nominal_name = self.scalar_data.columns[1]
        self.scalar_data = self.scalar_data.loc[self.sample]
        # self.scalar_data[np.isnan(self.scalar_data[self.rational_name])][self.rational_name]=np.inf
        labels_dict = braviz_tab_data.get_labels_dict(nominal_var_index)
        self.labels_dict = labels_dict
        self.plot_widget.draw_bars(
            self.scalar_data, orientation="horizontal", group_labels=labels_dict)

        sample_order = list(self.plot_widget.painted_plot.data.index)
        sample_order += list(
            self.scalar_data.index[np.where(np.isnan(self.scalar_data[self.rational_name]))])
        log = logging.getLogger(__name__)
        log.info(sample_order)
        log.info(len(sample_order))
        log.info(len(self.sample))
        log.info(self.plot_widget.painted_plot.data)
        self.scalar_data.sort(
            self.rational_name, inplace=True, ascending=False)
        self.sample = sample_order
        log.debug("sample: ")
        log.debug(self.sample)

    def select_from_bar(self, subj_id):
        log = logging.getLogger(__name__)
        log.debug("selecting subject %s" % subj_id)
        self.locate_subj(int(subj_id))

    def select_from_viewer(self, subj_id):
        log = logging.getLogger(__name__)
        log.debug("Select from viewer %s" % subj_id)
        self.locate_subj(subj_id)

    def load_visualization(self):
        return_dict = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(
            "subject_overview", return_dict)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            subj_state = return_dict.get("subject_state")
            if subj_state is not None:
                subj_state.pop("current_subject")
            log.info("loading dict")
            log.info(return_dict)
            try:
                space = return_dict["camera_state"].pop("space")
            except KeyError:
                pass
                log.info("No space found")
            else:
                self.current_space = space
                index = self.ui.space_combo.findText(space)
                self.ui.space_combo.setCurrentIndex(index)

            self.current_scenario = return_dict
            self.reload_viewers(scenario=return_dict)

    def load_scenario_in_viewer(self, viewer, scenario_dict, subj):
        img_code = subj
        wanted_state = scenario_dict

        # set space
        viewer.change_current_space(self.current_space)

        log = logging.getLogger(__name__)
        # images panel
        image_state = wanted_state.get("image_state")
        log.info(image_state)
        if image_state is not None:
            image_class = image_state.get("image_class", False)
            # None indicates no image
            if image_class is False:
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
            try:
                if image_class is None:
                    viewer.image.hide_image()
                else:
                    viewer.image.show_image()
                    viewer.image.image_plane_widget.SetInteraction(1)
                    viewer.image.change_image_modality(image_class, image_name, contrast=cont)
                    orient = image_state.get("orientation")
                    if orient is not None:
                        orientation_dict = {
                            "Axial": 2, "Coronal": 1, "Sagital": 0}
                        viewer.image.change_image_orientation(
                        orientation_dict[orient], skip_render=True)
                    img_slice = image_state.get("slice")
                    if img_slice is not None:
                        viewer.image.set_image_slice(
                        int(img_slice), skip_render=True)
                    window = image_state.get("window")
                    if window is not None:
                        viewer.image.set_image_window(window, skip_render=True)
                    level = image_state.get("level")
                    if level is not None:
                        viewer.image.set_image_level(level, skip_render=True)
            except Exception as e:
                log.warning(e.message)
                #viewer.image.change_image_modality(None, paradigm=None, skip_render=True)
                viewer.image.hide_image()

        QtGui.QApplication.instance().processEvents()
        # fmri panel
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
                viewer.set_contours_visibility(False)
            else:
                viewer.set_contours_visibility(vis, skip_render=True)
                if vis:
                    viewer.set_fmri_contours_image(
                        pdgm, ctrst, skip_render=True)
                    viewer.contours.set_value(val)
        else:
            viewer.set_contours_visibility(False)
        QtGui.QApplication.instance().processEvents()
        # segmentation panel
        segmentation_state = wanted_state.get("segmentation_state")
        selected_structs = tuple()
        if segmentation_state is not None:
            color = segmentation_state.get("color", False)
            if color is not False:
                viewer.models.set_color(color, skip_render=True)

            opac = segmentation_state.get("opacity")
            if opac is not None:
                viewer.models.set_opacity(opac, skip_render=True)
            selected_structs = segmentation_state.get("selected_structs")
            if selected_structs is not None:
                try:
                    viewer.models.set_models(
                        selected_structs, skip_render=True)
                except Exception as e:
                    log.warning(e.message)
        QtGui.QApplication.instance().processEvents()
        # tractography panel
        tractography_state = wanted_state.get("tractography_state")
        if tractography_state is not None:
            bundles = tractography_state.get("bundles")
            if bundles is not None:
                try:
                    viewer.tractography.set_active_db_tracts(
                        bundles, skip_render=True)
                except Exception as e:
                    log.warning(e.message)

            from_segment = tractography_state.get("from_segment")
            if from_segment is not None:
                try:
                    if from_segment == "None":
                        viewer.tractography.hide_checkpoints_bundle(
                            skip_render=True)
                    elif from_segment == "Through Any":
                        viewer.tractography.set_bundle_from_checkpoints(
                            selected_structs, False, skip_render=True)
                    else:
                        viewer.tractography.set_bundle_from_checkpoints(
                            selected_structs, True, skip_render=True)
                except Exception as e:
                    log.warning(e.message)
            color = tractography_state.get("color")
            if color is not None:
                color_codes = {"Orientation": "orient", "FA (Point)": "fa_p", "FA (Line)": "fa_l",
                               "MD (Point)": "md_p", "MD (Line)": "md_l",
                               "Length": "length",
                               "By Line": "rand", "By Bundle": "bundle"}
                try:
                    viewer.tractography.change_color(
                        color_codes[color], skip_render=True)
                except Exception as e:
                    log.warning(e.message)

            opac = tractography_state.get("opacity")
            if opac is not None:
                try:
                    viewer.tractography.set_opacity(
                        opac / 100, skip_render=True)
                except Exception as e:
                    log.warning(e.message)

        # tracula panel
        tracula_state = wanted_state.get("tracula_state")
        if tracula_state is not None:
            try:
                bundles = tracula_state["bundles"]
                opac = tracula_state["opacity"]
                viewer.tracula.set_bundles(bundles)
                viewer.tracula.set_opacity(opac)
            except Exception as e:
                log.warning(e.message)
        # surfaces panel
        surf_state = wanted_state.get("surf_state")
        if surf_state is not None:
            try:
                left_active = surf_state["left"]
                right_active = surf_state["right"]
                viewer.surface.set_hemispheres(
                    left_active, right_active, skip_render=True)
            except Exception as e:
                log.warning(e.message)
            try:
                surface = surf_state["surf"]
                viewer.surface.set_surface(surface, skip_render=True)
            except Exception as e:
                log.warning(e.message)
            try:
                scalar_index = surf_state["scalar_idx"]
                from braviz.applications.subject_overview import surfaces_scalars_dict
                scalars = surfaces_scalars_dict[scalar_index]
                viewer.surface.set_scalars(scalars, skip_render=True)
            except Exception as e:
                log.warning(e.message)
            try:
                opacity = surf_state["opacity"]
                viewer.surface.set_opacity(opacity, skip_render=True)
            except Exception as e:
                log.warning(e.message)

        QtGui.QApplication.instance().processEvents()
        # subject
        try:
            viewer.change_subject(img_code)
        except Exception as e:
            log.exception(e)
        # camera panel
        self.__load_camera_from_scenario(viewer)
        return

    def __load_camera_from_scenario(self, viewer):
        wanted_state = self.current_scenario
        camera_state = wanted_state.get("camera_state")
        if camera_state is not None:
            cam = camera_state.get("cam_params")
            if cam is not None:
                fp, pos, vu = cam
                viewer.set_camera(fp, pos, vu)
        viewer.ren_win.Render()

    def __set_camera_parameters(self, viewer, parameters):
        viewer.set_camera(*parameters)

    def __copy_camera_from_subject(self, subj):
        viewer = self.viewers_dict[subj]
        parameters = viewer.get_camera_parameters()
        logger = logging.getLogger(__name__)
        logger.info("copying camera")
        for subj2, viewer in self.viewers_dict.iteritems():
            if subj2 != subj:
                self.__set_camera_parameters(viewer, parameters)

    def __create_viewer(self, subject, parent):
        viewer = QSubjectViewerWidget(self.reader, parent)
        self.__set_viewer_subject(viewer, subject)
        return viewer

    def __set_viewer_subject(self, viewer, subject):
        viewer.setToolTip(str(subject))
        dummy_i = self.callback_maker(subject)
        # remove old observer
        old_observer = self.widget_observers.get(id(viewer))
        if old_observer is not None:
            viewer.subject_viewer.iren.RemoveObserver(old_observer)
        obs_id = viewer.subject_viewer.iren.AddObserver(
            "LeftButtonPressEvent", dummy_i, 1.0)
        self.widget_observers[id(viewer)] = obs_id
        viewer.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        context_handler = self.__get_context_menu_handler(viewer, subject)
        # disconnect old handlers
        try:
            viewer.customContextMenuRequested.disconnect()
        except TypeError:
            pass
        viewer.customContextMenuRequested.connect(context_handler)

    def __get_context_menu_handler(self, widget, subj):
        def re_enable_context():
            self.context_menu_opened_recently = False

        def context_menu_handler(pos):
            log = logging.getLogger(__name__)
            if self.context_menu_opened_recently:
                return
            log.info("Context for %s", subj)
            menu = QtGui.QMenu()
            show_action = QtGui.QAction(
                "Show %s in current viewers" % subj, menu)

            def show_subj_in_mri_viewer():
                self.show_in_mri_viewer(subj)

            show_action.triggered.connect(show_subj_in_mri_viewer)
            menu.addAction(show_action)

            new_viewer_action = QtGui.QAction(
                "Show %s in new viewer" % subj, menu)

            def launch_mri_viewer():
                self.launch_mri_viewer(subj)

            new_viewer_action.triggered.connect(launch_mri_viewer)
            menu.addAction(new_viewer_action)

            global_pos = widget.mapToGlobal(pos)
            menu.exec_(global_pos)
            widget.subject_viewer.iren.InvokeEvent(
                vtk.vtkCommand.RightButtonReleaseEvent)
            self.context_menu = menu
            self.context_menu_opened_recently = True

            QtCore.QTimer.singleShot(5000, re_enable_context)

        return context_menu_handler

    def reset_cameras_to_scenario(self):
        logger = logging.getLogger(__name__)
        logger.info("resetting camera to scenario")
        for viewer in self.viewers_dict.itervalues():
            self.__load_camera_from_scenario(viewer)

    def camera_combo_handle(self, index):
        if index == 0:
            return
        if index == 1:
            self.reset_cameras_to_scenario()
        if index == 2:
            self.__copy_camera_from_subject(self.current_selection)

        self.ui.camera_combo.setCurrentIndex(0)

    def set_space_from_menu(self, index):
        text = self.ui.space_combo.currentText()
        log = logging.getLogger(__name__)
        log.info("space changed to %s", text)
        text = str(text)
        if self.current_space == text:
            return
        self.current_space = text
        self.__change_space_in_viewers()

    def __change_space_in_viewers(self):
        self.ui.statusbar.addPermanentWidget(self.ui.progress_bar)
        self.ui.progress_bar.show()
        log = logging.getLogger(__name__)
        for i, v in enumerate(self.viewers_dict.itervalues()):
            self.ui.progress_bar.setValue(i / len(self.sample) * 100)
            try:
                v.change_current_space(self.current_space)
            except Exception as e:
                log.warning(e.message)
            QtGui.QApplication.instance().processEvents()
        self.ui.progress_bar.setValue(100)
        self.ui.statusbar.removeWidget(self.ui.progress_bar)
        self.ui.statusbar.showMessage("Loading complete")

    def select_nominal_variable(self, index):
        log = logging.getLogger(__name__)
        if index == 0:
            params = {}
            dialog = braviz.interaction.qt_dialogs.SelectOneVariableWithFilter(params, accept_nominal=True,
                                                                               accept_real=False, sample=self.sample)
            dialog.setWindowTitle("Select Nominal Variable")
            dialog.exec_()
            selected_facet_name = params.get("selected_outcome")
            if selected_facet_name is not None:
                log.info("selected facet:")
                log.info(selected_facet_name)
                selected_facet_index = braviz_tab_data.get_var_idx(
                    selected_facet_name)
                self.ui.nomina_combo.addItem(selected_facet_name)
                self.ui.nomina_combo.setCurrentIndex(
                    self.ui.nomina_combo.count() - 1)
                self.change_nominal_variable(selected_facet_index)
        else:
            selected_name = self.ui.nomina_combo.currentText()
            if selected_name == self.nominal_name:
                return
            if str(selected_name) != self.nominal_name:
                selected_index = braviz_tab_data.get_var_idx(
                    str(selected_name))

                log.info("%s, %s" % (selected_index, selected_name))
                self.change_nominal_variable(selected_index)

    def select_rational_variable(self, index):
        log = logging.getLogger(__name__)
        if index == 0:
            params = {}
            dialog = braviz.interaction.qt_dialogs.SelectOneVariableWithFilter(params, accept_nominal=False,
                                                                               accept_real=True, sample=self.sample)
            dialog.setWindowTitle("Select Nominal Variable")
            dialog.exec_()
            selected_facet_name = params.get("selected_outcome")
            if selected_facet_name is not None:
                log.info("selected facet: ")
                log.info(selected_facet_name)
                selected_facet_index = braviz_tab_data.get_var_idx(
                    selected_facet_name)
                self.ui.rational_combo.addItem(selected_facet_name)
                self.ui.rational_combo.setCurrentIndex(
                    self.ui.rational_combo.count() - 1)
                self.change_rational_variable(selected_facet_index)
        else:
            selected_name = self.ui.rational_combo.currentText()
            if str(selected_name) != self.rational_name:
                selected_index = braviz_tab_data.get_var_idx(
                    str(selected_name))
                log = logging.getLogger(__name__)
                log.info("%s, %s" % (selected_index, selected_name))
                self.change_rational_variable(selected_index)

    def take_screenshot(self, scenario_index):
        geom = self.geometry()
        pixmap = QtGui.QPixmap.grabWindow(QtGui.QApplication.desktop().winId(), geom.x(), geom.y(), geom.width(),
                                          geom.height())
        file_name = "scenario_%d.png" % scenario_index
        file_path = os.path.join(
            self.reader.get_dyn_data_root(), "braviz_data", "scenarios", file_name)
        pixmap.save(file_path, "png")
        log = logging.getLogger(__name__)
        log.info("chick %s" % file_path)

    def __get_state(self):
        state = {}
        # variables
        var_state = {
            "nominal": self.nominal_index, "rational": self.rational_index}
        state["variables"] = var_state
        # sample
        sample_state = {"ids": self.sample}
        state["sample"] = sample_state
        # visualization
        vis_state = {"scenario": self.current_scenario}
        cameras = {}
        for subj in self.sample:
            cameras[subj] = self.viewers_dict[subj].get_camera_parameters()
        vis_state["cameras"] = cameras
        vis_state["space"] = self.current_space
        state["viz"] = vis_state
        # meta
        meta = {"date": datetime.datetime.now(), "exec": sys.argv, "machine": platform.node(),
                "application": os.path.splitext(os.path.basename(__file__))[0]}
        state["meta"] = meta
        return state

    def save_scenario(self):
        state = self.__get_state()
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

    def load_scenario_dialog(self):
        new_state = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(
            "sample_overview", new_state)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == QtGui.QDialog.Accepted:
            log.info("New state : ")
            log.info(new_state)
            self.load_scenario(new_state)

    def load_scenario(self, state, initialized=True):
        #sample and scneario
        sample_state = state["sample"]
        new_sample = sample_state["ids"]

        vis_state = state["viz"]
        scenario = vis_state["scenario"]
        subj_state = scenario.get("subject_state")
        log = logging.getLogger(__name__)
        log.info("new scenario: %s" % scenario)
        if subj_state is not None:
            try:
                subj_state.pop("current_subject")
            except KeyError:
                pass
        try:
            space = scenario["camera_state"].pop("space")
        except KeyError:
            log.info("no space found")
        else:
            self.current_space = space
            index = self.ui.space_combo.findText(space)
            self.ui.space_combo.setCurrentIndex(index)

        if initialized is True:
            self.change_sample(new_sample, scenario)
            var_state = state["variables"]
            self.load_scalar_data(
                var_state["rational"], var_state["nominal"], force=True)
        else:
            self.sample = list(new_sample)
            var_state = state["variables"]
            self.load_scalar_data(
                var_state["rational"], var_state["nominal"], force=True)
            self.current_scenario = scenario
            self.add_subject_viewers(scenario)

        # variables

        self.re_arrange_viewers()

        # cameras
        cameras = vis_state["cameras"]
        for subj in self.sample:
            self.viewers_dict[subj].set_camera(*cameras[subj])

    def change_sample(self, new_sample, visualization_dict=None):
        # remove selection
        logger = logging.getLogger(__name__)
        logger.info("new sample: %s", new_sample)
        if self.current_selection is not None:
            i_widget = self.widgets_dict[self.current_selection]
            i_widget.setFrameStyle(QtGui.QFrame.NoFrame)
            self.current_selection = None

        old_sample = self.sample
        # reuse old widgets
        new_viewers_dict = {}
        new_widgets_dict = {}

        for os, ns in izip(old_sample, new_sample):
            new_viewers_dict[ns] = self.viewers_dict[os]
            new_widgets_dict[ns] = self.widgets_dict[os]
            # setup tooltip, and handlers
            self.__set_viewer_subject(new_widgets_dict[ns], ns)

        # delete left_over_widgets
        for os in old_sample[len(new_sample):]:
            widget = self.widgets_dict.pop(os)
            level = self.scalar_data.ix[os, self.nominal_name]
            if np.isnan(level):
                level = "nan"
            lay = self.inside_layouts[level]
            lay.removeWidget(widget)
            widget.deleteLater()
        # create new widgets
        log = logging.getLogger(__name__)
        for ns in new_sample[len(old_sample):]:
            log.info("creating widget for subject %s" % ns)
            viewer = self.__create_viewer(ns, None)
            new_viewers_dict[ns] = viewer.subject_viewer
            new_widgets_dict[ns] = viewer
            # needs to show before initializing
            level0 = self.scalar_data[self.nominal_name].iloc[0]
            self.inside_layouts[level0].addWidget(viewer, 0, 0)
            viewer.initialize_widget()
            QtGui.QApplication.instance().processEvents()

        self.sample = new_sample
        self.load_scalar_data(
            self.rational_index, self.nominal_index, force=True)
        self.viewers_dict = new_viewers_dict
        self.widgets_dict = new_widgets_dict
        log.info("loading visualization dict:")
        log.info(visualization_dict)
        if visualization_dict is not None:
            self.current_scenario = visualization_dict
        self.reload_viewers(self.current_scenario)

    def launch_mri_viewer(self, subject):
        log = logging.getLogger(__name__)
        if self.current_scenario is not None:
            scenario = self.current_scenario["meta"]["scn_id"]
        else:
            scenario = 0

        log.info("launching viewer")
        if self._message_client is None:
            log.warning("Menu not available, can't launch new viewer")
            return
        args = [sys.executable, "-m", "braviz.applications.subject_overview", str(scenario),
                self._message_client.server_broadcast, self._message_client.server_receive, str(subject)]
        braviz.utilities.launch_sub_process(args)

    def show_in_mri_viewer(self, subj):
        log = logging.getLogger(__name__)
        log.info("showing subject %s" % subj)
        if self._message_client is not None:
            self._message_client.send_message({"subject": str(subj)})

    def receive_message(self, msg):
        subj = msg.get("subject")
        if subj is not None:
            self.locate_subj(subj)
        if "sample" in msg:
            self.handle_sample_message(msg)

    def set_sample(self, new_sample):
        log = logging.getLogger(__name__)
        log.info("new sample: %s" % new_sample)
        self.change_sample(list(new_sample))
        self.load_scalar_data(
            self.rational_index, self.nominal_index, force=True)
        self.re_arrange_viewers()

    def load_sample(self):
        dialog = braviz.applications.sample_select.SampleLoadDialog(
            new__and_load=True,
            server_broadcast=None if self._message_client is None else self._message_client.server_broadcast,
            server_receive=None if self._message_client is None else self._message_client.server_receive,
        )
        res = dialog.exec_()
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            self.set_sample(new_sample)

    def send_sample(self):
        if self._message_client is None:
            log = logging.getLogger(__name__)
            log.warning("Can't send message, no menu found")
            return
        msg = {"sample" : list(self.sample)}
        self._message_client.send_message(msg)

    def modify_sample(self):
        if self._message_client is not None:
            braviz.applications.sample_select.launch_sample_create_dialog(
                server_broadcast=self._message_client.server_broadcast,
                server_receive=self._message_client.server_receive,
                parent_id=os.getpid(),
                sample=self.sample
            )
        else:
            braviz.applications.sample_select.launch_sample_create_dialog(
                sample=self.sample
            )

    def handle_sample_message(self, msg):
        sample = msg.get("sample", tuple())
        target = msg.get("target")
        if target is not None:
            accept = target == os.getpid()
        else:
            accept = self.accept_samples(len(sample))
        if accept:
            self.set_sample(sample)

    def accept_samples(self, sample_size):
        if self.sample_message_policy == "ask":
            answer = QtGui.QMessageBox.question(
                self, "Sample Received", "Size=%d\nAccept sample?"%sample_size,
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.YesToAll | QtGui.QMessageBox.NoToAll,
                QtGui.QMessageBox.Yes)
            if answer == QtGui.QMessageBox.Yes:
                return True
            elif answer == QtGui.QMessageBox.YesToAll:
                self.update_samples_policy("always")
                return True
            elif answer == QtGui.QMessageBox.No:
                return False
            elif answer == QtGui.QMessageBox.NoToAll:
                self.update_samples_policy("never")
                return False
        elif self.sample_message_policy == "always":
            return True
        else:
            return False

    def update_samples_policy(self, item):
        if item == "ask":
            self.ui.actionAlways.setChecked(False)
            self.ui.actionNever.setChecked(False)
            self.ui.actionAsk.setChecked(True)
        elif item == "never":
            self.ui.actionAlways.setChecked(False)
            self.ui.actionNever.setChecked(True)
            self.ui.actionAsk.setChecked(False)
        elif item == "always":
            self.ui.actionAlways.setChecked(True)
            self.ui.actionNever.setChecked(False)
            self.ui.actionAsk.setChecked(False)
        else:
            assert False
        self.sample_message_policy = item

    def save_figure(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Plot", ".", "PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.plot.fig.savefig(filename)

    def save_data(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Data", ".", "csv (*.csv)"))
        if len(filename) > 0:
            s_vars = [self.outcome_var_name] + \
                     list(self.regressors_model.get_regressors())
            out_df = braviz_tab_data.get_data_frame_by_name(s_vars)
            out_df.to_csv(filename)


def say_ciao():
    log = logging.getLogger(__name__)
    log.info("Exiting sample overview")


def run(server_broadcast=None, server_receive=None, scenario=None):
    """
    Launches the sample_overview application

    Args:
        server_broadcast (str) : The address used by a message broker to broadcast message
        server_receive (str) : The address used by a message broker to receive messages
        scenario (int) : The scenario id to load at startup
    """
    import sys
    from braviz.utilities import configure_logger_from_conf

    configure_logger_from_conf("sample_overview")
    log = logging.getLogger(__name__)
    app = QtGui.QApplication([])
    main_window = SampleOverview(server_broadcast, server_receive, scenario)
    main_window.show()
    main_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    main_window.destroyed.connect(say_ciao)
    try:
        sys.exit(app.exec_())
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    # args: [scenario] [server_broadcast] [server_receive]
    import sys

    from braviz.utilities import configure_logger_from_conf

    configure_logger_from_conf("sample_overview")
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

    run(server_broadcast, server_receive, scenario)
