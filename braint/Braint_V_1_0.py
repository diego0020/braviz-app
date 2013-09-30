from Tkinter import *
from tkFileDialog import askopenfile

import BraintProperties


class MainFrame:
    
    def __init__(self, myParent):
        self.braintProperties = BraintProperties.BraintProperties()
        self.container = Frame(myParent)
        menubar = Menu(myParent)
        
        menuFile = Menu(menubar, tearoff = 0)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileLoadRDF'), command = self.loadRdf)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileConnect'), command = self.connect)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileClose'), command = myParent.quit)
        menubar.add_cascade(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFile'), menu = menuFile)
        
        #display the menu
        myParent.config(menu=menubar)
    
    def loadRdf(self):
        rdfFileName = askopenfile()
        print rdfFileName
        
    def connect(self):
        print "connect"

        
root = Tk()
mainFrame = MainFrame(root)
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (w, h))
root.wm_title("Braint V 1.0")
root.mainloop()