from __future__ import division

__author__ = 'diego'

from PyQt4 import QtGui
from PyQt4 import QtCore
import braviz
from braviz.visualization.subject_viewer import QSuvjectViwerWidget
from braviz.interaction.qt_guis.sample_overview import Ui_SampleOverview
import braviz.interaction.qt_dialogs
from braviz.visualization.matplotlib_widget import MatplotWidget
from braviz.readAndFilter import tabular_data as braviz_tab_data
from braviz.readAndFilter import user_data as braviz_user_data
from itertools import izip
import numpy as np
import platform

from collections import Counter
import os
import datetime
import functools
import cPickle
import multiprocessing.connection
import binascii
import subprocess

#SAMPLE_SIZE = 0.3
SAMPLE_SIZE = 0.2
NOMINAL_VARIABLE = 11  # GENRE
RATIONAL_VARIBLE = 1  # VCIIQ


class SampleOverview(QtGui.QMainWindow):
    def __init__(self, initial_scenario=None):
        super(SampleOverview, self).__init__()
        self.reader = braviz.readAndFilter.kmc40AutoReader()

        self.plot_widget = None
        self.sample = braviz_tab_data.get_subjects()
        self.viewers_dict = {}
        self.widgets_dict = {}
        self.widget_observers = {}

        self.inside_layouts = dict()
        self.row_scroll_widgets = dict()
        self.row_widget_contents = dict()

        self.scalar_data = None
        self.nominal_name = None
        self.nominal_index = None
        self.rational_index = None
        self.rational_name = None

        self.current_selection = None
        self.current_scenario = None

        self.mri_viewer = None
        self.mri_pipe = None

        self.ui = None
        self.setup_gui()
        if initial_scenario is None:
            self.take_random_sample()
            self.load_scalar_data(RATIONAL_VARIBLE, NOMINAL_VARIABLE)
            QtCore.QTimer.singleShot(100, self.add_subject_viewers)
        else:
            self.sample = []
            state_str = braviz_user_data.get_scenario_data(initial_scenario)
            state = cPickle.loads(str(state_str))
            load_scn_funct = functools.partial(self.load_scenario, state)
            QtCore.QTimer.singleShot(100, load_scn_funct)

    def change_nominal_variable(self, new_var_index):
        self.load_scalar_data(self.rational_index, new_var_index)
        self.re_arrange_viewers()

    def change_rational_variable(self, new_var_index):
        self.load_scalar_data(new_var_index, self.nominal_index)
        self.re_arrange_viewers()

    def re_arrange_viewers(self):
        #reorganize rows
        unique_levels = sorted(self.scalar_data[self.nominal_name].unique())

        new_scrolls_dict = dict()
        new_contents_dict = dict()
        new_layouts_dict = dict()
        old_levels = sorted(self.row_scroll_widgets.keys())

        #reuse existing rows
        for nl, ol in izip(unique_levels, old_levels):
            new_scrolls_dict[nl] = self.row_scroll_widgets[ol]
            new_contents_dict[nl] = self.row_widget_contents[ol]
            new_layouts_dict[nl] = self.inside_layouts[ol]

        for nl in unique_levels[len(old_levels):]:
            #create new rows
            scroll = QtGui.QScrollArea(self.ui.view)
            new_scrolls_dict[nl] = scroll
            scroll.setWidgetResizable(True)
            contents = QtGui.QWidget()
            new_contents_dict[nl] = contents
            inside_lay = QtGui.QGridLayout(contents)
            inside_lay.setContentsMargins(0, 0, 0, 0)
            new_layouts_dict[nl] = inside_lay
            contents.setLayout(inside_lay)
            scroll.setWidget(contents)
            self.ui.row_layout.insertWidget(0, scroll, 9)
            print "new row created"

        #set to 0 column widths
        for nl in unique_levels:
            lay = new_layouts_dict[nl]
            for i in xrange(lay.columnCount()):
                lay.setColumnMinimumWidth(i, 0)
        cnt = Counter()
        for subj in self.sample:
            viewer = self.widgets_dict[subj]
            level = self.scalar_data.ix[subj, self.nominal_name]
            i = cnt[level]
            new_layouts_dict[level].addWidget(viewer, 0, i)
            new_layouts_dict[level].setColumnMinimumWidth(i, 400)
            cnt[level] += 1

        print cnt
        for nl in unique_levels:
            print nl, new_layouts_dict[nl].columnCount()

        #delete useless rows
        for ol in old_levels[len(unique_levels):]:
            print "adios row"
            self.row_scroll_widgets[ol].deleteLater()

        #set dictionaries
        self.row_scroll_widgets = new_scrolls_dict
        self.row_widget_contents = new_contents_dict
        self.inside_layouts = new_layouts_dict


    def take_random_sample(self):
        sample = braviz_tab_data.get_subjects()
        self.sample = list(np.random.choice(sample, np.ceil(len(sample) * SAMPLE_SIZE), replace=False))

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
        self.ui.progress_bar = QtGui.QProgressBar()
        self.ui.camera_combo.currentIndexChanged.connect(self.camera_combo_handle)
        self.ui.action_load_visualization.triggered.connect(self.load_visualization)
        self.ui.nomina_combo.currentIndexChanged.connect(self.select_nominal_variable)
        self.ui.rational_combo.currentIndexChanged.connect(self.select_rational_variable)
        self.ui.action_screenshot.triggered.connect(self.take_screenshot)
        self.ui.action_save_scenario.triggered.connect(self.save_scenario)
        self.ui.action_load_scenario.triggered.connect(self.load_scenario_dialog)

        self.ui.progress_bar.setValue(0)

    def callback_maker(self, subj):
        def cb(obj, event):
            self.select_from_viewer(subj)

        return cb

    def add_subject_viewers(self):
        #create parents:
        for level in self.scalar_data[self.nominal_name].unique():
            scroll = QtGui.QScrollArea(self.ui.view)
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
            self.ui.row_layout.insertWidget(0, scroll, 9)

        for subj in self.sample:
            level = self.scalar_data.ix[subj, self.nominal_name]
            contents = self.row_widget_contents[level]
            viewer = self.__create_viewer(subj, contents)
            self.viewers_dict[subj] = viewer.subject_viewer
            self.widgets_dict[subj] = viewer
            QtGui.QApplication.instance().processEvents()

        #add viewers to rows
        for subj in self.sample:
            viewer = self.widgets_dict[subj]
            level = self.scalar_data.ix[subj, self.nominal_name]
            i = self.inside_layouts[level].columnCount()
            self.inside_layouts[level].addWidget(viewer, 0, i)
            self.inside_layouts[level].setColumnMinimumWidth(i, 400)

        for widget in self.widgets_dict.values():
            widget.initialize_widget()
            QtGui.QApplication.instance().processEvents()

        self.reload_viewers()

    def reload_viewers(self, scenario=None):
        self.ui.statusbar.addPermanentWidget(self.ui.progress_bar)
        self.ui.progress_bar.show()
        for i, (subj, viewer) in enumerate(self.viewers_dict.iteritems()):
            self.ui.progress_bar.setValue(i / len(self.sample) * 100)
            print "loading viewer %d " % subj
            try:
                if scenario is None:
                    self.load_initial_view(subj, viewer)
                else:
                    self.load_scenario_in_viewer(viewer, scenario, subj)
            except Exception as e:
                print e.message
                raise
            QtGui.QApplication.instance().processEvents()
        self.ui.progress_bar.setValue(100)
        self.ui.statusbar.removeWidget(self.ui.progress_bar)
        self.ui.statusbar.showMessage("Loading complete")

    def load_initial_view(self, subject, viewer):
        img_code = str(braviz_tab_data.get_var_value(braviz_tab_data.IMAGE_CODE, subject))
        try:
            viewer.change_subject(img_code)
            #For testing
            return
            viewer.change_current_space("Talairach", skip_render=True)
            viewer.image.change_image_modality("MRI", skip_render=True)
            viewer.models.set_models(['CC_Anterior', 'CC_Central', 'CC_Mid_Anterior',
                                      'CC_Mid_Posterior', 'CC_Posterior'], skip_render=True)
            viewer.reset_camera(1)
        except Exception as e:
            print e.message
        QtGui.QApplication.instance().processEvents()


    def locate_subj(self, subj):
        #restore previous
        if self.current_selection is not None:
            i_widget = self.widgets_dict[self.current_selection]
            i_widget.setFrameStyle(QtGui.QFrame.NoFrame)

        #new selection
        i_widget = self.widgets_dict[subj]
        level = self.scalar_data.ix[subj, self.nominal_name]
        self.row_scroll_widgets[level].ensureWidgetVisible(i_widget)
        i_widget.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Plain)
        i_widget.setLineWidth(10)
        i_widget.setMidLineWidth(1)

        self.current_selection = subj

        #locate in bar plot
        self.plot_widget.highlight_id(int(subj))
        self.ui.camera_combo.setItemText(2, "Copy from %s" % self.current_selection)


    def load_scalar_data(self, rational_var_index, nominal_var_index):
        self.rational_index = rational_var_index
        self.nominal_index = nominal_var_index
        self.scalar_data = braviz_tab_data.get_data_frame_by_index((rational_var_index, nominal_var_index), self.reader)
        self.rational_name = self.scalar_data.columns[0]
        self.nominal_name = self.scalar_data.columns[1]
        #Take random subsample
        self.scalar_data = self.scalar_data.loc[self.sample]
        self.scalar_data.sort(self.rational_name, inplace=True, ascending=False)
        self.sample.sort(key=lambda s: self.scalar_data[self.rational_name][s])
        print self.sample
        labels_dict = braviz_tab_data.get_labels_dict(nominal_var_index)
        self.plot_widget.draw_bars(self.scalar_data, orientation="horizontal", group_labels=labels_dict)

    def select_from_bar(self, subj_id):
        print subj_id
        self.locate_subj(int(subj_id))

    def select_from_viewer(self, subj_id):
        print "Select from viewer %s" % subj_id
        self.locate_subj(subj_id)

    def load_visualization(self):
        return_dict = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog("subject_overview", return_dict, self.reader)
        dialog.exec_()
        subj_state = return_dict.get("subject_state")
        if subj_state is not None:
            subj_state.pop("current_subject")
        print return_dict
        self.current_scenario = return_dict
        self.reload_viewers(scenario=return_dict)

    def load_scenario_in_viewer(self, viewer, scenario_dict, subj):
        img_code = str(braviz_tab_data.get_var_value(braviz_tab_data.IMAGE_CODE, subj))
        wanted_state = scenario_dict
        #images panel
        image_state = wanted_state.get("image_state")
        if image_state is not None:
            mod = image_state.get("modality")
            if mod is not None:
                try:
                    viewer.image.change_image_modality(mod, skip_render=True)
                except Exception as e:
                    print e.message
            orient = image_state.get("orientation")
            if orient is not None:
                orientation_dict = {"Axial": 2, "Coronal": 1, "Sagital": 0}
                viewer.image.change_image_orientation(orientation_dict[orient], skip_render=True)
            window = image_state.get("window")
            if window is not None:
                viewer.image.set_image_window(window, skip_render=True)
            level = image_state.get("level")
            if level is not None:
                viewer.image.set_image_level(level, skip_render=True)
            slice = image_state.get("slice")
            if slice is not None:
                viewer.image.set_image_slice(int(slice), skip_render=True)
        QtGui.QApplication.instance().processEvents()
        #segmentation panel
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
                    viewer.models.set_models(selected_structs, skip_render=True)
                except Exception as e:
                    print e.message
        QtGui.QApplication.instance().processEvents()
        #tractography panel
        tractography_state = wanted_state.get("tractography_state")
        if tractography_state is not None:
            bundles = tractography_state.get("bundles")
            if bundles is not None:
                try:
                    viewer.tractography.set_active_db_tracts(bundles, skip_render=True)
                except Exception as e:
                    print e.message

            from_segment = tractography_state.get("from_segment")
            if from_segment is not None:
                try:
                    if from_segment == "None":
                        viewer.tractography.hide_checkpoints_bundle(skip_render=True)
                    elif from_segment == "Through Any":
                        viewer.tractography.set_bundle_from_checkpoints(selected_structs, False, skip_render=True)
                    else:
                        viewer.tractography.set_bundle_from_checkpoints(selected_structs, True, skip_render=True)
                except Exception as e:
                    print e.message
            color = tractography_state.get("color")
            if color is not None:
                color_codes = {"Orientation": "orient", "FA (Point)": "fa", "By Line": "rand", "By Bundle": "bundle"}
                try:
                    viewer.tractography.change_color(color_codes[color], skip_render=True)
                except Exception as e:
                    print e.message

            opac = tractography_state.get("opacity")
            if opac is not None:
                try:
                    viewer.tractography.set_opacity(opac, skip_render=True)
                except Exception as e:
                    print e.message
        QtGui.QApplication.instance().processEvents()
        #subject
        try:
            viewer.change_subject(img_code)
        except Exception as e:
            print e.message
        #camera panel
        self.__load_camera_from_scenario(viewer)
        return

    def __load_camera_from_scenario(self, viewer):
        wanted_state = self.current_scenario
        camera_state = wanted_state.get("camera_state")
        if camera_state is not None:
            space = camera_state.get("space")
            if space is not None:
                viewer.change_current_space(space)
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
        for subj2, viewer in self.viewers_dict.iteritems():
            if subj2 != subj:
                self.__set_camera_parameters(viewer, parameters)

    def __create_viewer(self, subject, parent):
        viewer = QSuvjectViwerWidget(self.reader, parent)
        self.__set_viewer_subject(viewer, subject)
        return viewer


    def __set_viewer_subject(self, viewer, subject):
        viewer.setToolTip(str(subject))
        dummy_i = self.callback_maker(subject)
        #remove old observer
        old_observer = self.widget_observers.get(id(viewer))
        if old_observer is not None:
            viewer.subject_viewer.iren.RemoveObserver(old_observer)
        obs_id=viewer.subject_viewer.iren.AddObserver("LeftButtonPressEvent", dummy_i, 1.0)
        self.widget_observers[id(viewer)]=obs_id
        viewer.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        context_handler = self.__get_context_menu_handler(viewer,subject)
        viewer.customContextMenuRequested.connect(context_handler)


    def __get_context_menu_handler(self, widget,subj):
        def context_menu_handler(pos):
            print "Context for", subj
            menu = QtGui.QMenu()
            action = QtGui.QAction("Show %s in subject viewer"%subj,menu)
            def show_subj_in_mri_viewer():
                self.show_in_mri_viewer(subj)
            action.triggered.connect(show_subj_in_mri_viewer)
            menu.addAction(action)
            global_pos=widget.mapToGlobal(pos)
            menu.exec_(global_pos)

        return context_menu_handler

    def reset_cameras_to_scenario(self):
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

    def select_nominal_variable(self, index):
        if index == 0:
            params = {}
            dialog = braviz.interaction.qt_dialogs.SelectOneVariableWithFilter(params, accept_nominal=True,
                                                                               accept_real=False)
            dialog.setWindowTitle("Select Nominal Variable")
            dialog.exec_()
            selected_facet_name = params.get("selected_outcome")
            if selected_facet_name is not None:
                #print selected_facet_name
                selected_facet_index = braviz_tab_data.get_var_idx(selected_facet_name)
                self.ui.nomina_combo.addItem(selected_facet_name)
                self.ui.nomina_combo.setCurrentIndex(self.ui.nomina_combo.count() - 1)
                self.change_nominal_variable(selected_facet_index)
        else:
            selected_name = self.ui.nomina_combo.currentText()
            if str(selected_name) != self.nominal_name:
                selected_index = braviz_tab_data.get_var_idx(str(selected_name))
                print selected_index, selected_name
                self.change_nominal_variable(selected_index)

    def select_rational_variable(self, index):
        if index == 0:
            params = {}
            dialog = braviz.interaction.qt_dialogs.SelectOneVariableWithFilter(params, accept_nominal=False,
                                                                               accept_real=True)
            dialog.setWindowTitle("Select Nominal Variable")
            dialog.exec_()
            selected_facet_name = params.get("selected_outcome")
            if selected_facet_name is not None:
                #print selected_facet_name
                selected_facet_index = braviz_tab_data.get_var_idx(selected_facet_name)
                self.ui.rational_combo.addItem(selected_facet_name)
                self.ui.rational_combo.setCurrentIndex(self.ui.rational_combo.count() - 1)
                self.change_rational_variable(selected_facet_index)
        else:
            selected_name = self.ui.rational_combo.currentText()
            if str(selected_name) != self.rational_name:
                selected_index = braviz_tab_data.get_var_idx(str(selected_name))
                print selected_index, selected_name
                self.change_rational_variable(selected_index)

    def take_screenshot(self, scenario_index):
        geom = self.geometry()
        pixmap = QtGui.QPixmap.grabWindow(QtGui.QApplication.desktop().winId(), geom.x(), geom.y(), geom.width(),
                                          geom.height())
        file_name = "scenario_%d.png" % scenario_index
        file_path = os.path.join(self.reader.getDataRoot(), "braviz_data", "scenarios", file_name)
        pixmap.save(file_path, "png")
        print "Chik"

    def __get_state(self):
        state = {}
        #variables
        var_state = {}
        var_state["nominal"] = self.nominal_index
        var_state["rational"] = self.rational_index
        state["variables"] = var_state
        #sample
        sample_state = {}
        sample_state["ids"] = self.sample
        state["sample"] = sample_state
        #visualization
        vis_state = {}
        vis_state["scenario"] = self.current_scenario
        cameras = {}
        for subj in self.sample:
            cameras[subj] = self.viewers_dict[subj].get_camera_parameters()
        vis_state["cameras"] = cameras
        state["viz"] = vis_state
        #meta
        meta = {}
        meta["date"] = datetime.datetime.now()
        meta["exec"] = sys.argv
        meta["machine"] = platform.node()
        meta["application"] = os.path.splitext(os.path.basename(__file__))[0]
        state["meta"] = meta
        return state

    def save_scenario(self):
        state = self.__get_state()
        app_name = state["meta"]["application"]
        params = {}
        dialog = braviz.interaction.qt_dialogs.SaveScenarioDialog(app_name, state, params)
        res = dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            scn_id = params["scn_id"]
            take_screen = functools.partial(self.take_screenshot, scn_id)
            QtCore.QTimer.singleShot(500, take_screen)

    def load_scenario_dialog(self):
        new_state = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog("sample_overview", new_state, self.reader)
        res = dialog.exec_()
        if res == QtGui.QDialog.Accepted:
            print new_state
            self.load_scenario(new_state)


    def load_scenario(self, state):
        #sample and scneario
        sample_state = state["sample"]
        new_sample = sample_state["ids"]

        vis_state = state["viz"]
        scn_id = vis_state["scenario"]

        self.change_sample(new_sample, scn_id)

        #variables
        var_state = state["variables"]
        self.load_scalar_data(var_state["rational"], var_state["nominal"])
        self.re_arrange_viewers()

        #cameras
        cameras = vis_state["cameras"]
        for subj in self.sample:
            self.viewers_dict[subj].set_camera(*cameras[subj])

    def change_sample(self, new_sample, scn_id=None):
        #remove selection
        if self.current_selection is not None:
            i_widget = self.widgets_dict[self.current_selection]
            i_widget.setFrameStyle(QtGui.QFrame.NoFrame)
            self.current_selection = None

        old_sample = self.sample
        #reuse old widgets
        new_viewers_dict = {}
        new_widgets_dict = {}


        for os, ns in izip(old_sample, new_sample):
            new_viewers_dict[ns] = self.viewers_dict[os]
            new_widgets_dict[ns] = self.widgets_dict[os]
            #setup tooltip, and handlers
            self.__set_viewer_subject(new_widgets_dict[ns], ns)

        #delete left_over_widgets
        for os in old_sample[len(new_sample):]:
            widget = self.widgets_dict.pop(os)
            level = self.scalar_data.ix[os, self.nominal_name]
            lay = self.inside_layouts[level]
            lay.removeWidget(widget)
            widget.deleteLater()
        #create new widgets
        for ns in new_sample[len(old_sample):]:
            print "creating widget for subject ", ns
            viewer = self.__create_viewer(ns, None)
            new_viewers_dict[ns] = viewer.subject_viewer
            new_widgets_dict[ns] = viewer
            #TODO: Test in linux
            viewer.initialize_widget()

        self.sample = new_sample
        self.viewers_dict = new_viewers_dict
        self.widgets_dict = new_widgets_dict
        self.reload_viewers(scn_id)

    def launch_mri_viewer(self):
        #TODO: Move this to the subject_viewer class
        #copied from anova_task
        address = ('localhost',6001)
        auth_key=multiprocessing.current_process().authkey
        auth_key_asccii = binascii.b2a_hex(auth_key)
        listener = multiprocessing.connection.Listener(address,authkey=auth_key)

        #self.mri_viewer_process = multiprocessing.Process(target=mriMultSlicer.launch_new, args=(pipe_mri_side,))
        print [sys.executable,"-m","braviz.applications.subject_overview","0",auth_key_asccii]
        self.mri_viewer = subprocess.Popen([sys.executable,"-m","braviz.applications.subject_overview",
                                                    "0",auth_key_asccii])

        #self.mri_viewer_process = multiprocessing.Process(target=subject_overview.run, args=(pipe_mri_side,))
        #self.mri_viewer_process.start()
        self.mri_pipe = listener.accept()
        #self.poll_timer.start(200)

    def show_in_mri_viewer(self,subj):
        print "showing subject", subj
        if self.mri_viewer is None:
            self.launch_mri_viewer()
        scn_id = self.current_scenario["meta"]["scn_id"]
        self.mri_pipe.send({"subject": subj,"scenario":scn_id})


def say_ciao():
    print "ciao"


def run(scn_id=None):
    import sys

    app = QtGui.QApplication([])
    main_window = SampleOverview(scn_id)
    main_window.show()
    main_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    main_window.destroyed.connect(say_ciao)
    sys.exit(app.exec_())


if __name__ == "__main__":
    import sys

    scn_id = None
    if len(sys.argv) >= 2:
        scn_id = sys.argv[1]

    run(scn_id)