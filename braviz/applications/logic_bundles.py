from __future__ import division
import logging
from functools import partial as partial_f

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QMainWindow, QDialog
import vtk
import numpy as np

import braviz
from braviz.interaction.qt_guis.logic_bundles import Ui_LogicBundlesApp
from braviz.interaction.qt_guis.roi_subject_change_confirm import Ui_RoiConfirmChangeSubject
from braviz.interaction.qt_guis.AddStructuresDialog import Ui_AddSegmented
from braviz.interaction.qt_guis.load_roi import Ui_LoadRoiDialog
from braviz.interaction.logic_bundle_model import LogicBundleQtTree
from braviz.visualization.subject_viewer import QOrthogonalPlanesWidget
from braviz.readAndFilter.filter_fibers import FilterBundleWithSphere
from braviz.interaction.qt_structures_model import StructureTreeModel
from braviz.interaction.qt_models import SubjectChecklist, DataFrameModel
from braviz.readAndFilter import geom_db, tabular_data

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
    'BA')
))

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

class AddSegmentedDialog(QDialog):
    def __init__(self,reader,subj):
        QDialog.__init__(self)
        self.ui = Ui_AddSegmented()
        self.ui.setupUi(self)
        self.model = StructureTreeModel(reader,subj)
        self.ui.treeView.setModel(self.model)

class ConfirmExitDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        self.ui = Ui_RoiConfirmChangeSubject()
        self.ui.setupUi(self)
        self.save_requested = False
        self.ui.buttonBox.button(self.ui.buttonBox.Save).clicked.connect(self.set_save)
        self.ui.buttonBox.button(self.ui.buttonBox.Discard).clicked.connect(self.accept)

    def set_save(self):
        self.save_requested = True


class LogicBundlesApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = None

        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.__subjects_list = tabular_data.get_subjects()
        self.__current_subject = self.__subjects_list[0]
        self.__current_img_id = None

        self.__current_image_mod = "MRI"
        self.__curent_space = "World"

        self.vtk_widget = QOrthogonalPlanesWidget(self.reader, parent=self)
        self.vtk_viewer = self.vtk_widget.orthogonal_viewer

        self.logic_tree = LogicBundleQtTree()

        self.__fibers_map = None
        self.__fibers_ac = None
        self.__filetred_pd = None
        self.__full_pd = None
        self.__fibers_filterer = None

        self.__subjects_check_model = SubjectChecklist(self.__subjects_list,show_checks=False)

        self.__sphere_modified = True

        self.setup_ui()


    def setup_ui(self):
        self.ui = Ui_LogicBundlesApp()
        self.ui.setupUi(self)

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
        self.ui.space_combo.currentTextChanged.connect(self.select_space)

        self.ui.subjects_list.setModel(self.__subjects_check_model)
        self.ui.subjects_list.activated.connect(self.select_subject)

        self.ui.surface_combo.currentIndexChanged.connect(self.select_surface)
        self.ui.scalar_combo.currentIndexChanged.connect(self.select_surface_scalars)
        self.ui.left_cortex_check.stateChanged.connect(self.toggle_left_surface)
        self.ui.right_cortex_check.stateChanged.connect(self.toggle_right_surface)
        self.ui.cortex_opac.valueChanged.connect(self.set_cortex_opacity)

        self.ui.actionSave_Scenario.triggered.connect(self.save_scenario)
        self.ui.actionLoad_Scenario.triggered.connect(self.load_scenario)

        self.ui.treeView.setModel(self.logic_tree)
        self.ui.treeView.customContextMenuRequested.connect(self.launch_tree_context_menu)

        #logic menu
        logic_menu = QtGui.QMenu(self.ui.add_logic)
        and_action = logic_menu.addAction("AND")
        and_action.triggered.connect(partial_f(self.add_logic_node,"AND"))
        or_action = logic_menu.addAction("OR")
        or_action.triggered.connect(partial_f(self.add_logic_node,"OR"))
        not_action = logic_menu.addAction("NOT")
        not_action.triggered.connect(partial_f(self.add_logic_node,"NOT"))
        self.ui.add_logic.setMenu(logic_menu)

        self.ui.add_segmented.clicked.connect(self.add_segmented_structure_dialog)
        self.ui.add_roi.clicked.connect(self.launch_add_roi_dialog)

    def add_logic_node(self,value):
        index = self.ui.treeView.currentIndex()
        self.logic_tree.add_node(index,node_type="LOGIC",value=value)
        self.ui.treeView.expandAll()

    def add_segmented_structure_dialog(self):
        dialog = AddSegmentedDialog(self.reader,self.__current_subject)
        res = dialog.exec_()
        if res == dialog.Accepted:
            selected = dialog.model.get_selected_structures()
            self.add_segmented_structures(selected)


    def add_segmented_structures(self,structures_list):
        """
        The structures in the list will be added inside an "or" node, if only one then it will be added alone
        """
        if len(structures_list)==0:
            return
        parent_index = self.ui.treeView.currentIndex()
        if len(structures_list)>1:
            parent_index=self.logic_tree.add_node(parent_index,"LOGIC",value="OR")
        for st in structures_list:
            self.logic_tree.add_node(parent_index,"STRUCT",value=st)
        self.ui.treeView.expandAll()

    def launch_add_roi_dialog(self):
        dialog = LoadRoiDialog()
        res = dialog.exec_()
        if res == dialog.Accepted:
            roi_name = dialog.name
            roi_id = geom_db.get_roi_id(roi_name)
            self.add_roi(roi_id,roi_name)


    def add_roi(self,roi_id,roi_name = None):
        if roi_name is None:
            roi_name = geom_db.get_roi_name(roi_id)
        parent = self.ui.treeView.currentIndex()
        self.logic_tree.add_node(parent,"ROI",roi_name,roi_id)


    def start(self):
        self.vtk_widget.initialize_widget()
        self.set_image("MRI")
        self.vtk_viewer.show_image()
        self.vtk_viewer.change_space(self.__curent_space)
        self.vtk_viewer.finish_initializing()
        self.change_subject(self.__current_subject)
        self.select_surface(None)

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

    def select_subject(self, index):
        subj = self.__subjects_check_model.data(index, QtCore.Qt.DisplayRole)
        self.change_subject(subj)

    def change_subject(self, new_subject):
        self.__current_subject = new_subject
        img_id = tabular_data.get_var_value(tabular_data.IMAGE_CODE, new_subject)
        self.__current_img_id = img_id
        log = logging.getLogger(__file__)
        try:
            self.vtk_viewer.change_subject(img_id)
        except Exception:
            log.warning("Couldnt load data for subject %s",new_subject)
        self.__full_pd = None
        print new_subject


    def select_image_modality(self, index):
        mod = str(self.ui.image_combo.currentText())
        self.change_image_modality(mod)

    def change_image_modality(self, new_mod):
        self.vtk_viewer.change_image_modality(new_mod)

    def select_surface_scalars(self,index):
        scalar_name = SURFACE_SCALARS_DICT[int(index)]
        self.vtk_viewer.cortex.set_scalars(scalar_name)

    def select_surface(self,index):
        surface_name = str(self.ui.surface_combo.currentText())
        self.vtk_viewer.cortex.set_surface(surface_name)

    def toggle_left_surface(self,status):
        b_status = (status == QtCore.Qt.Checked)
        self.vtk_viewer.cortex.set_hemispheres(left=b_status)

    def toggle_right_surface(self,status):
        b_status = (status == QtCore.Qt.Checked)
        self.vtk_viewer.cortex.set_hemispheres(right=b_status)

    def set_cortex_opacity(self,int_opac):
        self.vtk_viewer.cortex.set_opacity(int_opac)

    def select_space(self,index):
        space = str(self.ui.space_combo.currentText())
        self.change_space(space)

    def change_space(self,new_space):
        self.vtk_viewer.change_space(new_space)
        self.__curent_space = new_space


    def launch_tree_context_menu(self, pos):
        global_pos = self.ui.treeView.mapToGlobal(pos)
        selection = self.ui.treeView.currentIndex()
        if self.logic_tree.parent(selection).isValid() is False:
            "cant remove root"
            return
        remove_action = QtGui.QAction("Remove", None)
        menu = QtGui.QMenu()
        menu.addAction(remove_action)

        def remove_item(*args):
            self.logic_tree.remove_node(selection)
            self.ui.treeView.expandAll()

        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        menu.exec_(global_pos)

    def get_state(self):
        pass

    def load_state(self):
        pass

    def save_scenario(self):
        pass

    def load_scenario(self):
        pass

def run():
    import sys
    from braviz.utilities import configure_console_logger

    # configure_logger("build_roi")
    configure_console_logger("build_roi")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    logging.basicConfig(level=logging.DEBUG)
    main_window = LogicBundlesApp()
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()