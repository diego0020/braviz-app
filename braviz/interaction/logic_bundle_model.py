__author__ = 'Diego'

import PyQt4.QtCore as QtCore
from PyQt4.QtCore import QAbstractItemModel
import logging

NODE_TYPES = {"LOGIC":0,"STRUCT":1,"ROI":2}
NODE_TYPES_I = {0:"LOGIC",1:"STRUCT",2:"ROI"}

class LogicBundleNode:
    def __init__(self,parent,son_number,node_type,value,extra_data=None):
        self.__parent = parent
        if isinstance(node_type,str):
            node_type = NODE_TYPES[node_type]
        self.__node_type = int(node_type)
        self.__value = value
        self.__son_number = son_number
        self.__extra_data = extra_data
        self.children = []
        pass

    def __str__(self):
        return self.__value

    def add_son(self,logic,value,extra_data = None):
        new_son = LogicBundleNode(self,len(self.children),logic,value,extra_data)
        self.children.append(new_son)
        return new_son

    @property
    def parent(self):
        return self.__parent

    @property
    def son_number(self):
        return self.__son_number

    def decrease_son_number(self):
        """
        When a brother is removed
        """
        self.__son_number -= 1
        assert self.__son_number >= 0


    def remove_kid(self,index):
        self.children.pop(index)
        for s in self.children[index:]:
            s.decrease_son_number()






class LogicBundleQtTree(QAbstractItemModel):
    def __init__(self):
        QAbstractItemModel.__init__(self)
        self.__root = LogicBundleNode(None,0,True,"AND")
        self.__id_index=dict()
        self.__id_index[id(self.__root)]=self.__root

    def parent(self, QModelIndex=None):
        nid = QModelIndex.internalId()
        node = self.__id_index[nid]
        p = node.parent
        if p is None:
            return QtCore.QModelIndex()
        else:
            return self.__get_node_index(p)

    def rowCount(self, QModelIndex_parent=None, *args, **kwargs):
        if QModelIndex_parent.isValid():
            inid = QModelIndex_parent.internalId()
            parent = self.__id_index[inid]
            return len(parent.children)
        else:
            #root
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

        return QtCore.QVariant()

    def index(self, p_int, p_int_1, QModelIndex_parent=None, *args, **kwargs):
        if QModelIndex_parent.isValid():
            nid = QModelIndex_parent.internalId()
            parent = self.__id_index[nid]
            if p_int_1 == 0:
                if 0 <= p_int < len(parent.children):
                    child = parent.children[p_int]
                    index = self.__get_node_index(child)
                    return index
        else:
            #root
            index = self.createIndex(0,0,id(self.__root))
            assert index.isValid()
            return index

    def __get_node_index(self, node):
        index = self.createIndex(node.son_number, 0, id(node))
        assert index.isValid()
        return index

    def add_node(self,parent_index,node_type,value,extra_data = None):
        if not parent_index.isValid():
            parent = self.__root
        else:
            parent = self.__id_index[parent_index.internalId()]
        self.beginResetModel()
        new_node = parent.add_son(node_type,value,extra_data)
        self.__id_index[id(new_node)]=new_node
        self.endResetModel()
        return self.__get_node_index(new_node)

    def remove_node(self,index):
        self.beginResetModel()
        if not index.isValid():
            return
        node = self.__id_index[index.internalId()]
        self.__remove_node(node)
        self.modelAboutToBeReset.emit()
        self.endResetModel()

    def __remove_node(self,node):
        #remove kids
        for k in reversed(node.children):
            self.__remove_node(k)
        #remove from parent
        parent = node.parent
        parent.remove_kid(node.son_number)
        #remove from index
        del self.__id_index[id(node)]
