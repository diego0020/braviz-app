__author__ = 'Diego'

import PyQt4.QtGui as QtGui
from PyQt4.QtGui import QMainWindow

#load gui
from braviz.interaction.qt_guis.anova import Ui_Anova_gui
from braviz.interaction.qt_guis.outcome_select import Ui_SelectOutcomeDialog

class anova_app(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setup_gui()
    def setup_gui(self):
        self.ui=Ui_Anova_gui()
        self.ui.setupUi(self)
        self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
    def dispatch_outcome_select(self):

        print "outcome select %s / %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count()-1:
            print "dispatching dialog"
            dialog=QtGui.QDialog()
            dialog_ui=Ui_SelectOutcomeDialog()
            dialog_ui.setupUi(dialog)
            selection=dialog.exec_()


if __name__ == '__main__':
    import sys
    app=QtGui.QApplication(sys.argv)
    main_window=anova_app()
    main_window.show()
    app.exec_()
