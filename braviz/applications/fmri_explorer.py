from __future__ import division
from PyQt4 import QtCore,QtGui
import braviz
import braviz.visualization.subject_viewer
import braviz.visualization.fmri_timeseries
from braviz.readAndFilter import user_data as braviz_user_data
from braviz.readAndFilter import tabular_data as braviz_tab_data
from braviz.interaction.qt_models import DataFrameModel
from braviz.interaction import qt_dialogs
from braviz.interaction.connection import MessageClient
from braviz.interaction.qt_sample_select_dialog import SampleLoadDialog
import pandas as pd
import seaborn as sns

from braviz.interaction.qt_guis.fmri_explore import Ui_fMRI_Explorer
import logging

import numpy as np

#todo: receive messages and send, connect to menu
__author__ = 'Diego'

class ListValidator(QtGui.QValidator):
    def __init__(self,valid_options):
        super(ListValidator,self).__init__()
        self.valid = frozenset(valid_options)

    def validate(self, QString, p_int):
        str_value = str(QString)
        if str_value in self.valid:
            return QtGui.QValidator.Acceptable,p_int
        else:
            if len(str_value) == 0:
                return QtGui.QValidator.Intermediate,p_int
            try:
                i = int(str_value)
            except Exception:
                return QtGui.QValidator.Invalid,p_int
            else:
                return QtGui.QValidator.Intermediate,p_int

class FmriExplorer(QtGui.QMainWindow):
    def __init__(self,scenario,server_broadcast_address,server_receive_address):
        super(FmriExplorer,self).__init__()
        log = logging.getLogger(__name__)

        self.__reader = braviz.readAndFilter.BravizAutoReader()

        self.__valid_ids = frozenset(str(i) for i in braviz_tab_data.get_subjects())
        self.__current_subject = None
        self.__current_paradigm = None
        self.__current_contrast = 1

        self.__frozen_points = pd.DataFrame(columns=["Subject","Coordinates","Contrast","T Stat"],index=[])
        self.__frozen_model = DataFrameModel(self.__frozen_points,string_columns=(1,2),index_as_column=False)

        self.ui = None
        self.three_d_widget = None
        self.image_view = None
        self.time_plot = None
        self.start_ui()

        self._messages_client = None
        if server_broadcast_address is not None or server_receive_address is not None:
            self._messages_client = MessageClient(server_broadcast_address, server_receive_address)
            self._messages_client.message_received.connect(self.receive_message)
            log.info( "started messages client")


        if scenario is None or scenario == 0:
            QtCore.QTimer.singleShot(0, self.load_initial_view)
        else:
            print "Got scenario"
            print scenario

    def start_ui(self):
        self.ui = Ui_fMRI_Explorer()
        self.ui.setupUi(self)

        #image frame
        self.three_d_widget = braviz.visualization.subject_viewer.QFmriWidget(self.__reader,self.ui.vtk_frame)
        self.ui.vtk_frame_layout = QtGui.QVBoxLayout(self.ui.vtk_frame)
        self.ui.vtk_frame.setLayout(self.ui.vtk_frame_layout)
        self.ui.vtk_frame_layout.addWidget(self.three_d_widget)
        self.ui.vtk_frame_layout.setContentsMargins(0,0,0,0)
        self.image_view = self.three_d_widget.viewer
        self.three_d_widget.cursor_moved.connect(self.handle_cursor_move)

        #timeserios frame
        self.time_plot = braviz.visualization.fmri_timeseries.TimeseriesPlot(self.ui.timeline_frame)
        self.ui.timeline_frame_layout = QtGui.QVBoxLayout(self.ui.timeline_frame)
        self.ui.timeline_frame.setLayout(self.ui.timeline_frame_layout)
        self.ui.timeline_frame_layout.addWidget(self.time_plot)
        self.ui.timeline_frame_layout.setContentsMargins(0,0,0,0)

        #controls
        paradigms = sorted(self.__reader.get("fmri",None,index=True))
        for p in paradigms:
            self.ui.paradigm_combo.addItem(p)
        self.ui.paradigm_combo.setCurrentIndex(0)
        self.ui.contrast_combo.clear()
        self.ui.contrast_combo.activated.connect(self.update_fmri_data_view)
        self.ui.paradigm_combo.activated.connect(self.update_fmri_data_view)

        #subject
        self.ui.subj_completer = QtGui.QCompleter(list(self.__valid_ids))
        self.ui.subject_edit.setCompleter(self.ui.subj_completer)
        self.ui.subj_validator = ListValidator(self.__valid_ids)
        self.ui.subject_edit.setValidator(self.ui.subj_validator)
        self.ui.subject_edit.editingFinished.connect(self.update_fmri_data_view)

        #image
        self.three_d_widget.slice_changed.connect(self.ui.slice_slider.setValue)
        self.ui.slice_slider.valueChanged.connect(self.image_view.image.set_image_slice)
        self.ui.slice_spin.setMinimum(0)
        self.ui.slice_slider.setMinimum(0)

        self.ui.image_orientation_combo.setCurrentIndex(2)
        self.ui.image_orientation_combo.activated.connect(self.change_image_orientation)

        #contours
        self.ui.show_contours_value.valueChanged.connect(self.change_contour_value)
        self.ui.show_contours_check.clicked.connect(self.change_contour_visibility)
        self.ui.contour_opacity_slider.valueChanged.connect(self.change_contour_opacity)

        #Frozen
        self.ui.frozen_points_table.setModel(self.__frozen_model)
        self.ui.freeze_point_button.clicked.connect(self.freeze_point)
        self.ui.clear_button.clicked.connect(self.clear_frozen)
        self.ui.frozen_points_table.customContextMenuRequested.connect(self.get_frozen_context_menu)
        self.ui.frozen_points_table.activated.connect(self.highlight_frozen)
        self.ui.frozen_points_table.clicked.connect(self.highlight_frozen)
        self.ui.for_all_subjects.clicked.connect(self.add_point_for_all)

        #timelines
        self.ui.time_color_combo.insertSeparator(1)
        self.ui.time_color_combo.addItem("Select group variable")
        self.ui.time_color_combo.addItem("Group by location")
        self.ui.time_color_combo.activated.connect(self.select_time_color)
        self.ui.time_aggregrate_combo.activated.connect(self.timeline_aggregrate_combo)


    def start(self):
        self.three_d_widget.initialize_widget()

    def change_image_orientation(self):
        orientation_dict = {"Axial": 2, "Coronal": 1, "Sagital": 0}
        selection = str(self.ui.image_orientation_combo.currentText())
        orientation_index = orientation_dict[selection]
        self.image_view.change_orientation(orientation_index)
        self.update_slice_controls()


    def load_initial_view(self):
        self.__current_subject = braviz_tab_data.get_subjects()[0]
        self.ui.subject_edit.setText(str(self.__current_subject))
        self.update_fmri_data_view()

    def update_fmri_data_view(self):
        log = logging.getLogger(__name__)
        subj = str(self.ui.subject_edit.text())
        if subj in self.__valid_ids:
            if self._messages_client is not None and subj != self.__current_subject:
                self._messages_client.send_message('subject %s' % subj)
            self.__current_subject = subj
        new_paradigm = str(self.ui.paradigm_combo.currentText())
        if new_paradigm != self.__current_paradigm:
            res = self.warn_and_remove_frozen()
            if not res:
                #operation cancelled
                ix = self.ui.paradigm_combo.findText(self.__current_paradigm)
                self.ui.paradigm_combo.setCurrentIndex(ix)
                return
        image_code = braviz_tab_data.get_image_code(self.__current_subject)
        self.__current_paradigm = new_paradigm
        self.__current_contrast = self.ui.contrast_combo.currentIndex()+1

        try:
            spm_data = self.__reader.get("fmri",image_code,name=self.__current_paradigm,spm=True)
            contrasts = spm_data.get_contrast_names()
        except Exception:
            log.warning("Couldn't read spm file")
            spm_data = None
        else:
            self.ui.contrast_combo.clear()
            for i in xrange(len(contrasts)):
                self.ui.contrast_combo.addItem(contrasts[i+1])
            if 1<=self.__current_contrast <= len(contrasts):
                self.ui.contrast_combo.setCurrentIndex(self.__current_contrast-1)
            else:
                self.ui.contrast_combo.setCurrentIndex(0)
                self.__current_contrast = 1  # 0+1
        try:
            self.image_view.set_all(image_code,self.__current_paradigm,self.__current_contrast)
            bold_image = self.__reader.get("BOLD",image_code,name=self.__current_paradigm)
        except Exception:
            message = "%s not available for subject %s"%(self.__current_paradigm,self.__current_subject)
            log.warning(message)
            self.statusBar().showMessage(message,500)
            bold_image = None
            #raise

        self.update_slice_controls()
        self.time_plot.clear()
        self.time_plot.set_spm_and_bold(spm_data,bold_image)
        self.time_plot.set_contrast(self.__current_contrast)
        self.time_plot.draw_bold_signal(self.image_view.current_coords())

    def update_slice_controls(self):
        n_slices = self.image_view.image.get_number_of_image_slices()
        self.ui.slice_spin.setMaximum(n_slices)
        self.ui.slice_slider.setMaximum(n_slices)

    def handle_cursor_move(self,coords):
        cx,cy,cz = map(int,coords)
        stat = self.image_view.image.image_plane_widget.alternative_img.GetScalarComponentAsDouble(cx,cy,cz,0)
        self.statusBar().showMessage("(%d,%d,%d) : %.4g"%(cx,cy,cz,stat))
        self.time_plot.draw_bold_signal(coords)

    def change_contour_value(self,value):
        self.image_view.set_contour_value(value)

    def change_contour_visibility(self):
        checked = self.ui.show_contours_check.isChecked()
        self.image_view.set_contour_visibility(checked)

    def change_contour_opacity(self,value):
        self.image_view.set_contour_opacity(value)

    def freeze_point(self):
        #todo should include contrast?
        coords = self.image_view.current_coords()
        if coords is None:
            return
        cx,cy,cz = ( int(x) for x in coords)
        s = int(self.__current_subject)
        contrast = self.ui.contrast_combo.itemText(self.ui.contrast_combo.currentIndex())
        stat = self.image_view.image.image_plane_widget.alternative_img.GetScalarComponentAsDouble(cx,cy,cz,0)
        i = (s,cx,cy,cz)
        if i in self.__frozen_points.index:
            return
        df2 = pd.DataFrame({"Subject":[s],
                            "Coordinates":[(cx,cy,cz)],"Contrast":[contrast],
                            "T Stat":[stat]},
                           index=[i])
        self.__frozen_points = self.__frozen_points.append(df2)
        self.__frozen_model.set_df(self.__frozen_points)
        self.time_plot.add_frozen_bold_signal(i,(cx,cy,cz))

    def clear_frozen(self):
        self.__frozen_points = pd.DataFrame(columns=["Subject","Coordinates","T Stat"])
        self.__frozen_model.set_df(self.__frozen_points)
        self.time_plot.clear_frozen_bold_signals()

    def warn_and_remove_frozen(self):
        "When paradigm changes"
        if len(self.__frozen_points)>0:
            dialog = QtGui.QMessageBox()
            dialog.setText("Changing paradigm will delete the current frozen points")
            dialog.setInformativeText("Do you want to clear frozen points?")
            dialog.setStandardButtons(dialog.Discard | dialog.Cancel)
            dialog.setIcon(dialog.Question)
            res = dialog.exec_()
            if res == dialog.Discard:
                self.clear_frozen()
                return True
            else:
                return False
        return True



    def get_frozen_context_menu(self,pos):
        item = self.ui.frozen_points_table.currentIndex()
        if not item.isValid():
            return
        def delete_item():
            item_index = self.__frozen_model.get_item_index(item)
            self.__frozen_points = self.__frozen_points.drop(item_index)
            self.__frozen_model.set_df(self.__frozen_points)
            self.time_plot.remove_frozen_bold_signal(item_index)
        menu = QtGui.QMenu(self.ui.frozen_points_table)
        remove_action = QtGui.QAction("Remove",None)
        menu.addAction(remove_action)
        remove_action.triggered.connect(delete_item)
        global_pos = self.ui.frozen_points_table.mapToGlobal(pos)
        menu.exec_(global_pos)

    def highlight_frozen(self,item):
        item_index = self.__frozen_model.get_item_index(item)
        location = item_index[1:]
        if location != self.image_view.current_coords:
            self.image_view.set_cursor_coords(location)
        self.time_plot.highlight_frozen_bold(item_index)

    def add_point_for_all(self):
        log = logging.getLogger(__name__)
        coords = self.image_view.current_coords()
        contrast = self.ui.contrast_combo.itemText(self.ui.contrast_combo.currentIndex())
        if coords is None:
            return
        self.ui.clear_button.setEnabled(0)
        self.ui.freeze_point_button.setEnabled(0)
        self.ui.for_all_subjects.setEnabled(0)
        self.ui.time_color_combo.setEnabled(0)
        self.ui.time_aggregrate_combo.setEnabled(0)
        cx,cy,cz = ( int(x) for x in coords)
        subjs = self.__valid_ids
        self.ui.progressBar.setValue(0)
        for j,sbj in enumerate(sorted(subjs,key=int)):
            i = (int(sbj),cx,cy,cz)
            s_img = braviz_tab_data.get_image_code(sbj)
            progress = j/(len(self.__valid_ids))*100
            self.ui.progressBar.setValue(progress)
            QtCore.QCoreApplication.instance().processEvents()
            if i not in self.__frozen_points.index:
                try:
                    fmri = self.__reader.get("fMRI",s_img,name=self.__current_paradigm,contrast=self.__current_contrast,
                                             space="fmri-%s"%self.__current_paradigm)
                    bold = self.__reader.get("bold",s_img,name=self.__current_paradigm)
                except Exception:
                    log.warning("%s not found for subject %s"%(self.__current_paradigm,s_img))
                else:
                    stat = fmri.get_data()[cx,cy,cz]
                    df2 = pd.DataFrame({"Subject":[sbj],"Coordinates":[(cx,cy,cz)],
                                        "Contrast":[contrast],
                                        "T Stat":[stat]},
                                       index=[i])
                    self.__frozen_points = self.__frozen_points.append(df2)
                    self.__frozen_model.set_df(self.__frozen_points)
                    self.time_plot.add_frozen_bold_signal(i,(cx,cy,cz),bold.get_data())
        self.ui.progressBar.setValue(100)
        self.ui.clear_button.setEnabled(1)
        self.ui.freeze_point_button.setEnabled(1)
        self.ui.for_all_subjects.setEnabled(1)
        self.ui.time_color_combo.setEnabled(1)
        self.ui.time_aggregrate_combo.setEnabled(1)

    def select_time_color(self):
        if self.ui.time_color_combo.currentIndex() == self.ui.time_color_combo.count()-2:
            params = {}
            dialog = qt_dialogs.SelectOneVariableWithFilter(params,accept_real=False,sample=self.__valid_ids)
            res = dialog.exec_()
            if res == dialog.Accepted:
                var_name = params.get("selected_outcome")
                if var_name is not None:
                    self.ui.time_color_combo.insertItem(1,"Color by %s"%var_name)
                    self.set_timeline_colors(var_name)
                    self.ui.time_color_combo.setCurrentIndex(1)
        if self.ui.time_color_combo.currentIndex() == self.ui.time_color_combo.count()-1:
            self.set_timeline_colors_by_location()
        elif self.ui.time_color_combo.currentIndex() == 0:
            self.set_timeline_colors(None)
        else:
            var_name = str(self.ui.time_color_combo.itemText(self.ui.time_color_combo.currentIndex()))
            self.set_timeline_colors(var_name[9:]) # len("Color by ")


    def set_timeline_colors(self,var_name):
        print "Coloring by ", var_name
        if var_name is None:
            self.time_plot.set_frozen_colors(None)
            self.time_plot.set_frozen_groups_and_colors(None,None)
        else:
            df = braviz_tab_data.get_data_frame_by_name(var_name)
            series = df[var_name].astype(int)
            values = set(series.astype(int))
            values.add(None)
            n_values = len(values)
            color_palette = sns.color_palette("Set1",n_values)
            color_dict = dict( ( (v,color_palette[i]) for i,v in enumerate(values)))

            def color_fun(url):
                subj = url[0]
                val = series.get(subj)
                color = color_dict[val]
                return color

            def group_function(url):
                subj = url[0]
                val = series.get(subj,-1)
                return val
            self.time_plot.set_frozen_groups_and_colors(group_function,color_dict)
            self.time_plot.set_frozen_colors(color_fun)

    def set_timeline_colors_by_location(self):
        locations = [t for t in self.__frozen_points["Coordinates"]]
        unique_locs = set(locations)
        colors = sns.color_palette("Set1",len(unique_locs))
        loc_indexes = dict(( (l,i) for i,l in enumerate(unique_locs)))
        color_dict = dict(( (i,c) for i,c in enumerate(colors)))
        def color_fun(url):
            location = tuple(url[1:])
            l_i = loc_indexes[location]
            color = color_dict[l_i]
            return color

        def group_function(url):
            location = tuple(url[1:])
            return loc_indexes[location]

        self.time_plot.set_frozen_groups_and_colors(group_function,color_dict)
        self.time_plot.set_frozen_colors(color_fun)

    def timeline_aggregrate_combo(self):
        aggregrate=self.ui.time_aggregrate_combo.currentIndex()>0
        self.set_timeline_aggregate(aggregrate)


    def set_timeline_aggregate(self,aggregate=False):
        self.time_plot.set_frozen_aggregration(aggregate)

    def get_state(self):
        pass

    def save_scenario(self):
        pass

    def load_scenario(self):
        pass

    def load_state(self,wanted_state):
        pass

    def receive_message(self,msg):
        log = logging.getLogger(__name__)
        if msg.startswith("subject"):
            subj = msg.split()[1]
            if subj in self.__valid_ids:
                self.ui.subject_edit.setText(subj)
                log.info("Changing to subj %s"%subj)
                self.update_fmri_data_view()

    def change_sample(self,new_sample):
        log = logging.getLogger(__name__)
        log.info("*sample changed*")
        self.__valid_ids={"%s" for s in new_sample}
        logger = logging.getLogger(__name__)
        logger.info("new sample: %s" % new_sample)
        self.ui.subj_completer = QtGui.QCompleter(list(self.__valid_ids))
        self.ui.subject_edit.setCompleter(self.ui.subj_completer)
        self.ui.subj_validator = ListValidator(self.__valid_ids)
        self.ui.subject_edit.setValidator(self.ui.subj_validator)

    def select_sample(self):
        dialog = SampleLoadDialog()
        res = dialog.exec_()
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            self.change_sample(new_sample)


def run():
    import sys
    from braviz.utilities import configure_logger,configure_console_logger
    configure_console_logger("fmri")
    args = sys.argv
    scenario = None
    server_broadcast_address = None
    server_receive_address = None
    if len(args)>1:
        scenario = int(args[1])
        if len(args)>2:
            server_broadcast_address = args[2]
            if len(args)>3:
                server_receive_address = args[3]
    qt_args = args[4:]
    app = QtGui.QApplication(qt_args)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = FmriExplorer(scenario,server_broadcast_address,server_receive_address)
    main_window.show()
    main_window.start()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    run()
