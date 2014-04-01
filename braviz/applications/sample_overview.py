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

import numpy as np

SAMPLE_SIZE = 0.3
NOMINAL_VARIABLE = 11 # GENRE
RATIONAL_VARIBLE = 1 # VCIIQ

class SampleOverview(QtGui.QMainWindow):
    def __init__(self):
        super(SampleOverview, self).__init__()
        self.reader = braviz.readAndFilter.kmc40AutoReader()

        self.plot_widget = None
        self.sample = braviz_tab_data.get_subjects()
        self.subject_viewer_widgets = []
        self.viewers_dict = {}
        self.widgets_dict = {}

        self.inside_layouts = dict()
        self.row_scroll_widgets = dict()
        self.row_widget_contents = dict()

        self.scalar_data = None
        self.nominal_name = None

        self.current_selection = None
        self.current_scenario = None

        self.ui = None
        self.setup_gui()


        self.load_scalar_data()
        QtCore.QTimer.singleShot(100, self.add_subject_viewers)

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
        self.ui.row_layout.setContentsMargins(0,0,0,0)
        self.ui.progress_bar = QtGui.QProgressBar()
        self.ui.camera_combo.currentIndexChanged.connect(self.camera_combo_handle)
        self.ui.actionLoad_scenario.triggered.connect(self.load_scenario)

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
            self.row_widget_contents[level]=contents
            #contents.setGeometry(QtCore.QRect(0, 0, 345, 425))
            inside_lay = QtGui.QGridLayout(contents)
            inside_lay.setContentsMargins(0,0,0,0)
            self.inside_layouts[level] = inside_lay
            contents.setLayout(inside_lay)
            scroll.setWidget(contents)
            self.ui.row_layout.insertWidget(0,scroll,9)

        for subj in self.sample:
            level = self.scalar_data.ix[subj,self.nominal_name]
            contents = self.row_widget_contents[level]
            viewer = QSuvjectViwerWidget(self.reader, contents)
            self.subject_viewer_widgets.append(viewer)
            viewer.setToolTip(str(subj))
            self.viewers_dict[subj] = viewer.subject_viewer
            self.widgets_dict[subj] = viewer
            dummy_i = self.callback_maker(subj)
            viewer.subject_viewer.iren.AddObserver("LeftButtonPressEvent", dummy_i, 1.0)
            QtGui.QApplication.instance().processEvents()

        #add viewers to rows
        for subj,viewer in self.widgets_dict.iteritems():
            level = self.scalar_data.ix[subj,self.nominal_name]
            i = self.inside_layouts[level].columnCount()
            self.inside_layouts[level].addWidget(viewer, 0, i)
            self.inside_layouts[level].setColumnMinimumWidth(i, 400)

        for viewer in self.subject_viewer_widgets:
            viewer.initialize_widget()
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
        level = self.scalar_data.ix[subj,self.nominal_name]
        self.row_scroll_widgets[level].ensureWidgetVisible(i_widget)
        i_widget.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)
        i_widget.setLineWidth(3)

        self.current_selection = subj

        #locate in bar plot
        self.plot_widget.highlight_id(int(subj))
        self.ui.camera_combo.setItemText(2,"Copy from %s"%self.current_selection)


    def load_scalar_data(self):
        self.scalar_data = braviz_tab_data.get_data_frame_by_index((RATIONAL_VARIBLE,NOMINAL_VARIABLE), self.reader)
        self.nominal_name = self.scalar_data.columns[1]
        #Take random subsample
        idx = self.scalar_data.index
        idx2 = np.random.choice(idx, np.ceil(len(idx) * SAMPLE_SIZE), replace=False)
        self.scalar_data = self.scalar_data.loc[idx2]
        self.scalar_data.sort(self.scalar_data.columns[0], inplace=True, ascending=False)
        self.sample = [int(i) for i in self.scalar_data.index]
        labels_dict = braviz_tab_data.get_labels_dict(NOMINAL_VARIABLE)
        self.plot_widget.draw_bars(self.scalar_data, orientation="horizontal",group_labels=labels_dict)

    def select_from_bar(self, subj_id):
        print subj_id
        self.locate_subj(int(subj_id))

    def select_from_viewer(self, subj_id):
        print "Select from viewer %s" % subj_id
        self.locate_subj(subj_id)

    def load_scenario(self):
        return_dict = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog("subject_overview", return_dict)
        dialog.exec_()
        subj_state = return_dict.get("subject_state")
        if subj_state is not None:
            subj_state.pop("current_subject")
        print return_dict
        self.reload_viewers(scenario=return_dict)

    def load_scenario_in_viewer(self, viewer, scenario_dict, subj):
        wanted_state = scenario_dict
        self.current_scenario = wanted_state
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
        #camera panel
        self.__load_camera_from_scenario(viewer)
        return

    def __load_camera_from_scenario(self,viewer):
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

    def __set_camera_parameters(self,viewer,parameters):
        viewer.set_camera(*parameters)

    def __copy_camera_from_subject(self,subj):
        viewer = self.viewers_dict[subj]
        parameters = viewer.get_camera_parameters()
        for subj2,viewer in self.viewers_dict.iteritems():
            if subj2 != subj:
                self.__set_camera_parameters(viewer,parameters)


    def reset_cameras_to_scenario(self):
        for viewer in self.viewers_dict.itervalues():
            self.__load_camera_from_scenario(viewer)

    def camera_combo_handle(self,index):
        if index == 0:
            return
        if index == 1:
            self.reset_cameras_to_scenario()
        if index == 2:
            self.__copy_camera_from_subject(self.current_selection)

        self.ui.camera_combo.setCurrentIndex(0)
def say_ciao():
    print "ciao"

def run():
    import sys

    app = QtGui.QApplication([])
    main_window = SampleOverview()
    main_window.show()
    main_window.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    main_window.destroyed.connect(say_ciao)
    sys.exit(app.exec_())


if __name__ == "__main__":
    run()