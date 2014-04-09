from __future__ import division
__author__ = 'Diego'

from PyQt4 import QtCore
from PyQt4 import QtGui


class RotatedLabel(QtGui.QLabel):
    def __init__(self,parent):
        super(RotatedLabel,self).__init__(parent)
        self.color = (255,0,0)

    def set_color(self,color):
        if color is not None:
            self.color = color
        else:
            self.color = (0,0,0)
    def paintEvent(self, QPaintEvent):
        color = self.color
        painter = QtGui.QPainter(self)
        painter.save()
        painter.setPen(QtCore.Qt.black)
        text = self.text()
        font = painter.font()
        font.setPointSize(12)
        painter.setFont(font)
        fm=QtGui.QFontMetrics(painter.font())
        #print "g:",self.rect()
        #print "t:",fm.boundingRect(text)
        g=self.rect()
        x=g.width()/2  + (fm.ascent()/2)
        #-10 is for the square
        y=g.height()/2 + fm.width(text)/2-10
        #print "x:",x
        painter.translate(x,y)
        painter.rotate(270)
        qcolor = QtGui.QColor(color)
        painter.fillRect(QtCore.QRect(-1*fm.height(),-1*fm.ascent()+2,20,20),qcolor)
        painter.drawText(QtCore.QPoint(0,0),text)
        painter.restore()

