from Tkinter import *
import BraintProperties
from tkFileDialog import askopenfile

class MainFrame:
    
    def __init__(self, rootTk):
        w, h = rootTk.winfo_screenwidth(), rootTk.winfo_screenheight()
        self.braintProperties = BraintProperties.BraintProperties()
        self.container = Frame(rootTk)
        self.container.pack(expand=YES, fill=BOTH)
        menubar = Menu(rootTk)
        
        menuFile = Menu(menubar, tearoff = 0)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileLoadRDF'), command = self.loadRdf)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileConnect'), command = self.connect)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileClose'), command = rootTk.quit)
        menubar.add_cascade(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFile'), menu = menuFile)
        
        #display the menu
        rootTk.config(menu=menubar)
        
        #Frames in GUI
        self.topFrame = Frame(self.container, bg = 'cyan', height = h * 0.8)
        self.topFrame.pack(side = TOP, fill=BOTH, expand = YES)
        
                #Frame log
        self.logFrame = Frame(self.container, 
                              background = 'green',
                              borderwidth = 5,
                              relief = RIDGE,
                              height = h * 0.2)
        self.logFrame.pack(side = TOP, fill = X, expand = YES)
        
        self.focusFrame = Frame(self.topFrame, 
                                  background = 'red', 
                                  borderwidth = 5,
                                  relief = RIDGE,
                                  height = h * 0.8,
                                  width = w * 0.6)
        self.focusFrame.pack(side=LEFT,fill=Y,expand=YES,)
          
        self.contextFrame = Frame(self.topFrame, 
                                  background = 'yellow', 
                                  borderwidth = 5,
                                  relief = RIDGE,
                                  width = w * 0.2)
        self.contextFrame.pack(side=LEFT,fill=Y,expand=YES,)
  
        self.patientsFrame = Frame(self.topFrame, 
                                  background = 'blue', 
                                  borderwidth = 5,
                                  relief = RIDGE,
                                  width = w * 0.2)
        self.patientsFrame.pack(side=LEFT,fill=Y,expand=YES)
        

        
        testList = Listbox(self.patientsFrame)
        testList.pack(side=LEFT, fill=NONE, expand=1, anchor=CENTER)
        for i in range(20):
            testList.insert(END, str(i))
             
        #=======================================================================
        # button = Button(self.patientsFrame, text = 'X')
        # button.pack(side=LEFT, fill=NONE, expand=0, anchor=CENTER)
        #=======================================================================
            
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