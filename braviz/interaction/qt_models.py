__author__ = 'Diego'
from collections import namedtuple

import pandas as pd
import PyQt4.QtCore as QtCore
from PyQt4.QtCore import QAbstractListModel
from PyQt4.QtCore import QAbstractTableModel, QAbstractItemModel

import braviz.readAndFilter.tabular_data as braviz_tab_data
from braviz.interaction.r_functions import calculate_ginni_index


class VarListModel(QAbstractListModel):
    def __init__(self, outcome_var=None, parent=None,checkeable=False):
        QAbstractListModel.__init__(self, parent)
        self.internal_data = []
        self.header = "Variable"
        self.update_list()
        self.outcome = outcome_var
        self.checkeable=checkeable
        self.checks_dict=None
        if checkeable:
            self.checks_dict={}


    def update_list(self):
        panda_data = braviz_tab_data.get_variables()
        self.internal_data = list(panda_data["var_name"])

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.internal_data)

    def data(self, QModelIndex, int_role=None):
        idx = QModelIndex.row()
        if 0 <= idx < len(self.internal_data):
            if int_role == QtCore.Qt.DisplayRole:
                return self.internal_data[idx]
            elif (self.checkeable is True) and (int_role == QtCore.Qt.CheckStateRole):
                if self.checks_dict.get(self.internal_data[idx], False) is True:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
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
        if (QModelIndex.column()==0) and (0<=idx<len(self.internal_data)):
            flag=QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
            if self.checkeable is True:
                flag |= QtCore.Qt.ItemIsUserCheckable
            return flag

        else:
            return QtCore.Qt.NoItemFlags

    def setData(self, QModelIndex, QVariant, int_role=None):
        if not int_role == QtCore.Qt.CheckStateRole:
            return False
        else:
            idx=QModelIndex.row()
            self.checks_dict[self.internal_data[idx]]=QVariant.toBool()
            return True

    def select_items_by_name(self,items_list):
        for i in items_list:
            self.checks_dict[i]=True

    def select_items(self,items_list):
        for i in items_list:
            name=braviz_tab_data.get_var_name(i)
            self.checks_dict[name]=True

class VarAndGiniModel(QAbstractTableModel):
    def __init__(self, outcome_var=None, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.data_frame = braviz_tab_data.get_variables()
        self.data_frame.index = self.data_frame["var_name"]
        self.data_frame["Ginni"] = "?"
        self.ginni_calculated = False
        self.outcome = outcome_var

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.data_frame)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def data(self, QModelIndex, int_role=None):
        if not (int_role == QtCore.Qt.DisplayRole):
            return QtCore.QVariant()
        line = QModelIndex.row()
        col = QModelIndex.column()
        if 0 <= line < len(self.data_frame):
            if col == 0:
                return self.data_frame["var_name"][line]
            elif col == 1:
                return str(self.data_frame["Ginni"][line])
            else:
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
            print "An outcome var is required for this"
            return
        self.data_frame = calculate_ginni_index(self.outcome, self.data_frame)


class AnovaRegressorsModel(QAbstractTableModel):
    def __init__(self, regressors_list=tuple(), parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.conn = braviz_tab_data.get_connection()
        if len(regressors_list) > 0:
            initial_data = ( (r, self.get_degrees_of_freedom(r), 0) for r in regressors_list )
        else:
            initial_data = None
        self.data_frame = pd.DataFrame(initial_data, columns=["variable", "DF", "Interaction"])
        self.display_view = self.data_frame
        self.__show_interactions = True
        self.__show_regressors = True
        self.__interactors_dict = dict()
        self.__next_index = 0


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
        if not (int_role == QtCore.Qt.DisplayRole):
            return QtCore.QVariant()

        if 0 <= line < self.rowCount():
            if col == 0:
                return self.display_view["variable"].iloc[line]
            elif col == 1:
                return str(self.display_view["DF"].iloc[line])
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
            self.data_frame.sort("DF", ascending=reverse, inplace=True)
        self.update_display_view()
        self.modelReset.emit()

    def add_regressor(self, var_name):
        if (self.data_frame["variable"] == var_name).sum() > 0:
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
            indexes.pop(row)
        if len(indexes) == 0:
            self.data_frame = pd.DataFrame(columns=["variable", "DF", "Interaction"])
        else:
            print self.data_frame
            print indexes
            self.data_frame = self.data_frame.loc[indexes]

        self.remove_invalid_interactions()
        self.update_display_view()
        self.endRemoveRows()
        self.modelReset.emit()


    def get_degrees_of_freedom(self, var_name):
        is_real_cur = self.conn.execute("SELECT is_real FROM variables WHERE var_name = ?", (var_name,))
        is_real = is_real_cur.fetchone()[0]
        if is_real is None or is_real == 1:
            return 1
        query = """SELECT count(*) FROM nom_meta NATURAL JOIN variables WHERE  var_name=?"""
        cur = self.conn.execute(query, (var_name,))
        return cur.fetchone()[0] - 1

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
            print "Trying to add duplicated interaction"
            return

        #get var_names
        factor_names = self.data_frame["variable"].loc[factor_indexes]
        #create name
        interactor_name = '*'.join(factor_names)
        print interactor_name
        #get degrees of freedom
        interactor_df = self.data_frame["DF"].loc[factor_indexes].prod()
        print interactor_df
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
        print self.data_frame
        print self.__interactors_dict

    def get_data_frame(self):
        return self.data_frame

    def get_interactors_dict(self):
        return self.__interactors_dict


class NominalVariablesMeta(QAbstractTableModel):
    def __init__(self, var_name, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.var_name = var_name
        self.conn = braviz_tab_data.get_connection()
        self.names_dict = {}
        self.labels_list = []
        self.headers = ("label", "name")
        self.update_model(var_name)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.names_dict)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def data(self, QModelIndex, int_role=None):
        if not (int_role == QtCore.Qt.DisplayRole or int_role == QtCore.Qt.EditRole):
            return QtCore.QVariant()
        line = QModelIndex.row()
        col = QModelIndex.column()
        if 0 <= line < len(self.labels_list):
            if col == 0:
                return self.labels_list[line]
            elif col == 1:
                return self.names_dict[self.labels_list[line]]
            else:
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
        #print "Data change requested"
        #print int_role
        #print QVariant
        if int_role != QtCore.Qt.EditRole:
            return False
        if col != 1 or row < 0 or row >= self.rowCount():
            return False
        self.names_dict[self.labels_list[row]] = unicode(QVariant.toString())
        self.dataChanged.emit(QModelIndex, QModelIndex)
        return True


    def flags(self, QModelIndex):
        row = QModelIndex.row()
        col = QModelIndex.column()
        flags = QtCore.Qt.NoItemFlags
        if 0 <= row < self.rowCount() and 0 <= col < self.columnCount():
            flags = flags | QtCore.Qt.ItemIsSelectable
            flags = flags | QtCore.Qt.ItemIsEnabled
            if col == 1:
                flags = flags | QtCore.Qt.ItemIsEditable
        return flags

    def update_model(self, var_name):
        #print "*****loading model"
        self.var_name = var_name
        cur = self.conn.cursor()
        #Get labels
        query = """
        SELECT label2, name
        from
        (
        SELECT  distinct value as label2, variables.var_idx as var_idx2
        FROM variables natural join var_values
        WHERE variables.var_name = ?
        ) left outer join
        nom_meta ON (nom_meta.label = label2 and var_idx2 = nom_meta.var_idx)
        ORDER BY label2;
        """
        cur.execute(query, (self.var_name,))
        labels = cur.fetchall()
        self.names_dict = dict(labels)
        self.labels_list = list(self.names_dict.iterkeys())

    def save_into_db(self):
        #print self.names_dict
        query = """INSERT OR REPLACE INTO nom_meta
        VALUES (
        (SELECT var_idx FROM variables WHERE var_name = ?),
        ?, -- label
        ? -- name
        );
        """
        tuples = ( (self.var_name, k, v) for k, v in self.names_dict.iteritems())
        self.conn.executemany(query, tuples)
        self.conn.commit()


class AnovaResultsModel(QAbstractTableModel):
    def __init__(self, results_df=None, residuals=None, intercept=None):
        if results_df is None:
            self.__df = pd.DataFrame(None, columns=["Factor", "Sum Sq", "Df", "F value", "Pr(>F)"])
        else:
            self.__df = results_df

        self.residuals = residuals
        self.intercept = intercept
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
        return str(self.__df.iloc[line, col])

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

    def __get_next_id(self):
        iid = self.__next_id
        self.__next_id += 1
        #print "returning id",
        #print iid
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
    def __init__(self, initial_columns=None):
        QAbstractTableModel.__init__(self)
        if initial_columns is None:
            initial_columns = tuple()
        self.__df = None
        self.__is_var_real=None
        self.__labels=None
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
        if not (int_role in (QtCore.Qt.DisplayRole,QtCore.Qt.ToolTipRole)):
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
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        self.__df.sort(self.__df.columns[p_int], ascending=reverse, inplace=True)
        self.modelReset.emit()

    def set_var_columns(self, columns):
        vars_df = braviz_tab_data.get_data_frame_by_index(columns)
        codes_df = pd.DataFrame(vars_df.index.get_values(), index=vars_df.index, columns=("Code",))
        self.__df = codes_df.join(vars_df)
        is_var_code_real= braviz_tab_data.are_variables_real(columns)
        #we want to use the column number as index
        self.__is_var_real=dict((i+1, is_var_code_real[idx]) for i, idx in enumerate(columns))
        self.__labels={}
        for i,is_real in self.__is_var_real.iteritems():
            if not is_real:
                #column 0 is reserved for the Code
                self.__labels[i] = braviz_tab_data.get_labels_dict(columns[i-1])
        self.modelReset.emit()

class ContextVariablesModel(QAbstractTableModel):
    def __init__(self, context_vars_list=None, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.data_type_dict = dict()
        self.conn = braviz_tab_data.get_connection()
        if context_vars_list is not None:
            self.data_frame = pd.DataFrame(
                [(braviz_tab_data.get_var_name(idx),self.get_type(idx)) for idx in context_vars_list],
                columns=["variable","Type"],index=context_vars_list)
        else:
            self.data_frame = pd.DataFrame(tuple(), columns=["variable","Type"])


        self.headers_dict={0: "Variable", 1: "Type", 2:"Editable"}


    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.data_frame)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 3

    def headerData(self, p_int, Qt_Orientation, int_role=None):

        if Qt_Orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if int_role == QtCore.Qt.DisplayRole:
            return self.headers_dict.get(p_int,QtCore.QVariant())
        return QtCore.QVariant()

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        col = QModelIndex.column()
        if (int_role == QtCore.Qt.CheckStateRole) and (col==2):
            return QtCore.Qt.Unchecked

        if not (int_role == QtCore.Qt.DisplayRole):
            return QtCore.QVariant()

        if (0 <= line < self.rowCount()) and (0<=col<2):
            return self.data_frame.iloc[line,col]
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
        data_type=self.data_type_dict.get(var_idx)
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
        self.data_frame=self.data_frame.append(pd.DataFrame([(braviz_tab_data.get_var_name(var_idx), self.get_type(var_idx) )],
                                                              columns=["variable","Type"],
                                                              index=(var_idx,)))
        self.endInsertRows()


    def removeRows(self, row, count, QModelIndex_parent=None, *args, **kwargs):
        #self.layoutAboutToBeChanged.emit()
        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)
        indexes = list(self.data_frame.index)
        for i in xrange(count):
            self.data_frame.drop(indexes[row+i],inplace=True)
        self.endRemoveRows()
        self.modelReset.emit()

    def get_variables(self):
        return self.data_frame.index.tolist()