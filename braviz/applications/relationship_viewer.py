from PyQt4 import QtCore, QtGui
import logging

from PyQt4.QtGui import QMainWindow

from braviz.interaction.qt_guis.relation_viewer import Ui_RelationshipViewer
from braviz.interaction import braint_tree
from braviz.interaction import qt_models

from braviz.readAndFilter import tabular_data, braint_db
from functools import partial as partial_f

__author__ = 'Diego'


class RelationShipViewer(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.__big_tree_model = braint_tree.BraintTree()
        self.__vars_list = qt_models.VarListModel()
        self.__vars_list.internal_data.insert(0,"NONE")
        self.load_gui()


    def load_gui(self):
        self.ui = Ui_RelationshipViewer()
        self.ui.setupUi(self)
        self.ui.add_father_tree.setModel(self.__big_tree_model)
        self.ui.db_names_list.setModel(self.__vars_list)
        self.ui.add_var_button.clicked.connect(self.add_variable)
        self.ui.add_father_tree.customContextMenuRequested.connect(partial_f(self.show_remove_context,
                                                                            self.ui.add_father_tree))
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


    def reset_tree(self):
        self.__big_tree_model.fill_from_db()

    def show_remove_context(self,caller,pos):
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
            for n in ants:
                caller.expand(n)





        menu = QtGui.QMenu("Remove Node")
        delete_node_action = QtGui.QAction("delete %s"%label,caller)
        delete_node_action.triggered.connect(partial_f(delete_node,current_node.var_id))
        menu.addAction(delete_node_action)
        global_pos = caller.mapToGlobal(pos)
        menu.exec_(global_pos)

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
