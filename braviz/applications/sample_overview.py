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

from itertools import izip
import numpy as np

SAMPLE_SIZE = 0.3

class SampleOverview(QtGui.QMainWindow):
    def __init__(self):
        super(SampleOverview,self).__init__()
        self.reader = braviz.readAndFilter.kmc40AutoReader()

        self.plot_widget = None
        self.sample = braviz_tab_data.get_subjects()
        self.subject_viewer_widgets = []
        self.viewers_dict = {}
        self.viewers_dict_reverse = {}
        self.inside_layout = None

        self.scalar_data = None

        self.current_selection = None

        self.ui = None
        self.setup_gui()

        self.load_scalar_data()
        QtCore.QTimer.singleShot(100,self.add_subject_viewers)
    def setup_gui(self):
        self.ui = Ui_SampleOverview()
        self.ui.setupUi(self)
        self.plot_widget = MatplotWidget(self.ui.plot_1)
        self.plot_widget.point_picked.connect(self.select_from_bar)
        self.ui.plot_1_layout = QtGui.QHBoxLayout()
        self.ui.plot_1_layout.addWidget(self.plot_widget)
        self.ui.plot_1.setLayout(self.ui.plot_1_layout)
        self.inside_layout = self.ui.scrollAreaWidgetContents.layout()
        #print self.inside_layout
        #self.inside_layout = QtGui.QGridLayout()
        self.inside_layout.setContentsMargins(0,0,0,0)
        #self.ui.scrollAreaWidgetContents.setLayout(self.inside_layout)
        self.ui.view.layout().setColumnStretch(0,4)
        self.ui.view.layout().setColumnStretch(1,1)
        self.ui.progress_bar= QtGui.QProgressBar()
        self.ui.statusbar.addPermanentWidget(self.ui.progress_bar)
        self.ui.pushButton.pressed.connect(self.load_scenario)
        self.ui.pushButton.setText("load visualization scenario")

        self.ui.progress_bar.setValue(0)

    def callback_maker(self,subj):
        def cb(obj,event):
            self.select_from_viewer(subj)
        return cb
    def add_subject_viewers(self):
        for subj in self.sample:
            viewer = QSuvjectViwerWidget(self.reader,self.ui.scroll_1)
            self.subject_viewer_widgets.append(viewer)
            viewer.setToolTip(str(subj))
            self.viewers_dict[subj] = viewer.subject_viewer
            self.viewers_dict_reverse[id(viewer.subject_viewer.iren)]=subj
            dummy_i = self.callback_maker(subj)
            viewer.subject_viewer.iren.AddObserver("LeftButtonPressEvent",dummy_i,1.0)
            QtGui.QApplication.instance().processEvents()

        for i,viewer in enumerate(self.subject_viewer_widgets):
            self.inside_layout.addWidget(viewer,0,i)
            self.inside_layout.setColumnMinimumWidth(i, 400)

        for viewer in self.subject_viewer_widgets:
            viewer.initialize_widget()
            QtGui.QApplication.instance().processEvents()

        self.reload_viewers()

    def reload_viewers(self,scenario=None):
        for i,(subj,viewer) in enumerate(izip(self.sample,self.subject_viewer_widgets)):
            self.ui.progress_bar.setValue(i/len(self.sample)*100)
            if viewer.subject_viewer.ren_win.GetMapped():
                print "%d viewer is visible"%subj
            else:
                print "%d viewer is not visible"%subj
            try:
                if scenario is None:
                    self.load_initial_view(subj,viewer.subject_viewer)
                else:
                    self.load_scenario_in_viewer(viewer.subject_viewer,scenario,subj)
            except Exception as e:
                print e.message
            QtGui.QApplication.instance().processEvents()
        self.ui.progress_bar.setValue(100)

    def load_initial_view(self,subject,viewer):
        img_code = str(braviz_tab_data.get_var_value(braviz_tab_data.IMAGE_CODE,subject))
        try:
            viewer.change_subject(img_code)
            #For testing
            return
            viewer.change_current_space("Talairach",skip_render=True)
            viewer.image.change_image_modality("MRI",skip_render=True)
            viewer.models.set_models(['CC_Anterior','CC_Central','CC_Mid_Anterior',
                                      'CC_Mid_Posterior','CC_Posterior'],skip_render=True)
            viewer.reset_camera(1)
        except Exception as e:
            print e.message
        QtGui.QApplication.instance().processEvents()


    def locate_subj(self,subj):
        #restore previous
        if self.current_selection is not None:
            i = self.sample.index(self.current_selection)
            i_widget = self.subject_viewer_widgets[i]
            i_widget.setFrameStyle(QtGui.QFrame.NoFrame)

        #new selection
        i = self.sample.index(subj)
        i_widget = self.subject_viewer_widgets[i]
        self.ui.scroll_1.ensureWidgetVisible(i_widget)
        i_widget.setFrameStyle(QtGui.QFrame.Box | QtGui.QFrame.Raised)
        i_widget.setLineWidth(3)

        self.current_selection = subj

        #locate in bar plot
        self.plot_widget.highlight_id(int(subj))


    def load_scalar_data(self):
        self.scalar_data = braviz_tab_data.get_data_frame_by_index((1,),self.reader)
        #Take random subsample

        idx = self.scalar_data.index
        idx2=np.random.choice(idx,np.ceil(len(idx)*SAMPLE_SIZE),replace=False)
        self.scalar_data=self.scalar_data.loc[idx2]
        self.scalar_data.sort(self.scalar_data.columns[0],inplace=True,ascending=False)
        self.sample = [int(i) for i in self.scalar_data.index]
        self.plot_widget.draw_bars(self.scalar_data,orientation="horizontal")

    def select_from_bar(self,subj_id):
        print subj_id
        self.locate_subj(int(subj_id))

    def select_from_viewer(self,subj_id):
        print "Select from viewer %s"%subj_id
        self.locate_subj(subj_id)

    def load_scenario(self):
        return_dict = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog("subject_overview",return_dict)
        dialog.exec_()
        subj_state = return_dict.get("subject_state")
        if subj_state is not None:
            subj_state.pop("current_subject")
        print return_dict
        self.reload_viewers(scenario=return_dict)

    def load_scenario_in_viewer(self,viewer,scenario_dict,subj):
        wanted_state = scenario_dict
        #TODO: add more try/catch clauses
        #images panel
        image_state = wanted_state.get("image_state")
        if image_state is not None:
            mod = image_state.get("modality")
            if mod is not None:
                viewer.image.change_image_modality(mod,skip_render=True)
            orient = image_state.get("orientation")
            if orient is not None:
                orientation_dict = {"Axial": 2, "Coronal": 1, "Sagital": 0}
                viewer.image.change_image_orientation(orientation_dict[orient],skip_render=True)
            window= image_state.get("window")
            if window is not None:
                viewer.image.set_image_window(window,skip_render=True)
            level= image_state.get("level")
            if level is not None:
                viewer.image.set_image_level(level,skip_render=True)
            slice = image_state.get("slice")
            if slice is not None:
                viewer.image.set_image_slice(int(slice),skip_render=True)
        QtGui.QApplication.instance().processEvents()
        #segmentation panel
        segmentation_state =wanted_state.get("segmentation_state")
        selected_structs=tuple()
        if segmentation_state is not None:
            color = segmentation_state.get("color",False)
            if color is not False:
                viewer.models.set_color(color,skip_render=True)

            opac = segmentation_state.get("opacity")
            if opac is not None:
                viewer.models.set_opacity(opac,skip_render=True)
            selected_structs=segmentation_state.get("selected_structs")
            if selected_structs is not None:
                viewer.models.set_models(selected_structs,skip_render=True)
        QtGui.QApplication.instance().processEvents()
        #tractography panel
        tractography_state = wanted_state.get("tractography_state")
        if tractography_state is not None:
            bundles = tractography_state.get("bundles")
            if bundles is not None:
                viewer.tractography.set_active_db_tracts(bundles,skip_render=True)
            from_segment = tractography_state.get("from_segment")
            if from_segment is not None:
                if from_segment == "None":
                    viewer.tractography.hide_checkpoints_bundle(skip_render=True)
                elif from_segment == "Through Any":
                    viewer.tractography.set_bundle_from_checkpoints(selected_structs,False,skip_render=True)
                else:
                    viewer.tractography.set_bundle_from_checkpoints(selected_structs,True,skip_render=True)
            color = tractography_state.get("color")
            if color is not None:
                color_codes = {"Orientation": "orient", "FA (Point)": "fa", "By Line": "rand", "By Bundle": "bundle"}
                viewer.tractography.change_color(color_codes[color],skip_render=True)

            opac = tractography_state.get("opacity")
            if opac is not None:
                viewer.tractography.set_opacity(opac,skip_render=True)
        QtGui.QApplication.instance().processEvents()
        #camera panel
        camera_state = wanted_state.get("camera_state")
        if camera_state is not  None:
            space = camera_state.get("space")
            if space is not None:
                viewer.change_current_space(space)
            cam = camera_state.get("cam_params")
            if cam is not None:
                fp,pos,vu = cam
                viewer.set_camera(fp,pos,vu)
        viewer.ren_win.Render()
        return

def run():
    import sys
    app = QtGui.QApplication([])
    main_window = SampleOverview()
    main_window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    run()