'''
Created on 10/10/2013

@author: jc.forero47
'''
import os
import Tkinter as tk
import ttk
from kernel.RDFDBManagerClass import *


class App(tk.Frame):
    def __init__(self, master, path):
        tk.Frame.__init__(self, master)
        self.my_tree = ttk.Treeview(self)
        ysb = ttk.Scrollbar(self, orient='vertical', command=self.my_tree.yview)
        xsb = ttk.Scrollbar(self, orient='horizontal', command=self.my_tree.xview)
        self.my_tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        self.my_tree.heading('#0', text='BraInt Hierarchy', anchor='w')

        abspath = 'BraInt'
        root_node = self.my_tree.insert('', 'end', text=abspath, open=True)
        self.process_directory(root_node)

        self.my_tree.grid(row=0, column=0,sticky='NSEW')
        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)
        ysb.grid(row=0, column=1, sticky='ns')
        xsb.grid(row=1, column=0, sticky='ew')

        self.grid()

    def process_directory(self, parent):
        self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
        listResults=self.myManager.loadQuery('File\\rdfqueries\OnlyTSTSSTNames')
        itemsAdd = dict()
        for miItem in listResults:
            xValue = miItem['Evaluation']['value']
            if xValue not in itemsAdd:
               id=self.my_tree.insert(parent, 'end', text=xValue, open=False)
               itemsAdd.update({xValue:id})
            if 'TestName' in miItem:
                yValue=miItem['TestName']['value']
                if yValue not in itemsAdd:
                   EvalId=itemsAdd[xValue]
                   idTest=self.my_tree.insert(EvalId, 'end', text=yValue, open=False)
                   itemsAdd.update({yValue:idTest})
            if 'SubTestName' in miItem:
                zValue=miItem['SubTestName']['value']
                if zValue not in itemsAdd:
                   TestId=itemsAdd[yValue]
                   idSubTest=self.my_tree.insert(TestId, 'end', text=zValue, open=False)
                   itemsAdd.update({zValue:idSubTest})
            if 'SubSubTestName' in miItem:
                wValue=miItem['SubSubTestName']['value']
                if wValue not in itemsAdd:
                   SubTestId=itemsAdd[zValue]
                   idSubSubTest=self.my_tree.insert(SubTestId, 'end', text=wValue, open=False)
                   itemsAdd.update({wValue:idSubSubTest})           

root = tk.Tk()
path_to_my_project = 'BraInt'
app = App(root, path=path_to_my_project)
app.grid(sticky="nsew")
root.rowconfigure(0,weight=1)
root.columnconfigure(0,weight=1)
app.mainloop()