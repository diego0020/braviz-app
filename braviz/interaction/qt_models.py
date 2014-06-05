__author__ = 'Diego'
from collections import namedtuple
import logging

import pandas as pd
import PyQt4.QtCore as QtCore
from PyQt4.QtCore import QAbstractListModel
from PyQt4.QtCore import QAbstractTableModel, QAbstractItemModel

import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data
from braviz.readAndFilter import bundles_db
from braviz.interaction.r_functions import calculate_ginni_index
from braviz.interaction.qt_structures_model import StructureTreeModel


class VarListModel(QAbstractListModel):
    CheckedChanged = QtCore.pyqtSignal(list)
    def __init__(self, outcome_var=None, parent=None, checkeable=False):
        QAbstractListModel.__init__(self, parent)
        self.internal_data = []
        self.header = "Variable"
        self.update_list()
        self.outcome = outcome_var
        self.checkeable = checkeable
        self.checked_set = None
        if checkeable:
            self.checked_set = set()


    def update_list(self):
        panda_data = braviz_tab_data.get_variables()
        self.internal_data = list(panda_data["var_name"])
        self.modelReset.emit()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.internal_data)

    def data(self, QModelIndex, int_role=None):
        idx = QModelIndex.row()
        if 0 <= idx < len(self.internal_data):
            if int_role == QtCore.Qt.DisplayRole:
                return self.internal_data[idx]
            elif (self.checkeable is True) and (int_role == QtCore.Qt.CheckStateRole):
                if self.internal_data[idx] in self.checked_set:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
            elif int_role == QtCore.Qt.ToolTipRole:
                name = self.internal_data[idx]
                desc = braviz_tab_data.get_var_description_by_name(name)
                return desc
        else:
            return QtCore.QVariant()

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if int_role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        if Qt_Orientation == QtCore.Qt.Horizontal and p_int == 0:
            return self.header
        else:
            return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        self.internal_data.sort(reverse=reverse)
        self.modelReset.emit()

    def flags(self, QModelIndex):
        idx = QModelIndex.row()
        if (QModelIndex.column() == 0) and (0 <= idx < len(self.internal_data)):
            flag = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            if self.checkeable is True:
                flag |= QtCore.Qt.ItemIsUserCheckable
            return flag

        else:
            return QtCore.Qt.NoItemFlags

    def setData(self, QModelIndex, QVariant, int_role=None):
        if not int_role == QtCore.Qt.CheckStateRole:
            return False
        else:
            idx = QModelIndex.row()
            if QVariant.toBool() is True:
                self.checked_set.add(self.internal_data[idx])
            else:
                self.checked_set.remove(self.internal_data[idx])
            self.CheckedChanged.emit(sorted(self.checked_set))
            return True


    def select_items_by_name(self, items_list):
        for i in items_list:
            self.checked_set.add(i)

    def select_items(self, items_list):
        for i in items_list:
            name = braviz_tab_data.get_var_name(i)
            self.checked_set.add(name)


class VarAndGiniModel(QAbstractTableModel):
    def __init__(self, outcome_var=None, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.data_frame = braviz_tab_data.get_variables()
        #self.data_frame["var_idx"]=self.data_frame.index
        self.data_frame["Ginni"] = "?"
        self.ginni_calculated = False
        self.outcome = outcome_var

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.data_frame)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        col = QModelIndex.column()
        if 0 <= line < len(self.data_frame):
            if col == 0:
                if int_role == QtCore.Qt.DisplayRole:
                    return self.data_frame.iloc[line, 0]
                elif int_role == QtCore.Qt.ToolTipRole:
                    return braviz_tab_data.get_var_description(self.data_frame.index[line])
            elif col == 1:
                if int_role == QtCore.Qt.DisplayRole:
                    return str(self.data_frame.iloc[line, 1])
        return QtCore.QVariant()

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if int_role == QtCore.Qt.DisplayRole:
            if p_int == 0:
                return "Variable"
            elif p_int == 1:
                return "Importance"
        elif int_role == QtCore.Qt.ToolTipRole:
            if p_int == 0:
                return "Variable name"
            elif p_int == 1:
                return "This measure is calculated as how effective each variable is at predicting the outcome"
        else:
            return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        if p_int == 0:
            self.data_frame.sort("var_name", ascending=reverse, inplace=True)
        elif p_int == 1:
            if self.ginni_calculated is False:
                self.calculate_gini_indexes()
                self.ginni_calculated = True
            self.data_frame.sort("Ginni", ascending=reverse, inplace=True)
        self.modelReset.emit()

    def calculate_gini_indexes(self):
        #get outcome var:
        if self.outcome is None:
            log = logging.getLogger(__name__)
            log.error("An outcome var is required for this")
            return
        self.data_frame = calculate_ginni_index(self.outcome, self.data_frame)


class AnovaRegressorsModel(QAbstractTableModel):
    def __init__(self, regressors_list=tuple(), parent=None):
        QAbstractTableModel.__init__(self, parent)
        if len(regressors_list) > 0:
            initial_data = ( (r, self.get_degrees_of_freedom(r), 0) for r in regressors_list )
        else:
            initial_data = None
        self.data_frame = pd.DataFrame(initial_data, columns=["variable", "DF", "Interaction"])
        self.display_view = self.data_frame
        self.__show_interactions = True
        self.__show_regressors = True
        self.__interactors_dict = dict()
        self.__next_index = len(regressors_list)


    def reset_data(self, regressors_list):
        if len(regressors_list) > 0:
            initial_data = ( (r, self.get_degrees_of_freedom(r), 0) for r in regressors_list )
        else:
            initial_data = None
        self.data_frame = pd.DataFrame(initial_data, columns=["variable", "DF", "Interaction"])
        self.display_view = self.data_frame
        self.__show_interactions = True
        self.__show_regressors = True
        self.__interactors_dict = dict()
        self.__next_index = len(regressors_list)
        self.modelReset.emit()

    def update_display_view(self):
        if self.__show_interactions and self.__show_regressors:
            self.display_view = self.data_frame
        else:
            if self.__show_interactions is True:
                self.display_view = self.data_frame[self.data_frame["Interaction"] == 1]
            else:
                self.display_view = self.data_frame[self.data_frame["Interaction"] == 0]


    def show_interactions(self, value=True):
        self.__show_interactions = value
        self.update_display_view()
        self.modelReset.emit()

    def show_regressors(self, value=True):
        self.__show_regressors = value
        self.update_display_view()
        self.modelReset.emit()


    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.display_view)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()

        if int_role == QtCore.Qt.DisplayRole:
            if p_int == 0:
                return "Variable"
            elif p_int == 1:
                return "DF"
        elif int_role == QtCore.Qt.ToolTipRole and p_int == 1:
            return "Degrees of freedom"
        else:
            return QtCore.QVariant()

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        col = QModelIndex.column()

        if 0 <= line < self.rowCount():
            if col == 0:
                if int_role == QtCore.Qt.DisplayRole:
                    return self.display_view["variable"].iloc[line]
                elif int_role == QtCore.Qt.ToolTipRole:
                    name = self.display_view["variable"].iloc[line]
                    return braviz_tab_data.get_var_description_by_name(name)
            elif col == 1:
                if int_role == QtCore.Qt.DisplayRole:
                    return str(self.display_view["DF"].iloc[line])
        return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        #We will be using type2 or type3 Sums of Squares, and therefore order is not important
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        if p_int == 0:
            self.data_frame.sort("variable", ascending=reverse, inplace=True)
        elif p_int == 1:
            self.data_frame.sort("DF", ascending=reverse, inplace=True)
        self.update_display_view()
        self.modelReset.emit()

    def add_regressor(self, var_name):

        if var_name in self.data_frame["variable"].values:
            #ignore duplicates
            return

        self.beginInsertRows(QtCore.QModelIndex(), len(self.data_frame), len(self.data_frame))
        self.data_frame = self.data_frame.append(pd.DataFrame([(var_name, self.get_degrees_of_freedom(var_name), 0 )],
                                                              columns=["variable", "DF", "Interaction"],
                                                              index=(self.__next_index,)
        ))
        self.__next_index += 1
        self.endInsertRows()
        self.update_display_view()

    def removeRows(self, row, count, QModelIndex_parent=None, *args, **kwargs):
        #self.layoutAboutToBeChanged.emit()
        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)
        indexes = list(self.data_frame.index)
        for i in xrange(count):
            r=indexes.pop(row)
            #print r
            if r in self.__interactors_dict:
                del self.__interactors_dict[r]
        if len(indexes) == 0:
            self.data_frame = pd.DataFrame(columns=["variable", "DF", "Interaction"])
        else:
            log = logging.getLogger(__name__)
            log.debug(self.data_frame)
            log.debug(indexes)
            self.data_frame = self.data_frame.loc[indexes]

        self.remove_invalid_interactions()
        self.update_display_view()
        self.endRemoveRows()
        self.modelReset.emit()


    def get_degrees_of_freedom(self, var_name):
        is_real = braviz_tab_data.is_variable_name_real(var_name)
        if is_real is None or is_real == 1:
            return 1
        labels = braviz_tab_data.get_names_label_dict(var_name)
        return len(labels) - 1

    def get_regressors(self):
        regs_col = self.data_frame["variable"][self.data_frame["Interaction"] == 0]
        return regs_col.get_values()

    def get_interactions(self):
        regs_col = self.data_frame["variable"][self.data_frame["Interaction"] == 1]
        return regs_col.get_values()


    def add_interactor(self, factor_rw_indexes):
        #The indexes should be taken from a view showing only the factors in the same order as present model
        factors_data_frame = self.data_frame[self.data_frame["Interaction"] == 0]
        factor_indexes = [factors_data_frame.index[i] for i in factor_rw_indexes]
        if len(factor_indexes) < 2:
            #can't add interaction with just one factor
            return

        #check if already added:
        if frozenset(factor_indexes) in self.__interactors_dict.values():
            log = logging.getLogger(__name__)
            log.warning("Trying to add duplicated interaction")
            return

        #get var_names
        factor_names = self.data_frame["variable"].loc[factor_indexes]
        self.add_interactor_by_names(factor_names)

    def add_interactor_by_names(self, factor_names):
        df = self.data_frame
        factor_indexes = [df.index[df["variable"] == fn].values[0] for fn in factor_names]
        #create name
        interactor_name = '*'.join(factor_names)
        log = logging.getLogger(__name__)
        log.debug(interactor_name)
        #get degrees of freedom
        interactor_df = self.data_frame["DF"].loc[factor_indexes].prod()
        log.debug(interactor_df)
        #add to dictionary
        interactor_idx = self.__next_index
        self.__next_index += 1
        self.__interactors_dict[interactor_idx] = frozenset(factor_indexes)
        #add to data frame
        self.beginInsertRows(QtCore.QModelIndex(), len(self.data_frame), len(self.data_frame))

        temp_data_frame = pd.DataFrame([(interactor_name, interactor_df, 1)], columns=["variable", "DF", "Interaction"],
                                       index=(interactor_idx,))
        self.data_frame = self.data_frame.append(temp_data_frame)
        self.endInsertRows()
        self.update_display_view()

    def remove_invalid_interactions(self):
        index = frozenset(self.data_frame.index)
        to_remove = []
        for k, v in self.__interactors_dict.iteritems():
            for i in v:
                if i not in index:
                    to_remove.append(k)

        for k in to_remove:
            del self.__interactors_dict[k]
            try:
                self.data_frame.drop(k, inplace=True)
            except ValueError:
                pass
        log = logging.getLogger(__name__)
        log.debug(self.data_frame)
        log.debug(self.__interactors_dict)

    def get_data_frame(self):
        return self.data_frame

    def get_interactors_dict(self):
        return self.__interactors_dict


class NominalVariablesMeta(QAbstractTableModel):
    def __init__(self, var_name, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.var_name = var_name
        self.names_dict = {}
        self.labels_list = []
        self.headers = ("label", "name")
        self.update_model(var_name)
        self.checkeable = False
        self.unchecked = set()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.labels_list)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        col = QModelIndex.column()
        if 0 <= line < len(self.labels_list):
            if col == 0:
                if (int_role == QtCore.Qt.DisplayRole) or (int_role == QtCore.Qt.EditRole):
                    return self.labels_list[line]
                if self.checkeable and (int_role == QtCore.Qt.CheckStateRole):
                    checked = not (self.labels_list[line] in self.unchecked)
                    return QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
            elif col == 1:
                if (int_role == QtCore.Qt.DisplayRole) or (int_role == QtCore.Qt.EditRole):
                    return self.names_dict.get(self.labels_list[line], "")
            else:
                return QtCore.QVariant()
        return QtCore.QVariant()

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if int_role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if p_int == 0:
                return "Label"
            elif p_int == 1:
                return "Name"
        else:
            return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        self.labels_list.sort(reverse=reverse)
        self.modelReset.emit()

    def setData(self, QModelIndex, QVariant, int_role=None):
        row = QModelIndex.row()
        col = QModelIndex.column()
        if (int_role == QtCore.Qt.EditRole) and (col == 1 and 0 <= row < self.rowCount()):
            self.names_dict[self.labels_list[row]] = unicode(QVariant.toString())
            self.dataChanged.emit(QModelIndex, QModelIndex)
            return True
        elif (int_role == QtCore.Qt.CheckStateRole) and (col == 0 and 0 <= row < self.rowCount()):
            state = QVariant.toInt()[0]
            label = self.labels_list[row]
            if state == QtCore.Qt.Checked:
                self.unchecked.remove(label)
            elif state == QtCore.Qt.Unchecked:
                self.unchecked.add(label)
            else:
                return False
            self.emit(QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"), QModelIndex, QModelIndex)
            return True
        return False


    def flags(self, QModelIndex):
        row = QModelIndex.row()
        col = QModelIndex.column()
        flags = QtCore.Qt.NoItemFlags
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            flags = flags | QtCore.Qt.ItemIsSelectable
            flags = flags | QtCore.Qt.ItemIsEnabled
            if col == 1:
                flags = flags | QtCore.Qt.ItemIsEditable
            elif col == 0 and (self.checkeable is True):
                flags |= QtCore.Qt.ItemIsUserCheckable
        return flags

    def update_model(self, var_name):
        if self.var_name is None:
            #generic labels
            self.labels_list = range(1, 3)
            self.names_dict = {}
            return
        self.var_name = var_name
        self.names_dict = braviz_tab_data.get_names_label_dict(var_name)
        self.labels_list = list(self.names_dict.iterkeys())

    def save_into_db(self, var_idx=None):
        tuples = ( (k, v) for k, v in self.names_dict.iteritems())
        if self.var_name is not None:
            braviz_tab_data.save_nominal_labels_by_name(self.var_name, tuples)
        else:
            if var_idx is None:
                raise Exception("Var_idx is required")
            braviz_tab_data.save_nominal_labels(var_idx, tuples)

    def add_label(self):
        self.labels_list.append(len(self.labels_list) + 1)
        self.modelReset.emit()

    def set_checkeable(self, checkeable):
        self.checkeable = bool(checkeable)

    def get_unchecked(self):
        return self.unchecked

    def get_checked(self):
        return set(self.labels_list) - self.unchecked


class AnovaResultsModel(QAbstractTableModel):
    def __init__(self, results_df=None, residuals=None, intercept=None, fitted=None):
        if results_df is None:
            self.__df = pd.DataFrame(None, columns=["Factor", "Sum Sq", "Df", "F value", "Pr(>F)"])
        else:
            self.__df = results_df

        self.residuals = residuals
        self.intercept = intercept
        self.fitted = fitted
        super(AnovaResultsModel, self).__init__()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__df)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.__df.shape[1]

    def data(self, QModelIndex, int_role=None):
        if not (int_role == QtCore.Qt.DisplayRole):
            return QtCore.QVariant()
        line = QModelIndex.row()
        col = QModelIndex.column()
        data = self.__df.iloc[line, col]
        if col == 0:
            #names
            return data
        elif col == 2:
            #df
            return "%d" % data
        elif col == 4:
            #p
            return "{:.1e}".format(data)
        else:
            return "{:.3g}".format(data)


    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if int_role == QtCore.Qt.DisplayRole:
            return self.__df.columns[p_int]
        return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        self.__df.sort(self.__df.columns[p_int], ascending=reverse, inplace=True)
        self.modelReset.emit()

    def flags(self, QModelIndex):
        line = QModelIndex.row()
        col = QModelIndex.column()
        result = QtCore.Qt.NoItemFlags
        if 0 <= line <= self.rowCount() and 0 <= line <= self.rowCount():
            result |= QtCore.Qt.ItemIsSelectable
            result |= QtCore.Qt.ItemIsEnabled
        return result


class DataFrameModel(QAbstractTableModel):
    """
    This model is used for displaying data frames in a QT table view
    """
    def __init__(self, data_frame, columns=None,string_columns=tuple()):
        if not isinstance(data_frame,pd.DataFrame):
            raise ValueError("A pandas data frame is required")
        if columns is None:
            columns = data_frame.columns
        self.__df = data_frame
        self.__cols = columns
        self.__string_cols = frozenset(string_columns)
        super(DataFrameModel, self).__init__()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__df)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__cols)+1

    def data(self, QModelIndex, int_role=None):
        if not (int_role == QtCore.Qt.DisplayRole):
            return QtCore.QVariant()
        line = QModelIndex.row()
        col = QModelIndex.column()
        if col == 0:
            return self.format_data(0, self.__df.index[line] )
        else:
            col_name = self.__cols[col-1]
            data = self.__df[col_name].iloc[line]
            return self.format_data(col,data)

    def format_data(self,col_i,data):
        if col_i in self.__string_cols:
            return unicode(data)
        else:
            return "%.4g"%data
    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if int_role == QtCore.Qt.DisplayRole:
            if p_int == 0:
                return unicode(self.__df.index.name)
            else:
                return self.__cols[p_int-1]
        return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        if p_int == 0:
            i_name = self.__df.index.name
            i_l = list(self.__df.index)
            i_l.sort(reverse=reverse)
            self.__df=self.__df.loc[i_l].copy()
            self.__df.index.name = i_name
        else:
            self.__df.sort(self.__df.columns[p_int-1], ascending=reverse, inplace=True)
        self.modelReset.emit()

    def flags(self, QModelIndex):
        line = QModelIndex.row()
        # col = QModelIndex.column()
        result = QtCore.Qt.NoItemFlags
        if 0 <= line <= self.rowCount() and 0 <= line <= self.rowCount():
            result |= QtCore.Qt.ItemIsSelectable
            result |= QtCore.Qt.ItemIsEnabled
        return result
    def set_df(self,new_df):
        self.__df = new_df.copy()
        self.modelReset.emit()

class SampleTree(QAbstractItemModel):
    def __init__(self, columns=None):
        super(SampleTree, self).__init__()
        if columns is None:
            columns = ["lat", "UBIC3", "GENERO"]
        self.data_aspects = columns
        self.__headers = {0: "Attribute", 1: "N"}
        self.__data_frame = braviz_tab_data.get_data_frame_by_name(columns)
        self.item_tuple = namedtuple("item_tuple", ["nid", "row", "label", "count", "parent", "children"])
        self.__tree_list = []
        self.__id_index = {}
        self.__next_id = 0
        self.populate_tree_dicts()

    def set_sample(self, new_sample):
        self.__data_frame = braviz_tab_data.get_data_frame_by_name(self.data_aspects)
        self.__data_frame = self.__data_frame.loc[sorted(new_sample)]
        self.__tree_list = []
        self.__id_index = {}
        self.__next_id = 0
        self.populate_tree_dicts()
        self.modelReset.emit()

    def __get_next_id(self):
        iid = self.__next_id
        self.__next_id += 1
        return iid

    def populate_tree_dicts(self):
        #All
        iid = self.__get_next_id()
        children = self.__data_frame.index
        parent_id = iid
        children_list = []
        for r, c in enumerate(children):
            iid = self.__get_next_id()
            c_item = self.item_tuple(nid=iid, row=r, label=str(c), count=1, parent=parent_id, children=None)
            self.__id_index[iid] = c_item
            children_list.append(c_item)
        all_item = self.item_tuple(nid=parent_id, row=0, label="All", count=len(self.__data_frame), parent=None,
                                   children=children_list)
        self.__tree_list.append(all_item)
        self.__id_index[parent_id] = all_item


        #Other aspectes
        for r, aspect in enumerate(self.data_aspects):
            aspect_id = self.__get_next_id()
            children = self.populate_aspect(aspect, aspect_id)
            new_item = self.item_tuple(nid=aspect_id, row=r + 1, label=aspect, count=len(self.__data_frame),
                                       parent=None, children=children)
            self.__tree_list.append(new_item)
            self.__id_index[aspect_id] = new_item

        #check index integrity
        for i in xrange(self.__next_id):
            assert self.__id_index.has_key(i)

    def populate_aspect(self, var_name, aspect_id):
        #get labels
        conn = braviz_tab_data.get_connection()
        cur = conn.execute("SELECT label,name FROM nom_meta NATURAL JOIN variables WHERE var_name=?",
                           (var_name,))
        labels_list = []
        for i, (label, name) in enumerate(cur.fetchall()):
            lab_id = self.__get_next_id()
            children = self.__data_frame[self.__data_frame[var_name] == label].index
            children_list = []
            for r, c in enumerate(children):
                c_id = self.__get_next_id()
                c_item = self.item_tuple(nid=c_id, row=r, label=str(c), count=1, parent=lab_id, children=None)
                children_list.append(c_item)
                self.__id_index[c_id] = c_item
            lab_item = self.item_tuple(nid=lab_id, row=i, label=name, count=len(children_list), parent=aspect_id,
                                       children=children_list)
            labels_list.append(lab_item)
            self.__id_index[lab_id] = lab_item
        return labels_list


    def parent(self, QModelIndex=None):
        if not QModelIndex.isValid():
            return QtCore.QModelIndex()
        item_id = QModelIndex.internalId()
        item = self.__id_index[item_id]
        if item.parent is None:
            return QtCore.QModelIndex()
        else:
            parent = self.__id_index[item.parent]
            return self.createIndex(parent.row, 0, parent.nid)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        if not QModelIndex_parent.isValid():
            #print "top_row_count"
            #print len(self.data_aspects)+1
            return len(self.data_aspects) + 1
        nid = QModelIndex_parent.internalId()
        item = self.__id_index[nid]
        if item.children is None:
            return 0
        else:
            return len(item.children)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def data(self, QModelIndex, int_role=None):
        if int_role == QtCore.Qt.DisplayRole:
            col = QModelIndex.column()
            nid = QModelIndex.internalId()
            item = self.__id_index[nid]
            #print item
            #print sid
            if col == 0:
                return item.label
            elif col == 1:
                return item.count

        return QtCore.QVariant()

    def index(self, p_int, p_int_1, QModelIndex_parent, *args, **kwargs):
        if not QModelIndex_parent.isValid():
            #top level
            if p_int >= len(self.data_aspects) + 1 or p_int < 0:
                return QtCore.QModelIndex()
            item = self.__tree_list[p_int]
            nid = item.nid
            out_index = self.createIndex(p_int, p_int_1, nid)
            assert out_index.isValid()
            return out_index
        else:
            parent_id = QModelIndex_parent.internalId()
            parent_item = self.__id_index[parent_id]
            childrens = parent_item.children
            if childrens is None:
                return QtCore.QModelIndex()
            else:
                nid = childrens[p_int].nid
                out_index = self.createIndex(p_int, p_int_1, nid)
            assert out_index.isValid()
            return out_index


    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal and int_role == QtCore.Qt.DisplayRole:
            self.__headers.get(p_int, QtCore.QVariant())
            return self.__headers.get(p_int, QtCore.QVariant())
        return QtCore.QVariant()

    def hasChildren(self, QModelIndex_parent=None, *args, **kwargs):
        if not QModelIndex_parent.isValid():
            #top level has children
            return True
        parent_item = self.__id_index[QModelIndex_parent.internalId()]
        #print "has children"
        #print parent_item
        if parent_item.children is None:
            return False
        else:
            return True

    def get_leafs(self, QModelIndex):
        iid = QModelIndex.internalId()
        item = self.__id_index[iid]
        return self.__get_leafs(item)

    def __get_leafs(self, item):
        if item.children is None:
            return [item.label]
        else:
            leafs = []
            for c in item.children:
                leafs.extend(self.__get_leafs(c))
            return leafs


class SubjectsTable(QAbstractTableModel):
    def __init__(self, initial_columns=None, sample=None):
        QAbstractTableModel.__init__(self)
        if initial_columns is None:
            initial_columns = tuple()
        self.__df = None
        self.__is_var_real = None
        self.__labels = None
        self.__col_indexes = None
        self.sample = sample
        if sample is None:
            self.sample = braviz_tab_data.get_subjects()
        self.set_var_columns(initial_columns)


    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.__df.shape[0]

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.__df.shape[1]

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if not (int_role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole)):
            return QtCore.QVariant()
        if Qt_Orientation == QtCore.Qt.Vertical:
            return QtCore.QVariant()
        elif 0 <= p_int < self.__df.shape[1]:
            return self.__df.columns[p_int]
        else:
            return QtCore.QVariant()

    def data(self, QModelIndex, int_role=None):
        if not (int_role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole)):
            return QtCore.QVariant()
        line = QModelIndex.row()
        col = QModelIndex.column()
        if (0 <= line < len(self.__df)) and (0 <= col < self.__df.shape[1]):
            datum = self.__df.iloc[line, col]
            if col == 0:
                return "%d" % int(datum)
            else:
                if self.__is_var_real[col]:
                    return str(datum)
                else:
                    return self.__labels[col][int(datum)]

        else:
            return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = False
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = True
        self.__df.sort(self.__df.columns[p_int], ascending=reverse, inplace=True)
        self.modelReset.emit()

    def set_var_columns(self, columns):
        self.__col_indexes = columns
        vars_df = braviz_tab_data.get_data_frame_by_index(columns)
        codes_df = pd.DataFrame(vars_df.index.get_values(), index=vars_df.index, columns=("Code",))
        self.__df = codes_df.join(vars_df)
        self.__df = self.__df.loc[self.sample]
        is_var_code_real = braviz_tab_data.are_variables_real(columns)
        #we want to use the column number as index
        self.__is_var_real = dict((i + 1, is_var_code_real[idx]) for i, idx in enumerate(columns))
        self.__labels = {}
        for i, is_real in self.__is_var_real.iteritems():
            if not is_real:
                #column 0 is reserved for the Code
                self.__labels[i] = braviz_tab_data.get_labels_dict(columns[i - 1])
        self.modelReset.emit()

    def set_sample(self, new_sample):
        self.sample = new_sample
        self.set_var_columns(self.__col_indexes)


    def get_current_columns(self):
        return self.__df.columns[1:]

    def get_current_column_indexes(self):
        return self.__col_indexes

    def get_subject_index(self, subj_id):
        row = self.__df.index.get_loc(int(subj_id))
        return row


class ContextVariablesModel(QAbstractTableModel):
    def __init__(self, context_vars_list=None, parent=None, editable_dict=None):
        QAbstractTableModel.__init__(self, parent)
        self.data_type_dict = dict()
        self.conn = braviz_tab_data.get_connection()
        if context_vars_list is not None:
            self.data_frame = pd.DataFrame(
                [(braviz_tab_data.get_var_name(idx), self.get_type(idx)) for idx in context_vars_list],
                columns=["variable", "Type"], index=context_vars_list)
        else:
            self.data_frame = pd.DataFrame(tuple(), columns=["variable", "Type"])

        self.editables_dict = editable_dict
        if self.editables_dict is None:
            self.editables_dict = dict((idx, False) for idx in context_vars_list)
        self.headers_dict = {0: "Variable", 1: "Type", 2: "Editable"}


    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.data_frame)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 3

    def headerData(self, p_int, Qt_Orientation, int_role=None):

        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if int_role == QtCore.Qt.DisplayRole:
            return self.headers_dict.get(p_int, QtCore.QVariant())
        return QtCore.QVariant()

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        col = QModelIndex.column()
        if (int_role == QtCore.Qt.CheckStateRole) and (col == 2):
            var_idx = self.data_frame.index[line]
            if self.editables_dict.get(var_idx) is True:
                return QtCore.Qt.Checked
            else:
                return QtCore.Qt.Unchecked
        if (int_role == QtCore.Qt.ToolTipRole) and (col == 0):
            var_idx = self.data_frame.index[line]
            return braviz_tab_data.get_var_description(var_idx)

        if not (int_role == QtCore.Qt.DisplayRole):
            return QtCore.QVariant()

        if (0 <= line < self.rowCount()) and (0 <= col < 2):
            return self.data_frame.iloc[line, col]
        else:
            return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        #We will be using type2 or type3 Sums of Squares, and therefore order is not important
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        if p_int == 0:
            self.data_frame.sort("variable", ascending=reverse, inplace=True)
        elif p_int == 1:
            self.data_frame.sort("Type", ascending=reverse, inplace=True)
        self.modelReset.emit()

    def get_type(self, var_idx):
        data_type = self.data_type_dict.get(var_idx)
        if data_type is None:
            if braviz_tab_data.is_variable_nominal(var_idx):
                data_type = "Nominal"
            else:
                data_type = "Real"
            self.data_type_dict[var_idx] = data_type
        return data_type

    def add_variable(self, var_idx):
        if var_idx in self.data_frame.index:
            #ignore duplicates
            return

        self.beginInsertRows(QtCore.QModelIndex(), len(self.data_frame), len(self.data_frame))
        self.data_frame = self.data_frame.append(
            pd.DataFrame([(braviz_tab_data.get_var_name(var_idx), self.get_type(var_idx))],
                         columns=["variable", "Type"],
                         index=(var_idx,)))
        self.endInsertRows()
        self.editables_dict[var_idx] = False


    def removeRows(self, row, count, QModelIndex_parent=None, *args, **kwargs):
        #self.layoutAboutToBeChanged.emit()
        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)
        indexes = list(self.data_frame.index)
        for i in xrange(count):
            var_idx = indexes[row + i]
            del self.editables_dict[var_idx]
            self.data_frame.drop(var_idx, inplace=True)
        self.endRemoveRows()
        self.modelReset.emit()

    def setData(self, QModelIndex, QVariant, int_role=None):
        if not int_role == QtCore.Qt.CheckStateRole:
            return False
        else:
            row = QModelIndex.row()
            if QModelIndex.column() != 2:
                return False
            self.editables_dict[self.data_frame.index[row]] = QVariant.toBool()
            return True

    def flags(self, QModelIndex):
        row = QModelIndex.row()
        if (0 <= QModelIndex.column() <= 2) and (0 <= row < len(self.data_frame)):
            flag = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            if QModelIndex.column() == 2:
                flag |= QtCore.Qt.ItemIsUserCheckable
            return flag

        else:
            return QtCore.Qt.NoItemFlags

    def get_variables(self):
        return self.data_frame.index.tolist()


class SubjectDetails(QAbstractTableModel):
    def __init__(self, initial_vars=None, initial_subject=None):
        QAbstractTableModel.__init__(self)
        if initial_vars is None:
            initial_vars = tuple()
        self.__df = None
        self.__is_var_real = None
        self.__normal_ranges = None
        self.__current_subject = initial_subject
        self.set_variables(initial_vars)
        self.headers = ("Variable", "Value")


    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.__df.shape[0]

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if not (int_role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole)):
            return QtCore.QVariant()
        if Qt_Orientation == QtCore.Qt.Vertical:
            return QtCore.QVariant()
        elif 0 <= p_int < len(self.headers):
            name = self.headers[p_int]
            desc = braviz_tab_data.get_var_description_by_name(name)
            return "\n".join((name, desc))
        else:
            return QtCore.QVariant()

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        col = QModelIndex.column()
        if int_role == QtCore.Qt.ToolTipRole:
            var_idx = self.__df.index[line]
            desc = braviz_tab_data.get_var_description(var_idx)
            return desc
        if not int_role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        if (0 <= line < len(self.__df)) and (0 <= col < self.__df.shape[1]):
            datum = self.__df.iloc[line, col]
            var_idx = self.__df.index[line]
            if self.__is_var_real[var_idx] and col == 1:
                a, b = self.__normal_ranges[var_idx]
                message = "%s\t(%s - %s)" % (datum, a, b)
                if not (a <= datum <= b):
                    message = "* " + message
                return message
            return unicode(datum)
        else:
            return QtCore.QVariant()

    def set_variables(self, variable_ids):
        vars_df = braviz_tab_data.get_subject_variables(self.__current_subject, variable_ids)
        self.__df = vars_df
        self.__is_var_real = braviz_tab_data.are_variables_real(variable_ids)
        self.__normal_ranges = dict((int(idx), braviz_tab_data.get_variable_normal_range(int(idx)))
                                    for idx in variable_ids if self.__is_var_real[int(idx)])

        self.modelReset.emit()

    def change_subject(self, new_subject):
        self.__current_subject = new_subject
        self.set_variables(self.__df.index)

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def flags(self, QModelIndex):
        idx = QModelIndex.row()
        if (0 <= QModelIndex.column() < 2) and (0 <= idx < len(self.__df)):
            flag = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            flag |= QtCore.Qt.ItemIsDragEnabled
            return flag

        else:
            return QtCore.Qt.ItemIsDropEnabled

    def dropMimeData(self, QMimeData, Qt_DropAction, p_int, p_int_1, QModelIndex):
        row = p_int
        if Qt_DropAction != QtCore.Qt.MoveAction:
            return False
        #only accept drops between lines
        if QModelIndex.isValid():
            return False
        data_stream = QtCore.QDataStream(QMimeData.data("application/x-qabstractitemmodeldatalist"))
        source_row = data_stream.readInt()
        #print "Moving from %d to %d"%(source_row,row)
        index_list = list(self.__df.index)
        source_id = index_list.pop(source_row)
        index_list.insert(row, source_id)
        self.__df = self.__df.loc[index_list]
        self.modelReset.emit()
        return True

    def get_current_variables(self):
        return self.__df.index


class NewVariableValues(QAbstractTableModel):
    def __init__(self):
        super(NewVariableValues, self).__init__()
        self.subjects_list = braviz_tab_data.get_subjects()
        self.values_dict = {}

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.subjects_list)

    def data(self, QModelIndex, int_role=None):
        if int_role == QtCore.Qt.DisplayRole:
            row = QModelIndex.row()
            col = QModelIndex.column()
            if col == 0:
                return self.subjects_list[row]
            elif col == 1:
                return self.values_dict.get(self.subjects_list[row], "")
        return QtCore.QVariant()

    def flags(self, QModelIndex):
        row = QModelIndex.row()
        col = QModelIndex.column()
        if 0 <= row < len(self.subjects_list):
            if 0 <= col < 2:
                flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
                if col == 1:
                    flags |= QtCore.Qt.ItemIsEditable
                return flags
        return QtCore.Qt.NoItemFlags


    def setData(self, QModelIndex, QVariant, int_role=None):
        row = QModelIndex.row()
        col = QModelIndex.column()
        if int_role != QtCore.Qt.EditRole:
            return False
        if col != 1 or row < 0 or row >= self.rowCount():
            return False
        try:
            self.values_dict[self.subjects_list[row]] = float(QVariant.toString())
        except ValueError:
            return False
        self.dataChanged.emit(QModelIndex, QModelIndex)
        return True

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if (Qt_Orientation == QtCore.Qt.Horizontal) and (int_role == QtCore.Qt.DisplayRole):
            if p_int == 0:
                return "Subject"
            elif p_int == 1:
                return "Value"
        return QtCore.QVariant()

    def save_into_db(self, var_idx):
        value_tuples = ((s, self.values_dict.get(s, "nan")) for s in self.subjects_list)
        braviz_tab_data.update_variable_values(var_idx, value_tuples)


class SimpleBundlesList(QAbstractListModel):
    def __init__(self):
        super(SimpleBundlesList, self).__init__()
        self.id_list = None
        self.names_list = None
        self.__showing_special = False
        self.restart_structures()


    def restart_structures(self):
        self.id_list = []
        self.names_list = []
        self.id_list.append(None)
        self.names_list.append("<From Segment>")

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        if self.__showing_special:
            return len(self.names_list)
        else:
            return len(self.names_list) - 1

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if 0 <= row < len(self.names_list):
                if int_role == QtCore.Qt.DisplayRole:
                    return self.names_list[row]
                if int_role == QtCore.Qt.UserRole:
                    return self.id_list[row]
        return QtCore.QVariant()

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        return QtCore.QVariant()

    def add_bundle(self, bundle_id, name):
        if bundle_id in self.id_list:
            return
        self.id_list.insert(len(self.id_list) - 1, bundle_id)
        self.names_list.insert(len(self.names_list) - 1, name)

    def get_bundle_name(self, bid):
        try:
            idx = self.id_list.index(bid)
        except ValueError:
            return "<Invalid>"
        return self.names_list[idx]

    def set_show_special(self, show_special):
        self.__showing_special = show_special
        self.modelReset.emit()

    def get_ids(self):
        return self.id_list[:-1]

    def set_ids(self, id_list, names_dict=None):
        self.restart_structures()
        if names_dict is None:
            names_dict = dict(bundles_db.get_bundle_ids_and_names())
        for b in id_list:
            self.add_bundle(b, names_dict[b])
        self.modelReset.emit()


class BundlesSelectionList(QAbstractListModel):
    def __init__(self):
        super(BundlesSelectionList, self).__init__()
        self.id_list = []
        self.names_dict = {}
        self._selected = {}
        self.refresh_model()

    def refresh_model(self):
        tuples = bundles_db.get_bundle_ids_and_names()
        self.names_dict = dict(tuples)
        self.id_list = sorted(self.names_dict.keys())

    def select_many_ids(self, ids_it):
        for i in ids_it:
            self._selected[i] = True

    def get_selected(self):
        return (i for i, k in self._selected.iteritems() if k is True)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.id_list)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if 0 <= row < len(self.id_list):
                bid = self.id_list[row]
                if int_role == QtCore.Qt.DisplayRole:
                    return self.names_dict[bid]
                if int_role == QtCore.Qt.CheckStateRole:
                    if self._selected.get(bid, False) is True:
                        return QtCore.Qt.Checked
                    else:
                        return QtCore.Qt.Unchecked

        return QtCore.QVariant()

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        return QtCore.QVariant()

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if 0 <= row < len(self.id_list):
                flag = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable
                return flag
        return QtCore.Qt.NoItemFlags

    def setData(self, QModelIndex, QVariant, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if int_role == QtCore.Qt.CheckStateRole:
                if 0 <= row < len(self.id_list):
                    value = QVariant.toBool()
                    bid = self.id_list[row]
                    self._selected[bid] = value
                    return True
        return False


class ScenariosTableModel(QAbstractTableModel):
    def __init__(self, app_name):
        super(ScenariosTableModel, self).__init__()
        self.df = braviz_user_data.get_scenarios_data_frame(app_name)
        self.headers = ("Date", "Name", "Description")
        self.columns = ("scn_date", "scn_name", "scn_desc")


    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if 0 <= p_int < self.df.shape[1]:
                if int_role == QtCore.Qt.DisplayRole:
                    return self.headers[p_int]
        return QtCore.QVariant()

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            col = QModelIndex.column()
            if (0 <= col < self.columnCount()) and (0 <= row < self.rowCount()):
                if (int_role == QtCore.Qt.DisplayRole) or (int_role == QtCore.Qt.ToolTipRole):
                    return str(self.df[self.columns[col]].iloc[row])
                elif int_role == QtCore.Qt.UserRole:
                    return self.df.index[row]
        return QtCore.QVariant()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.df.shape[0]

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.df.shape[1]

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        self.df.sort(self.columns[p_int], ascending=reverse, inplace=True)
        self.modelReset.emit()

    def get_index(self, row):
        return self.df.index[row]


class SimpleSetModel(QAbstractListModel):
    def __init__(self):
        super(SimpleSetModel, self).__init__()
        self.__internal_list = []

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__internal_list)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if 0 <= row < len(self.__internal_list):
                if int_role == QtCore.Qt.DisplayRole:
                    return str(self.__internal_list[row])
        return QtCore.QVariant()

    def get_elements(self):
        return set(self.__internal_list)

    def set_elements(self, set):
        self.__internal_list = sorted(list(set))
        self.modelReset.emit()


class SamplesFilterModel(QAbstractListModel):
    def __init__(self):
        super(SamplesFilterModel, self).__init__()
        self.__filters_list = []

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__filters_list)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if 0 <= row < len(self.__filters_list):
                if int_role == QtCore.Qt.DisplayRole:
                    return str(self.__filters_list[row][0])
        return QtCore.QVariant()

    def add_filter(self, filter_name, filter_func):
        new_row = len(self.__filters_list)
        self.beginInsertRows(QtCore.QModelIndex(), new_row, new_row)
        self.__filters_list.append((filter_name, filter_func))
        self.endInsertRows()


    def apply_filters(self, input_set):
        output_set = input_set
        for _, f in self.__filters_list:
            output_set = filter(f, output_set)
        return output_set

    def remove_filter(self, index):
        row = index.row()
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.__filters_list.pop(row)
        self.endRemoveRows()


class SamplesSelectionModel(QAbstractTableModel):
    def __init__(self):
        super(SamplesSelectionModel, self).__init__()
        self.data_frame = braviz_user_data.get_samples_df()
        self.columns = ("sample_size", "sample_name", "sample_desc")
        self.headers = ("Size", "Name", "Description")


    def reload(self):
        self.data_frame = braviz_user_data.get_samples_df()
        self.modelReset.emit()

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            col = QModelIndex.column()
            if int_role == QtCore.Qt.DisplayRole or int_role == QtCore.Qt.ToolTipRole:
                return str(self.data_frame[self.columns[col]].iloc[row])
        return QtCore.QVariant()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.data_frame.shape[0]

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.data_frame.shape[1]

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if int_role == QtCore.Qt.DisplayRole:
                return self.headers[p_int]
        return QtCore.QVariant()

    def sort(self, p_int, Qt_SortOrder_order=None):
        sort_col = self.columns[p_int]
        ascending = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            ascending = False
        self.data_frame.sort(columns=sort_col, ascending=ascending, inplace=True)
        self.modelReset.emit()

    def get_sample(self, QModelIndex):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            sample_index = self.data_frame.index[row]
            data = braviz_user_data.get_sample_data(int(sample_index))
            return data

class SubjectChecklist(QAbstractListModel):
    def __init__(self,initial_list=tuple()):
        QAbstractListModel.__init__(self)
        self.__list = list(initial_list)
        self.__checked = set()

    @property
    def checked(self):
        return self.__checked

    @checked.setter
    def checked(self,new_set):
        self.__checked = new_set

    def set_list(self,lst):
        self.__list = list(lst)
        self.modelReset.emit()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__list)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            try:
                name = self.__list[row]
            except IndexError:
                return QtCore.QVariant()
            if int_role == QtCore.Qt.DisplayRole:
                return name
            if int_role == QtCore.Qt.CheckStateRole:
                if name in self.checked:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
        return QtCore.QVariant()


    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            flags =  QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            return flags
        return QtCore.Qt.NoItemFlags

if __name__ == "__main__":
    import braviz

    reader = braviz.readAndFilter.BravizAutoReader()
    test_tree = StructureTreeModel(reader)