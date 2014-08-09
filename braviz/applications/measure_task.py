from __future__ import division
import logging
from functools import partial as partial_f

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QMainWindow, QDialog
import vtk
import numpy as np

import braviz
from braviz.interaction.qt_guis.ortho_measure import Ui_OrtoMeasure
from braviz.interaction.qt_guis.ortho_measure_start import Ui_OpenMeasureApp
from braviz.interaction.qt_guis.new_orthogonal_measure import Ui_NewRoi
from braviz.interaction.qt_guis.load_roi import Ui_LoadRoiDialog
from braviz.interaction.qt_guis.roi_subject_change_confirm import Ui_RoiConfirmChangeSubject

from braviz.visualization.subject_viewer import QMeasurerWidget
from braviz.interaction.qt_models import SubjectChecklist, DataFrameModel, SubjectCheckTable
from braviz.readAndFilter import geom_db, tabular_data
from braviz.interaction.qt_dialogs import SaveScenarioDialog, LoadScenarioDialog
import datetime
import platform
import os
import sys

__author__ = 'Diego'

AXIAL = 2
SAGITAL = 0
CORONAL = 1

class StartDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = Ui_OpenMeasureApp()
        self.ui.setupUi(self)
        self.name = "?"
        self.scenario_data = None
        self.ui.new_roi_button.clicked.connect(self.new_roi)
        self.ui.load_roi_button.clicked.connect(self.load_roi)
        self.ui.load_scenario.clicked.connect(self.load_scenario)

    def new_roi(self):
        new_roi_dialog = NewMeasure()
        res = new_roi_dialog.exec_()
        if res == new_roi_dialog.Accepted:
            self.name = new_roi_dialog.name
            coords = new_roi_dialog.coords
            desc = new_roi_dialog.desc
            code = 10+new_roi_dialog.plane
            geom_db.create_roi(self.name, code, coords, desc)
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

class NewMeasure(QDialog):
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
        self.plane = None
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
        self.plane = globals()[str(self.ui.plane_combo.currentText()).upper()]


class LoadRoiDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = Ui_LoadRoiDialog()
        self.ui.setupUi(self)
        self.name = None
        spheres_df = geom_db.get_available_lines_df()
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
        self.ui.label.setText("Save changes to current measure?")
        self.setWindowTitle("Measure modified")
        self.ui.buttonBox.button(self.ui.buttonBox.Save).clicked.connect(self.set_save)
        self.ui.buttonBox.button(self.ui.buttonBox.Discard).clicked.connect(self.accept)

    def set_save(self):
        self.save_requested = True


class MeasureApp(QMainWindow):
    def __init__(self, roi_name=None):
        log = logging.getLogger(__name__)
        QMainWindow.__init__(self)
        self.ui = None
        self.__roi_name = roi_name
        if roi_name is not None:
            self.__roi_id = geom_db.get_roi_id(roi_name)
        else:
            self.__roi_id = None
            self.__roi_name = ""

        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.__subjects_list = tabular_data.get_subjects()
        self.__current_subject = self.__subjects_list[0]
        self.__current_img_id = tabular_data.get_var_value(tabular_data.IMAGE_CODE,self.__current_subject)

        self.__current_image_mod = "MRI"
        self.__current_contrast = None
        try:
            self.__curent_space = geom_db.get_roi_space(roi_name)
        except Exception:
            self.__curent_space = "Talairach"
        assert self.__curent_space == "Talairach"
        self.meaure_axis = 0
        try:
            self.meaure_axis = (geom_db.get_roi_type(roi_name)) % 10
        except Exception:
            log.error("Invalid roi type, unknown measure axis, assuming SAGITAL")
        self.vtk_widget = QMeasurerWidget(self.reader, parent=self)
        self.vtk_viewer = self.vtk_widget.orthogonal_viewer
        self.vtk_viewer.set_measure_axis(self.meaure_axis)

        if self.__roi_id is not None:
            self.__checked_subjects = geom_db.subjects_with_line(self.__roi_id)
        else:
            self.__checked_subjects = set()
        assert isinstance(self.__checked_subjects, set)
        self.__subjects_check_model = SubjectChecklist(self.__subjects_list)
        self.__subjects_check_model.checked = self.__checked_subjects

        self.__line_modified = True

        self.setup_ui()
        self.__line_color = (255,255,255)
        self.__aux_lut = None


    def setup_ui(self):
        self.ui = Ui_OrtoMeasure()
        self.ui.setupUi(self)
        self.ui.measure_name.setText(self.__roi_name)

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
        if self.meaure_axis == AXIAL:
            check = self.ui.axial_check
        elif self.meaure_axis == CORONAL:
            check = self.ui.coronal_check
        else:
            check = self.ui.sagital_check
        check.setChecked(True)
        check.setEnabled(False)
        self.vtk_widget.slice_changed.connect(self.update_slice_controls)
        self.vtk_widget.distance_changed.connect(self.update_measure)
        self.ui.image_combo.currentIndexChanged.connect(self.select_image_modality)
        paradigms = self.reader.get("fMRI",None,index=True)
        for p in paradigms:
            self.ui.image_combo.addItem(p.title())
        self.ui.contrast_combo.setEnabled(0)
        self.ui.contrast_combo.setCurrentIndex(0)
        self.ui.contrast_combo.setEnabled(False)
        self.ui.contrast_combo.activated.connect(self.change_contrast)
        self.ui.line_opac.valueChanged.connect(self.set_line_opac)

        self.ui.subjects_list.setModel(self.__subjects_check_model)
        self.ui.subjects_list.activated.connect(self.select_subject)
        self.ui.subject_line_label.setText("Subject %s" % self.__current_subject)
        self.ui.save_line.clicked.connect(self.save_line)

        self.ui.actionSave_Scenario.triggered.connect(self.save_scenario)
        self.ui.actionLoad_Scenario.triggered.connect(self.load_scenario)
        self.ui.actionSave_line_as.triggered.connect(self.save_line_as)
        self.ui.color_button.clicked.connect(self.set_line_color)

        self.ui.reset_measure.clicked.connect(self.reset_measure)
        self.ui.reset_camera_button.clicked.connect(self.reset_camera)

        self.setFocusPolicy(QtCore.Qt.ClickFocus)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Right:
            subj = self.__current_subject
            idx = self.__subjects_list.index(subj)
            next_idx = (idx+1)%len(self.__subjects_list)
            next_one = self.__subjects_list[next_idx]
            self.select_subject(subj=next_one)
        elif event.key() == QtCore.Qt.Key_Left:
            subj = self.__current_subject
            idx = self.__subjects_list.index(subj)
            prev = self.__subjects_list[idx-1]
            self.select_subject(subj=prev)
        elif event.key() == QtCore.Qt.Key_Up:
            sl = self.vtk_viewer.get_current_slice()[self.meaure_axis]
            sl += 1
            self.vtk_viewer.image_planes[self.meaure_axis].set_image_slice(sl)
        elif event.key() == QtCore.Qt.Key_Down:
            sl = self.vtk_viewer.get_current_slice()[self.meaure_axis]
            sl -= 1
            self.vtk_viewer.image_planes[self.meaure_axis].set_image_slice(sl)
        else:
            super(MeasureApp,self).keyPressEvent(event)

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

    def reset_measure(self):
        self.vtk_viewer.reset_measure()

    def update_measure(self,d):
        self.ui.measure_label.setText("%.3f"%d)
        self.ui.point_1.setText(point_to_str(self.vtk_viewer.point1))
        self.ui.point_2.setText(point_to_str(self.vtk_viewer.point2))
        self.line_just_changed()

    def set_image(self, modality,contrast=None):
        self.__current_image_mod = modality
        self.__current_contrast = contrast
        log = logging.getLogger(__name__)
        try:
            self.vtk_viewer.change_image_modality(modality,contrast)
        except Exception as e:
            self.statusBar().showMessage(e.message,500)
            log.warning(e.message)
        self.update_slice_maximums()

    def update_slice_maximums(self):
        dims = self.vtk_viewer.get_number_of_slices()
        print dims
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
        self.line_just_changed()

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


    def set_line_opac(self, opac_val):
        self.vtk_viewer.sphere.set_opacity(opac_val)
        self.vtk_viewer.ren_win.Render()

    def select_subject(self, index=None,subj=None):
        if subj is None:
            subj = self.__subjects_check_model.data(index, QtCore.Qt.DisplayRole)
        if self.__line_modified:
            confirmation_dialog = ConfirmSubjectChangeDialog()
            res = confirmation_dialog.exec_()
            if res == confirmation_dialog.Rejected:
                return
            if confirmation_dialog.save_requested:
                self.save_line()
        self.change_subject(subj)

    def change_subject(self, new_subject):
        self.__current_subject = new_subject
        self.ui.subject_line_label.setText("Subject %s" % self.__current_subject)
        img_id = tabular_data.get_var_value(tabular_data.IMAGE_CODE, new_subject)
        self.__current_img_id = img_id
        self.reload_contrast_names()
        log = logging.getLogger(__file__)
        try:
            self.vtk_viewer.change_subject(img_id)
        except Exception:
            log.warning("Couldnt load data for subject %s",new_subject)
        else:
            self.update_slice_maximums()
        self.load_line(new_subject)
        self.__line_modified = False
        print new_subject

    def save_line(self):
        p1 = self.vtk_viewer.point1
        p2 = self.vtk_viewer.point2
        geom_db.save_line(self.__roi_id,self.__current_subject,p1,p2)
        self.refresh_checked()
        self.__line_modified = False
        self.ui.save_line.setEnabled(0)

    def line_just_changed(self):
        self.__line_modified = True
        self.ui.save_line.setEnabled(1)

    def load_line(self, subj):
        res = geom_db.load_line(self.__roi_id, subj)
        if res is None:
            return
        p1 = np.array(res[0:3])
        p2 = np.array(res[3:6])

        self.vtk_viewer.set_points(p1,p2)
        slice_position = p1[self.meaure_axis]
        self.vtk_viewer.set_slice_coords(slice_position)
        self.__line_modified = False
        self.ui.save_line.setEnabled(0)

    def refresh_checked(self):
        checked = geom_db.subjects_with_line(self.__roi_id)
        self.__subjects_check_model.checked = checked

    def reset_camera(self):
        fp,pos,vu = self.vtk_viewer.get_camera_parameters()
        print fp
        print pos
        print vu
        self.vtk_viewer.reset_camera()

    def select_image_modality(self, dummy_index):
        mod = str(self.ui.image_combo.currentText())
        if self.ui.image_combo.currentIndex() > 3:
            #functional
            self.ui.contrast_combo.setEnabled(1)
            self.reload_contrast_names(mod)
            contrast = int(self.ui.contrast_combo.currentIndex())+1
        else:
            self.ui.contrast_combo.setEnabled(0)
            contrast = None
        self.set_image(mod,contrast)

    def reload_contrast_names(self,mod=None):
        if mod is None:
            mod = str(self.ui.image_combo.currentText())
        if mod.upper() not in self.reader.get("FMRI",None,index=True):
            return
        previus_index = self.ui.contrast_combo.currentIndex()
        try:
            contrasts_dict = self.reader.get("FMRI",self.__current_img_id,name=mod,contrasts_dict=True)
        except Exception:
            pass
        else:
            self.ui.contrast_combo.clear()
            for i in xrange(len(contrasts_dict)):
                self.ui.contrast_combo.addItem(contrasts_dict[i+1])
            if 0<=previus_index<len(contrasts_dict):
                self.ui.contrast_combo.setCurrentIndex(previus_index)
            else:
                self.ui.contrast_combo.setCurrentIndex(0)
                self.change_contrast()


    def change_contrast(self,dummy_index=None):
        new_contrast = self.ui.contrast_combo.currentIndex()+1
        mod = str(self.ui.image_combo.currentText())
        self.set_image(mod,new_contrast)

    def get_state(self):
        state = dict()
        state["roi_id"] = self.__roi_id
        #context
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
        visual_dict["sphere_color"] = self.__line_color
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

    def load_state(self,state):
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
            self.__curent_space = "World"
        self.vtk_viewer.change_space(self.__curent_space)
        self.__checked_subjects = geom_db.subjects_with_sphere(self.__roi_id)
        self.__subjects_check_model.checked = self.__checked_subjects
        self.__line_modified = False

        #context
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
        self.__line_color = visual_dict["sphere_color"]
        self.vtk_viewer.sphere.set_color(*self.__line_color)
        fp,pos,vu = visual_dict["camera"]
        self.vtk_viewer.set_camera(fp,pos,vu)
        self.ui.sphere_rep.setCurrentIndex(visual_dict["spher_rep"])
        self.ui.sphere_opac.setValue(visual_dict["sphere_opac"])
        self.ui.show_fibers_check.setChecked(visual_dict.get("show_fibers",False))

        self.change_subject(self.__current_subject)
        self.__line_modified = False


    def save_scenario(self):
        state = self.get_state()
        app_name = state["meta"]["application"]
        dialog = SaveScenarioDialog(app_name,state)
        res = dialog.exec_()
        if res == dialog.Accepted:
            scn_id = dialog.params["scn_id"]
            self.save_screenshot(scn_id)


    def save_screenshot(self,scenario_index):
        file_name = "scenario_%d.png"%scenario_index
        file_path = os.path.join(self.reader.getDynDataRoot(), "braviz_data","scenarios",file_name)
        log = logging.getLogger(__name__)
        log.info(file_path)
        braviz.visualization.save_ren_win_picture(self.vtk_viewer.ren_win,file_path)

    def load_scenario(self):
        my_name = os.path.splitext(os.path.basename(__file__))[0]
        dialog = LoadScenarioDialog(my_name,reader=self.reader)
        res = dialog.exec_()
        if res == dialog.Accepted:
            wanted_state = dialog.out_dict
            self.load_state(wanted_state)


    def save_line_as(self):
        dialog = NewMeasure(self.__curent_space)
        res = dialog.exec_()
        if res == dialog.Accepted:
            new_name = dialog.name
            desc = dialog.desc
            new_id = geom_db.create_roi(new_name,0,self.__curent_space,desc)
            geom_db.copy_spheres(self.__roi_id,new_id)
            self.__roi_id=new_id
            self.__roi_name = new_name
            self.refresh_checked()




    def set_line_color(self):
        color = QtGui.QColorDialog.getColor()
        self.ui.color_button.setStyleSheet("#color_button{color : %s}"%color.name())
        self.vtk_viewer.set_measure_color(color.red(),color.green(),color.blue())
        self.__line_color = (color.red(),color.green(),color.blue())
        self.vtk_viewer.ren_win.Render()


def run():
    import sys
    from braviz.utilities import configure_console_logger

    # configure_logger("build_roi")
    configure_console_logger("build_roi")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    logging.basicConfig(level=logging.DEBUG)
    start_dialog = StartDialog()
    res = start_dialog.exec_()
    if res != start_dialog.Accepted:
        return
    if start_dialog.scenario_data is not None:
        main_window = MeasureApp(None)
        main_window.show()
        main_window.start()
        main_window.load_state(start_dialog.scenario_data)
    else:
        roi_name = start_dialog.name
        main_window = MeasureApp(roi_name)
        main_window.show()
        main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

def point_to_str(p):
    if p is None:
        return ""
    else:
        ss = ",".join(("%.1f"%x for x in p))
        return " ".join(("(",ss,")"))

if __name__ == '__main__':
    run()