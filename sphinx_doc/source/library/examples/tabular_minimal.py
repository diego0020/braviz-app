from braviz.readAndFilter import tabular_data
from braviz.visualization.matplotlib_qt_widget import MatplotWidget
from PyQt4 import QtCore, QtGui

app=QtGui.QApplication([])
df = tabular_data.get_data_frame_by_name(["BIRTH_peso5","BIRTH_ballar5"])
mp = MatplotWidget()
mp.draw_scatter(df,"BIRTH_peso5","BIRTH_ballar5")
mp.highlight_id(119)
mp.show()
app.exec_()

