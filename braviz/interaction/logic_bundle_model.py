
__author__ = 'Diego'

import PyQt4.QtCore as QtCore
from PyQt4.QtCore import QAbstractItemModel
import logging
from braviz.readAndFilter import geom_db, tabular_data
import vtk


class LogicBundleNode(object):
    """
    A node for a bundle based on a logical hierarchy

    See :func:`braviz.readAndFilter.bundles_db.get_logic_bundle_dict` for more information

    Args:
        parent (braviz.interaction.logic_bundle_model.LogicBundleNode) : Reference to parent node, ``None`` if root
        son_number (int) : Number of siblings before the current node
        node_type (int) : Type of the current node. May be 0 for logic, 1 for structure or 2 for roi
        value : Logical operation for logic nodes, or structure name for structure nodes
        extra_data (int) : Roi database index for roi nodes
    """
    LOGIC = 0
    STRUCT = 1
    ROI = 2

    def __init__(self, parent, son_number, node_type, value, extra_data=None):
        assert node_type in {self.LOGIC, self.STRUCT, self.ROI}
        self.__parent = parent
        self.__node_type = node_type
        self.__value = value
        self.__son_number = son_number
        self.__extra_data = extra_data
        # only logic may have children
        if self.__node_type == self.LOGIC:
            self.children = []
        else:
            self.children = tuple()
        pass

    def __str__(self):
        return self.__value

    def add_son(self, node_type, value, extra_data=None):
        """
        Add a son to the current node

        Args:
            node_type (int) : Node type of the new son
            value : Value for the new son
            extra_data : Extra data for the new son
        """
        new_son = LogicBundleNode(self, len(self.children), node_type, value, extra_data)
        assert self.__node_type == self.LOGIC
        self.children.append(new_son)
        return new_son

    @property
    def parent(self):
        """
        Parent node
        """
        return self.__parent

    @property
    def son_number(self):
        """
        Number of sons added before this one
        """
        return self.__son_number

    @property
    def node_type(self):
        """
        Type of this node, 0: Logical, 1: Structure or 2: Roi
        """
        return self.__node_type

    def decrease_son_number(self):
        """
        Decrease my son number, call this when an older brother is removed
        """
        self.__son_number -= 1
        assert self.__son_number >= 0


    def remove_kid(self, index):
        """
        Remove a child

        Younger brother numbers are updated

        Args:
            index (int) : number of son to remove
        """
        assert self.node_type == self.LOGIC
        self.children.pop(index)
        for s in self.children[index:]:
            s.decrease_son_number()

    def to_dict(self):
        """
        Transform the tree based at this node into a dictionary

        This allows for easy serialization (picking)
        """
        ans = dict()
        ans["node_type"] = self.node_type
        ans["value"] = self.__value
        ans["extra_data"] = self.__extra_data
        ans["children"] = [c.to_dict() for c in self.children]
        return ans

    @staticmethod
    def from_dict(values):
        """
        Construct a tree from a dictionary

        Args:
            values (dict) : Recursive dictionary with the following keys for each node:
                node_type, value, extra_data, children (each of them as another dictionary with these keys)

        Returns:
            The root node of the resulting tree
        """

        new_root = LogicBundleNode(None, 0, values["node_type"], values["value"],
                                   values["extra_data"])

        for k in values["children"]:
            new_root.add_son_from_dict(k)

        return new_root

    def add_son_from_dict(self, values):
        """
        Adds a son from a dictionary

        Args:
            values (dict) : Recursive dictionary with the following keys:
                node_type, value, extra_data, children (each of them as another dictionary with these keys)
        """
        new_son = self.add_son(values["node_type"], values["value"], values["extra_data"])
        for k in values["children"]:
            new_son.add_son_from_dict(k)

    def __iter__(self):
        yield self
        for k in self.children:
            # recuersively call in children
            # for i in k calls __iter__ in children k
            for i in k:
                yield i


class LogicBundleNodeWithVTK(LogicBundleNode):
    """
    Adds VTK drawing capabilities to the :class:`LogicBundleNode`

    Args:
        parent (braviz.interaction.logic_bundle_model.LogicBundleNode) : Reference to parent node, ``None`` if root
        son_number (int) : Number of siblings before the current node
        node_type (int) : Type of the current node. May be 0 for logic, 1 for structure or 2 for roi
        value : Logical operation for logic nodes, or structure name for structure nodes
        extra_data (int) : Roi database index for roi nodes
        reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object to get data from
        subj : Subject index for the subject fibers you want to draw
        space : Coordinate systems in which you want the drawing.
            See :meth:`braviz.readAndFilter.base_reader.BaseReader.get`

    """
    def __init__(self, parent, son_number, node_type, value, extra_data=None, reader=None, subj=None, space="World"):
        LogicBundleNode.__init__(self, parent, son_number, node_type, value, extra_data=extra_data)
        self.__reader = reader
        self.subj = subj
        self.space = space
        self.__value = value
        subj_img = subj
        if node_type == self.LOGIC:
            self.__prop = None
        elif node_type == self.STRUCT:
            if subj is not None:
                try:
                    self.__pd = reader.get("MODEL", subj_img, name=value, space=space)
                except Exception:
                    self.__pd = None
            else:
                self.__pd = None
            self.__mapper = vtk.vtkPolyDataMapper()
            self.__prop = vtk.vtkActor()
            self.__prop.SetMapper(self.__mapper)
            if self.__pd is not None:
                self.__mapper.SetInputData(self.__pd)
                self.prop.SetVisibility(1)
            else:
                self.prop.SetVisibility(0)
        elif node_type == self.ROI:
            self.__roi_id = extra_data
            self.__mapper = vtk.vtkPolyDataMapper()
            self.__prop = vtk.vtkActor()
            self.__prop.SetMapper(self.__mapper)
            self.__sphere_source = vtk.vtkSphereSource()
            RESOLUTION = 20
            self.__sphere_source.SetThetaResolution(RESOLUTION)
            self.__sphere_source.SetPhiResolution(RESOLUTION)
            self.__sphere_source.LatLongTessellationOn()
            sphere_data = geom_db.load_sphere(extra_data, subj)
            if sphere_data is None:
                self.prop.SetVisibility(0)
            else:
                r, x, y, z = sphere_data
                self.prop.SetVisibility(1)

                self.__sphere_source.SetRadius(r)
                self.__sphere_source.SetCenter(x, y, z)
                self.__sphere_source.Update()
                # coordinates
                source_coords = geom_db.get_roi_space(roi_id=extra_data)
                # source -> world
                self.__sphere_world = reader.transform_points_to_space(self.__sphere_source.GetOutput(), source_coords,
                                                                    subj_img, inverse=True)
                # world -> current
                self.__sphere_current = reader.transform_points_to_space(self.__sphere_world, self.space,
                                                                      subj_img, inverse=False)
                self.__mapper.SetInputData(self.__sphere_current)
        else:
            raise Exception("Wrong type")

    def remove_kid(self, index):
        LogicBundleNode.remove_kid(self, index)

    def add_son(self, node_type, value, extra_data=None):
        assert self.node_type == self.LOGIC
        new_son = LogicBundleNodeWithVTK(self, len(self.children), node_type, value, extra_data, self.__reader,
                                         self.subj, self.space)
        self.children.append(new_son)
        return new_son

    def __update_sphere(self, subj, space):
        sphere_data = geom_db.load_sphere(self.__roi_id, subj)
        reader = self.__reader
        subj_img = subj
        self.space = space
        if sphere_data is None:
            self.prop.SetVisibility(0)
        else:
            r, x, y, z = sphere_data
            self.__sphere_source.SetRadius(r)
            self.__sphere_source.SetCenter(x, y, z)
            self.__sphere_source.Update()
            # coordinates
            try:
                source_coords = geom_db.get_roi_space(roi_id=self.__roi_id)
                # source -> world
                self.__sphere_world = reader.transform_points_to_space(self.__sphere_source.GetOutput(), source_coords,
                                                                    subj_img, inverse=True)

                # world -> current
                self.__sphere_current = reader.transform_points_to_space(self.__sphere_world, self.space,

                                                                      subj_img, inverse=False)
            except Exception:
                self.prop.SetVisibility(0)
            else:
                self.__mapper.SetInputData(self.__sphere_current)
                self.prop.SetVisibility(1)

    def __update_struct(self, subj, space):
        reader = self.__reader
        subj_img = subj
        try:
            self.__pd = reader.get("MODEL", subj_img, name=self.__value, space=space)
        except Exception:
            self.__pd = None
            self.prop.SetVisibility(0)
        else:
            self.__mapper.SetInputData(self.__pd)
            self.prop.SetVisibility(1)


    def update(self, subj, space):
        """
        Change subject or coordinate system

        Args:
            subj : New subject id
            space: New coordinate system
                See :meth:`braviz.readAndFilter.base_reader.BaseReader.get`
        """
        for c in self.children:
            c.update(subj, space)
        self.space = space
        self.subj = subj
        if self.node_type == self.STRUCT:
            self.__update_struct(subj, space)
        elif self.node_type == self.ROI:
            self.__update_sphere(subj, space)

    @property
    def prop(self):
        """
        Get the :obj:`vtkProp` for the bundle
        """
        return self.__prop

    def set_opacity(self, int_opac):
        """
        Sets the opacity of the actor

        Args:
            int_opac (int) : From 0 to 100 where 0 is invisible and 100 is opaque
        """
        if self.node_type == self.LOGIC:
            for i in self.children:
                i.set_opacity(int_opac)
        else:
            self.prop.GetProperty().SetOpacity(int_opac / 100.0)

    def set_color(self, color):
        """
        Set color for the actor

        Args:
            color (tuple) : RGB components of the color
        """
        if self.node_type == self.LOGIC:
            for i in self.children:
                i.set_color(color)
        else:
            self.prop.GetProperty().SetColor(*color)

    @staticmethod
    def vtk_from_dict(values, reader, subj=None, space="World"):
        """
        Create a tree from a recursive dictionary

        Args:
            values (dict) : Recursive dictionary with the following keys for each node:
                node_type, value, extra_data, children (each of them as another dictionary with these keys)
            reader (braviz.readAndFilter.base_reader.BaseReader) : Reader object to get data from
            subj : Subject index for the subject fibers you want to draw
            space : Coordinate systems in which you want the drawing.
                See :meth:`braviz.readAndFilter.base_reader.BaseReader.get`

        Returns:
            The root node of the resulting tree
        """

        new_root = LogicBundleNodeWithVTK(None, 0, values["node_type"], values["value"],
                                          values["extra_data"], reader, subj, space)

        for k in values["children"]:
            new_root.add_son_from_dict(k)

        return new_root


class LogicBundleQtTree(QAbstractItemModel):
    """
    A Qt representation of a logical fiber bundle

    Args:
        root (braviz.interaction.logic_bundle_model.LogicBundleNode) : Root of the logic bundle tree
    """
    def __init__(self, root=None):
        QAbstractItemModel.__init__(self)
        if root is None:
            self.__root = LogicBundleNode(None, 0, LogicBundleNode.LOGIC, "AND")
        else:
            assert isinstance(root, LogicBundleNode)
            self.__root = root

        self.__id_index = dict()
        self.__id_index[id(self.__root)] = self.__root

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
            # root
            index = self.createIndex(0, 0, id(self.__root))
            assert index.isValid()
            return index

    def __get_node_index(self, node):
        index = self.createIndex(node.son_number, 0, id(node))
        assert index.isValid()
        return index

    def add_node(self, parent, node_type, value, extra_data=None):
        """
        Add a son to an specific node in the tree

        Args:
            parent (braviz.interaction.logic_bundle_model.LogicBundleNode) : Node to which the son will be added
            node_type (int) : Type of the new node
            value : Value of the new node
            extra_data : Extra data for the new node
        """
        self.beginResetModel()
        new_node = parent.add_son(node_type, value, extra_data)
        self.__id_index[id(new_node)] = new_node
        self.endResetModel()
        return new_node

    def remove_node(self, index):
        """
        Remove a node from the tree

        Args:
            index (QAbstractModelIndex) : Index of node to remove
        """
        self.beginResetModel()
        if not index.isValid():
            return
        node = self.__id_index[index.internalId()]
        self.__remove_node(node)
        self.modelAboutToBeReset.emit()
        self.endResetModel()

    def get_node(self, index):
        """
        Get the node at a given index

        Args:
            index (QAbstractModelIndex) : Index of a node
        """
        if index.isValid():
            i = index.internalId()
            return self.__id_index[i]
        else:
            return None

    def __remove_node(self, node):
        # remove kids
        for k in reversed(node.children):
            self.__remove_node(k)
        # remove from parent
        parent = node.parent
        if parent is not None:
            parent.remove_kid(node.son_number)
        # remove from index
        del self.__id_index[id(node)]

    def set_root(self, new_root):
        """
        Sets a new tree for the model

        Args:
            new_root (braviz.interaction.logic_bundle_model.LogicBundleNode) : Root of new tree
        """
        # remove everything
        self.beginResetModel()
        self.__remove_node(self.__root)
        self.__root = new_root
        assert len(self.__id_index) == 0
        self._rebuild_index(self.__root)
        self.endResetModel()

    def _rebuild_index(self, node):
        self.__id_index[id(node)] = node
        for c in node.children:
            self._rebuild_index(c)


    @property
    def root(self):
        """
        root node of the underlying tree
        """
        return self.__root

