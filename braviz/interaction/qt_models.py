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


__author__ = 'Diego'
from collections import namedtuple
import logging

import pandas as pd
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QAbstractListModel
from PyQt4.QtCore import QAbstractTableModel, QAbstractItemModel

import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data
from braviz.readAndFilter import config_file
from braviz.readAndFilter import bundles_db

from braviz.interaction.qt_structures_model import StructureTreeModel
import numpy as np

class VarListModel(QAbstractListModel):

    """
    List of available variables, optionally with checkboxes

    The list can be filtered to include only variables whose name include a certain pattern

    Args:
        parent (QObject) : Qt parent
        checkeable (bool) : If ``True`` the list will be displayed with checkboxes
    """
    CheckedChanged = QtCore.pyqtSignal(list)

    def __init__(self, parent=None, checkeable=False):
        QAbstractListModel.__init__(self, parent)
        self.internal_data = []
        self.header = "Variable"
        self.update_list()
        self.checkeable = checkeable
        self.checked_set = None
        self.highlighted_name = None
        if checkeable:
            self.checked_set = set()

    def update_list(self, mask=None):
        """
        Update the variable list to show variables whose name match a mask

        Args:
            mask (str) : Mask in sql format, the database is configured to be case insensitive. To
                search for variables that include the word ``"age"`` use ``"%age%"``
        """
        panda_data = braviz_tab_data.get_variables(mask=mask)
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
            elif int_role == QtCore.Qt.FontRole:
                name = self.internal_data[idx]
                font = QtGui.QFont()
                if name == self.highlighted_name:
                    font.setBold(font.Bold)
                return font
        else:
            return None

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if int_role != QtCore.Qt.DisplayRole:
            return None
        if Qt_Orientation == QtCore.Qt.Horizontal and p_int == 0:
            return self.header
        else:
            return None

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
            if QVariant == QtCore.Qt.Checked:
                self.checked_set.add(self.internal_data[idx])
            else:
                self.checked_set.remove(self.internal_data[idx])
            self.dataChanged.emit(QModelIndex, QModelIndex)
            self.CheckedChanged.emit(sorted(self.checked_set))
            return True

    def select_items_by_name(self, items_list):
        """
        Add variables to the set of checked items

        This will cause checks to appear in the respective boxes when the view is updated

        Args:
            items_list (list) : List of variable to check
        """
        for i in items_list:
            self.checked_set.add(i)

    def select_items(self, items_list):
        """
        Add checks to variables by id

        This will cause checks to appear in the respective boxes when the view is updated

        Args:
            items_list (list) : List of variable ids to check
        """
        for i in items_list:
            name = braviz_tab_data.get_var_name(i)
            self.checked_set.add(name)

    def set_highlighted(self, highlighted_name=None):
        """
        The highlighted item will appear in bold

        Args:
            highlighted_name (str) : Name of a variable to show in bold, use None
                to don't highlight any variable
        """
        self.highlighted_name = highlighted_name

    def clear_selection(self):
        """
        Removes checks from all variables
        """
        self.checked_set.clear()
        self.dataChanged.emit(self.index(0), self.index(self.rowCount()))
        self.CheckedChanged.emit(sorted(self.checked_set))


class VarAndGiniModel(QAbstractTableModel):

    """
    A table of variables which can include the gini index.

    The
    `gini index <http://en.wikipedia.org/wiki/Decision_tree_learning#Gini_impurity>`_
    is associated to each variable when predicting an outcome variable

    Args:
        outcome_var (str) : Name of variable to treat as outcome
        parent (QObject) : Qt parent for this object
    """

    def __init__(self, outcome_var=None, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self.data_frame = braviz_tab_data.get_variables()
        # self.data_frame["var_idx"]=self.data_frame.index
        self.data_frame["Ginni"] = "?"
        self.ginni_calculated = False
        self.outcome = outcome_var
        self.filtered_index = self.data_frame.index

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.filtered_index)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        col = QModelIndex.column()
        df2 = self.data_frame.loc[self.filtered_index]
        if 0 <= line < len(df2):
            if col == 0:
                if int_role == QtCore.Qt.DisplayRole:
                    return df2.iloc[line, 0]
                elif int_role == QtCore.Qt.ToolTipRole:
                    return braviz_tab_data.get_var_description(df2.index[line])
            elif col == 1:
                if int_role == QtCore.Qt.DisplayRole:
                    return str(df2.iloc[line, 1])
        return None

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return None
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
            return None

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
            index2 = [
                i for i in self.data_frame.index if i in self.filtered_index]
            df2 = self.data_frame.loc[index2]
            df2.sort("Ginni", ascending=reverse, inplace=True)
            self.filtered_index = df2.index
        self.modelReset.emit()

    def calculate_gini_indexes(self):
        """
        Calculates the gini indices of the variables via a random forest
        """
        from braviz.interaction.r_functions import calculate_ginni_index
        # get outcome var:
        if self.outcome is None:
            log = logging.getLogger(__name__)
            log.error("An outcome var is required for this")
            return
        self.data_frame = calculate_ginni_index(self.outcome, self.data_frame)

    def update_list(self, mask):
        """
        Updates the list to include only variables whose names match a mask

        Args:
            mask (str) : mask in sql syntax
        """
        pdf = braviz_tab_data.get_variables(mask=mask)
        self.filtered_index = pdf.index
        self.modelReset.emit()


class AnovaRegressorsModel(QAbstractTableModel):

    """
    Holds the regressors and interaction terms for a linear model

    The model exposes two columns, regressor name and degrees of freedom. Internally it keeps track if each
    regressor is a single term or an interaction of multiple variables

    It is possible to show only interactions, or only single term regressors

    Args:
        regressors_list (list) : List of variable names to be used as regressors
        parent (QObject) : Qt parent
    """

    def __init__(self, regressors_list=tuple(), parent=None):
        QAbstractTableModel.__init__(self, parent)
        if len(regressors_list) > 0:
            initial_data = ((r, self._get_degrees_of_freedom(r), 0)
                            for r in regressors_list)
        else:
            initial_data = None
        self.data_frame = pd.DataFrame(
            initial_data, columns=["variable", "DF", "Interaction"])
        self.display_view = self.data_frame
        self.__show_interactions = True
        self.__show_regressors = True
        self.__interactors_dict = dict()
        self.__next_index = len(regressors_list)

    def reset_data(self, regressors_list):
        """
        Sets a new list of regressors

        Args:
            regressors_list (list) : List of variable names
        """
        if len(regressors_list) > 0:
            initial_data = ((r, self._get_degrees_of_freedom(r), 0)
                            for r in regressors_list)
        else:
            initial_data = None
        self.data_frame = pd.DataFrame(
            initial_data, columns=["variable", "DF", "Interaction"])
        self.display_view = self.data_frame
        self.__show_interactions = True
        self.__show_regressors = True
        self.__interactors_dict = dict()
        self.__next_index = len(regressors_list)
        self.modelReset.emit()

    def _update_display_view(self):
        """
        Updates the display
        """

        if self.__show_interactions and self.__show_regressors:
            self.display_view = self.data_frame
        else:
            if self.__show_interactions is True:
                self.display_view = self.data_frame[
                    self.data_frame["Interaction"] == 1]
            else:
                self.display_view = self.data_frame[
                    self.data_frame["Interaction"] == 0]

    def show_interactions(self, value=True):
        """
        Set if interaction terms should be shown

        Args:
            value (bool) : if ``False`` interaction terms will be hidden
        """
        self.__show_interactions = value
        self._update_display_view()
        self.modelReset.emit()

    def show_regressors(self, value=True):
        """
        Set if single variable terms should be shown

        Args:
            value (bool) : if ``False`` single variable terms will be hidden
        """
        self.__show_regressors = value
        self._update_display_view()
        self.modelReset.emit()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.display_view)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return None

        if int_role == QtCore.Qt.DisplayRole:
            if p_int == 0:
                return "Variable"
            elif p_int == 1:
                return "DF"
        elif int_role == QtCore.Qt.ToolTipRole and p_int == 1:
            return "Degrees of freedom"
        else:
            return None

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
        return None

    def sort(self, p_int, Qt_SortOrder_order=None):
        # We will be using type2 or type3 Sums of Squares, and therefore order
        # is not important
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        if p_int == 0:
            self.data_frame.sort("variable", ascending=reverse, inplace=True)
        elif p_int == 1:
            self.data_frame.sort("DF", ascending=reverse, inplace=True)
        self._update_display_view()
        self.modelReset.emit()

    def add_regressor(self, var_name):
        """
        Add a regressor to the list

        Args:
            var_name (str) : Name of a variable
        """
        if var_name in self.data_frame["variable"].values:
            # ignore duplicates
            return

        self.beginInsertRows(
            QtCore.QModelIndex(), len(self.data_frame), len(self.data_frame))
        self.data_frame = self.data_frame.append(pd.DataFrame([(var_name, self._get_degrees_of_freedom(var_name), 0)],
                                                              columns=[
                                                                  "variable", "DF", "Interaction"],
                                                              index=(
                                                                  self.__next_index,)
                                                              ))
        self.__next_index += 1
        self.endInsertRows()
        self._update_display_view()

    def removeRows(self, row, count, QModelIndex_parent=None, *args, **kwargs):
        # self.layoutAboutToBeChanged.emit()
        self.beginRemoveRows(QtCore.QModelIndex(), row, row + count - 1)
        indexes = list(self.data_frame.index)
        for i in xrange(count):
            r = indexes.pop(row)
            # print r
            if r in self.__interactors_dict:
                del self.__interactors_dict[r]
        if len(indexes) == 0:
            self.data_frame = pd.DataFrame(
                columns=["variable", "DF", "Interaction"])
        else:
            log = logging.getLogger(__name__)
            log.debug(self.data_frame)
            log.debug(indexes)
            self.data_frame = self.data_frame.loc[indexes]

        self._remove_invalid_interactions()
        self._update_display_view()
        self.endRemoveRows()
        self.modelReset.emit()

    def _get_degrees_of_freedom(self, var_name):
        is_real = braviz_tab_data.is_variable_name_real(var_name)
        if is_real is None or is_real == 1:
            return 1
        labels = braviz_tab_data.get_labels_dict_by_name(var_name)
        return len(labels) - 1

    def get_regressors(self):
        """
        Get a list of single term regressors
        """
        regs_col = self.data_frame["variable"][
            self.data_frame["Interaction"] == 0]
        return regs_col.get_values()

    def get_interactions(self):
        """
        Get a list of interaction terms
        """
        regs_col = self.data_frame["variable"][
            self.data_frame["Interaction"] == 1]
        return regs_col.get_values()

    def add_interactor(self, factor_rw_indexes):
        """
        Add an interaction term to the model

        Args:
            factor_rw_indexes (list) : Positions of single term regressors that compose the interaction.
                This positions are the row number of the variable in this model, without counting
                interaction terms (or the row number when interaction terms are hidden)
        """

        factors_data_frame = self.data_frame[
            self.data_frame["Interaction"] == 0]
        factor_indexes = [factors_data_frame.index[i]
                          for i in factor_rw_indexes]
        if len(factor_indexes) < 2:
            # can't add interaction with just one factor
            return

        # check if already added:
        if frozenset(factor_indexes) in self.__interactors_dict.values():
            log = logging.getLogger(__name__)
            log.warning("Trying to add duplicated interaction")
            return

        # get var_names
        factor_names = self.data_frame["variable"].loc[factor_indexes]
        self.add_interactor_by_names(factor_names)

    def add_interactor_by_names(self, factor_names):
        """
        Add an interaction term by giving the name of its terms

        Args:
            factor_names (list) : List of variable names, already in the model, which make up the interaction
        """
        df = self.data_frame
        factor_indexes = [df.index[df["variable"] == fn].values[0]
                          for fn in factor_names]
        # create name
        interactor_name = '*'.join(factor_names)
        log = logging.getLogger(__name__)
        log.debug(interactor_name)
        # get degrees of freedom
        interactor_df = self.data_frame["DF"].loc[factor_indexes].prod()
        log.debug(interactor_df)
        # add to dictionary
        interactor_idx = self.__next_index
        self.__next_index += 1
        self.__interactors_dict[interactor_idx] = frozenset(factor_indexes)
        # add to data frame
        self.beginInsertRows(
            QtCore.QModelIndex(), len(self.data_frame), len(self.data_frame))

        temp_data_frame = pd.DataFrame([(interactor_name, interactor_df, 1)], columns=["variable", "DF", "Interaction"],
                                       index=(interactor_idx,))
        self.data_frame = self.data_frame.append(temp_data_frame)
        self.endInsertRows()
        self._update_display_view()

    def _remove_invalid_interactions(self):
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
        """
        Get the internal data frame

        Returns:
            :class:`pandas.DataFrame` with three columns: regressor name, degrees of freedom, and interaction.
            The last column has zeros for single variable regressors and 1 for interaction terms.
        """
        return self.data_frame

    def get_interactors_dict(self):
        """
        Get the interactions dictionary

        Returns:
            A dictionary that maps dataframe indices of interactions terms to the dataframe indices of
            its factors.
        """
        return self.__interactors_dict


class NominalVariablesMeta(QAbstractTableModel):

    """
    A table with numerical labels in the first column and corresponding text labels in the second column

    These labels correspond to the possible values a nominal variable can take
    Textual labels can be edited

    Args:
        var_name (str) : Name of a nominal variable
    """

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
                return None
        return None

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if int_role != QtCore.Qt.DisplayRole:
            return None
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if p_int == 0:
                return "Label"
            elif p_int == 1:
                return "Name"
        else:
            return None

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
            self.names_dict[self.labels_list[row]] = QVariant
            self.dataChanged.emit(QModelIndex, QModelIndex)
            return True
        elif (int_role == QtCore.Qt.CheckStateRole) and (col == 0 and 0 <= row < self.rowCount()):
            state = QVariant
            label = self.labels_list[row]
            if state == QtCore.Qt.Checked:
                self.unchecked.remove(label)
            elif state == QtCore.Qt.Unchecked:
                self.unchecked.add(label)
            else:
                return False
            self.emit(
                QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"), QModelIndex, QModelIndex)
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
        """
        Update the table with data from the database

        Args:
            var_name (str) : Read labels for this variable
        """
        self.modelAboutToBeReset.emit()
        if var_name is None:
            # generic labels
            self.labels_list = range(1, 3)
            self.names_dict = {}
            return
        self.var_name = var_name
        self.names_dict = braviz_tab_data.get_labels_dict_by_name(var_name)
        self.labels_list = self.names_dict.keys()
        self.modelReset.emit()

    def save_into_db(self, var_idx=None):
        """
        Save the textual labels into the database

        Args:
            var_idx (int) : Index of the variable to which the labels will be saved, only required if *var_name*
                is not set.
        """
        tuples = ((k, v) for k, v in self.names_dict.iteritems())
        if self.var_name is not None:
            braviz_tab_data.save_nominal_labels_by_name(self.var_name, tuples)
        else:
            if var_idx is None:
                raise Exception("Var_idx is required")
            braviz_tab_data.save_nominal_labels(var_idx, tuples)

    def add_label(self):
        """
        Add another row with the next numerical label to the table
        """
        self.labels_list.append(len(self.labels_list) + 1)
        self.modelReset.emit()

    def set_labels_dict(self, labels_dict):
        """
        Sets textual labels

        Args:
            labels_dict (dict) : Dictionary that maps numerical labels to textual labels
        """
        self.labels_list = labels_dict.keys()
        self.names_dict = labels_dict
        self.modelReset.emit()

    def set_checkeable(self, checkeable):
        """
        Choose if check boxes should be displayed next to numerical labels

        Args:
            checkeable (bool) : If ``True`` checkboxes will appear
        """
        self.checkeable = bool(checkeable)

    def get_unchecked(self):
        """
        Get a set of labels whose checkbox is empty
        """
        return self.unchecked

    def get_checked(self):
        """
        Get a set of labels whose checkbox is checked
        """
        return set(self.labels_list) - self.unchecked


class AnovaResultsModel(QAbstractTableModel):

    """
    A model to represent the results of an anova regression

    It has columns for factor names, sum of squares, degrees of freedom, F statistic, and p value.
    Internally it also holds residuals, fitted values and intercept.

    Args:
        results_df (pandas.DataFrame) : A Data Frame containing the columns indicated above
        residuals (list) : A vector of the regression residuals
        intercept (float) : Value of the intercept term of the regression
        fitted (list) : Vector of fitted values
    """

    def __init__(self, results_df=None, residuals=None, intercept=None, fitted=None):
        if results_df is None:
            self.__df = pd.DataFrame(
                None, columns=["Factor", "Sum Sq", "Df", "F value", "Pr(>F)"])
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
            return None
        line = QModelIndex.row()
        col = QModelIndex.column()
        data = self.__df.iloc[line, col]
        if col == 0:
            # names
            return data
        elif col == 2:
            # df
            return "%d" % data
        elif col == 4:
            # p
            return "{:.6f}".format(data)
        else:
            return "{:.6g}".format(data)

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation != QtCore.Qt.Horizontal:
            return None
        if int_role == QtCore.Qt.DisplayRole:
            return self.__df.columns[p_int]
        return None

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        self.__df.sort(
            self.__df.columns[p_int], ascending=reverse, inplace=True)
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

    Args:
        data_frame (pandas.DataFrame) : Data Frame
        columns (list) : Optional, names for columns of the data frame
        string_columns (list) : List of column names that should be displayed as strings
        index_as_column (bool) : Display the data frame index as the first column
        checks (bool) : Display checkboxes next to the first column
    """

    def __init__(self, data_frame, columns=None, string_columns=tuple(), index_as_column=True, checks=False):
        if not isinstance(data_frame, pd.DataFrame):
            raise ValueError("A pandas data frame is required")
        if columns is None:
            columns = data_frame.columns
        self.__df = data_frame
        self.__cols = columns
        self.__string_cols = frozenset(string_columns)
        self.__checks = checks
        self.__checked = set()
        self.__disabled = set()
        self.index_as_column = index_as_column
        super(DataFrameModel, self).__init__()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__df)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        if self.index_as_column:
            return len(self.__cols) + 1
        else:
            return len(self.__cols)

    def data(self, QModelIndex, int_role=None):

        line = QModelIndex.row()
        col = QModelIndex.column()

        if self.__checks is True and int_role == QtCore.Qt.CheckStateRole:
            if col == 0:
                idx = self.__df.index[line]
                if idx in self.__checked:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked

        if not (int_role == QtCore.Qt.DisplayRole):
            return None

        if self.index_as_column:
            if col == 0:
                return self.format_data(0, self.__df.index[line])
            else:
                col_name = self.__cols[col - 1]
                data = self.__df[col_name].iloc[line]
                return self.format_data(col, data)
        else:
            col_name = self.__cols[col]
            data = self.__df[col_name].iloc[line]
            return self.format_data(col, data)

    def setData(self, QModelIndex, QVariant, int_role=None):
        if int_role != QtCore.Qt.CheckStateRole or not self.__checks:
            return False
        col = QModelIndex.column()
        row = QModelIndex.row()
        assert col == 0
        state = QVariant
        idx = self.__df.index[row]
        if state == QtCore.Qt.Checked:
            self.__checked.add(idx)
        elif state == QtCore.Qt.Unchecked:
            self.__checked.remove(idx)
        self.emit(
            QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"), QModelIndex, QModelIndex)
        return True

    def get_item_index(self, QModelIndex):
        if not QModelIndex.isValid():
            return
        row = QModelIndex.row()
        return self.__df.index[row]

    def format_data(self, col_i, data):
        if col_i in self.__string_cols:
            return unicode(data)
        else:
            try:
                if isinstance(data,(int, np.integer)):
                    ans = format(data,"d")
                else:
                    ans = format(data,".6f")
            except Exception:
                ans = str(data)
            return ans

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if int_role == QtCore.Qt.DisplayRole:
                if self.index_as_column:
                    if p_int == 0:
                        return unicode(self.__df.index.name)
                    else:
                        return self.__cols[p_int - 1]
                else:
                    return self.__cols[p_int]
        elif Qt_Orientation == QtCore.Qt.Vertical:
            if int_role == QtCore.Qt.DisplayRole:
                return str(self.__df.index[p_int])

        return None

    def sort(self, p_int, Qt_SortOrder_order=None):
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        if p_int == 0 and self.index_as_column:
            i_name = self.__df.index.name
            i_l = list(self.__df.index)
            i_l.sort(reverse=reverse)
            self.__df = self.__df.loc[i_l].copy()
            self.__df.index.name = i_name
        else:
            if self.index_as_column:
                self.__df.sort(
                    self.__df.columns[p_int - 1], ascending=reverse, inplace=True)
            else:
                self.__df.sort(
                    self.__df.columns[p_int], ascending=reverse, inplace=True)
        self.modelReset.emit()

    def flags(self, QModelIndex):
        line = QModelIndex.row()
        col = QModelIndex.column()
        result = QtCore.Qt.NoItemFlags
        if 0 <= line <= self.rowCount() and 0 <= line <= self.rowCount():
            result |= QtCore.Qt.ItemIsSelectable
        if self.__df.index[line] not in self.__disabled:
            result |= QtCore.Qt.ItemIsEnabled
        if self.__checks and col == 0:
            result |= QtCore.Qt.ItemIsUserCheckable
        return result

    def set_df(self, new_df):
        self.__df = new_df.copy()
        self.modelReset.emit()

    @property
    def checked(self):
        return frozenset(self.__checked)

    @checked.setter
    def checked(self, checked_names):
        self.modelAboutToBeReset.emit()
        self.__checked = set(checked_names)
        self.modelReset.emit()

    @property
    def disabled_items(self):
        return frozenset(self.__disabled)

    @disabled_items.setter
    def disabled_items(self, disabled_set):
        self.modelAboutToBeReset.emit()
        self.__disabled = set(disabled_set)
        self.modelReset.emit()


class SampleTree(QAbstractItemModel):

    """
    Creates a tree for representing a sample

    Each first level child represents a nominal variable, and its sons are the different values for that variable
    finally, the leafs contain the subject ids. For each node the number of subjects it contains is represented in the
    second column

    Args:
        columns (list) : List of nominal variable names to include in the tree.
    """

    def __init__(self, columns=None):
        super(SampleTree, self).__init__()
        if columns is None:
            conf = config_file.get_apps_config()
            a_vars = conf.get_default_variables()
            columns = [a_vars["nom1"], a_vars["nom2"], a_vars["lat"]]
        self.data_aspects = columns
        self.__headers = {0: "Attribute", 1: "N"}
        self.__data_frame = braviz_tab_data.get_data_frame_by_name(columns)
        self.item_tuple = namedtuple(
            "item_tuple", ["nid", "row", "label", "count", "parent", "children"])
        self.__tree_list = []
        self.__id_index = {}
        self.__next_id = 0
        self._populate_tree_dicts()

    def set_sample(self, new_sample):
        """
        Sets the subsample to show in the tree

        Args:
            new_sample (set) : Set of subjects in the new subsample
        """
        self.__data_frame = braviz_tab_data.get_data_frame_by_name(
            self.data_aspects)
        self.__data_frame = self.__data_frame.loc[sorted(new_sample)]
        self.__tree_list = []
        self.__id_index = {}
        self.__next_id = 0
        self._populate_tree_dicts()
        self.modelReset.emit()

    def __get_next_id(self):
        iid = self.__next_id
        self.__next_id += 1
        return iid

    def _populate_tree_dicts(self):
        # All
        iid = self.__get_next_id()
        children = self.__data_frame.index
        parent_id = iid
        children_list = []
        for r, c in enumerate(children):
            iid = self.__get_next_id()
            c_item = self.item_tuple(
                nid=iid, row=r, label=str(c), count=1, parent=parent_id, children=None)
            self.__id_index[iid] = c_item
            children_list.append(c_item)
        all_item = self.item_tuple(nid=parent_id, row=0, label="All", count=len(self.__data_frame), parent=None,
                                   children=children_list)
        self.__tree_list.append(all_item)
        self.__id_index[parent_id] = all_item

        # Other aspectes
        for r, aspect in enumerate(self.data_aspects):
            aspect_id = self.__get_next_id()
            children = self._populate_aspect(aspect, aspect_id)
            new_item = self.item_tuple(nid=aspect_id, row=r + 1, label=aspect, count=len(self.__data_frame),
                                       parent=None, children=children)
            self.__tree_list.append(new_item)
            self.__id_index[aspect_id] = new_item

        # check index integrity
        for i in xrange(self.__next_id):
            assert self.__id_index.has_key(i)

    def _populate_aspect(self, var_name, aspect_id):
        # get labels
        d = braviz_tab_data.get_labels_dict_by_name(var_name)
        labels_list = []
        for i, (label, name) in enumerate(d.iteritems()):
            if label is None:
                continue
            lab_id = self.__get_next_id()
            children = self.__data_frame[
                self.__data_frame[var_name] == label].index
            children_list = []
            for r, c in enumerate(children):
                c_id = self.__get_next_id()
                c_item = self.item_tuple(
                    nid=c_id, row=r, label=str(c), count=1, parent=lab_id, children=None)
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
            # print "top_row_count"
            # print len(self.data_aspects)+1
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
            # print item
            # print sid
            if col == 0:
                return item.label
            elif col == 1:
                return item.count

        return None

    def index(self, p_int, p_int_1, QModelIndex_parent, *args, **kwargs):
        if not QModelIndex_parent.isValid():
            # top level
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
            self.__headers.get(p_int, None)
            return self.__headers.get(p_int, None)
        return None

    def hasChildren(self, QModelIndex_parent=None, *args, **kwargs):
        if not QModelIndex_parent.isValid():
            # top level has children
            return True
        parent_item = self.__id_index[QModelIndex_parent.internalId()]
        # print "has children"
        # print parent_item
        if parent_item.children is None:
            return False
        else:
            return True

    def get_leafs(self, QModelIndex):
        """
        Get subjectids under a certain node

        Args:
            QModelIndex (QModelIndex) : Index of a node in the tree
        """
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

    """
    A table of subjects and values for specified variables

    The first column contains subject codes. There are additional columns for each requested variable.
    Values for nominal variables are shown as textual labels

    Args:
        initial_columns (list) : List of initial variables indices to include as columns in the table
        sample (list) : List of subject ids to show in the table
    """

    def __init__(self, initial_columns=None, sample=None):
        QAbstractTableModel.__init__(self)
        if initial_columns is None:
            initial_columns = tuple()
        self.__df = None
        self.__is_var_real = None
        self.__labels = None
        self.__col_indexes = None
        self.__highlight_subject = None
        self._sort_column = 0
        self._sort_reversed = False
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
            return None
        if Qt_Orientation == QtCore.Qt.Vertical:
            return None
        elif 0 <= p_int < self.__df.shape[1]:
            return self.__df.columns[p_int]
        else:
            return None

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        name = self.__df.iloc[line, 0]
        if int_role == QtCore.Qt.FontRole:
            if name == self.__highlight_subject:
                font = QtGui.QFont()
                font.setBold(True)
                return font
        if int_role == QtCore.Qt.BackgroundRole:
            if name == self.__highlight_subject:
                brush = QtGui.QBrush()
                brush.setColor(QtGui.QColor("palegreen"))
                brush.setStyle(QtCore.Qt.SolidPattern)
                return brush
        if not (int_role in (QtCore.Qt.DisplayRole, QtCore.Qt.ToolTipRole)):
            return None

        col = QModelIndex.column()
        if (0 <= line < len(self.__df)) and (0 <= col < self.__df.shape[1]):
            datum = self.__df.iloc[line, col]
            if col == 0:
                return "%d" % int(datum)
            else:
                if self.__is_var_real[col]:
                    return str(datum)
                else:
                    try:
                        label = self.__labels[col][int(datum)]
                    except ValueError:
                        label = "?"
                    return label

        else:
            return None

    def sort(self, p_int=None, Qt_SortOrder_order=None):
        reverse = False
        self._sort_reversed = reverse
        if p_int is None:
            sort_column_name = self.__df.columns[self._sort_column]
        else:
            sort_column_name = self.__df.columns[p_int]
            self._sort_column = p_int

        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = True

        self.modelAboutToBeReset.emit()
        # Merge sort is stable
        self.__df.sort_values(
            sort_column_name , ascending=reverse, inplace=True, kind="mergesort")
        self.modelReset.emit()

    def set_var_columns(self, columns):
        """
        Set the columns in the table

        Args:
            columns (list) : List of variable indices
        """
        self.__col_indexes = columns
        vars_df = braviz_tab_data.get_data_frame_by_index(columns)
        codes_df = pd.DataFrame(
            vars_df.index.get_values(), index=vars_df.index, columns=("Code",))
        self.__df = codes_df.join(vars_df)
        self.__df = self.__df.loc[self.sample]
        is_var_code_real = braviz_tab_data.are_variables_real(columns)
        # we want to use the column number as index
        self.__is_var_real = dict(
            (i + 1, is_var_code_real[idx]) for i, idx in enumerate(columns))
        self.__labels = {}
        for i, is_real in self.__is_var_real.iteritems():
            if not is_real:
                # column 0 is reserved for the Code
                self.__labels[i] = braviz_tab_data.get_labels_dict(
                    columns[i - 1])
        self.modelReset.emit()

    def set_sample(self, new_sample):
        """
        Set the subsample of subjects in the table

        Args:
            new_sample (set) : List of subject ids
        """
        self.sample = list(new_sample)
        self.set_var_columns(self.__col_indexes)
        self.sort()

    def get_current_columns(self):
        """
        Get a list of current variable names shown as columns
        """
        return self.__df.columns[1:]

    def get_current_column_indexes(self):
        """
        Get a list of current variable indices shown as columns
        """
        return self.__col_indexes

    def get_subject_index(self, subj_id):
        """
        Get row number for a certain subject id
        """
        row = self.__df.index.get_loc(int(subj_id))
        return row

    @property
    def highlighted_subject(self):
        return self.__highlight_subject

    @highlighted_subject.setter
    def highlighted_subject(self, subj):
        self.__highlight_subject = subj
        self.modelReset.emit()

    @property
    def sorted_sample(self):
        return list(self.__df.index)

    @sorted_sample.setter
    def sorted_sample(self, new_order):
        assert set(new_order) == set(self.__df.index)
        self.modelAboutToBeReset.emit()
        self.__df = self.__df.loc[new_order]
        self.modelReset.emit()

class ContextVariablesModel(QAbstractTableModel):

    """
    A table with three columns: Variable name, variable type, and a checkbox called "editable"

    This table is used to select a list of variables, and decide which of those should be made
    writable, and which readonly

    Args:
        context_vars_list (list) : List of variables ids to include at the start
        parent (QObject) : Qt parent
        editable_dict (dict) : Dictionary where keys are variable ids and values are booleans indicating
            if the variable should be writable by the user. This object will be modified.


    """

    def __init__(self, context_vars_list=None, parent=None, editable_dict=None):
        QAbstractTableModel.__init__(self, parent)
        self.data_type_dict = dict()
        if context_vars_list is not None and len(context_vars_list) > 0:
            self.data_frame = pd.DataFrame(
                [(braviz_tab_data.get_var_name(idx), self._get_type(idx))
                 for idx in context_vars_list],
                columns=["variable", "Type"], index=context_vars_list)
        else:
            self.data_frame = pd.DataFrame(columns=["variable", "Type"])

        self.editables_dict = editable_dict
        if self.editables_dict is None:
            self.editables_dict = dict((idx, False)
                                       for idx in context_vars_list)
        self.headers_dict = {0: "Variable", 1: "Type", 2: "Editable"}

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.data_frame)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 3

    def headerData(self, p_int, Qt_Orientation, int_role=None):

        if Qt_Orientation != QtCore.Qt.Horizontal:
            return None
        if int_role == QtCore.Qt.DisplayRole:
            return self.headers_dict.get(p_int, None)
        return None

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
            return None

        if (0 <= line < self.rowCount()) and (0 <= col < 2):
            return self.data_frame.iloc[line, col]
        else:
            return None

    def sort(self, p_int, Qt_SortOrder_order=None):
        # We will be using type2 or type3 Sums of Squares, and therefore order
        # is not important
        reverse = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            reverse = False
        if p_int == 0:
            self.data_frame.sort("variable", ascending=reverse, inplace=True)
        elif p_int == 1:
            self.data_frame.sort("Type", ascending=reverse, inplace=True)
        self.modelReset.emit()

    def _get_type(self, var_idx):
        """
        Gets the type of a variable as a string
        """
        data_type = self.data_type_dict.get(var_idx)
        if data_type is None:
            if braviz_tab_data.is_variable_nominal(var_idx):
                data_type = "Nominal"
            else:
                data_type = "Real"
            self.data_type_dict[var_idx] = data_type
        return data_type

    def add_variable(self, var_idx):
        """
        Add a variable to the table

        The removeRows method can be used to remove a variable
        Args:
            var_idx (int) : Variable index
        """
        if var_idx in self.data_frame.index:
            # ignore duplicates
            return

        self.beginInsertRows(
            QtCore.QModelIndex(), len(self.data_frame), len(self.data_frame))
        self.data_frame = self.data_frame.append(
            pd.DataFrame([(braviz_tab_data.get_var_name(var_idx), self._get_type(var_idx))],
                         columns=["variable", "Type"],
                         index=(var_idx,)))
        self.endInsertRows()
        self.editables_dict[var_idx] = False

    def removeRows(self, row, count, QModelIndex_parent=None, *args, **kwargs):
        # self.layoutAboutToBeChanged.emit()
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
            self.editables_dict[self.data_frame.index[row]] = QVariant == QtCore.Qt.Checked
            self.dataChanged.emit(QModelIndex, QModelIndex)
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
        """
        Gets a list of variable indices currently in the table
        """
        return self.data_frame.index.tolist()


class SubjectDetails(QAbstractTableModel):

    """
    A table showing variable values for a single subject

    The first column contains variable names, and the second column its values, together with
    the range of values for the reference population

    The user may drag table rows to change the order

    Args:
        initial_vars (list) : List of variables codes to include in the table from the start
        initial_subject : Code of the initial subject

    """

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
            return None
        if Qt_Orientation == QtCore.Qt.Vertical:
            return None
        elif 0 <= p_int < len(self.headers):
            name = self.headers[p_int]
            return name
        else:
            return None

    def data(self, QModelIndex, int_role=None):
        line = QModelIndex.row()
        col = QModelIndex.column()
        if int_role == QtCore.Qt.ToolTipRole:
            var_idx = self.__df.index[line]
            desc = braviz_tab_data.get_var_description(var_idx)
            return desc
        if not int_role == QtCore.Qt.DisplayRole:
            return None
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
            return None

    def set_variables(self, variable_ids):
        """
        Set the list of variables

        Args:
            variable_ids : list of new variable ids to show in the table
        """
        vars_df = braviz_tab_data.get_subject_variables(
            self.__current_subject, variable_ids)
        self.__df = vars_df
        self.__is_var_real = braviz_tab_data.are_variables_real(variable_ids)
        self.__normal_ranges = dict((int(idx), braviz_tab_data.get_variable_normal_range(int(idx)))
                                    for idx in variable_ids if self.__is_var_real[int(idx)])

        self.modelReset.emit()

    def change_subject(self, new_subject):
        """
        Change the current subject to whih the variable values correspond

        Args:
            new_subject : New subject code
        """
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
        # only accept drops between lines
        if QModelIndex.isValid():
            return False
        data_stream = QtCore.QDataStream(
            QMimeData.data("application/x-qabstractitemmodeldatalist"))
        source_row = data_stream.readInt()
        # print "Moving from %d to %d"%(source_row,row)
        index_list = list(self.__df.index)
        source_id = index_list.pop(source_row)
        index_list.insert(row, source_id)
        self.__df = self.__df.loc[index_list]
        self.modelReset.emit()
        return True

    def get_current_variables(self):
        """
        Get a list of current variable codes
        """
        return self.__df.index

    def sort(self, p_int, Qt_SortOrder_order=None):
        if p_int == 0:
            ascending = not (Qt_SortOrder_order == QtCore.Qt.AscendingOrder)
            self.__df.sort("name", inplace=True, ascending=ascending)
            self.modelReset.emit()


class NewVariableValues(QAbstractTableModel):

    """
    A table with on column for subject, and a writable second column for variable values

    Values are restricted to numbers
    """

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
        return None

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
            self.values_dict[self.subjects_list[row]] = QVariant
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
        return None

    def save_into_db(self, var_idx):
        """
        Save values from the model into the braviz database

        Args:
            var_idx (int) : Index of the variable to which the values should be saved
        """
        value_tuples = ((s, self.values_dict.get(s, "nan"))
                        for s in self.subjects_list)
        braviz_tab_data.update_variable_values(var_idx, value_tuples)

    def set_values_dict(self, values_dict):
        """
        Set values for variables

        Args:
            values_dict (dict) :  A dictionary with subject codes as keys, and variable values as values
        """
        self.modelAboutToBeReset.emit()
        self.values_dict = values_dict
        self.modelReset.emit()


class SimpleBundlesList(QAbstractListModel):

    """
    A list of database fiber bundles

    An optional special bundle, called "<From Segment>" may also be shown
    """

    def __init__(self):
        super(SimpleBundlesList, self).__init__()
        self.id_list = None
        self.names_list = None
        self.__showing_special = False
        self._restart_structures()

    def _restart_structures(self):
        """
        Clear the list state
        """

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
        return None

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        return None

    def add_bundle(self, bundle_id, name):
        """
        Add a bundle to the list

        Args:
            bundle_id (int) : Bundle database index
            name (str) : Bundle name to show
        """
        if bundle_id in self.id_list:
            return
        self.id_list.insert(len(self.id_list) - 1, bundle_id)
        self.names_list.insert(len(self.names_list) - 1, name)

    def get_bundle_name(self, bid):
        """
        Get the name used to show a bundle with the given id

        Args:
            bid (int) : Bundle database id
        """
        try:
            idx = self.id_list.index(bid)
        except ValueError:
            log = logging.getLogger(__name__)
            log.error("Invalid bundle id")
            raise
        return self.names_list[idx]

    def set_show_special(self, show_special):
        """
        Show or hide the special "<From segment>" bundle

        Args:
            show_special (bool) : If ``True`` the special bundle will appear on the list
        """
        self.__showing_special = show_special
        self.modelReset.emit()

    def get_ids(self):
        """
        Get ids in the list, if the special bundle is present it is ignored
        """
        return self.id_list[:-1]

    def set_ids(self, id_list, names_dict=None):
        """
        Set bundle ids to show in the list

        Args:
            id_list (list) : List of database indices of bundles
            names_dict (dict) : Optional, if present it is used to map ids to names; otherwise the names in the
                database are used
        """
        self._restart_structures()
        if names_dict is None:
            names_dict = dict(bundles_db.get_bundle_ids_and_names())
        for b in id_list:
            self.add_bundle(b, names_dict[b])
        self.modelReset.emit()


class BundlesSelectionList(QAbstractListModel):

    """
    A list of bundles with checkboxes
    """

    def __init__(self):
        super(BundlesSelectionList, self).__init__()
        self.id_list = []
        self.names_dict = {}
        self._selected = set()
        self.refresh_model()
        self.showing_special = False

    def refresh_model(self):
        """
        Reloads data from the database
        """
        self.modelAboutToBeReset.emit()
        tuples = bundles_db.get_bundle_ids_and_names()
        self.names_dict = dict(tuples)
        self.id_list = sorted(self.names_dict.keys())
        self._selected.intersection_update(self.id_list)
        self.modelReset.emit()

    def select_many_ids(self, ids_it):
        """
        Adds several bundles to the selection

        Args:
            ids_it (list) : List of database ids to add
        """
        self.modelAboutToBeReset.emit()
        self._selected.update(set(self.id_list).intersection(ids_it))
        self.modelReset.emit()


    def get_selected(self):
        """
        Get a list of selected bundle ids
        """
        return list(self._selected)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.id_list)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if self.showing_special:
                row -= 1
            if 0 <= row < len(self.id_list):
                bid = self.id_list[row]
                if int_role == QtCore.Qt.DisplayRole:
                    return self.names_dict[bid]
                elif int_role == QtCore.Qt.CheckStateRole:
                    if bid in self._selected:
                        return QtCore.Qt.Checked
                    else:
                        return QtCore.Qt.Unchecked
                elif int_role == QtCore.Qt.UserRole:
                    return bid
            elif row == -1:
                if int_role == QtCore.Qt.DisplayRole:
                    return "<From Segmentation>"
                elif int_role == QtCore.Qt.CheckStateRole:
                    return QtCore.Qt.Checked
        return None

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        return None

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if self.showing_special:
                row -= 1
            if 0 <= row < len(self.id_list):
                flag = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable
                return flag
            elif row == -1:
                flag = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                return flag
        return QtCore.Qt.NoItemFlags

    def setData(self, QModelIndex, QVariant, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if self.showing_special:
                row -= 1
            if int_role == QtCore.Qt.CheckStateRole:
                if 0 <= row < len(self.id_list):
                    value = QVariant == QtCore.Qt.Checked
                    bid = self.id_list[row]
                    if value:
                        self._selected.add(bid)
                    else:
                        self._selected.remove(bid)
                    self.dataChanged.emit(QModelIndex,QModelIndex)
                    return True
        return False

    def set_show_special(self, show):
        self.modelAboutToBeReset.emit()
        self.showing_special = show
        self.modelReset.emit()


class ScenariosTableModel(QAbstractTableModel):

    """
    A table with available scenarios

    Optionally restricts the table to scenarios for a certain application
    It has three columns: date, name and description

    Args:
        app_name (str) : Name of application, if ``None`` scenarios for all applications are shown
    """

    def __init__(self, app_name):
        super(ScenariosTableModel, self).__init__()
        self.app_name = app_name
        self.headers = ("Date", "Name", "Description")
        self.columns = ("scn_date", "scn_name", "scn_desc")
        self.reload_data()

    def reload_data(self):
        self.df = braviz_user_data.get_scenarios_data_frame(self.app_name)
        self.modelReset.emit()

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if 0 <= p_int < self.df.shape[1]:
                if int_role == QtCore.Qt.DisplayRole:
                    return self.headers[p_int]
        return None

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            col = QModelIndex.column()
            if (0 <= col < self.columnCount()) and (0 <= row < self.rowCount()):
                if (int_role == QtCore.Qt.DisplayRole) or (int_role == QtCore.Qt.ToolTipRole):
                    return str(self.df[self.columns[col]].iloc[row])
                elif int_role == QtCore.Qt.UserRole:
                    return self.df.index[row]
        return None

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
        """
        Get the database index for the scenario in a given row
        """
        return self.df.index[row]

    def get_name(self, row):
        """
        Get the name of the scenario at a given row
        """
        return self.df["scn_name"].iloc[row]


class SimpleSetModel(QAbstractListModel):

    """
    Transforms a python :class:`set` into a Qt List Model
    """

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
        return None

    def get_elements(self):
        """
        Returns a set of the current data
        """
        return set(self.__internal_list)

    def set_elements(self, data_set):
        """
        Sets the current elements in the model

        Args:
            data_set (set) : Items to be stored in the model
        """
        self.__internal_list = sorted(list(data_set))
        self.modelReset.emit()


class SimpleCheckModel(QAbstractListModel):

    """
    Provides a model for selecting items from a set of choices (represented with checkboxes in Qt Views)
    """

    def __init__(self, choices):
        """
        Provides a model for selecting items from a set of choices (represented with checkboxes in Qt Views)

        Args:
            choices (list) : List of elements
        """
        super(SimpleCheckModel, self).__init__()
        self.choices_list = list(choices)
        self.__selected = set()

    def get_selected(self):
        """
        Gets a tuple of the checked items
        """
        return tuple(self.__selected)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.choices_list)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if 0 <= row < len(self.choices_list):
                item = self.choices_list[row]
                if int_role == QtCore.Qt.DisplayRole:
                    return item
                if int_role == QtCore.Qt.CheckStateRole:
                    if item in self.__selected:
                        return QtCore.Qt.Checked
                    else:
                        return QtCore.Qt.Unchecked
        return None

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        return None

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if 0 <= row < len(self.choices_list):
                flag = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable
                return flag
        return QtCore.Qt.NoItemFlags

    def setData(self, QModelIndex, QVariant, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            if int_role == QtCore.Qt.CheckStateRole:
                if 0 <= row < len(self.choices_list):
                    value = QVariant == QtCore.Qt.Checked
                    item = self.choices_list[row]
                    if value:
                        self.__selected.add(item)
                    else:
                        self.__selected.discard(item)
                    self.dataChanged.emit(QModelIndex, QModelIndex)
                    return True
        return False

    def set_selection(self, selection):
        """
        Sets the currently selected items to those (and only those) in *selection*

        Args:
            selection (set) : New set of checked items
        """
        self.__selected = set(selection)
        self.modelReset.emit()
        self.dataChanged.emit(self.index(0, 0), self.index(self.rowCount(), 0))


class SamplesFilterModel(QAbstractListModel):

    """
    A list of filters that can be applied to a sample
    """

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
        return None

    def add_filter(self, filter_name, filter_func):
        """
        Adds a filter to the list

        Args:
            filter_name (str) : Name of the filter, this will be shown to the user
            filter_func (function) : This function should take a subject id and return a boolean.
        """
        new_row = len(self.__filters_list)
        self.beginInsertRows(QtCore.QModelIndex(), new_row, new_row)
        self.__filters_list.append((filter_name, filter_func))
        self.endInsertRows()

    def apply_filters(self, input_set):
        """
        Apply all filters to a given set

        Args:
            input_set (set) : Set of subject ids

        Returns:
            filtered set of subject ids
        """
        output_set = input_set
        for _, f in self.__filters_list:
            output_set = filter(f, output_set)
        return output_set

    def remove_filter(self, index):
        """
        Removes a filter located at a given row

        Args:
            index (QModelIndex) : Index of the row containing the filter
        """
        row = index.row()
        self.beginRemoveRows(QtCore.QModelIndex(), row, row)
        self.__filters_list.pop(row)
        self.endRemoveRows()


class SamplesSelectionModel(QAbstractTableModel):

    """
    A table showing available subsamples

    It has three columns: sample size, sample name, and sample description
    """

    def __init__(self):
        super(SamplesSelectionModel, self).__init__()
        self.data_frame = braviz_user_data.get_samples_df()
        self.columns = ("sample_size", "sample_name", "sample_desc")
        self.headers = ("Size", "Name", "Description")

    def reload(self):
        """
        Reload subsamples from the database
        """
        df = braviz_user_data.get_samples_df()
        if not df.equals(self.data_frame):
            self.modelAboutToBeReset.emit()
            self.data_frame = df
            self.modelReset.emit()

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            col = QModelIndex.column()
            if int_role == QtCore.Qt.DisplayRole or int_role == QtCore.Qt.ToolTipRole:
                return str(self.data_frame[self.columns[col]].iloc[row])
        return None

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.data_frame.shape[0]

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return self.data_frame.shape[1]

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if int_role == QtCore.Qt.DisplayRole:
                return self.headers[p_int]
        return None

    def sort(self, p_int, Qt_SortOrder_order=None):
        sort_col = self.columns[p_int]
        ascending = True
        if Qt_SortOrder_order == QtCore.Qt.DescendingOrder:
            ascending = False
        self.data_frame.sort(
            columns=sort_col, ascending=ascending, inplace=True)
        self.modelReset.emit()

    def get_sample(self, QModelIndex):
        """
        Get the set of subjects in a subsample located at a certain row

        Args:
            QModelIndex (QModelIndex) : Index of a cell in the table (only the row is important)
        """
        if QModelIndex.isValid():
            row = QModelIndex.row()
            sample_index = self.data_frame.index[row]
            data = braviz_user_data.get_sample_data(int(sample_index))
            return data

    def get_sample_index(self, QModelIndex):
        """
        Get the database index of a subsample located at a certain row

        Args:
            QModelIndex (QModelIndex) : Index of a cell in the table (only the row is important)
        """
        if QModelIndex.isValid():
            row = QModelIndex.row()
            sample_index = self.data_frame.index[row]
            return sample_index

    def get_sample_name(self, QModelIndex):
        """
        Get the name of a subsample located at a certain row

        Args:
            QModelIndex (QModelIndex) : Index of a cell in the table (only the row is important)
        """
        if QModelIndex.isValid():
            row = QModelIndex.row()
            sample_name = self.data_frame["sample_name"].iloc[row]
            return sample_name


class SubjectChecklist(QAbstractListModel):

    """
    A list of subjects with checkboxes

    Args:
        initial_list (list) : List of subject ids
        show_checks (bool) : If ``False`` no checkboxes will be shown
    """

    def __init__(self, initial_list=tuple(), show_checks=True):
        QAbstractListModel.__init__(self)
        self.__list = list(initial_list)
        self.__checked = frozenset()
        self.__show_checks = show_checks
        self.__highlight_subject = None

    @property
    def checked(self):
        """
        set of checked subjects
        """
        return self.__checked

    @checked.setter
    def checked(self, new_set):
        self.__checked = frozenset(int(s) for s in new_set)
        self.modelReset.emit()

    @property
    def highlighted_subject(self):
        return self.__highlight_subject

    @highlighted_subject.setter
    def highlighted_subject(self, subj):
        self.__highlight_subject = subj
        self.modelReset.emit()

    def set_list(self, lst):
        """
        Set the list of subjects

        Args:
            lst (list) : List of subject ids
        """
        self.__list = [int(s) for s in lst]
        self.modelReset.emit()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__list)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            try:
                name = self.__list[row]
            except IndexError:
                return None
            if int_role == QtCore.Qt.DisplayRole:
                return name
            if (int_role == QtCore.Qt.CheckStateRole) and self.__show_checks:
                if name in self.__checked:
                    return QtCore.Qt.Checked
                else:
                    return QtCore.Qt.Unchecked
            if int_role == QtCore.Qt.FontRole:
                if name == self.__highlight_subject:
                    font = QtGui.QFont()
                    font.setBold(True)
                    return font
            if int_role == QtCore.Qt.BackgroundRole:
                if name == self.__highlight_subject:
                    brush = QtGui.QBrush()
                    brush.setColor(QtGui.QColor("palegreen"))
                    brush.setStyle(QtCore.Qt.SolidPattern)
                    return brush

        return None

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            return flags
        return QtCore.Qt.NoItemFlags


class SubjectCheckTable(QAbstractTableModel):

    """
    A table of subjects with optional checkboxes

    Args:
        initial_list (list) : List of subject ids
        data_cols (list) : List of columns to shown, where each column is an iterable of the same length as the subject
            lists, such that the value for the subject in position *i* is also located at position *i*
        headers (list) : List of strings used as headers for the table on top of each data column
    """

    def __init__(self, initial_list=tuple(), data_cols=tuple(), headers=("", "")):
        QAbstractTableModel.__init__(self)
        assert len(data_cols) == len(headers) - 1
        self.__list = list(initial_list)
        self.__checked = set()
        self.__data = data_cols
        self.__headers = headers

    def set_data_cols(self, new_cols):
        """
        Sets new data columns

        Args:
            new_cols (list) : List of data columns, must have the same length as the headers. Each data column
                is itself an iterable of the same length and indices as the subjects list
        """
        assert len(new_cols) == len(self.__headers) - 1
        self.__data = new_cols
        self.modelReset.emit()

    @property
    def checked(self):
        """
        Set of checked subjects
        """
        return self.__checked

    @checked.setter
    def checked(self, new_set):
        self.__checked = set(new_set)
        self.modelReset.emit()

    def set_list(self, lst):
        self.__list = list(lst)
        self.modelReset.emit()

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        return len(self.__list)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 1 + len(self.__data)

    def data(self, QModelIndex, int_role=None):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            col = QModelIndex.column()
            if col == 0:
                try:
                    name = self.__list[row]
                except IndexError:
                    return None
                if int_role == QtCore.Qt.DisplayRole:
                    return name
                if int_role == QtCore.Qt.CheckStateRole:
                    if name in self.checked:
                        return QtCore.Qt.Checked
                    else:
                        return QtCore.Qt.Unchecked
            else:
                if int_role == QtCore.Qt.DisplayRole:
                    try:
                        return unicode(self.__data[col - 1][row])
                    except IndexError:
                        return None
                if int_role == QtCore.Qt.TextAlignmentRole:
                    return QtCore.Qt.AlignHCenter
        return None

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            row = QModelIndex.row()
            col = QModelIndex.column()
            flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            if col == 0:
                flags |= QtCore.Qt.ItemIsUserCheckable
            return flags
        return QtCore.Qt.NoItemFlags

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if int_role == QtCore.Qt.DisplayRole:
                return self.__headers[p_int]
            if int_role == QtCore.Qt.TextAlignmentRole:
                if p_int > 0:
                    return QtCore.Qt.AlignHCenter
                else:
                    return QtCore.Qt.AlignLeft
        return None

    def setData(self, QModelIndex, QVariant, int_role=None):
        if QModelIndex.isValid():
            col = QModelIndex.column()
            row = QModelIndex.row()
            if col == 0 and int_role == QtCore.Qt.CheckStateRole:
                value = QVariant == QtCore.Qt.Checked
                name = self.__list[row]
                if value is True:
                    self.checked.add(name)
                else:
                    self.checked.remove(name)
                self.dataChanged.emit(QModelIndex, QModelIndex)
                return True
        return False


if __name__ == "__main__":
    import braviz

    reader = braviz.readAndFilter.BravizAutoReader()
    test_tree = StructureTreeModel(reader)
