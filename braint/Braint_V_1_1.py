from Tkinter import *
from tkFileDialog import askopenfile
import ttk
from os.path import join as path_join

import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import BraintProperties
from kernel.RDFDBManagerClass import  RDFDBManager
from ScatterPlotClass import ScatterPlotClass
from VolumeRendererClass import VolumeRendererClass
import braviz


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
        
        self.reader=braviz.readAndFilter.BravizAutoReader()
        
        #self.topFrame.pack(side = TOP, fill=BOTH, expand = YES)
        
        for r in range(5):
            self.main_frame_root.rowconfigure(r, weight=1)    
        for c in range(6):
            self.main_frame_root.columnconfigure(c, weight=1)
        
        #Desde aqui empiezo a agregar todas las cosas a mi frame grandote    
                
        self.focusFrame = Frame(self.main_frame_root, background = 'white')
        #self.focusFrame = Frame(self.main_frame_root, background = 'red')
        self.focusFrame.grid(row=0, column=0, rowspan = 4, columnspan = 4, sticky = W+E+N+S)
        
        self.contextFrame = Frame(self.main_frame_root, background = 'white')
        #self.contextFrame = Frame(self.main_frame_root, background = 'yellow')
        self.contextFrame.grid(row=0, column=4, rowspan = 4, columnspan = 1, sticky = W+E+N+S)
        
        self.patientsFrame = Frame(self.main_frame_root, background = 'white')
        #self.patientsFrame = Frame(self.main_frame_root, background = 'blue')
        self.patientsFrame.grid(row=0, column=5, rowspan = 4, columnspan = 1, sticky = W+E+N+S)
                
        self.logFrame = Frame(self.main_frame_root,background = 'white')
        #self.logFrame = Frame(self.main_frame_root,background = 'green')
        self.logFrame.grid(row=4, column=0, rowspan= 1, columnspan=6, sticky = W+E+N+S)
        
        self.current_subject = '143'
        self.current_subject_index = 1
        self.current_volume = 'Left-Putamen'
        self.current_test = 'WMIIQ'
        
        
        self.current_x_axis_code_name = 'RID21015'
        self.current_x_axis_name = 'Volume of Left Putamen'
        self.current_x_axis = []
        self.current_y_axis_code_name = 'WMIIQ'
        self.current_y_axis_name = 'Score Working Memory'
        self.current_y_axis = []
        self.current_subject_x_score = [0]
        self.current_subject_y_score = [0]
        
        
        self.add_tree_hierarchy_to_frame(self.patientsFrame)
        self.show_patients_list(self.patientsFrame)
        self.add_vtk_plot_to_frame(self.focusFrame) 
        
        
        self.create_viewer_2(self.contextFrame, 'model',self.current_subject,self.current_volume, 'mri')
        
        
        
              
        self.main_frame_root.protocol("WM_DELETE_WINDOW", self.clean_exit)
        
        self.update_tables(self.current_x_axis_code_name, self.current_x_axis_name, self.current_y_axis_code_name, self.current_y_axis_name)
        self.update_scatterplot()
          
    
    def show_patients_list(self, parent_frame):  
        """
        Muestra la lista de pacientes en un list box y lo pinto en el parent_frame que yo ingrese
        """      
        self.select_subj_frame=braviz.interaction.subjects_list(self.reader,self.setSubj,parent_frame,text='Subject',padx=10,pady=5,height='100')
        
        index = self.select_subj_frame.getSelectionIndex(self.current_subject)
        self.select_subj_frame.setSelection(index)
        self.select_subj_frame.pack(side='top')
   
    def setSubj(self,event=None):
        """
        Es el evento que se lanza cuando selecciono algo de la lista show_patients_list
        """
        subj=self.select_subj_frame.get()
        self.update_current_subject(subj)
        
    def update_current_subject(self, subj):
        """
        Funcion que realiza las acciones en mi visualizacion cuando cambio un paciente
        Esto puede ser por medio de la seleccion de un sujeto en la list box o por la seleccion en el
        scatterplot
        """
        self.volume_renderer.update_image_plane('mri', subj, 'vtk')
        self.volume_renderer.remove_current_actors()
        self.volume_renderer.load_model('model', subj, self.current_volume)
        self.volume_renderer.refresh()
        #self.scatterPlot.addAxes(column, chosen, self.volumes, name, self.codes, 'code')
        self.current_subject = subj
        self.update_plot_one_patient()
                  
    def add_tree_hierarchy_to_frame(self, parent_frame):      
        """
        Esta funcion pinta un arbol con la informacion que se encuentra en el repositorio RDF de las jerarquias.
        Test-Subtest-Subsubtest
        Importante revisar en RDFDBManager que este trayendo las cosas del repositorio adecuado
        """    
        self.my_tree = ttk.Treeview(parent_frame)
        ysb = ttk.Scrollbar(parent_frame, orient='vertical', command=self.my_tree.yview)
        xsb = ttk.Scrollbar(parent_frame, orient='horizontal', command=self.my_tree.xview)
        #self.my_tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        self.my_tree.heading('#0', text='BraInt Hierarchy', anchor='w')
        abspath = 'BraInt'
        parent=self.my_tree.insert('', 'end', text=abspath, open=True)
        self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
        #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
        #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
        self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
        listResults=self.myManager.loadQuery('File\\rdfqueries\IdAndNames')
        self.items_add = dict()
        id_tree_vol='i'
        id_tree_fib='i'
        self.volume_list=[]
        self.fiber_list=[]
        for my_item in listResults:
            evaluation_name = my_item['Evaluation']['value']
            if evaluation_name not in self.items_add:
                tree_id_evaluation= self.my_tree.insert(parent, 'end', text=evaluation_name, tags=(evaluation_name), open=False)
                self.items_add.update({evaluation_name:tree_id_evaluation})              
            if 'Test' in my_item:
                raw_test_id = my_item['Test']['value']
                wVal,wSep,test_id = raw_test_id.partition('#')
                if test_id not in self.items_add:
                    list_id_evaluation=self.items_add[evaluation_name]
                    node_name = test_id + '-'
                    if 'TestName' in my_item:
                         test_name=my_item['TestName']['value']
                         node_name = node_name + test_name
                    tree_id_test=self.my_tree.insert(list_id_evaluation, 'end', text=node_name, tags=(test_id), open=False)
                    self.items_add.update({test_id:tree_id_test})
                
            if 'SubTest' in my_item:
                raw_subtest_id = my_item['SubTest']['value']
                wVal,wSep,subtest_id = raw_subtest_id.partition('#')
                if subtest_id not in self.items_add:
                    list_id_test=self.items_add[test_id]
                    node_name = subtest_id + '-'
                    if 'SubTestName' in my_item:
                        subtest_name=my_item['SubTestName']['value']
                        node_name = node_name + subtest_name
                    tree_id_subtest=self.my_tree.insert(list_id_test, 'end', text=node_name, tags=(subtest_id), open=False)
                    self.items_add.update({subtest_id:tree_id_subtest})
                    if subtest_name=='Volume':
                        id_tree_vol=tree_id_subtest
                    if subtest_name=='Total number':
                        id_tree_fib=tree_id_subtest    
            if 'SubSubTest' in my_item:
                raw_subsubtest_id = my_item['SubSubTest']['value']
                wVal,wSep,subsubtest_id = raw_subsubtest_id.partition('#')
                if subsubtest_id not in self.items_add:   
                    list_id_subtest=self.items_add[subtest_id]
                    node_name = subsubtest_id + '-'
                    if 'SubSubTestName' in my_item:
                        subsubtest_name=my_item['SubSubTestName']['value']
                        node_name = node_name + subsubtest_name
                    tree_id_subsubtest=self.my_tree.insert(list_id_subtest, 'end', text=node_name, tags=(subsubtest_id), open=False)
                    #self.my_tree.tag_configure(subsubtest_id, background='black')#Si quiero cambiar el color de  fondo del tree
                    self.items_add.update({subsubtest_id:tree_id_subsubtest})
                    if list_id_subtest==id_tree_vol:
                        self.volume_list.append(subsubtest_id)
                    if list_id_subtest==id_tree_fib:
                        self.fiber_list.append(subsubtest_id) 
                    #print self.fiber_list, 'fibraaaaaaaaas'       
        self.my_tree.pack(side=TOP, fill=BOTH, expand=1, anchor=NW)
        self.my_tree.bind('<Double-1>',self.treeview_selection_handler)          
        return self.volume_list        

    def treeview_selection_handler(self, event):
        """
        Esta funcion se activa cuando en la funcion anterior alguien hace doble clic sobre el arbol.
        Si la seleccion esta dentro de las variables del CSV se trae el valor normal.
        Si esta dentro del subtest Volumen entonces realiza la consulta del nombre freesurfer para calcular el volumen correspondiente.
        Tambien realiza la consulta de las demas varialbes que se relacionan con la seleccion y las pinta de amarillo
        Tambien pinta un volumen en caso de haber sido seleccionado en el arbol
        Importante revisar en RDFDBManager que este trayendo las cosas del repositorio adecuado
        """
        item = self.my_tree.selection()[0]
        chosen = self.my_tree.item(item, "text")
        regexIndex=chosen.find('-')
        name = chosen[regexIndex + 1:]
        chosen=chosen[0:regexIndex]
        #print 'name chosen is' + name
        #print 'chosen is ' + chosen
        #print self.volume_list
#===============================================================================
#         if chosen in self.volume_list:
#             self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
#             #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
#             Result=self.myManager.load_each_free_name('File\\rdfqueries\\Each_Free_Name.txt', chosen)             
#             column=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,self.codes)
#             self.current_volume = Result
#             self.volume_renderer.remove_current_actors()
#             self.volume_renderer.load_model('model', self.current_subject, self.current_volume)
#             self.volume_renderer.refresh()
# 
#         else: 
#             column = self.scatterPlot.get_columnFromCSV(self.file_name, chosen, True)
#             self.current_test = chosen
#===============================================================================

        self.update_tables(chosen, name, self.current_y_axis_code_name, self.current_y_axis_name)
       
        #self.volumes=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, self.current_volume,code) ,self.codes)
        #self.scatterPlot.addAxes(column, chosen, self.volumes, name, self.codes, 'code')
        
        
        
        self.update_scatterplot()
        
        children = self.myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch', chosen, 'isRelatedWith')
        for my_component in self.items_add:            
            #tree_item=self.items_add[my_component]
            #tag_item= self.my_tree.item(tree_item, "text")
            if my_component in children:
                #tree_item=self.items_add[my_component]
                #tag_item= self.my_tree.item(tree_item, "text")
                #self.my_tree.tag_configure(tag_item, background='yellow')
                self.my_tree.tag_configure(my_component, background='yellow')
            elif my_component in chosen:
                self.my_tree.tag_configure(chosen, background='red')
            else:
                self.my_tree.tag_configure(my_component, background='white')
            #print my_component

        
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
        
        
    def update_tables(self, x_axis_code, x_axis_name, y_axis_code, y_axis_name):
        if x_axis_code in self.volume_list:
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            Result=self.myManager.load_each_free_name('File\\rdfqueries\\Each_Free_Name.txt', x_axis_code)             
            self.current_x_axis=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,self.codes)
            self.current_x_axis_code_name = Result
            self.current_x_axis_name = x_axis_name
            self.current_volume = Result
            self.volume_renderer.remove_current_actors()
            self.volume_renderer.load_model('model', self.current_subject, self.current_volume)
            self.volume_renderer.refresh()
            
            self.current_subject_x_score = map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,[self.current_subject])

        else: 
            self.current_x_axis = self.scatterPlot.get_columnFromCSV(self.file_name, x_axis_code, True)
            self.current_x_axis_code_name = x_axis_code
            self.current_x_axis_name = x_axis_name
            self.current_subject_x_score = [self.current_x_axis[self.current_subject_index]]
            
        if y_axis_code in self.volume_list:
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080')
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
            #self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
            Result=self.myManager.load_each_free_name('File\\rdfqueries\\Each_Free_Name.txt', y_axis_code)             
            self.current_y_axis=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,self.codes)
            self.current_y_axis_code_name = Result
            self.current_y_axis_name = y_axis_name
            self.current_volume = Result
            self.volume_renderer.remove_current_actors()
            self.volume_renderer.load_model('model', self.current_subject, self.current_volume)
            self.volume_renderer.refresh()
            
            self.current_subject_y_score = map(lambda code: self.scatterPlot.get_struct_volume(self.reader, Result, code) ,[self.current_subject])

        else: 
            self.current_y_axis = self.scatterPlot.get_columnFromCSV(self.file_name, y_axis_code, True)
            self.current_y_axis_code_name = y_axis_code
            self.current_y_axis_name = y_axis_name
            self.current_subject_y_score = [self.current_y_axis[self.current_subject_index]]

    def create_plot_test(self):
        
        data_root=self.reader.get_data_root()
        self.file_name=path_join(data_root,'test_small2.csv')
        self.scatterPlot = ScatterPlotClass(500,500)
        self.codes = self.scatterPlot.get_columnFromCSV(self.file_name, 'CODE', False)
        self.scatterPlot.set_callback(self.scatterplot_callback)
        self.update_plot_one_patient()
        
        
        
        
        #=======================================================================
        # wmi = self.scatterPlot.get_columnFromCSV(self.file_name, 'WMIIQ', True)
        # self.codes = self.scatterPlot.get_columnFromCSV(self.file_name, 'CODE', False)
        # print self.codes
        # print wmi
        # self.my_new_codelist=[]
        # self.my_new_testlist=[]
        # for each_code in self.codes:
        #     if each_code != self.current_subject:
        #         self.my_new_codelist.append(each_code)
        #         
        #     else:
        #         code_pos=self.codes.index(each_code)
        # self.my_new_testlist=wmi
        # del self.my_new_testlist[code_pos]
        # current_subject_score=[wmi.pop(code_pos)]
        # 
        #         
        # print self.my_new_testlist           
        # print self.my_new_codelist        
        # 
        # #self.volumes=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, self.current_volume,code) ,self.my_new_codelist)
        # #self.scatterPlot.addAxes(self.my_new_testlist, 'wmi', self.volumes, 'volume', self.my_new_codelist, 'code')
        # #self.scatterPlot.points.SetColor(0,255,0,255)
        # 
        # one_subject_list=[self.current_subject]
        # 
        # current_volume_one=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, self.current_volume,code) , one_subject_list)
        # self.scatterPlot.addAxes(current_subject_score, 'wmi', current_volume_one, 'volume', one_subject_list, 'code') 
        #=======================================================================
    
        
        #=======================================================================
        # self.reader=braviz.readAndFilter.kmc40AutoReader()
        # data_root=self.reader.getDataRoot()
        # self.file_name=path_join(data_root,'test_small2.csv')
        # self.scatterPlot = ScatterPlotClass(500,500)
        # wmi = self.scatterPlot.get_columnFromCSV(self.file_name, 'WMIIQ', True)
        # self.codes = self.scatterPlot.get_columnFromCSV(self.file_name, 'CODE', False)
        # self.volumes=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, 'CC_Anterior',code) ,self.codes)
        # self.scatterPlot.addAxes(wmi, 'wmi', self.volumes, 'volume', self.codes, 'code')
        #=======================================================================
        
    def update_plot_one_patient(self):
        
 #==============================================================================
 #        test = self.scatterPlot.get_columnFromCSV(self.file_name, self.current_test, True)
 #        self.codes = self.scatterPlot.get_columnFromCSV(self.file_name, 'CODE', False)
 # 
 #        self.my_new_codelist=[]
 #        self.my_new_testlist=[]
 #        for each_code in self.codes:
 #            if each_code != self.current_subject:
 #                self.my_new_codelist.append(each_code)
 #            else:
 #                code_pos=self.codes.index(each_code)
 #        self.my_new_testlist=test
 #        del self.my_new_testlist[code_pos]
 #        current_subject_score=[test.pop(code_pos)]     
 #==============================================================================
        one_subject_list=[self.current_subject]  
  
        print 'calculate volume of ', self.current_subject
        current_volume_one=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, self.current_volume,code) , one_subject_list)
        #self.scatterPlot.addAxes(current_subject_score, 'wmi', current_volume_one, 'volume', one_subject_list, 'code')
        
        self.create_plot_test_minus_one()
        volumes_minus_one=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, self.current_volume,code) ,self.my_new_codelist)

        self.scatterPlot.add_axes_complete(self.my_new_testlist, 'wmi', volumes_minus_one, 'volume', self.my_new_codelist, 'code', self.current_subject_score, current_volume_one) 
        
    def create_plot_test_minus_one(self):
        self.reader=braviz.readAndFilter.BravizAutoReader()
        data_root=self.reader.get_data_root()
        self.file_name=path_join(data_root,'test_small2.csv')
        
        
        wmi = self.scatterPlot.get_columnFromCSV(self.file_name, self.current_test, True)
        self.codes = self.scatterPlot.get_columnFromCSV(self.file_name, 'CODE', False)

        self.my_new_testlist = list(wmi)
        self.my_new_codelist = list(self.codes)
        
        #=======================================================================
        # i = 0
        # for code in self.my_new_codelist:
        #     if code == self.current_subject:
        #         break
        #     i+=1
        #=======================================================================
        
        i = self.select_subj_frame.getSelectionIndex(self.current_subject)
        
        self.current_subject_score = [wmi[i]]
        self.my_new_codelist[i] 
        #del self.my_new_testlist[i]
        #del self.my_new_codelist[i]
        
        

        
        #self.volumes=map(lambda code: self.scatterPlot.get_struct_volume(self.reader, 'CC_Anterior',code) ,self.codes)
        #self.scatterPlot.addAxes(wmi, 'wmi', self.volumes, 'volume', self.codes, 'code')     
        
    
    def create_viewer_2(self, parent_frame, model, patient, structure, image_type,):        
        self.volume_renderer = VolumeRendererClass()
        self.volume_renderer.load_model(model,patient,structure)
        self.volume_renderer.load_image_plane(image_type, patient,'vtk')
        #self.volume_renderer.load_fibers('325','fa','CC_Central')
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

    def scatterplot_callback(self, caller, event):
        sel = caller.GetCurrentSelection()
 
        for nn in range(sel.GetNumberOfNodes()):
            sel_ids = sel.GetNode(nn).GetSelectionList()
            if sel_ids.GetNumberOfTuples() > 0:
                for ii in range(sel_ids.GetNumberOfTuples()):
                    code_index = int(sel_ids.GetTuple1(ii))
                    subj = self.my_new_codelist[code_index]
                    self.update_current_subject(subj)
                    self.select_subj_frame.setSelection(code_index)
                    print 'patient',subj
            else:
                print "-- empty"

    def update_scatterplot(self):
        self.scatterPlot.add_axes_complete(self.current_x_axis, self.current_x_axis_name, self.current_y_axis, self.current_y_axis_name, self.codes, 'codes', self.current_subject_x_score, self.current_subject_y_score) 
        
root = Tk()
mainFrame = MainFrame(root)
w, h = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry("%dx%d+0+0" % (w, h))
root.wm_title("Braint V 1.1")
root.mainloop()