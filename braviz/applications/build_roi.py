from __future__ import division
import logging
from functools import partial as partial_f
import datetime
import platform
import os
import sys

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QMainWindow, QDialog
import vtk
import numpy as np
from scipy import ndimage

import braviz

from braviz.interaction.qt_guis.roi_builder import Ui_RoiBuildApp
from braviz.interaction.qt_guis.roi_builder_start import Ui_OpenRoiBuilder
from braviz.interaction.qt_guis.new_roi import Ui_NewRoi
from braviz.interaction.qt_guis.load_roi import Ui_LoadRoiDialog
from braviz.interaction.qt_guis.roi_subject_change_confirm import Ui_RoiConfirmChangeSubject
from braviz.interaction.qt_guis.extrapolate_spheres import Ui_ExtrapolateSpheres
from braviz.visualization.subject_viewer import QOrthogonalPlanesWidget
from braviz.readAndFilter.filter_fibers import FilterBundleWithSphere
from braviz.interaction.qt_models import SubjectChecklist, DataFrameModel, SubjectCheckTable
from braviz.readAndFilter import geom_db, tabular_data
from braviz.interaction.qt_dialogs import SaveScenarioDialog, LoadScenarioDialog
from braviz.interaction.structure_metrics import AggregateInRoi
from braviz.interaction.roi import export_roi
from braviz.readAndFilter.config_file import get_config
__author__ = 'Diego'

AXIAL = 2
SAGITAL = 0
CORONAL = 1

# "curv,avg_curv,area,thickness,sulc,aparc,aparc.a2009s,BA".split(",")
SURFACE_SCALARS_DICT = dict(enumerate((
    'curv',
    'avg_curv',
    'area',
    'thickness',
    'sulc',
    'aparc',
    'aparc.a2009s',
    'aparc.DKTatlas40',
    'BA')
))

COORDS = {
    0 : "world",
    1 : "talairach",
    2 : "dartel"
}


def get_unit_vectors():
    # from http://blog.marmakoide.org/?p=1
    n = 20
    golden_angle = np.pi * (3 - np.sqrt(5))
    theta = golden_angle * np.arange(n)
    z = np.linspace(1 - 1.0 / n, 1.0 / n - 1, n)
    radius = np.sqrt(1 - z * z)

    points = np.zeros((n, 3))
    points[:, 0] = radius * np.cos(theta)
    points[:, 1] = radius * np.sin(theta)
    points[:, 2] = z
    return points


UNIT_VECTORS = get_unit_vectors()


class ExtrapolateDialog(QDialog):
    def __init__(self, initial_source, subjects_list, sphere_id, reader):
        QDialog.__init__(self)
        self.__subjects = subjects_list
        self.__sphere_id = sphere_id
        self.__roi_space = geom_db.get_roi_space(roi_id=sphere_id)
        self.__origin = initial_source
        self.__reader = reader
        self.__pos_opt = PositionOptimizer(reader)
        self.spheres_df = None
        data_cols = self.create_data_cols()
        self.targets_model = SubjectCheckTable(subjects_list, data_cols, ("Subject", "Sphere R", "Sphere Center"))
        self.ui = Ui_ExtrapolateSpheres()
        self.ui.setupUi(self)
        self.ui.tableView.setModel(self.targets_model)
        self.ui.select_all_button.clicked.connect(self.select_all)
        self.ui.select_empty.clicked.connect(self.select_empty)
        self.ui.clear_button.clicked.connect(self.clear_sel)
        self.populate_origin()
        try:
            idx = self.spheres_df.index.get_loc(initial_source)
        except KeyError:
            idx = 0
        self.ui.origin_combo.setCurrentIndex(idx)
        self.ui.quit_button.clicked.connect(self.accept)
        self.ui.start_button.clicked.connect(self.start_button_handle)

        self.__started = False
        self.__cancel_flag = False
        self.__link_space = None
        self.__scale_radius = False

        self.__origin_img_id = None
        self.__origin_radius = None
        self.__origin_center = None
        self.__center_link = None
        self.__radius_link = None

    def create_data_cols(self):
        self.spheres_df = geom_db.get_all_spheres(self.__sphere_id)
        radiuses = [""] * len(self.__subjects)
        centers = [""] * len(self.__subjects)
        df2 = self.spheres_df.transpose()
        for i, s in enumerate(self.__subjects):
            row = df2.get(s)
            if row is not None:
                radiuses[i] = "%.4g" % row.radius
                centers[i] = "( %.3g , %.3g , %.3g )" % (row.ctr_x, row.ctr_y, row.ctr_z)
        return radiuses, centers

    def select_all(self):
        self.targets_model.checked = self.__subjects

    def clear_sel(self):
        self.targets_model.checked = tuple()

    def select_empty(self):
        self.targets_model.checked = set(self.__subjects) - set(self.spheres_df.index)

    def populate_origin(self):
        for s in self.spheres_df.index:
            self.ui.origin_combo.addItem(str(s))


    def translate_one_point(self, pt, subj):

        subj_img_id = subj
        # link -> world
        w_pt = self.__reader.transform_points_to_space(pt, self.__link_space,
                                                    subj_img_id, inverse=True)
        #world -> roi
        r_pt = self.__reader.transform_points_to_space(w_pt, self.__roi_space,
                                                    subj_img_id, inverse=False)
        return r_pt

    def extrapolate_one(self, target):
        log = logging.getLogger(__file__)
        log.debug("extrapolating %s", target)
        if target == self.__origin:
            return
        # coordinates
        if self.__link_space == "None":
            ctr = self.__origin_center
        else:
            try:
                ctr = self.translate_one_point(self.__center_link, target)
            except Exception:
                log.warning("Couldn't extrapolate subject %s", target)
                return

        max_opt = self.ui.optimize_radius.value()
        if max_opt>0:
            try:
                print "optimizing"
                subj_img_id = target
                self.__pos_opt.get_optimum(ctr,max_opt,subj_img_id,self.__roi_space,"FA")
            except Exception:
                log.warning("Couldn't optimize for subject %s", target)
                return

        #radius
        if self.__scale_radius is False or self.__link_space == "None":
            r = self.__origin_radius
        else:
            vecs_roi = np.array([self.translate_one_point(r, target) for r in self.__radius_link])
            r_roi = vecs_roi - ctr
            #print r_roi
            norms_r_roi = np.apply_along_axis(np.linalg.norm, 1, r_roi)
            #print norms_r_roi
            r = np.mean(norms_r_roi)

        geom_db.save_sphere(self.__sphere_id, target, r, ctr)


    def start_button_handle(self):
        if self.__started is True:
            self.__cancel_flag = True
            self.ui.start_button.setEnabled(0)
        else:
            self.__cancel_flag = False
            self.ui.start_button.setText("Cancel")
            self.extrapolate_selected()

    def extrapolate_selected(self):
        self.__started = True
        self.ui.progressBar.setValue(0)
        self.set_controls(0)
        selected = list(self.targets_model.checked)
        # set parameters
        self.__origin = int(self.ui.origin_combo.currentText())
        self.__link_space = str(self.ui.link_combo.currentText())
        self.__scale_radius = (self.ui.radio_combo.currentIndex() == 1)
        origin_sphere = geom_db.load_sphere(self.__sphere_id, self.__origin)
        self.__origin_radius = origin_sphere[0]
        self.__origin_center = origin_sphere[1:4]
        self.__origin_img_id = self.__origin

        if self.__link_space != "None":
            # roi -> world
            ctr_world = self.__reader.transform_points_to_space(self.__origin_center, self.__roi_space,
                                                             self.__origin_img_id, inverse=True)
            #world -> link
            ctr_link = self.__reader.transform_points_to_space(ctr_world, self.__link_space,
                                                            self.__origin_img_id, inverse=False)
            self.__center_link = ctr_link
            if self.__scale_radius is True:
                rad_vectors = (self.__origin_center + v * self.__origin_radius for v in UNIT_VECTORS)
                #roi -> world
                rad_vectors_world = (self.__reader.transform_points_to_space(r, self.__roi_space,
                                                                          self.__origin_img_id, inverse=True) for r in
                                     rad_vectors)
                #world -> link
                rad_vectors_link = (self.__reader.transform_points_to_space(r, self.__link_space,
                                                                         self.__origin_img_id, inverse=False) for r in
                                    rad_vectors_world)
                self.__radius_link = list(rad_vectors_link)

        for i, s in enumerate(selected):
            QtGui.QApplication.instance().processEvents()
            if self.__cancel_flag is True:
                break
            self.extrapolate_one(s)
            self.ui.progressBar.setValue((i + 1) * 100 / len(selected))
        r, c = self.create_data_cols()
        self.targets_model.set_data_cols((r, c))
        self.__started = False
        self.ui.start_button.setText("Start Extrapolation")
        self.set_controls(1)
        QtCore.QTimer.singleShot(1000, partial_f(self.ui.start_button.setEnabled, 1))


    def set_controls(self, value):
        self.ui.select_all_button.setEnabled(value)
        self.ui.select_empty.setEnabled(value)
        self.ui.clear_button.setEnabled(value)
        self.ui.tableView.setEnabled(value)
        self.ui.origin_combo.setEnabled(value)
        self.ui.link_combo.setEnabled(value)
        self.ui.quit_button.setEnabled(value)
        self.ui.radio_combo.setEnabled(value)


class StartDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = Ui_OpenRoiBuilder()
        self.ui.setupUi(self)
        self.name = "?"
        self.scenario_data = None
        self.ui.new_roi_button.clicked.connect(self.new_roi)
        self.ui.load_roi_button.clicked.connect(self.load_roi)
        self.ui.load_scenario.clicked.connect(self.load_scenario)

    def new_roi(self):
        new_roi_dialog = NewRoi()
        res = new_roi_dialog.exec_()
        if res == new_roi_dialog.Accepted:
            self.name = new_roi_dialog.name
            coords_key = new_roi_dialog.coords
            coords = COORDS[coords_key]
            desc = new_roi_dialog.desc
            geom_db.create_roi(self.name, "sphere", coords, desc)
            self.accept()

    def load_roi(self):
        load_roi_dialog = LoadRoiDialog()
        res = load_roi_dialog.exec_()
        if res == load_roi_dialog.Accepted:
            self.name = load_roi_dialog.name
            assert self.name is not None
            self.accept()

    def load_scenario(self):
        my_name = os.path.splitext(os.path.basename(__file__))[0]
        dialog = LoadScenarioDialog(my_name)
        res = dialog.exec_()
        if res == dialog.Accepted:
            self.scenario_data = dialog.out_dict
            self.accept()
        else:
            self.scenario_data = None


class NewRoi(QDialog):
    def __init__(self, block_space=None):
        QDialog.__init__(self)
        self.ui = Ui_NewRoi()
        self.ui.setupUi(self)
        self.ui.error_msg.setText("")
        self.ui.dialogButtonBox.button(self.ui.dialogButtonBox.Save).setEnabled(0)
        self.ui.roi_name.textChanged.connect(self.check_name)
        if block_space is not None:
            index = self.ui.roi_space.findText(block_space)
            self.ui.roi_space.setCurrentIndex(index)
            self.ui.roi_space.setEnabled(0)
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
        self.ui.buttonBox.button(self.ui.buttonBox.Discard).clicked.connect(self.accept)

    def set_save(self):
        self.save_requested = True


class BuildRoiApp(QMainWindow):
    def __init__(self, roi_name=None):
        QMainWindow.__init__(self)
        config = get_config(__file__)
        self.ui = None
        self.__roi_name = roi_name
        if roi_name is not None:
            self.__roi_id = geom_db.get_roi_id(roi_name)
        else:
            self.__roi_id = None
            self.__roi_name = ""

        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.__subjects_list = tabular_data.get_subjects()
        self.__current_subject = config.get_default_subject()
        self.__current_img_id = self.__current_subject

        self.__current_image_mod = "MRI"
        self.__current_contrast = None
        try:
            self.__curent_space = geom_db.get_roi_space(name=roi_name)
        except Exception:
            raise

        self.vtk_widget = QOrthogonalPlanesWidget(self.reader, parent=self)
        self.vtk_viewer = self.vtk_widget.orthogonal_viewer

        self.__fibers_map = None
        self.__fibers_ac = None
        self.__filetred_pd = None
        self.__full_pd = None
        self.__fibers_filterer = None

        if self.__roi_id is not None:
            self.__checked_subjects = geom_db.subjects_with_sphere(self.__roi_id)
        else:
            self.__checked_subjects = set()
        assert isinstance(self.__checked_subjects, set)
        self.__subjects_check_model = SubjectChecklist(self.__subjects_list)
        self.__subjects_check_model.checked = self.__checked_subjects

        self.__sphere_modified = True

        self.setup_ui()
        self.__sphere_color = (255, 255, 255)
        self.__sphere_center = None
        self.__sphere_radius = None
        self.__aux_lut = None
        self.__mean_in_img_calculator = AggregateInRoi(self.reader)

        #for optimization
        self.__pos_optimizer = PositionOptimizer(self.reader)

        self.__mean_fa_in_roi_calculator = AggregateInRoi(self.reader)
        self.__mean_md_in_roi_calculator = AggregateInRoi(self.reader)
        self.ui.sphere_space.setText(self.__curent_space)
        self.vtk_viewer.sphere.show()
        self.update_sphere_radius()
        self.update_sphere_center()
        if self.__roi_id is not None:
            self.load_sphere(self.__current_subject)

        if self.__curent_space.lower() == "dartel":
            self.ui.optimize_button.setEnabled(0)
            self.ui.optimize_button.setToolTip("Not possible in dartel space")
            self.ui.inside_check.setEnabled(0)
            self.ui.inside_check.setToolTip("Not possible in dartel space")


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
        self.ui.image_combo.currentIndexChanged.connect(self.select_image_modality)
        paradigms = self.reader.get("fMRI", None, index=True)
        for p in paradigms:
            self.ui.image_combo.addItem(p.title())
        self.ui.contrast_combo.setEnabled(0)
        self.ui.contrast_combo.setCurrentIndex(0)
        self.ui.contrast_combo.setEnabled(False)
        self.ui.contrast_combo.activated.connect(self.change_contrast)
        self.ui.sphere_radius.valueChanged.connect(self.update_sphere_radius)
        self.ui.sphere_x.valueChanged.connect(self.update_sphere_center)
        self.ui.sphere_y.valueChanged.connect(self.update_sphere_center)
        self.ui.sphere_z.valueChanged.connect(self.update_sphere_center)
        self.ui.copy_from_cursor_button.clicked.connect(self.copy_coords_from_cursor)
        self.ui.optimize_button.clicked.connect(self.optimize_sphere_from_button)
        self.ui.sphere_rep.currentIndexChanged.connect(self.set_sphere_representation)
        self.ui.sphere_opac.valueChanged.connect(self.set_sphere_opac)

        self.ui.show_fibers_check.stateChanged.connect(self.show_fibers)

        self.ui.subjects_list.setModel(self.__subjects_check_model)
        self.ui.subjects_list.activated.connect(self.select_subject)
        self.ui.subject_sphere_label.setText("Subject %s" % self.__current_subject)
        self.ui.save_sphere.clicked.connect(self.save_sphere)

        self.ui.surface_combo.currentIndexChanged.connect(self.select_surface)
        self.ui.scalar_combo.currentIndexChanged.connect(self.select_surface_scalars)
        self.ui.left_cortex_check.stateChanged.connect(self.toggle_left_surface)
        self.ui.right_cortex_check.stateChanged.connect(self.toggle_right_surface)
        self.ui.cortex_opac.valueChanged.connect(self.set_cortex_opacity)

        self.ui.extrapolate_button.clicked.connect(self.launch_extrapolate_dialog)

        self.ui.actionSave_Scenario.triggered.connect(self.save_scenario)
        self.ui.actionLoad_Scenario.triggered.connect(self.load_scenario)
        self.ui.actionSave_sphere_as.triggered.connect(self.save_sphere_as)
        self.ui.actionExport_ROI.triggered.connect(self.export_sphere)
        self.ui.color_button.clicked.connect(self.set_sphere_color)

        self.ui.inside_check.clicked.connect(self.caclulate_image_in_roi_pre)

        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Right:
            subj = self.__current_subject
            idx = self.__subjects_list.index(subj)
            next_idx = (idx + 1) % len(self.__subjects_list)
            next_one = self.__subjects_list[next_idx]
            self.select_subject(subj=next_one)
        elif event.key() == QtCore.Qt.Key_Left:
            subj = self.__current_subject
            idx = self.__subjects_list.index(subj)
            prev = self.__subjects_list[idx - 1]
            self.select_subject(subj=prev)
        elif event.key() == QtCore.Qt.Key_C:
            self.copy_coords_from_cursor()
        elif event.key() == QtCore.Qt.Key_O:
            self.optimize_sphere_from_button()
        else:
            super(BuildRoiApp, self).keyPressEvent(event)

    def start(self):
        self.vtk_widget.initialize_widget()
        self.set_image("MRI")
        try:
            self.vtk_viewer.show_image()
        except Exception as e:
            log = logging.getLogger(__file__)
            log.warning(e)
        self.vtk_viewer.change_space(self.__curent_space)
        self.vtk_viewer.finish_initializing()
        if self.__roi_id is not None:
            self.change_subject(self.__current_subject)
        self.select_surface(None)

    def set_image(self, modality, contrast=None):
        self.__current_image_mod = modality
        self.__current_contrast = contrast
        log = logging.getLogger(__name__)
        try:
            self.vtk_viewer.change_image_modality(modality, contrast)
        except Exception as e:
            self.statusBar().showMessage(e.message, 500)
            log.warning(e.message)
        self.update_slice_maximums()

    def update_slice_maximums(self):
        dims = self.vtk_viewer.get_number_of_slices()
        self.ui.axial_slice.setMaximum(dims[AXIAL])
        self.ui.coronal_slice.setMaximum(dims[CORONAL])
        self.ui.sagital_slice.setMaximum(dims[SAGITAL])
        self.update_slice_controls()
        self.caclulate_image_in_roi_pre()

    def caclulate_image_in_roi_pre(self):
        if not self.ui.inside_check.isChecked():
            self.ui.mean_inside_text.clear()
            self.ui.mean_inside_text.setEnabled(0)
            self.ui.mean_fa.clear()
            self.ui.mean_fa.setEnabled(0)
            self.ui.mean_md.clear()
            self.ui.mean_md.setEnabled(0)
            return

        modality = self.__current_image_mod
        contrast = self.__current_contrast
        if self.__sphere_center is None or self.__sphere_radius is None:
            self.ui.mean_inside_text.clear()
            return
        self.ui.mean_inside_text.setEnabled(1)
        self.ui.mean_fa.setEnabled(1)
        self.ui.mean_md.setEnabled(1)
        if contrast is not None:
            self.ui.mean_inside_label.setText("Mean Z-score")
            self.ui.mean_inside_label.setToolTip("Mean Z-score inside the ROI")
            self.__mean_in_img_calculator.load_image(self.__current_img_id, self.__curent_space, "FMRI", modality,
                                                     contrast,
                                                     mean=True)
        else:
            if modality in {"DTI" , "FA"}:
                self.ui.mean_inside_label.setText("Mean FA")
                self.ui.mean_inside_label.setToolTip("Mean FA inside the ROI")
                self.__mean_in_img_calculator.load_image(self.__current_img_id, self.__curent_space, "FA", mean=True)
            elif modality in {"APARC", "WMPARC"}:
                self.ui.mean_inside_label.setText("Label Mode")
                self.ui.mean_inside_label.setToolTip("Mode of labels inside the ROI")
                self.__mean_in_img_calculator.load_image(self.__current_img_id, self.__curent_space, modality,
                                                         mean=False)
                self.__aux_lut = self.reader.get(self.__current_image_mod, None, lut=True)
            else:
                assert modality == "MRI"
                self.ui.mean_inside_label.setText("Mean value")
                self.ui.mean_inside_label.setToolTip("Mean value of image inside the ROI")
                self.__mean_in_img_calculator.load_image(self.__current_img_id, self.__curent_space, modality,
                                                         mean=True)
        self.__mean_fa_in_roi_calculator.load_image(self.__current_img_id, self.__curent_space, "FA", mean=True)
        self.__mean_md_in_roi_calculator.load_image(self.__current_img_id, self.__curent_space, "MD", mean=True)
        self.caclulate_image_in_roi()

    def caclulate_image_in_roi(self):
        if not self.ui.inside_check.isChecked():
            return
        # calculate Mean
        try:
            value = self.__mean_in_img_calculator.get_value(self.__sphere_center, self.__sphere_radius)
        except Exception:
            value = np.nan
        if self.__current_image_mod in {"APARC", "WMPARC"}:
            int_val = int(value[0])
            idx = self.__aux_lut.GetAnnotatedValueIndex(int_val)
            label = self.__aux_lut.GetAnnotation(idx)
            self.ui.mean_inside_text.setText(label)
        else:
            self.ui.mean_inside_text.setText("%.4g" % value)
        #calculate FA
        try:
            value = self.__mean_fa_in_roi_calculator.get_value(self.__sphere_center, self.__sphere_radius)
        except Exception:
            value = np.nan
        self.ui.mean_fa.setText("%.4g" % value)
        #calculate MD
        try:
            value = self.__mean_md_in_roi_calculator.get_value(self.__sphere_center, self.__sphere_radius)
        except Exception:
            value = np.nan
        self.ui.mean_md.setText("%.4g" % value)

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
            try:
                self.vtk_viewer.image_planes[axis].show_image()
            except Exception as e:
                log = logging.getLogger(__file__)
                log.warning(e)
        elif state == QtCore.Qt.Unchecked:
            self.vtk_viewer.image_planes[axis].hide_image()
        self.vtk_viewer.ren_win.Render()

    def update_sphere_center(self, dummy=None):
        ctr = (self.ui.sphere_x.value(), self.ui.sphere_y.value(), self.ui.sphere_z.value())
        self.__sphere_center = ctr
        self.vtk_viewer.sphere.set_center(ctr)
        self.show_fibers()
        self.caclulate_image_in_roi()
        self.vtk_viewer.ren_win.Render()
        self.sphere_just_changed()

    def update_sphere_radius(self, r=None):
        if r is None:
            r = self.ui.sphere_radius.value()
        self.__sphere_radius = r
        self.vtk_viewer.sphere.set_radius(r)
        self.show_fibers()
        self.caclulate_image_in_roi()
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

        if self.__full_pd == "Unavailable":
            # dont try to load again
            return

        assert self.__fibers_map is not None
        if self.__fibers_filterer is None:
            self.__fibers_filterer = FilterBundleWithSphere()
        if self.__full_pd is None:
            try:
                self.__full_pd = self.reader.get("fibers", self.__current_img_id, space=self.__curent_space)
            except Exception:
                self.__full_pd = "Unavailable"
                self.__fibers_ac.SetVisibility(0)
                self.vtk_viewer.ren_win.Render()
                return
            self.__fibers_filterer.set_bundle(self.__full_pd)

        ctr = (self.ui.sphere_x.value(), self.ui.sphere_y.value(), self.ui.sphere_z.value())
        r = self.ui.sphere_radius.value()
        self.__filetred_pd = self.__fibers_filterer.filter_bundle_with_sphere(ctr, r)
        self.__fibers_map.SetInputData(self.__filetred_pd)
        self.__fibers_ac.SetVisibility(1)
        if event is not None:
            self.vtk_viewer.ren_win.Render()

    def action_confirmed(self):
        if self.__sphere_modified:
            confirmation_dialog = ConfirmSubjectChangeDialog()
            res = confirmation_dialog.exec_()
            if res == confirmation_dialog.Rejected:
                return False
            if confirmation_dialog.save_requested:
                self.save_sphere()
        return True

    def select_subject(self, index=None, subj=None):
        if subj is None:
            subj = self.__subjects_check_model.data(index, QtCore.Qt.DisplayRole)
        if self.action_confirmed():
            self.change_subject(subj)

    def change_subject(self, new_subject):
        self.__current_subject = new_subject
        self.ui.subject_sphere_label.setText("Subject %s" % self.__current_subject)
        img_id = new_subject
        self.__current_img_id = img_id
        self.reload_contrast_names()
        log = logging.getLogger(__file__)
        try:
            self.vtk_viewer.change_subject(img_id)
        except Exception:
            log.warning("Couldnt load data for subject %s", new_subject)
        else:
            self.update_slice_maximums()
        self.load_sphere(new_subject)
        self.__full_pd = None
        self.show_fibers()
        self.caclulate_image_in_roi_pre()
        self.__sphere_modified = False
        self.vtk_viewer.ren_win.Render()
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

    def load_sphere(self, subj):
        res = geom_db.load_sphere(self.__roi_id, subj)
        if res is None:
            return
        r, x, y, z = res
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

    def select_image_modality(self, dummy_index):
        mod = str(self.ui.image_combo.currentText())
        if self.ui.image_combo.currentIndex() > 4:
            # functional
            self.ui.contrast_combo.setEnabled(1)
            self.reload_contrast_names(mod)
            contrast = int(self.ui.contrast_combo.currentIndex()) + 1
        else:
            self.ui.contrast_combo.setEnabled(0)
            contrast = None
        self.set_image(mod, contrast)

    def reload_contrast_names(self, mod=None):
        if mod is None:
            mod = str(self.ui.image_combo.currentText())
        if mod.upper() not in self.reader.get("FMRI", None, index=True):
            return
        previus_index = self.ui.contrast_combo.currentIndex()
        try:
            contrasts_dict = self.reader.get("FMRI", self.__current_img_id, name=mod, contrasts_dict=True)
        except Exception:
            pass
        else:
            self.ui.contrast_combo.clear()
            for i in xrange(len(contrasts_dict)):
                self.ui.contrast_combo.addItem(contrasts_dict[i + 1])
            if 0 <= previus_index < len(contrasts_dict):
                self.ui.contrast_combo.setCurrentIndex(previus_index)
            else:
                self.ui.contrast_combo.setCurrentIndex(0)
                self.change_contrast()


    def change_contrast(self, dummy_index=None):
        new_contrast = self.ui.contrast_combo.currentIndex() + 1
        mod = str(self.ui.image_combo.currentText())
        self.set_image(mod, new_contrast)

    def select_surface_scalars(self, index):
        scalar_name = SURFACE_SCALARS_DICT[int(index)]
        self.vtk_viewer.cortex.set_scalars(scalar_name)

    def select_surface(self, index):
        surface_name = str(self.ui.surface_combo.currentText())
        self.vtk_viewer.cortex.set_surface(surface_name)

    def toggle_left_surface(self, status):
        b_status = (status == QtCore.Qt.Checked)
        self.vtk_viewer.cortex.set_hemispheres(left=b_status)

    def toggle_right_surface(self, status):
        b_status = (status == QtCore.Qt.Checked)
        self.vtk_viewer.cortex.set_hemispheres(right=b_status)

    def set_cortex_opacity(self, int_opac):
        self.vtk_viewer.cortex.set_opacity(int_opac)

    def launch_extrapolate_dialog(self):
        if self.__sphere_modified:
            check_save = ConfirmSubjectChangeDialog()
            res = check_save.exec_()
            if res == check_save.Rejected:
                return
            if check_save.save_requested:
                self.save_sphere()
        extrapol_dialog = ExtrapolateDialog(self.__current_subject, self.__subjects_list, self.__roi_id, self.reader)
        res = extrapol_dialog.exec_()
        self.refresh_checked()

    def get_state(self):
        state = dict()
        state["roi_id"] = self.__roi_id
        # context
        context_dict = {}
        context_dict["image_type"] = self.ui.image_combo.currentText()
        context_dict["axial_on"] = self.ui.axial_check.checkState() == QtCore.Qt.Checked
        context_dict["coronal_on"] = self.ui.coronal_check.checkState() == QtCore.Qt.Checked
        context_dict["sagital_on"] = self.ui.sagital_check.checkState() == QtCore.Qt.Checked

        context_dict["axial_slice"] = int(self.ui.axial_slice.value())
        context_dict["coronal_slice"] = int(self.ui.coronal_slice.value())
        context_dict["sagital_slice"] = int(self.ui.sagital_slice.value())

        context_dict["cortex"] = str(self.ui.surface_combo.currentText())
        context_dict["surf_scalars"] = str(self.ui.scalar_combo.currentText())
        context_dict["left_surface"] = self.ui.left_cortex_check.checkState() == QtCore.Qt.Checked
        context_dict["right_surface"] = self.ui.right_cortex_check.checkState() == QtCore.Qt.Checked
        context_dict["cortex_opac"] = int(self.ui.cortex_opac.value())
        state["context"] = context_dict
        #visual
        visual_dict = {}
        visual_dict["coords"] = self.__curent_space
        #camera
        visual_dict["camera"] = self.vtk_viewer.get_camera_parameters()
        visual_dict["spher_rep"] = self.ui.sphere_rep.currentIndex()
        visual_dict["sphere_opac"] = self.ui.sphere_opac.value()
        visual_dict["sphere_color"] = self.__sphere_color
        visual_dict["show_fibers"] = self.ui.show_fibers_check.checkState() == QtCore.Qt.Checked
        state["visual"] = visual_dict

        #subject
        subjs_state = {}
        subjs_state["subject"] = self.__current_subject
        subjs_state["img_code"] = self.__current_img_id
        subjs_state["sample"] = self.__subjects_list
        state["subjects"] = subjs_state

        #meta
        meta = {"date": datetime.datetime.now(), "exec": sys.argv, "machine": platform.node(),
                "application": os.path.splitext(os.path.basename(__file__))[0]}
        state["meta"] = meta
        return state

    def load_state(self, state):
        self.__roi_id = state["roi_id"]
        self.__roi_name = geom_db.get_roi_name(self.__roi_id)
        self.ui.sphere_name.setText(self.__roi_name)
        subjs_state = state["subjects"]
        subjs_state["subject"] = self.__current_subject
        self.vtk_viewer.change_subject(self.__current_subject)
        self.__subjects_list = subjs_state["sample"]
        self.__current_subject = subjs_state["subject"]
        self.__current_img_id = subjs_state["img_code"]
        try:
            self.__curent_space = geom_db.get_roi_space(self.__roi_name)
        except Exception:
            self.__curent_space = "world"
        self.vtk_viewer.change_space(self.__curent_space)
        self.__checked_subjects = geom_db.subjects_with_sphere(self.__roi_id)
        self.__subjects_check_model.checked = self.__checked_subjects
        self.__sphere_modified = False

        # context
        context_dict = state["context"]
        img = context_dict["image_type"]
        idx = self.ui.image_combo.findText(img)
        assert idx >= 0
        self.ui.image_combo.setCurrentIndex(idx)
        assert self.__current_image_mod == img
        self.ui.axial_check.setChecked(context_dict["axial_on"])
        self.ui.coronal_check.setChecked(context_dict["coronal_on"])
        self.ui.sagital_check.setChecked(context_dict["sagital_on"])

        self.ui.axial_slice.setValue(context_dict["axial_slice"])
        self.ui.coronal_slice.setValue(context_dict["coronal_slice"])
        self.ui.sagital_slice.setValue(context_dict["sagital_slice"])

        ctx = context_dict["cortex"]
        idx = self.ui.surface_combo.findText(ctx)
        assert idx >= 0
        self.ui.surface_combo.setCurrentIndex(idx)

        csc = context_dict["surf_scalars"]
        idx = self.ui.scalar_combo.findText(csc)
        assert idx >= 0
        self.ui.scalar_combo.setCurrentIndex(idx)

        self.ui.left_cortex_check.setChecked(context_dict["left_surface"])
        self.ui.right_cortex_check.setChecked(context_dict["right_surface"])
        self.ui.cortex_opac.setValue(context_dict["cortex_opac"])

        #visual
        visual_dict = state["visual"]
        self.__sphere_color = visual_dict["sphere_color"]
        self.vtk_viewer.sphere.set_color(*self.__sphere_color)
        fp, pos, vu = visual_dict["camera"]
        self.vtk_viewer.set_camera(fp, pos, vu)
        self.ui.sphere_rep.setCurrentIndex(visual_dict["spher_rep"])
        self.ui.sphere_opac.setValue(visual_dict["sphere_opac"])
        self.ui.show_fibers_check.setChecked(visual_dict.get("show_fibers", False))

        self.change_subject(self.__current_subject)
        self.__sphere_modified = False
        self.update_slice_maximums()

    def save_scenario(self):
        state = self.get_state()
        app_name = state["meta"]["application"]
        dialog = SaveScenarioDialog(app_name, state)
        res = dialog.exec_()
        if res == dialog.Accepted:
            scn_id = dialog.params["scn_id"]
            self.save_screenshot(scn_id)


    def save_screenshot(self, scenario_index):
        file_name = "scenario_%d.png" % scenario_index
        file_path = os.path.join(self.reader.get_dyn_data_root(), "braviz_data", "scenarios", file_name)
        log = logging.getLogger(__name__)
        log.info(file_path)
        save_ren_win_picture(self.vtk_viewer.ren_win, file_path)

    def load_scenario(self):
        if self.action_confirmed():
            my_name = os.path.splitext(os.path.basename(__file__))[0]
            dialog = LoadScenarioDialog(my_name)
            res = dialog.exec_()
            if res == dialog.Accepted:
                wanted_state = dialog.out_dict
                self.load_state(wanted_state)


    def save_sphere_as(self):
        dialog = NewRoi(self.__curent_space)
        res = dialog.exec_()
        if res == dialog.Accepted:
            new_name = dialog.name
            desc = dialog.desc
            space = COORDS[self.__curent_space]
            new_id = geom_db.create_roi(new_name, "sphere", space, desc)
            geom_db.copy_spheres(self.__roi_id, new_id)
            self.__roi_id = new_id
            self.__roi_name = new_name
            self.ui.sphere_name.setText(new_name)
            self.refresh_checked()


    def set_sphere_color(self):
        color = QtGui.QColorDialog.getColor()
        self.ui.color_button.setStyleSheet("#color_button{color : %s}" % color.name())
        self.vtk_viewer.sphere.set_color(color.red(), color.green(), color.blue())
        self.__sphere_color = (color.red(), color.green(), color.blue())
        self.vtk_viewer.ren_win.Render()


    def export_sphere(self):
        file_name = unicode(QtGui.QFileDialog.getSaveFileName(self, "Save Shere Image", self.reader.get_dyn_data_root(),
                                                      "Nifti (*.nii.gz)"))
        if len(file_name)<=5:
            return

        self.statusBar().showMessage("saving to %s" % file_name,5000)
        export_roi(self.__current_subject,self.__roi_id,"world",file_name,self.reader)
        self.statusBar().showMessage("DONE: saved to %s" % file_name,5000)

    def optimize_sphere_from_button(self):
        max_opt = min(10,self.__sphere_radius)
        opt_ctr = self.__pos_optimizer.get_optimum(self.__sphere_center,max_opt,self.__current_img_id,
                                                   self.__curent_space,"FA")
        cx, cy, cz = opt_ctr
        self.ui.sphere_x.setValue(cx)
        self.ui.sphere_y.setValue(cy)
        self.ui.sphere_z.setValue(cz)
        self.update_sphere_center()

    def get_optimum_position(self,ctr,max_opt):
        print "optimizing"
        if self.__fa_smoothed is None :
            fa_image = self.reader.get("FA",self.__current_img_id,space=self.__curent_space)
            self.__fa_affine = fa_image.get_affine()
            print self.__fa_affine
            self.__fa_i_affine = np.linalg.inv(self.__fa_affine)
            self.__fa_smoothed = ndimage.gaussian_filter(fa_image.get_data(),3)

        print ctr
        ctr_h = np.ones(4)
        ctr_h[:3]=ctr
        ctr_coords = np.round(self.__fa_i_affine.dot(ctr_h))
        ctr_coords = ctr_coords[:3]/ctr_coords[3]
        x0,y0,z0 = ctr_coords-max_opt
        xn,yn,zn = ctr_coords+max_opt+1
        mini_fa = self.__fa_smoothed[x0:xn,y0:yn,z0:zn]
        mini_i = np.unravel_index(mini_fa.argmax(),mini_fa.shape)
        max_i = np.ones(4)
        max_i[:3] = mini_i + ctr_coords - max_opt
        opt_ctr = self.__fa_affine.dot(max_i)
        opt_ctr = opt_ctr[:3]/opt_ctr[3]
        return opt_ctr

class PositionOptimizer(object):
    def __init__(self,reader):
        self.reader = reader
        self.__fa_affine = None
        self.__fa_i_affine = None
        self.__fa_smoothed = None
        self.__last_subj = None
        self.__last_space = None
        pass
    def get_optimum(self,ctr,max_opt,img_id,space,img_type="FA"):
        print "optimizing"
        if self.__last_subj != img_id or self.__last_space != space:
            fa_image = self.reader.get(img_type,img_id,space=space)
            self.__fa_affine = fa_image.get_affine()
            print self.__fa_affine
            self.__fa_i_affine = np.linalg.inv(self.__fa_affine)
            self.__fa_smoothed = ndimage.gaussian_filter(fa_image.get_data(),3)
            self.__last_subj = img_id
            self.__last_space = space

        print ctr
        ctr_h = np.ones(4)
        ctr_h[:3]=ctr
        ctr_coords = np.round(self.__fa_i_affine.dot(ctr_h))
        ctr_coords = ctr_coords[:3]/ctr_coords[3]
        x0,y0,z0 = ctr_coords-max_opt
        xn,yn,zn = ctr_coords+max_opt+1
        mini_fa = self.__fa_smoothed[x0:xn,y0:yn,z0:zn]
        mini_i = np.unravel_index(mini_fa.argmax(),mini_fa.shape)
        max_i = np.ones(4)
        max_i[:3] = mini_i + ctr_coords - max_opt
        opt_ctr = self.__fa_affine.dot(max_i)
        opt_ctr = opt_ctr[:3]/opt_ctr[3]
        return opt_ctr


def run():
    import sys
    from braviz.utilities import configure_logger_from_conf

    # configure_logger("build_roi")
    configure_logger_from_conf("build_roi")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    logging.basicConfig(level=logging.DEBUG)
    start_dialog = StartDialog()
    res = start_dialog.exec_()
    if res != start_dialog.Accepted:
        return
    if start_dialog.scenario_data is not None:
        main_window = BuildRoiApp(None)
        main_window.show()
        main_window.start()
        main_window.load_state(start_dialog.scenario_data)
    else:
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