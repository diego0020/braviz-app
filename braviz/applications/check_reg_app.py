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

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

from braviz.interaction.qt_guis.check_reg import Ui_check_reg_app
from braviz.visualization.checkerboard_view import QCheckViewer
from braviz.interaction.qt_widgets import ListValidator, ImageComboBoxManager
from braviz.readAndFilter import tabular_data
from braviz.readAndFilter.config_file import get_config


import braviz

import logging


class CheckRegApp(QMainWindow):

    def __init__(self):
        QMainWindow.__init__(self)
        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.ui = None
        self.image_combo_manager_1 = ImageComboBoxManager(self.reader, show_none=True, show_fmri=False)
        self.image_combo_manager_2 = ImageComboBoxManager(self.reader, show_none=True, show_fmri=False)
        self.vtk_widget = None
        self.vtk_viewer = None
        self.valid_ids = [str(i) for i in tabular_data.get_subjects()]
        self.subjs_validator = ListValidator(self.valid_ids)
        self.completer = QtGui.QCompleter(list(self.valid_ids))
        self.setup_gui()

    def setup_gui(self):
        conf = get_config(__file__)
        initial_subj = conf.get_default_subject()

        self.ui = Ui_check_reg_app()
        self.ui.setupUi(self)
        self.vtk_widget = QCheckViewer(self.reader, self.ui.vtk_frame)
        self.vtk_viewer = self.vtk_widget.viewer
        # view frame
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)

        # image 1
        self.image_combo_manager_1.setup(self.ui.mod1)
        self.image_combo_manager_1.image_changed.connect(self.update_image1)

        self.ui.subj1.editingFinished.connect(self.update_image1)
        self.ui.subj1.setText("%s" % initial_subj)
        self.ui.subj1.setValidator(self.subjs_validator)
        self.ui.subj1.setCompleter(self.completer)

        # image 2
        self.image_combo_manager_2.setup(self.ui.mod2)
        self.image_combo_manager_2.image_changed.connect(self.update_image2)

        self.ui.subj2.editingFinished.connect(self.update_image2)
        self.ui.subj2.setValidator(self.subjs_validator)
        self.ui.subj2.setCompleter(self.completer)
        self.ui.subj2.setText("%s" % initial_subj)

        # join controls
        self.ui.divisions_box.valueChanged.connect(self.set_divs)
        self.ui.orientation_combo.activated.connect(self.set_orientation)
        self.ui.coords_combo.activated.connect(self.change_space)
        self.ui.slice_slider.valueChanged.connect(self.change_slice)
        self.vtk_widget.slice_changed.connect(self.ui.slice_slider.setValue)

    def start(self):
        self.vtk_widget.initialize_widget()
        # load test
        # self.vtk_viewer.viewer.load_test_view()

    def update_image1(self, class_and_name=None):
        if class_and_name is not None:
            img_class, img_name = class_and_name
        else:
            img_class, img_name = self.image_combo_manager_1.current_class_and_name
        subj = int(self.ui.subj1.text())
        self.vtk_viewer.set_img1(subj, img_class, img_name)
        self.ui.slice_slider.setMaximum(
            self.vtk_viewer.get_number_of_image_slices())

    def update_image2(self, class_and_name=None):
        if class_and_name is not None:
            img_class, img_name = class_and_name
        else:
            img_class, img_name = self.image_combo_manager_2.current_class_and_name
        subj = int(self.ui.subj2.text())
        self.vtk_viewer.set_img2(subj, img_class, img_name)
        self.ui.slice_slider.setMaximum(
            self.vtk_viewer.get_number_of_image_slices())

    def set_divs(self, divs):
        self.vtk_viewer.set_number_of_divisions(divs)

    def set_orientation(self):
        orientation_dict = {"Axial": 2, "Coronal": 1, "Sagital": 0}
        selection = str(self.ui.orientation_combo.currentText())
        orientation_val = orientation_dict[selection]
        self.vtk_viewer.set_orientation(orientation_val)

    def change_space(self):
        space = str(self.ui.coords_combo.currentText())
        self.vtk_viewer.change_space(space)

    def change_slice(self, img_slice):
        self.vtk_viewer.set_image_slice(img_slice)


def run():
    from braviz.utilities import configure_logger_from_conf
    configure_logger_from_conf("check_reg")
    app = QtGui.QApplication([])
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = CheckRegApp()
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    run()
