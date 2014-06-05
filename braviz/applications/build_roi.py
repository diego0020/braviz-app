from __future__ import division
import logging
from functools import partial as partial_f

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QMainWindow, QDialog
import vtk

import braviz
from braviz.interaction.qt_guis.roi_builder import Ui_RoiBuildApp
from braviz.interaction.qt_guis.roi_builder_start import Ui_OpenRoiBuilder
from braviz.interaction.qt_guis.new_roi import Ui_NewRoi
from braviz.interaction.qt_guis.load_roi import Ui_LoadRoiDialog
from braviz.interaction.qt_guis.roi_subject_change_confirm import Ui_RoiConfirmChangeSubject
from braviz.visualization.subject_viewer import QOrthogonalPlanesWidget
from braviz.readAndFilter.filter_fibers import FilterBundleWithSphere
from braviz.interaction.qt_models import SubjectChecklist, DataFrameModel
from braviz.readAndFilter import geom_db, tabular_data

__author__ = 'Diego'

AXIAL = 2
SAGITAL = 0
CORONAL = 1


class StartDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = Ui_OpenRoiBuilder()
        self.ui.setupUi(self)
        self.name = "?"
        self.ui.new_roi_button.clicked.connect(self.new_roi)
        self.ui.load_roi_button.clicked.connect(self.load_roi)

    def new_roi(self):
        new_roi_dialog = NewRoi()
        res = new_roi_dialog.exec_()
        if res == new_roi_dialog.Accepted:
            self.name = new_roi_dialog.name
            coords = new_roi_dialog.coords
            desc = new_roi_dialog.desc
            geom_db.create_roi(self.name, 0, coords, desc)
            self.accept()

    def load_roi(self):
        load_roi_dialog = LoadRoiDialog()
        res = load_roi_dialog.exec_()
        if res == load_roi_dialog.Accepted:
            self.name = load_roi_dialog.name
            assert self.name is not None
            self.accept()


class NewRoi(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = Ui_NewRoi()
        self.ui.setupUi(self)
        self.ui.error_msg.setText("")
        self.ui.dialogButtonBox.button(self.ui.dialogButtonBox.Save).setEnabled(0)
        self.ui.roi_name.textChanged.connect(self.check_name)
        self.name = None
        self.coords = None
        self.desc = None
        self.accepted.connect(self.before_accepting)

    def check_name(self):
        self.name = unicode(self.ui.roi_name.text())

        if len(self.name) > 2:
            if geom_db.roi_name_exists(self.name):
                self.ui.error_msg.setText("Name already exists")
            else:
                self.ui.dialogButtonBox.button(self.ui.dialogButtonBox.Save).setEnabled(1)
                self.ui.error_msg.setText("")
        else:
            self.ui.error_msg.setText("")

    def before_accepting(self):
        self.coords = self.ui.roi_space.currentIndex()
        self.desc = unicode(self.ui.roi_desc.toPlainText())


class LoadRoiDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = Ui_LoadRoiDialog()
        self.ui.setupUi(self)
        self.name = None
        spheres_df = geom_db.get_available_spheres_df()
        self.model = DataFrameModel(spheres_df, string_columns={0, 1})
        self.ui.tableView.setModel(self.model)
        self.ui.buttonBox.button(self.ui.buttonBox.Open).setEnabled(0)
        self.ui.tableView.clicked.connect(self.select)

    def select(self, index):
        name_index = self.model.index(index.row(), 0)
        self.name = unicode(self.model.data(name_index, QtCore.Qt.DisplayRole))
        self.ui.buttonBox.button(self.ui.buttonBox.Open).setEnabled(1)

class ConfirmSubjectChangeDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = Ui_RoiConfirmChangeSubject()
        self.ui.setupUi(self)
        self.save_requested = False
        self.ui.buttonBox.button(self.ui.buttonBox.Save).clicked.connect(self.set_save)
        self.ui.buttonBox.button(self.ui.buttonBox.Discard).clicked.connect(self.reject)

    def set_save(self):
        self.save_requested = True


class BuildRoiApp(QMainWindow):
    def __init__(self, roi_name=None):
        QMainWindow.__init__(self)
        self.ui = None
        self.__roi_name = roi_name
        self.__roi_id = geom_db.get_roi_id(roi_name)

        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.__subjects_list = tabular_data.get_subjects()
        self.__current_subject = self.__subjects_list[0]

        self.__current_image_mod = "MRI"
        try:
            self.__curent_space = geom_db.get_roi_space(roi_name)
        except Exception:
            self.__curent_space = "World"
        self.vtk_widget = QOrthogonalPlanesWidget(self.reader, parent=self)
        self.vtk_viewer = self.vtk_widget.orthogonal_viewer

        self.__fibers_map = None
        self.__fibers_ac = None
        self.__filetred_pd = None
        self.__full_pd = None
        self.__fibers_filterer = None

        self.__checked_subjects = geom_db.subjects_with_sphere(self.__roi_id)
        assert isinstance(self.__checked_subjects, set)
        self.__subjects_check_model = SubjectChecklist(self.__subjects_list)
        self.__subjects_check_model.checked = self.__checked_subjects

        self.__sphere_modified = True

        self.setup_ui()
        self.load_sphere(self.__current_subject)
        self.vtk_viewer.sphere.show()
        self.update_sphere_radius()
        self.update_sphere_center()

    def setup_ui(self):
        self.ui = Ui_RoiBuildApp()
        self.ui.setupUi(self)
        self.ui.sphere_name.setText(self.__roi_name)

        self.ui.vtk_frame_layout = QtGui.QVBoxLayout()
        self.ui.vtk_frame_layout.addWidget(self.vtk_widget)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.setContentsMargins(0, 0, 0, 0)
        self.ui.axial_check.stateChanged.connect(partial_f(self.show_image, AXIAL))
        self.ui.coronal_check.stateChanged.connect(partial_f(self.show_image, CORONAL))
        self.ui.sagital_check.stateChanged.connect(partial_f(self.show_image, SAGITAL))
        self.ui.axial_slice.valueChanged.connect(partial_f(self.set_slice, AXIAL))
        self.ui.coronal_slice.valueChanged.connect(partial_f(self.set_slice, CORONAL))
        self.ui.sagital_slice.valueChanged.connect(partial_f(self.set_slice, SAGITAL))
        self.vtk_widget.slice_changed.connect(self.update_slice_controls)

        self.ui.sphere_radius.valueChanged.connect(self.update_sphere_radius)
        self.ui.sphere_x.valueChanged.connect(self.update_sphere_center)
        self.ui.sphere_y.valueChanged.connect(self.update_sphere_center)
        self.ui.sphere_z.valueChanged.connect(self.update_sphere_center)
        self.ui.copy_from_cursor_button.clicked.connect(self.copy_coords_from_cursor)
        self.ui.sphere_rep.currentIndexChanged.connect(self.set_sphere_representation)
        self.ui.sphere_opac.valueChanged.connect(self.set_sphere_opac)

        self.ui.show_fibers_check.stateChanged.connect(self.show_fibers)

        self.ui.subjects_list.setModel(self.__subjects_check_model)
        self.ui.subjects_list.activated.connect(self.select_subject)
        self.ui.subject_sphere_label.setText("Subject %s" % self.__current_subject)
        self.ui.save_sphere.clicked.connect(self.save_sphere)

    def start(self):
        self.vtk_widget.initialize_widget()
        self.set_image("MRI")
        self.vtk_viewer.finish_initializing()

    def set_image(self, modality):
        self.vtk_viewer.change_image_modality(modality)
        dims = self.vtk_viewer.get_number_of_slices()
        self.ui.axial_slice.setMaximum(dims[AXIAL])
        self.ui.coronal_slice.setMaximum(dims[CORONAL])
        self.ui.sagital_slice.setMaximum(dims[SAGITAL])
        self.update_slice_controls()

    def update_slice_controls(self, new_slice=None):
        curr_slices = self.vtk_viewer.get_current_slice()
        self.ui.axial_slice.setValue(curr_slices[AXIAL])
        self.ui.coronal_slice.setValue(curr_slices[CORONAL])
        self.ui.sagital_slice.setValue(curr_slices[SAGITAL])

    def set_slice(self, axis, index):
        self.vtk_viewer.image_planes[axis].set_image_slice(index)
        self.vtk_viewer.ren_win.Render()

    def show_image(self, axis, state):
        if state == QtCore.Qt.Checked:
            self.vtk_viewer.image_planes[axis].show_image()
        elif state == QtCore.Qt.Unchecked:
            self.vtk_viewer.image_planes[axis].hide_image()
        self.vtk_viewer.ren_win.Render()

    def update_sphere_center(self, dummy=None):
        ctr = (self.ui.sphere_x.value(), self.ui.sphere_y.value(), self.ui.sphere_z.value())
        self.vtk_viewer.sphere.set_center(ctr)
        self.show_fibers()
        self.vtk_viewer.ren_win.Render()
        self.sphere_just_changed()

    def update_sphere_radius(self, r=None):
        if r is None:
            r = self.ui.sphere_radius.value()
        self.vtk_viewer.sphere.set_radius(r)
        self.show_fibers()
        self.vtk_viewer.ren_win.Render()
        self.sphere_just_changed()

    def set_sphere_representation(self, index):
        if index == 0:
            rep = "solid"
        else:
            rep = "wire"
        self.vtk_viewer.sphere.set_repr(rep)
        self.vtk_viewer.ren_win.Render()

    def set_sphere_opac(self, opac_val):
        self.vtk_viewer.sphere.set_opacity(opac_val)
        self.vtk_viewer.ren_win.Render()

    def copy_coords_from_cursor(self):
        coords = self.vtk_viewer.current_position()
        if coords is None:
            return
        cx, cy, cz = coords
        self.ui.sphere_x.setValue(cx)
        self.ui.sphere_y.setValue(cy)
        self.ui.sphere_z.setValue(cz)

    def show_fibers(self, event=None):
        if self.ui.show_fibers_check.checkState() != QtCore.Qt.Checked:
            if self.__fibers_ac is not None:
                self.__fibers_ac.SetVisibility(0)
                if event is not None:
                    self.vtk_viewer.ren_win.Render()
            return
        if self.__fibers_ac is None:
            self.__fibers_ac = vtk.vtkActor()
            self.__fibers_map = vtk.vtkPolyDataMapper()
            self.vtk_viewer.ren.AddActor(self.__fibers_ac)
            self.__fibers_ac.SetMapper(self.__fibers_map)
            self.__fibers_ac.SetVisibility(0)

        assert self.__fibers_map is not None
        if self.__fibers_filterer is None:
            self.__fibers_filterer = FilterBundleWithSphere()
        if self.__full_pd is None:
            self.__full_pd = self.reader.get("fibers", self.__current_subject, space=self.__curent_space)
            self.__fibers_filterer.set_bundle(self.__full_pd)

        ctr = (self.ui.sphere_x.value(), self.ui.sphere_y.value(), self.ui.sphere_z.value())
        r = self.ui.sphere_radius.value()
        self.__filetred_pd = self.__fibers_filterer.filter_bundle_with_sphere(ctr, r)
        self.__fibers_map.SetInputData(self.__filetred_pd)
        self.__fibers_ac.SetVisibility(1)
        if event is not None:
            self.vtk_viewer.ren_win.Render()

    def select_subject(self, index):
        subj = self.__subjects_check_model.data(index, QtCore.Qt.DisplayRole)
        if self.__sphere_modified:
            confirmation_dialog = ConfirmSubjectChangeDialog()
            res = confirmation_dialog.exec_()
            if res == confirmation_dialog.Rejected:
                return
            if confirmation_dialog.save_requested:
                self.save_sphere()
        self.change_subject(subj)

    def change_subject(self, new_subject):
        self.__current_subject = new_subject
        self.ui.subject_sphere_label.setText("Subject %s" % self.__current_subject)
        img_id = tabular_data.get_var_value(tabular_data.IMAGE_CODE,new_subject)
        self.vtk_viewer.change_subject(img_id)
        self.load_sphere(new_subject)
        self.__full_pd = None
        self.show_fibers()
        print new_subject

    def save_sphere(self):
        x = self.ui.sphere_x.value()
        y = self.ui.sphere_y.value()
        z = self.ui.sphere_z.value()
        r = self.ui.sphere_radius.value()
        geom_db.save_sphere(self.__roi_id, self.__current_subject, r, (x, y, z))
        self.refresh_checked()
        self.__sphere_modified = False
        self.ui.save_sphere.setEnabled(0)

    def sphere_just_changed(self):
        self.__sphere_modified = True
        self.ui.save_sphere.setEnabled(1)

    def load_sphere(self,subj):
        res = geom_db.load_sphere(self.__roi_id,subj)
        if res is None:
            return
        r,x,y,z = res
        self.ui.sphere_radius.setValue(r)
        self.ui.sphere_x.setValue(x)
        self.ui.sphere_y.setValue(y)
        self.ui.sphere_z.setValue(z)
        self.update_sphere_radius()
        self.update_sphere_center()
        self.__sphere_modified = False
        self.ui.save_sphere.setEnabled(0)

    def refresh_checked(self):
        checked = geom_db.subjects_with_sphere(self.__roi_id)
        self.__subjects_check_model.checked = checked


def run():
    import sys
    from braviz.utilities import configure_console_logger

    # configure_logger("build_roi")
    configure_console_logger("build_roi")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    start_dialog = StartDialog()
    res = start_dialog.exec_()
    if res != start_dialog.Accepted:
        return
    roi_name = start_dialog.name
    main_window = BuildRoiApp(roi_name)
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()