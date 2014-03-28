from __future__ import division
__author__ = 'diego'

from PyQt4 import QtGui
from braviz.interaction.qt_guis.sample_overview import Ui_SampleOverview
from braviz.interaction import qt_dialogs
from braviz.readAndFilter import tabular_data as braviz_tab_data

class SampleOverview(QtGui.QMainWindow):
    def __init__(self):
        super(SampleOverview,self).__init__()

        self.plot_widget = None
        self.sample = braviz_tab_data.get_subjects()
        self.subject_viewers = []
        self.inside_layout = None

        self.ui = None
        self.setup_gui()

        self.add_subject_viewers()
    def setup_gui(self):
        self.ui = Ui_SampleOverview()
        self.ui.setupUi(self)
        self.plot_widget = qt_dialogs.MatplotWidget(self.ui.plot_1,initial_message="Hello")
        self.ui.plot_1_layout = QtGui.QHBoxLayout()
        self.ui.plot_1_layout.addWidget(self.plot_widget)
        self.ui.plot_1.setLayout(self.ui.plot_1_layout)
        self.inside_layout = QtGui.QGridLayout()
        self.ui.inside_frame.setLayout(self.inside_layout)
        self.ui.view.layout().setColumnStretch(0,4)
        self.ui.view.layout().setColumnStretch(1,1)

    def add_subject_viewers(self):
        for i,subj in enumerate(self.sample):
            label = QtGui.QLabel(self.ui.inside_frame)
            label.setText(str(subj))
            self.subject_viewers.append(label)
            self.inside_layout.addWidget(label,0,i)
            self.inside_layout.setColumnMinimumWidth(i, 200)



def run():
    app = QtGui.QApplication([])
    main_window = SampleOverview()
    main_window.show()
    app.exec_()

if __name__ == "__main__":
    run()