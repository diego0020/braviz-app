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


from PyQt4.QtCore import QAbstractItemModel
from PyQt4 import QtCore, QtGui
from braviz.readAndFilter import braint_db
__author__ = 'Diego'


class BraintNode(object):
    def __init__(self, parent, son_number, label, var_id=None):
        self.__parent = parent
        self.__label = label
        self.__var_id = var_id
        self.__son_number = son_number
        # only logic may have children
        self.children = []

    def __str__(self):
        return str(self.__label)

    def add_son(self, label,var_id=None):
        new_son = BraintNode(self, len(self.children), label,var_id)
        self.children.append(new_son)
        return new_son

    @property
    def parent(self):
        return self.__parent

    @property
    def son_number(self):
        return self.__son_number

    @property
    def var_id(self):
        return self.__var_id

    @property
    def label(self):
        return self.__label
    @label.setter
    def label(self,value):
        self.__label = value

class BraintTree(QAbstractItemModel):
    def __init__(self):
        QAbstractItemModel.__init__(self)
        self.__root = BraintNode(None,0,"<root>",None)
        self.__id_index = dict()
        self.__id_index[id(self.__root)] = self.__root
        self.__var_id_index = {None: self.__root}
        self.fill_from_db()

    def parent(self, QModelIndex=None):
        nid = QModelIndex.internalId()
        node = self.__id_index[nid]
        p = node.parent
        if p is None:
            return QtCore.QModelIndex()
        else:
            return self.get_node_index(p)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        if QModelIndex_parent.isValid():
            inid = QModelIndex_parent.internalId()
            parent = self.__id_index[inid]
            return len(parent.children)
        else:
            # root
            return 1

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 1

    def data(self, QModelIndex, int_role=None):
        iid = QModelIndex.internalId()
        row = QModelIndex.row()
        node = self.__id_index[iid]
        assert node.son_number == row
        if int_role == QtCore.Qt.DisplayRole:
            return str(node)
        elif int_role == QtCore.Qt.ToolTipRole:
            desc = braint_db.get_description(node.var_id)
            if desc is not None:
                return desc

        return QtCore.QVariant()

    def index(self, p_int, p_int_1, QModelIndex_parent=None, *args, **kwargs):
        if QModelIndex_parent.isValid():
            nid = QModelIndex_parent.internalId()
            parent = self.__id_index[nid]
            if p_int_1 >= 0:
                if 0 <= p_int < len(parent.children):
                    child = parent.children[p_int]
                    index = self.get_node_index(child,p_int_1)
                    return index
        else:
            # root
            index = self.createIndex(0, p_int_1, id(self.__root))
            assert index.isValid()
            return index

    def get_node_index(self, node,col=0):
        index = self.createIndex(node.son_number, col, id(node))
        assert index.isValid()
        return index

    def add_node(self, parent, label,var_id=None):
        self.beginResetModel()
        new_node = parent.add_son(label, var_id)
        self.__id_index[id(new_node)] = new_node
        self.__var_id_index[var_id] = new_node
        self.endResetModel()
        return new_node

    def get_node(self, index):
        if index.isValid():
            i = index.internalId()
            return self.__id_index[i]
        else:
            return None

    @property
    def root(self):
        return self.__root

    def fill_from_db(self):
        self.beginResetModel()
        tuples = braint_db.get_all_variables()
        for var_id, label,father in tuples:
            if var_id in self.__var_id_index:
                pass # already in the tree
            else:
                father = self.__var_id_index.get(father)
                if father is None:
                    father = self.__root
                new_son=father.add_son(label,var_id)
                self.__id_index[id(new_son)]=new_son
                self.__var_id_index[var_id]=new_son
        self.endResetModel()

    def __get_antecessors(self,var_id):
        ans = []
        node = self.__var_id_index[var_id]
        if node.parent is None:
            return []
        ans.append(node.parent)
        ans.extend(self.__get_antecessors(node.parent.var_id))
        return ans

    def get_antecessors(self,var_id):
        nodes = self.__get_antecessors(var_id)
        nodes.append(self.__var_id_index[var_id])
        indexes = map(self.get_node_index,nodes)
        return indexes

    def __delete_sons(self,node):
        for c in reversed(node.children):
            self.__delete_sons(c)
        node.parent = None
        node.children = None
        del node
    def clear(self):
        self.beginResetModel()
        self.__delete_sons(self.__root)
        self.__id_index.clear()
        self.__var_id_index.clear()
        self.__root = BraintNode(None,0,"<root>")
        self.__id_index[id(self.__root)]=self.__root
        self.__var_id_index[None]=self.__root
        self.endResetModel()

    def aux_change_data(self,node):
        #update sons
        #update me
        idx  = self.get_node_index(node,0)
        self.modelAboutToBeReset.emit()
        self.dataChanged.emit(idx,idx)
        self.emit(QtCore.SIGNAL("dataChanged"),idx,idx)
        self.modelReset.emit()


class BraintTreeWithCount(BraintTree):
    def __init__(self):
        BraintTree.__init__(self)
        self.__count_dict = {}
        self.__direct_count_dict = {}

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 2

    def data(self, QModelIndex, int_role=None):
        row = QModelIndex.row()
        col = QModelIndex.column()
        node = self.get_node(QModelIndex)
        assert node.son_number == row
        if int_role == QtCore.Qt.DisplayRole:
            if col==0:
                return str(node)
            else:
                return self.__count_dict.get(node.var_id,0)
        elif int_role == QtCore.Qt.FontRole:
            count = self.__direct_count_dict.get(node.var_id,0)
            if count>0:
                font = QtGui.QFont()
                font.setBold(font.Bold)
                return font
        elif int_role == QtCore.Qt.ToolTipRole:
            desc = braint_db.get_description(node.var_id)
            if desc is not None:
                return desc
        return QtCore.QVariant()

    _header = ("Identifier","Relations")
    def headerData(self, p_int, Qt_Orientation, int_role=None):
        if Qt_Orientation == QtCore.Qt.Horizontal:
            if int_role == QtCore.Qt.DisplayRole:
                return self._header[p_int]
        return QtCore.QVariant()

    def set_count(self,counts,direct_counts = None):
        self.__count_dict=counts
        if direct_counts is None:
            self.__direct_count_dict = self.__count_dict
        else:
            self.__direct_count_dict = direct_counts
        self.aux_change_data(self.root)

    def aux_change_data(self,node):
        #update sons
        for k in node.children:
            self.aux_change_data(k)
        #update me
        idx  = self.get_node_index(node,1)
        self.emit(QtCore.SIGNAL("dataChanged"),idx,idx)

    def direct_relation(self,var_id):
        return self.__direct_count_dict.get(var_id,0)















