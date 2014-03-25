from __future__ import division

__author__ = 'Diego'

import PyQt4.QtCore as QtCore
from PyQt4.QtCore import QAbstractItemModel
from braviz.readAndFilter.link_with_rdf import cached_get_free_surfer_dict
from braviz.interaction.structural_hierarchy import get_structural_hierarchy_with_names


class StructureTreeNode:
    def __init__(self, parent=None, name="", son_number=0):
        self.parent_id = id(parent)
        self.parent = parent
        self.children = []
        self.tooltip = name
        self.name = name
        self.checked = QtCore.Qt.Unchecked
        self.leaf_name = None
        self.son_number = son_number

    def is_leaf(self):
        return len(self.children) == 0

    def add_child(self, name):
        child = StructureTreeNode(self, name, len(self.children))
        self.children.append(child)
        return child

    def check_and_update_tree(self, check=True):
        self.__check_and_propagate_down(check)
        self.__propagate_up()

    def __propagate_up(self):
        if self.parent is not None:
            self.parent.__update_from_children()

    def __check_and_propagate_down(self, check=True):
        self.checked = QtCore.Qt.Checked if check is True else QtCore.Qt.Unchecked
        for k in self.children:
            k.__check_and_propagate_down(check)

    def __update_from_children(self):
        #self.name += "*"
        previus_state = self.checked
        if len(self.children) == 0:
            return
        found_checked = False
        found_unchecked = False
        for k in self.children:
            state = k.checked
            if state == QtCore.Qt.Checked:
                found_checked = True
            if state == QtCore.Qt.Unchecked:
                found_unchecked = True
            if (state == QtCore.Qt.PartiallyChecked) or (found_checked and found_unchecked):
                self.checked = QtCore.Qt.PartiallyChecked
                if self.checked != previus_state:
                    self.__propagate_up()
                return
        if not found_unchecked:
            self.checked = QtCore.Qt.Checked
        else:
            self.checked = QtCore.Qt.Unchecked
        if self.checked != previus_state:
            self.__propagate_up()


class StructureTreeModel(QAbstractItemModel):
    selection_changed = QtCore.pyqtSignal()

    def __init__(self, reader, subj="144", dominant=False):
        super(StructureTreeModel, self).__init__()
        self.subj = subj
        self.reader = reader
        self.pretty_names = cached_get_free_surfer_dict(reader)
        self.hierarchy = None
        self.__id_index = {}
        self.__root = None
        self.leaf_ids = set()
        self.reload_hierarchy(subj, dominant)


    def reload_hierarchy(self, subj="144", dominant=False):
        # print "reloading hierarchy"
        # print
        self.leaf_ids=set()
        if dominant is True:
            self.hierarchy = get_structural_hierarchy_with_names(self.reader, subj, True, False, False)
        else:
            self.hierarchy = get_structural_hierarchy_with_names(self.reader, subj, False, True, False)
        self.__root = StructureTreeNode(None, "root")
        self.__id_index[id(self.__root)] = self.__root
        self.__load_sub_tree(self.__root, self.hierarchy)
        self.modelReset.emit()


    def __load_sub_tree(self, sub_root, hierarchy_dict):
        for k, v in sorted(hierarchy_dict.items(), key=lambda x: x[0]):
            new_node = sub_root.add_child(k)
            self.__id_index[id(new_node)] = new_node
            if isinstance(v, dict):
                self.__load_sub_tree(new_node, v)
            else:
                #is a leaf
                new_node.leaf_name = v
                new_node.tooltip = self.pretty_names.get(v, v)
                self.leaf_ids.add(id(new_node))

    def parent(self, QModelIndex=None):
        if QModelIndex.isValid():
            nid = QModelIndex.internalId()
            node = self.__id_index[nid]
            parent = node.parent
            if parent is None:
                #root node
                return QtCore.QModelIndex()
            #print "parent of %s is %s"%(node.name,parent.name)
            index = self.__get_node_index(parent)
            return index

        assert True

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        if QModelIndex_parent.isValid():
            nid = QModelIndex_parent.internalId()
            parent = self.__id_index[nid]
            return len(parent.children)
        #Start at second level
        return len(self.__root.children)

    def columnCount(self, QModelIndex_parent=None, *args, **kwargs):
        return 1

    def data(self, QModelIndex, int_role=None):

        nid = QModelIndex.internalId()
        row = QModelIndex.row()
        node = self.__id_index[nid]
        assert node.son_number == row
        #print "data", node.name
        if int_role == QtCore.Qt.DisplayRole:
            return node.name
        elif int_role == QtCore.Qt.ToolTipRole:
            return node.tooltip
        elif int_role == QtCore.Qt.CheckStateRole:
            #print node.name, node.checked
            return node.checked
        return QtCore.QVariant()

    def index(self, p_int, p_int_1, QModelIndex_parent=None, *args, **kwargs):
        if QModelIndex_parent.isValid():
            nid = QModelIndex_parent.internalId()
            parent = self.__id_index[nid]
            if p_int_1 == 0:
                if 0 <= p_int < len(parent.children):
                    child = parent.children[p_int]
                    #print "index", child.name
                    index = self.__get_node_index(child)
                    return index
        else:
            #asking for root nodes
            meta_root = self.__root
            if (0 <= p_int < len(meta_root.children)) and (p_int_1 == 0):
                #print "papasito"
                root = meta_root.children[p_int]
                index = self.__get_node_index(root)
                return index
        assert True

    def headerData(self, p_int, Qt_Orientation, int_role=None):
        pass

    def hasChildren(self, QModelIndex_parent=None, *args, **kwargs):
        if QModelIndex_parent.isValid():
            nid = QModelIndex_parent.internalId()
            node = self.__id_index[nid]
            return not node.is_leaf()
        return True

    def setData(self, QModelIndex, QVariant, int_role=None):
        if int_role == QtCore.Qt.CheckStateRole:
            nid = QModelIndex.internalId()
            node = self.__id_index[nid]
            assert node.son_number == QModelIndex.row()
            check = QVariant.toBool()
            node.check_and_update_tree(check)
            self.dataChanged.emit(QModelIndex, QModelIndex)
            #self.dataChanged.emit(QtCore.QModelIndex(), QtCore.QModelIndex())
            #print "signaling"
            self.emit(QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"), QModelIndex, QModelIndex)
            #parents
            self.__notify_parents(node)
            self.__notify_children(node)
            self.selection_changed.emit()
            return True
        return False

    def __notify_parents(self, node):
        parent = node.parent
        if parent is None:
            return
        index = self.__get_node_index(parent)
        #print "notifying", parent.name
        self.dataChanged.emit(index, index)
        self.emit(QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"), index, index)
        self.__notify_parents(parent)

    def __notify_children(self, node):
        if node.is_leaf():
            return
        first_children = node.children[0]
        last_children = node.children[-1]
        first_index = self.__get_node_index(first_children)
        last_index = self.__get_node_index(last_children)
        self.emit(QtCore.SIGNAL("DataChanged(QModelIndex,QModelIndex)"), first_index, last_index)

    def flags(self, QModelIndex):
        if QModelIndex.isValid():
            flags = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
            return flags
        return QtCore.Qt.NoItemFlags

    def __get_node_index(self, node):
        index = self.createIndex(node.son_number, 0, id(node))
        assert index.isValid()
        return index

    def get_selected_structures(self):
        selected_leaf_names = [self.__id_index[leaf].leaf_name for leaf in self.leaf_ids if
                               self.__id_index[leaf].checked == QtCore.Qt.Checked]
        # print "selected leafs names",selected_leaf_names
        # return selected_leaf_names

    def set_selected_structures(self,selected_list):
        for leaf in self.leaf_ids:
            node = self.__id_index[leaf]
            if node.leaf_name in selected_list:
                node.check_and_update_tree(True)
            else:
                node.check_and_update_tree(False)
        self.selection_changed.emit()
        self.modelReset.emit()


