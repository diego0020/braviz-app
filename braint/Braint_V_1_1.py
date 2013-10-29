from Tkinter import *
import BraintProperties
from tkFileDialog import askopenfile
import os
import Tkinter as tk
import ttk
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor
from kernel.RDFDBManagerClass import *

from ScatterPlotClass import ScatterPlotClass
from VolumeRendererClass import VolumeRendererClass
import braviz
from os.path import join as path_join 

class MainFrame(Frame):
    def __init__(self, rootTk):
        Frame.__init__(self, rootTk)
        self.grid()
        self.braintProperties = BraintProperties.BraintProperties()
       
        #self.container.pack(expand=YES, fill=BOTH)
        self.main_frame_root = rootTk
        menubar = Menu(self.main_frame_root)
        
        menuFile = Menu(menubar, tearoff = 0)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileLoadRDF'), command = self.load_rdf)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileConnect'), command = self.connect_to_repository)
        menuFile.add_command(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFileClose'), command = self.main_frame_root.quit)
        menubar.add_cascade(label = self.braintProperties.configLang.get('braint_V_1_0', 'menuFile'), menu = menuFile)
        
        #display the menu
        self.main_frame_root.config(menu=menubar)
        
        #self.topFrame.pack(side = TOP, fill=BOTH, expand = YES)
        
        for r in range(5):
            self.main_frame_root.rowconfigure(r, weight=1)    
        for c in range(6):
            self.main_frame_root.columnconfigure(c, weight=1)
                
        self.focusFrame = Frame(self.main_frame_root, background = 'red')
        self.focusFrame.grid(row=0, column=0, rowspan = 4, columnspan = 4, sticky = W+E+N+S)
        
        self.contextFrame = Frame(self.main_frame_root, background = 'yellow')
        self.contextFrame.grid(row=0, column=4, rowspan = 4, columnspan = 1, sticky = W+E+N+S)
        
        self.patientsFrame = Frame(self.main_frame_root, background = 'blue')
        self.patientsFrame.grid(row=0, column=5, rowspan = 4, columnspan = 1, sticky = W+E+N+S)
                
        self.logFrame = Frame(self.main_frame_root,background = 'green')
        self.logFrame.grid(row=4, column=0, rowspan= 1, columnspan=6, sticky = W+E+N+S)
        
        self.add_tree_hierarchy_to_frame(self.patientsFrame)
        self.add_vtk_plot_to_frame(self.focusFrame) 
        
        self.create_viewer_2(self.contextFrame)    
        
        self.main_frame_root.protocol("WM_DELETE_WINDOW", self.clean_exit)
                  
    def add_tree_hierarchy_to_frame(self, parent_frame):
                 
            self.my_tree = ttk.Treeview(parent_frame)
            ysb = ttk.Scrollbar(parent_frame, orient='vertical', command=self.my_tree.yview)
            xsb = ttk.Scrollbar(parent_frame, orient='horizontal', command=self.my_tree.xview)
            #self.my_tree.configure(yscroll=ysb.set, xscroll=xsb.set)
            self.my_tree.heading('#0', text='BraInt Hierarchy', anchor='w')
            abspath = 'BraInt'
            parent=self.my_tree.insert('', 'end', text=abspath, open=True)
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            listResults=self.myManager.loadQuery('File\\rdfqueries\IdAndNames')
            itemsAdd = dict()
            for my_item in listResults:
                evaluation_name = my_item['Evaluation']['value']
                if evaluation_name not in itemsAdd:
                   tree_id_evaluation= self.my_tree.insert(parent, 'end', text=evaluation_name, open=False)
                   itemsAdd.update({evaluation_name:tree_id_evaluation})
                #===============================================================
                # if 'TestName' in my_item:
                #     test_name=my_item['TestName']['value']
                #     if test_name not in itemsAdd:
                #        list_id_evaluation=itemsAdd[evaluation_name]
                #        raw_test_id = my_item['Test']['value']
                #        wVal,wSep,test_id = raw_test_id.partition('#')
                #        tree_id_test=self.my_tree.insert(list_id_evaluation, 'end', text=test_id + '-' + test_name, open=False)
                #        itemsAdd.update({test_name:tree_id_test})
                #     
                # if 'SubTestName' in my_item:
                #     subtest_name=my_item['SubTestName']['value']
                #     if subtest_name not in itemsAdd:
                #        list_id_test=itemsAdd[test_name]
                #        raw_subtest_id = my_item['SubTest']['value']
                #        wVal,wSep,subtest_id = raw_subtest_id.partition('#')
                #        tree_id_subtest=self.my_tree.insert(list_id_test, 'end', text=subtest_id + '-' + subtest_name, open=False)
                #        itemsAdd.update({subtest_name:tree_id_subtest})
                # if 'SubSubTestName' in my_item:
                #     subsubtest_name=my_item['SubSubTestName']['value']
                #     if subsubtest_name not in itemsAdd:
                #        list_id_subtest=itemsAdd[subtest_name]
                #        raw_subsubtest_id = my_item['SubSubTest']['value']
                #        wVal,wSep,subsubtest_id = raw_subsubtest_id.partition('#')
                #        tree_id_subsubtest=self.my_tree.insert(list_id_subtest, 'end', text=subsubtest_id + '-' + subsubtest_name, open=False)
                #        itemsAdd.update({subsubtest_name:tree_id_subsubtest})
                #===============================================================
                
                if 'Test' in my_item:
                    raw_test_id = my_item['Test']['value']
                    wVal,wSep,test_id = raw_test_id.partition('#')
                    if test_id not in itemsAdd:
                       list_id_evaluation=itemsAdd[evaluation_name]
                       node_name = test_id + '-'
                       if 'TestName' in my_item:
                           test_name=my_item['TestName']['value']
                           node_name = node_name + test_name
                       tree_id_test=self.my_tree.insert(list_id_evaluation, 'end', text=node_name, open=False)
                       itemsAdd.update({test_id:tree_id_test})
                    
                if 'SubTest' in my_item:
                    raw_subtest_id = my_item['SubTest']['value']
                    wVal,wSep,subtest_id = raw_subtest_id.partition('#')
                    if subtest_id not in itemsAdd:
                        list_id_test=itemsAdd[test_id]
                        node_name = subtest_id + '-'
                        if 'SubTestName' in my_item:
                            subtest_name=my_item['SubTestName']['value']
                            node_name = node_name + subtest_name
                        tree_id_subtest=self.my_tree.insert(list_id_test, 'end', text=node_name, open=False)
                        itemsAdd.update({subtest_id:tree_id_subtest})
                if 'SubSubTest' in my_item:
                    raw_subsubtest_id = my_item['SubSubTest']['value']
                    wVal,wSep,subsubtest_id = raw_subsubtest_id.partition('#')
                    if subsubtest_id not in itemsAdd:   
                        list_id_subtest=itemsAdd[subtest_id]
                        node_name = subsubtest_id + '-'
                        if 'SubSubTestName' in my_item:
                            subsubtest_name=my_item['SubSubTestName']['value']
                            node_name = node_name + subsubtest_name
                        tree_id_subsubtest=self.my_tree.insert(list_id_subtest, 'end', text=node_name, open=False)
                        itemsAdd.update({subsubtest_id:tree_id_subsubtest})

            self.my_tree.pack(side=LEFT, fill=BOTH, expand=1, anchor=NW)
            self.my_tree.bind('<Double-1>',self.treeview_selection_handler)
            #ysb.pack(side=LEFT, fill=Y, expand=1, anchor=NW)          

    def treeview_selection_handler(self, event):
        item = self.my_tree.selection()[0]
        chosen = self.my_tree.item(item, "text")
        regexIndex=chosen.find('-')
        chosen=chosen[0:regexIndex]
            
        print 'chosen is ' + chosen
        column = self.scatterPlot.get_columnFromCSV(self.file_name, chosen, True)
        self.scatterPlot.addAxes(column, chosen, self.volumes, 'volume', self.codes, 'code')
    #===========================================================================
    #     children = self.myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch', chosen, 'isRelatedWith')
    # 
    #     tab_list_size = tab_list.size()
    #     intList = list()
    #     for child in children:
    #         for i in range(0, tab_list_size):
    #             item = tab_list.get(i)
    #             regexIndex=item.find('-')
    #             item=item[0:regexIndex]
    #             if i not in intList:
    #                 if item == child:
    #                     tab_list.itemconfig(i, bg='red', fg='black')
    #                     intList.append(i)
    #                 else:
    #                     tab_list.itemconfig(i, bg='white', fg='black')
    #             print item
    #===========================================================================
        
    def search_treeview(self, item=''):
        children = self.my_tree.get_children(item)
        for child in children:
            text = self.my_tree.item(child, 'text')
            if text == item:
                return True
            else:
                res = self.search(child)
                if res:
                    return True
        
                  
        #=======================================================================
        # button = Button(self.patientsFrame, text = 'X')
        # button.pack(side=LEFT, fill=NONE, expand=0, anchor=CENTER)
        #=======================================================================
             
    def load_rdf(self):
        rdfFileName = askopenfile()
        print rdfFileName
        
    def connect_to_repository(self):
        print "connect"
        
    def add_vtk_plot_to_frame(self, parent_frame):
        self.create_plot_test()
        view = self.scatterPlot.get_vtk_view()

        renWin=vtk.vtkRenderWindow()
        render_widget = vtkTkRenderWindowInteractor(parent_frame,rw=renWin,width=600, height=600)  
        iact=render_widget.GetRenderWindow().GetInteractor()                            
        view.SetRenderWindow(render_widget.GetRenderWindow())
        view.SetInteractor(iact)
        render_widget.pack(side=LEFT, fill=BOTH, expand=1, anchor=NW)
        view.GetRenderWindow().SetMultiSamples(0)
        iact.Initialize()
        view.GetRenderWindow().Render()
        iact.Start()

    def create_plot_test(self):
        reader=braviz.readAndFilter.kmc40AutoReader()
        data_root=reader.getDataRoot()
        self.file_name=path_join(data_root,'test_small2.csv')
        self.scatterPlot = ScatterPlotClass(500,500)
        wmi = self.scatterPlot.get_columnFromCSV(self.file_name, 'WMIIQ', True)
        self.codes = self.scatterPlot.get_columnFromCSV(self.file_name, 'CODE', False)
        self.volumes=map(lambda code: self.scatterPlot.get_struct_volume(reader, 'CC_Anterior',code) ,self.codes)
        self.scatterPlot.addAxes(wmi, 'wmi', self.volumes, 'volume', self.codes, 'code')
        
    def create_viewer(self,parent_frame):
        reader=braviz.readAndFilter.kmc40AutoReader()

        #leer putamen
        putamen=reader.get('model','093',name='Left-Putamen')
        
        #crear visualizador
        self.renWin=vtk.vtkRenderWindow()
        ren=vtk.vtkRenderer()
        self.renWin.AddRenderer(ren)
        ren.SetBackground(0.0,0,0.0)
        
        
        #agregar putamen al visualizador
        putamen_mapper=vtk.vtkPolyDataMapper()
        putamen_mapper.SetInputData(putamen)
        putamen_actor=vtk.vtkActor()
        putamen_actor.SetMapper(putamen_mapper)
        ren.AddActor(putamen_actor)
        
        #iniciar visualizador
        
        #Agregar amygdala
        amygdala=reader.get('model','093',name='Right-Amygdala')
        amydala_mapper=vtk.vtkPolyDataMapper()
        amydala_mapper.SetInputData(amygdala)
        amygdala_actor=vtk.vtkActor()
        amygdala_actor.SetMapper(amydala_mapper)
        ren.AddActor(amygdala_actor)
        
        
        #Agregar imagen
        mri=reader.get('mri','093',format='vtk')
        image_plane=braviz.visualization.persistentImagePlane()
        image_plane.SetInputData(mri)
        
        ##=========GUI================
        #root = tk.Tk()
        #root.title('Tutorial Yoyis')
        #root=self.rootTk
        
        render_widget = vtkTkRenderWindowInteractor(parent_frame,
                                                    rw=self.renWin, width=700,
                                                    height=600)
        
        render_widget.grid(sticky='nsew')
        parent_frame.grid(sticky='ewsn')
        
        def clean_exit():
            
            print "adios"
            self.renWin.Finalize()
            del self.renWin
            render_widget.destroy()
            root.quit()
            root.destroy()
        root.protocol("WM_DELETE_WINDOW", clean_exit)
        
        #inicializar
        
        interactor = render_widget.GetRenderWindow().GetInteractor()
        interactor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        image_plane.SetInteractor(interactor)
        image_plane.On()
        interactor.Initialize()
        interactor.Start()
        
        root.mainloop()
    
    def create_viewer_2(self, parent_frame):
        self.volume_renderer = VolumeRendererClass()
        self.volume_renderer.load_model('model','325','Left-Putamen')
        self.volume_renderer.load_image_plane('mri','325','vtk')
        self.volume_renderer.load_fibers('325','fa','CC_Central')
        ren_win = self.volume_renderer.get_render_window()
        self.render_widget = vtkTkRenderWindowInteractor(parent_frame,
                                                    rw=ren_win, width=700,
                                                    height=600)
        self.render_widget.grid(sticky='e')
        
        self.volume_renderer.render(self.render_widget)
    
    def clean_exit(self):     
        print "adios"
        self.volume_renderer.clean_exit()
        self.render_widget.destroy()
        self.main_frame_root.quit()
        self.main_frame_root.destroy()


        
root = Tk()
mainFrame = MainFrame(root)
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (w, h))
root.wm_title("Braint V 1.0")
root.mainloop()