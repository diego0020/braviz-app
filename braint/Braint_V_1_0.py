from Tkinter import *
import BraintProperties
from tkFileDialog import askopenfile
import os
import Tkinter as tk
import ttk
from kernel.RDFDBManagerClass import *

class MainFrame:
    
    def __init__(self, rootTk):
        w, h = rootTk.winfo_screenwidth(), rootTk.winfo_screenheight()
        self.braintProperties = BraintProperties.BraintProperties()
        self.container = Frame(rootTk)
        self.container.grid(row=0, sticky=W+E+N+S)
        #self.container.pack(expand=YES, fill=BOTH)
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
        self.topFrame.grid(row=0, column=0, sticky=W+E)
        #self.topFrame.pack(side = TOP, fill=BOTH, expand = YES)
        
                #Frame log
        self.logFrame = Frame(self.container, 
                              background = 'green',
                              borderwidth = 5,
                              relief = RIDGE,
                              height = h * 0.2)
        self.logFrame.grid(row=1, column=0, columnspan=3, rowspan=1, sticky=W+E)
        #self.logFrame.grid(row=2, column=0, columnspan=3, rowspan=1, sticky=W+E+N+S)
        #self.logFrame.pack(side = TOP, fill = X, expand = YES)
         
        self.focusFrame = Frame(self.topFrame, 
                                  background = 'red', 
                                  borderwidth = 5,
                                  relief = RIDGE,
                                  height = h * 0.8,
                                  width = w * 0.6)
        self.focusFrame.grid(row=0, column=0, sticky=W)
        #self.focusFrame.pack(side=LEFT,fill=Y,expand=YES,)
           
        self.contextFrame = Frame(self.topFrame, 
                                  background = 'yellow', 
                                  borderwidth = 5,
                                  relief = RIDGE,
                                  height = h * 0.8, ##Esto lo puse yo demas
                                  width = w * 0.2)
        self.contextFrame.grid(row=0, column=1, sticky=W)
        #self.contextFrame.pack(side=LEFT,fill=Y,expand=YES,)
        
        self.patientsFrame = Frame(self.topFrame, 
                                  background = 'blue', 
                                  borderwidth = 5,
                                  relief = RIDGE,
                                  height = h * 0.8, ##Esto lo puse yo demas
                                  width = w * 0.2)
        self.patientsFrame.grid(row=0, column=2, sticky=W)
        #self.patientsFrame.pack(side=LEFT,fill=Y,expand=YES)
           
        
           
        testList = Listbox(self.patientsFrame)
        testList.grid(row=2, column=2, sticky=S)
        #testList.pack(side=LEFT, fill=NONE, expand=1, anchor=CENTER)
        for i in range(20):
            testList.insert(END, str(i))
                
        ##SUFROOOO
                 
        
        self.get_tree_hierarchy()     
                      
                  
    def get_tree_hierarchy(self):
                 
            my_tree = ttk.Treeview(self.patientsFrame)
            ysb = ttk.Scrollbar(self.patientsFrame, orient='vertical', command=my_tree.yview)
            xsb = ttk.Scrollbar(self.patientsFrame, orient='horizontal', command=my_tree.xview)
            my_tree.configure(yscroll=ysb.set, xscroll=xsb.set)
            my_tree.heading('#0', text='BraInt Hierarchy', anchor='w')
            abspath = 'BraInt'
            parent=my_tree.insert('', 'end', text=abspath, open=True)
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            listResults=self.myManager.loadQuery('File\\rdfqueries\OnlyTSTSSTNames')
            itemsAdd = dict()
            for miItem in listResults:
                xValue = miItem['Evaluation']['value']
                if xValue not in itemsAdd:
                   id= my_tree.insert(parent, 'end', text=xValue, open=False)
                   itemsAdd.update({xValue:id})
                if 'TestName' in miItem:
                    yValue=miItem['TestName']['value']
                    if yValue not in itemsAdd:
                       EvalId=itemsAdd[xValue]
                       idTest=my_tree.insert(EvalId, 'end', text=yValue, open=False)
                       itemsAdd.update({yValue:idTest})
                if 'SubTestName' in miItem:
                    zValue=miItem['SubTestName']['value']
                    if zValue not in itemsAdd:
                       TestId=itemsAdd[yValue]
                       idSubTest=my_tree.insert(TestId, 'end', text=zValue, open=False)
                       itemsAdd.update({zValue:idSubTest})
                if 'SubSubTestName' in miItem:
                    wValue=miItem['SubSubTestName']['value']
                    if wValue not in itemsAdd:
                       SubTestId=itemsAdd[zValue]
                       idSubSubTest=my_tree.insert(SubTestId, 'end', text=wValue, open=False)
                       itemsAdd.update({wValue:idSubSubTest})
            my_tree.grid(row=0, column=2, sticky=N)
            ysb.grid(row=0, column=3, sticky=N+S)
            xsb.grid(row=1, column=2, sticky=E+W)
            #my_tree.pack(side=LEFT, fill=X, expand=1, anchor=NW)          
                  
                  
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