from PyQt4 import QtCore, QtGui
import logging

from PyQt4.QtGui import QMainWindow

from braviz.interaction.qt_guis.relation_viewer import Ui_RelationshipViewer
from braviz.interaction import braint_tree
from braviz.interaction import qt_models

from braviz.readAndFilter import tabular_data, braint_db
from functools import partial as partial_f
from braviz.interaction.qt_dialogs import NewVariableDialog

__author__ = 'Diego'


class RelationShipViewer(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.__big_tree_model = braint_tree.BraintTree()
        self.__rels_model = braint_tree.BraintTreeWithCount()
        self.__vars_list = qt_models.VarListModel()
        self.__vars_list.internal_data.insert(0,"NONE")
        self.__current_rel_source = None
        self.load_gui()

    def reset_tree_views(self):
        self.ui.add_source_tree.expandToDepth(3)
        self.ui.add_dest_tree.expandToDepth(3)
        self.ui.view_source_tree.expandToDepth(3)
        self.ui.view_rel_tree.expandToDepth(3)
        self.ui.link_tree.expandToDepth(3)



    def load_gui(self):
        self.ui = Ui_RelationshipViewer()
        self.ui.setupUi(self)
        self.ui.add_father_tree.setModel(self.__big_tree_model)
        self.ui.db_names_list.setModel(self.__vars_list)
        self.ui.add_var_button.clicked.connect(self.add_variable)
        self.ui.add_father_tree.customContextMenuRequested.connect(partial_f(self.show_remove_node_context,
                                                                            self.ui.add_father_tree))
        self.ui.new_var_button.clicked.connect(self.create_new_variable)
        self.ui.add_source_tree.setModel(self.__big_tree_model)
        self.ui.add_dest_tree.setModel(self.__big_tree_model)
        self.ui.add_source_tree.expandToDepth(3)
        self.ui.add_dest_tree.expandToDepth(3)

        self.ui.add_rel_button.clicked.connect(self.add_relation)

        self.ui.view_source_tree.setModel(self.__big_tree_model)
        self.ui.view_source_tree.expandToDepth(3)

        self.ui.view_rel_tree.setModel(self.__rels_model)
        self.ui.rels_label.setText("Relationships from <None>:")
        self.ui.view_source_tree.clicked.connect(self.update_relations)
        self.ui.view_source_tree.activated.connect(self.update_relations)
        self.ui.view_rel_tree.expandToDepth(3)
        self.ui.view_rel_tree.customContextMenuRequested.connect(self.show_remove_relation_context)

        self.ui.link_tree.setModel(self.__big_tree_model)
        self.ui.link_var_list.setModel(self.__vars_list)
        self.ui.link_tree.clicked.connect(self.update_link)
        self.ui.link_tree.activated.connect(self.update_link)
        self.ui.link_tree.expandToDepth(3)
        self.ui.save_link_button.clicked.connect(self.save_link)

        self.ui.tabWidget.currentChanged.connect(self.page_change)

    def add_variable(self):
        father_idx = self.ui.add_father_tree.currentIndex()
        father_node = self.__big_tree_model.get_node(father_idx)
        if not father_idx.isValid():
            father_id = None
        else:
            father_id = father_node.var_id
        pretty_name = str(self.ui.pretty_name.text())
        tab_var_idx = self.ui.db_names_list.currentIndex()
        tab_var_name = str(self.__vars_list.data(tab_var_idx,QtCore.Qt.DisplayRole))
        if not tab_var_idx.isValid():
            tab_var_id = None
        elif tab_var_name == "NONE":
            tab_var_id = None
        else:
            tab_var_id = tabular_data.get_var_idx(tab_var_name)
        new_id=braint_db.add_variable(father_id,pretty_name,tab_var_id)
        self.reset_tree()

        ants = self.__big_tree_model.get_antecessors(new_id)
        for n in ants:
            self.ui.add_father_tree.expand(n)

    def create_new_variable(self):
        dialog = NewVariableDialog()
        dialog.exec_()
        self.__vars_list.update_list()

    def reset_tree(self):
        self.__big_tree_model.fill_from_db()
        self.__rels_model.fill_from_db()
        self.reset_tree_views()

    def show_remove_node_context(self,caller,pos):
        current_node_index = caller.currentIndex()
        if not current_node_index.isValid():
            return
        current_node = self.__big_tree_model.get_node(current_node_index)
        label = current_node.label
        def delete_node(var_idx):
            print "deleting"
            parent = braint_db.get_var_parent(var_idx)
            braint_db.delete_node(var_idx)
            self.__big_tree_model.clear()
            self.__big_tree_model.fill_from_db()
            ants = self.__big_tree_model.get_antecessors(parent)
            self.reset_tree_views()
            for n in ants:
                caller.expand(n)

        menu = QtGui.QMenu("Remove Node")
        delete_node_action = QtGui.QAction("delete %s"%label,caller)
        delete_node_action.triggered.connect(partial_f(delete_node,current_node.var_id))
        menu.addAction(delete_node_action)
        global_pos = caller.mapToGlobal(pos)
        menu.exec_(global_pos)

    def show_remove_relation_context(self,pos):
        current_node_index = self.ui.view_rel_tree.currentIndex()
        if not current_node_index.isValid():
            return
        current_node = self.__rels_model.get_node(current_node_index)
        label = current_node.label
        dest_var_id = current_node.var_id
        if not self.__rels_model.direct_relation(dest_var_id):
            return
        origin_idx = self.__current_rel_source
        def delete_rel(dest_var_idx):
            message = "deleting relation between %s and %s"%(origin_idx,dest_var_idx)
            self.statusBar().showMessage(message,1000)
            braint_db.delete_relation(origin_idx,dest_var_idx)
            self.update_relations()


        menu = QtGui.QMenu("Remove Relation")
        delete_rel_action = QtGui.QAction("delete relation to%s"%label,menu)
        delete_rel_action.triggered.connect(partial_f(delete_rel,current_node.var_id))
        menu.addAction(delete_rel_action)
        global_pos = self.ui.view_rel_tree.mapToGlobal(pos)
        menu.exec_(global_pos)

    def add_relation(self):
        origin_index = self.ui.add_source_tree.currentIndex()
        if not origin_index.isValid():
            return
        dest_index = self.ui.add_dest_tree.currentIndex()
        if not dest_index.isValid():
            return
        origin_id = int(self.__big_tree_model.get_node(origin_index).var_id)
        dest_id = int(self.__big_tree_model.get_node(dest_index).var_id)
        ambiguous = bool(self.ui.ambi_check.isChecked())
        message = "adding relationship from %s to %s"%(origin_id,dest_id)
        message += "ambi" if ambiguous else "not ambi"
        braint_db.add_relation(origin_id,dest_id,ambiguous)
        self.statusBar().showMessage(message,1000)

    def update_relations(self,index=None):
        if index is not None:
            node = self.__big_tree_model.get_node(index)
            self.ui.rels_label.setText("Relationships from %s:"%node.label)
            self.__current_rel_source = node.var_id
        var_id = self.__current_rel_source
        rels = braint_db.get_relations_count(var_id,aggregate=True)
        direct_rels = braint_db.get_relations_count(var_id,aggregate=False)
        self.__rels_model.set_count(rels,direct_rels)
        self.aux_update_tree(self.__rels_model.root)


    def aux_update_tree(self,node):
        #update me
        idx = self.__rels_model.get_node_index(node,1)
        idx2 = self.__rels_model.get_node_index(node,0)
        self.ui.view_rel_tree.update(idx)
        self.ui.view_rel_tree.update(idx2)
        #update my kids
        for k in node.children:
            self.aux_update_tree(k)

    def update_link(self,index):
        node = self.__big_tree_model.get_node(index)
        node_id = node.var_id
        linked_var_name = braint_db.get_linked_var(node_id)
        if linked_var_name is None:
            linked_var_name = "NONE"
        self.__vars_list.set_highlighted(linked_var_name)
        i=self.__vars_list.internal_data.index(linked_var_name)
        ix=self.__vars_list.index(i,0)
        self.ui.link_var_list.scrollTo(ix)
        self.ui.link_var_list.dataChanged(ix,ix)


    def save_link(self):
        braint_index = self.ui.link_tree.currentIndex()
        if not braint_index.isValid():
            return
        var_index = self.ui.link_var_list.currentIndex()
        if not var_index.isValid():
            return
        braint_id = self.__big_tree_model.get_node(braint_index).var_id
        tab_name = str(self.__vars_list.data(var_index,QtCore.Qt.DisplayRole))
        if tab_name == "NONE":
            braint_db.delete_link(braint_id)
            message = "unlinking %s "%braint_id
            self.statusBar().showMessage(message,1000)
        else:
            tab_id = tabular_data.get_var_idx(tab_name)
            message = "linking %s with %s"%(braint_id,tab_id)
            self.statusBar().showMessage(message,1000)
            braint_db.save_link(braint_id,tab_id)
        self.update_link(braint_index)

    def page_change(self,index):
        self.__vars_list.set_highlighted("NONE")
        self.reset_tree_views()

def run():
    import sys
    from braviz.utilities import configure_logger
    configure_logger("anova_app")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = RelationShipViewer()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    run()
