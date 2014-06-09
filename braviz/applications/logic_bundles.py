from __future__ import division
import logging
from functools import partial as partial_f

from PyQt4 import QtGui, QtCore
from PyQt4.QtGui import QMainWindow, QDialog
import vtk
import numpy as np
import os
import datetime
import sys
import platform

import braviz
from braviz.interaction.qt_guis.logic_bundles import Ui_LogicBundlesApp
from braviz.interaction.qt_guis.roi_subject_change_confirm import Ui_RoiConfirmChangeSubject
from braviz.interaction.qt_guis.AddStructuresDialog import Ui_AddSegmented
from braviz.interaction.qt_guis.load_roi import Ui_LoadRoiDialog
from braviz.interaction.logic_bundle_model import LogicBundleQtTree, LogicBundleNodeWithVTK
from braviz.visualization.subject_viewer import QOrthogonalPlanesWidget
from braviz.interaction.qt_structures_model import StructureTreeModel
from braviz.interaction.qt_models import SubjectChecklist, DataFrameModel
from braviz.readAndFilter import geom_db, tabular_data
from braviz.readAndFilter.hierarchical_fibers import read_logical_fibers
from braviz.interaction import compute_fiber_lengths
from braviz.interaction.structure_metrics import get_scalar_from_fiber_ploydata
from braviz.interaction.qt_dialogs import SaveScenarioDialog,LoadScenarioDialog

__author__ = 'Diego'

#TODO Save bundle
#TODO Export scalars


AXIAL = 2
SAGITAL = 0
CORONAL = 1
NORMAL_COLOR = (0.10588235294117647, 0.6196078431372549, 0.4666666666666667)
ACCENT_COLOR = (0.9019607843137255, 0.6705882352941176, 0.00784313725490196)


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

FIBER_SCALARS_DICT = dict(enumerate((
    "number",
    "mean_length",
    "mean_fa",
    "mean_md"
)))

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
        self.__current_img_id = tabular_data.get_var_value(tabular_data.IMAGE_CODE,self.__current_subject)

        self.__current_image_mod = "MRI"
        self.__curent_space = "World"

        self.vtk_widget = QOrthogonalPlanesWidget(self.reader, parent=self)
        self.vtk_viewer = self.vtk_widget.orthogonal_viewer

        self.vtk_tree = LogicBundleNodeWithVTK(None,0,LogicBundleNodeWithVTK.LOGIC,
                                               "AND",reader=self.reader,subj=self.__current_subject,
                                               space = self.__curent_space)

        self.logic_tree = LogicBundleQtTree(self.vtk_tree)

        self.__fibers_map = vtk.vtkPolyDataMapper()
        self.__fibers_ac = vtk.vtkActor()
        self.__filetred_pd = None
        self.__fibers_color = "orient"
        self.__fibers_lut = None

        self.__fibers_ac.SetMapper(self.__fibers_map)
        self.vtk_viewer.ren.AddActor(self.__fibers_ac)
        self.__fibers_ac.SetVisibility(0)

        self.__subjects_check_model = SubjectChecklist(self.__subjects_list,show_checks=False)

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
        self.ui.treeView.clicked.connect(self.highlight_waypoints)

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
        self.ui.waypoints_opacity.valueChanged.connect(self.change_waypoint_opac)

        self.ui.preview_bundle.stateChanged.connect(self.update_fibers)

        self.ui.fiber_scalar_combo.currentIndexChanged.connect(self.update_fibers)


    def get_valid_parent(self):
        index = self.ui.treeView.currentIndex()
        node = self.logic_tree.get_node(index)
        if node is None:
            node = self.logic_tree.root

        while node.node_type != node.LOGIC:
            node = node.parent
        return node


    def add_logic_node(self,value):
        parent = self.get_valid_parent()
        self.logic_tree.add_node(parent,parent.LOGIC,value=value)
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
        parent = self.get_valid_parent()
        if len(structures_list)>1:
            parent=self.logic_tree.add_node(parent,parent.LOGIC,value="OR")
        for st in structures_list:
            new_node = self.logic_tree.add_node(parent,parent.STRUCT,value=st)
            self.vtk_viewer.ren.AddActor(new_node.prop)
        self.ui.treeView.expandAll()
        self.refresh_waypoints()
        self.update_fibers()
        #self.update_scalar_metric()

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
        parent = self.get_valid_parent()
        node = self.logic_tree.add_node(parent,parent.ROI,roi_name,roi_id)
        self.vtk_viewer.ren.AddActor(node.prop)
        self.ui.treeView.expandAll()
        self.refresh_waypoints()
        self.update_fibers()
        #self.update_scalar_metric()


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
        self.__current_image_mod = modality
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
        img_id = str(tabular_data.get_var_value(tabular_data.IMAGE_CODE, new_subject))
        self.__current_img_id = img_id
        log = logging.getLogger(__file__)
        self.vtk_tree.update(new_subject,self.__curent_space)
        try:
            self.vtk_viewer.change_subject(img_id)
        except Exception:
            log.warning("Couldnt load data for subject %s",new_subject)
        self.update_fibers()
        #self.update_scalar_metric()


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
        self.vtk_tree.update(self.__current_img_id,new_space)
        self.update_fibers()
        #self.update_scalar_metric()

    def change_waypoint_opac(self,value):
        self.logic_tree.root.set_opacity(value)
        self.vtk_viewer.ren_win.Render()

    def change_waypoints_color(self,color):
        self.logic_tree.root.set_color(color)
        self.vtk_viewer.ren_win.Render()

    def highlight_waypoints(self,index):
        self.logic_tree.root.set_color(NORMAL_COLOR)
        node = self.logic_tree.get_node(index)
        node.set_color(ACCENT_COLOR)
        self.vtk_viewer.ren_win.Render()


    def refresh_waypoints(self):
        self.change_waypoint_opac(self.ui.waypoints_opacity.value())
        self.change_waypoints_color(NORMAL_COLOR)

    def launch_tree_context_menu(self, pos):
        global_pos = self.ui.treeView.mapToGlobal(pos)
        selection = self.ui.treeView.currentIndex()
        if self.logic_tree.parent(selection).isValid() is False:
            "cant remove root"
            return
        remove_action = QtGui.QAction("Remove", None)
        menu = QtGui.QMenu()
        menu.addAction(remove_action)

        def remove_node_from_render(node):
            for c in node.children:
                remove_node_from_render(c)
            self.vtk_viewer.ren.RemoveActor(node.prop)

        def remove_item(*args):
            node = self.logic_tree.get_node(selection)
            remove_node_from_render(node)
            self.logic_tree.remove_node(selection)
            self.ui.treeView.expandAll()
            self.vtk_viewer.ren_win.Render()

        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        menu.exec_(global_pos)

    def get_bundle(self):
        dict_tree = self.logic_tree.root.to_dict()
        if self.__fibers_color == "orient":
            sc = None
        else:
            sc = self.__fibers_color
        fibers = read_logical_fibers(self.__current_subject,dict_tree,self.reader,space=self.__curent_space,
                                     scalars=sc)
        return fibers

    def read_fibers(self,dummy=None):
        if self.ui.preview_bundle.checkState() == QtCore.Qt.Checked:

            try:
                self.__filetred_pd = self.get_bundle()
            except Exception:
                self.statusBar().showMessage("Error loading fibers",2000)
                self.__fibers_ac.SetVisibility(0)
            else:
                self.__fibers_map.SetInputData(self.__filetred_pd)
                self.__fibers_ac.SetVisibility(1)
        else:
            self.__fibers_ac.SetVisibility(0)
        if self.__fibers_color == "orient":
            self.__fibers_lut = None
            self.__fibers_map.SetColorModeToDefault()
        else:
            self.__fibers_lut = self.reader.get("Fibers",None,scalars=self.__fibers_color,lut = True)
            self.__fibers_map.UseLookupTableScalarRangeOn()
            self.__fibers_map.SetColorModeToMapScalars()
            self.__fibers_map.SetLookupTable(self.__fibers_lut)
        self.vtk_viewer.ren_win.Render()


    def update_fibers(self,dummy=None):
        if self.ui.preview_bundle.checkState() != QtCore.Qt.Checked:
            self.ui.fiber_scalar_combo.setEnabled(0)
            self.ui.scalar_box.setEnabled(0)
            self.__fibers_ac.SetVisibility(0)
            self.vtk_viewer.ren_win.Render()
            return
        self.ui.fiber_scalar_combo.setEnabled(1)
        self.ui.scalar_box.setEnabled(1)
        index=self.ui.fiber_scalar_combo.currentIndex()
        logger = logging.getLogger(__file__)
        metric = FIBER_SCALARS_DICT[int(index)]
        self.set_fiber_color(metric)
        try:
            self.read_fibers()
        except Exception:
            logger.warning("Couldn't read fibers")
            self.ui.scalar_box.setValue(float("nan"))

            return

        self.update_scalar_metric(metric)


    def update_scalar_metric(self,metric):
        logger = logging.getLogger(__file__)
        try:
            ans = self.get_scalar_metric(metric)
        except Exception:
            logger.warning("Couldnt calculate metric")
            ans = float("nan")

        self.ui.scalar_box.setValue(ans)


    def set_fiber_color(self,metric):
        if metric == "mean_fa":
            color = "fa_p"
        elif metric == "mean_md":
            color = "md_p"
        else:
            color = "orient"
        self.__fibers_color = color

    def get_scalar_metric(self,metric):

        fibers = self.__filetred_pd
        self.ui.scalar_box.setSuffix("")
        if metric == "number":
            return fibers.GetNumberOfLines()
        elif metric == "mean_length":
            lengths = compute_fiber_lengths(fibers)
            return np.mean(lengths)
        elif metric in {"mean_fa","mean_md"}:
            ans = get_scalar_from_fiber_ploydata(fibers,"mean_color")
            if metric=="mean_md":
                ans *= 10e9
                self.ui.scalar_box.setSuffix(" x10e9")
            return ans
        else:
            raise Exception("Unknwon metric")

    def save_bundle(self):
        pass

    def get_state(self):
        state = dict()
        #current tree
        state["logic_tree"] = self.vtk_tree.to_dict()
        #context
        context_dict = {}
        context_dict["image_type"] = self.__current_image_mod
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
        visual_dict["waypoints_opac"] = int(self.ui.waypoints_opacity.value())
        visual_dict["preview"] = self.ui.preview_bundle.checkState() == QtCore.Qt.Checked
        visual_dict["scalar"] = str(self.ui.fiber_scalar_combo.currentText())
        #camera
        visual_dict["camera"] = self.vtk_viewer.get_camera_parameters()
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
        #subject
        subjs_state = state["subjects"]
        subj = subjs_state["subject"]
        self.change_subject(subj)
        assert self.__current_img_id == subjs_state["img_code"]
        self.__subjects_list = subjs_state["sample"]
        #context
        context_dict =state["context"]
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

        tree = state["logic_tree"]
        #remove all from render
        for node in self.vtk_tree:
            self.vtk_viewer.ren.RemoveActor(node.prop)
        self.vtk_tree = LogicBundleNodeWithVTK.from_dict(tree,self.reader,self.__current_subject,self.__curent_space)
        self.logic_tree.set_root(self.vtk_tree)
        #add all to render
        for node in self.vtk_tree:
            self.vtk_viewer.ren.AddActor(node.prop)
        self.refresh_waypoints()

        #visual
        visual_dict = state["visual"]
        coords = visual_dict["coords"]
        idx = self.ui.space_combo.findText(coords)
        assert idx >= 0
        self.ui.space_combo.setCurrentIndex(idx)

        self.ui.waypoints_opacity.setValue(visual_dict["waypoints_opac"])
        self.ui.preview_bundle.setChecked(visual_dict["preview"])
        fsc = visual_dict["scalar"]
        idx = self.ui.fiber_scalar_combo.findText(fsc)
        assert  idx >= 0
        self.ui.fiber_scalar_combo.setCurrentIndex(idx)
        #camera
        fp,pos,vu = visual_dict["camera"]
        self.vtk_viewer.set_camera(fp,pos,vu)



    def save_scenario(self):
        state = self.get_state()
        meta = state["meta"]
        dialog = SaveScenarioDialog(meta["application"], state)
        res=dialog.exec_()
        if res==QtGui.QDialog.Accepted:
            scn_id = dialog.params["scn_id"]
            self.save_screenshot(scn_id)
        pass

    def load_scenario(self):
        my_name = os.path.splitext(os.path.basename(__file__))[0]
        dialog = LoadScenarioDialog(my_name, reader=self.reader)
        res = dialog.exec_()
        if res == dialog.Accepted:
            wanted_state = dialog.out_dict
            self.load_state(wanted_state)

    def save_screenshot(self,scenario_index):
        file_name = "scenario_%d.png"%scenario_index
        file_path = os.path.join(self.reader.getDynDataRoot(), "braviz_data","scenarios",file_name)
        log = logging.getLogger(__name__)
        log.info(file_path)
        braviz.visualization.save_ren_win_picture(self.vtk_viewer.ren_win,file_path)

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