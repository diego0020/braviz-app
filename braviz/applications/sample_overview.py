from __future__ import division
__author__ = 'diego'

from PyQt4 import QtGui
from PyQt4 import QtCore
import braviz
from braviz.visualization.subject_viewer import QSuvjectViwerWidget
from braviz.interaction.qt_guis.sample_overview import Ui_SampleOverview
from braviz.interaction import qt_dialogs
from braviz.readAndFilter import tabular_data as braviz_tab_data

from itertools import izip

class SampleOverview(QtGui.QMainWindow):
    def __init__(self):
        super(SampleOverview,self).__init__()
        self.reader = braviz.readAndFilter.kmc40AutoReader()

        self.plot_widget = None
        self.sample = braviz_tab_data.get_subjects()
        self.subject_viewer_widgets = []
        self.viewers_dict = {}
        self.inside_layout = None

        self.ui = None
        self.setup_gui()

        QtCore.QTimer.singleShot(100,self.add_subject_viewers)
    def setup_gui(self):
        self.ui = Ui_SampleOverview()
        self.ui.setupUi(self)
        self.plot_widget = qt_dialogs.MatplotWidget(self.ui.plot_1,initial_message="Hello")
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
        self.ui.pushButton.pressed.connect(self.locate_556)
        self.ui.pushButton.setText("Locat 556")

        self.ui.progress_bar.setValue(0)

    def add_subject_viewers(self):
        for subj in self.sample:
            viewer = QSuvjectViwerWidget(self.reader,self.ui.scroll_1)
            self.subject_viewer_widgets.append(viewer)
            viewer.setToolTip(str(subj))
            QtGui.QApplication.instance().processEvents()
        for i,viewer in enumerate(self.subject_viewer_widgets):
            self.inside_layout.addWidget(viewer,0,i)
            self.inside_layout.setColumnMinimumWidth(i, 400)
            self.viewers_dict[subj] = viewer.subject_viewer
        for viewer in self.subject_viewer_widgets:
            viewer.initialize_widget()
            QtGui.QApplication.instance().processEvents()

        for i,(subj,viewer) in enumerate(izip(self.sample,self.subject_viewer_widgets)):
            self.ui.progress_bar.setValue(i/len(self.sample)*100)
            if viewer.subject_viewer.ren_win.GetMapped():
                print "%d viewer is visible"%subj
            else:
                print "%d viewer is not visible"%subj
            self.load_initial_view(subj,viewer.subject_viewer)
            QtGui.QApplication.instance().processEvents()
        self.ui.progress_bar.setValue(100)

    def load_initial_view(self,subject,viewer):
        img_code = str(braviz_tab_data.get_var_value(braviz_tab_data.IMAGE_CODE,subject))
        try:
            viewer.change_subject(img_code)
            viewer.change_current_space("Talairach",skip_render=True)
            viewer.image.change_image_modality("MRI",skip_render=True)
            viewer.models.set_models(['CC_Anterior','CC_Central','CC_Mid_Anterior',
                                      'CC_Mid_Posterior','CC_Posterior'],skip_render=True)
            viewer.reset_camera(1)
        except Exception as e:
            print e.message
        QtGui.QApplication.instance().processEvents()

    def locate_556(self):
        i = self.sample.index(566)
        i_widget = self.subject_viewer_widgets[i]
        self.ui.scroll_1.ensureWidgetVisible(i_widget)

def run():
    app = QtGui.QApplication([])
    main_window = SampleOverview()
    main_window.show()
    app.exec_()

if __name__ == "__main__":
    run()