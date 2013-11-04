#Este prograa permite ver los subtest y subsubrtest en un scatterplot atraves de un query del rdf
#Este ejemplo ejecuta scatter plot por cada varialbe que se relaciona con una seleccion hecha en el scatter plot inicial
from __future__ import division
import vtk
import braviz
import Tkinter as tk
import tkMessageBox
import ttk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor
from os.path import join as path_join 
import cPickle
from kernel.RDFDBManagerClass import *
from ScatterPlotClass import ScatterPlotClass

#kbDatabaseRoot = 'K:\\JohanaForero\\KAB-db'

class TestVis:
    def __init__(self,file): ##Constructor donde inicializo mis atributos de archivo de entrada
       self.file_name=file
       self.table=vtk.vtkTable()
       self.chart=vtk.vtkChartXY()
       self.chart.SetShowLegend(False)
       self.points=self.chart.AddPlot(vtk.vtkChart.POINTS)
       self.points.SetColor(0,0,0,255)
       self.points.SetWidth(1.0)


    #Trae los headers del archivo CSV
    def get_headers(self):
        csv_file=open(self.file_name)
        headers=csv_file.readline()
        headers=headers.rstrip('\n')
        headers=headers.split(';')
        csv_file.close()
        return headers
    
    def get_column(self,name,numeric=False): ##Este metodo retorna el contenido de la columna dependiendo del nombre del header que ingrese por parametro y redondea el contenido de la columna si numeric=True... Si es letra pone nan
        csv_file=open(self.file_name)
        headers=csv_file.readline()
        headers=headers.rstrip('\n')
        headers=headers.split(';')
        if name not in headers:
            print "column %s not found in file"%name
            return None
        idx=headers.index(name)
        column=[]
        for l in iter(csv_file.readline,''):
            l2=l.rstrip('\n')
            l2=l2.split(';')
            item=l2[idx]
            if numeric:
                try:
                    num=float(item)
                except ValueError:
                    try:
                        #some decimals number saved using a comma
                        item=item.replace(',','.')
                        num=float(item)
                    except:
                        num=float('nan')
                item=num
            column.append(item)
        csv_file.close()
        return column
    
    def column_to_vtk_array(self,col,name='unknown'):
        if not isinstance(col[0],str):
            array=vtk.vtkFloatArray()
            array.InsertNextValue(col[0])
        else:
            array=vtk.vtkStringArray()
            array.InsertNextValue(col[0])
        for item in col:
            array.InsertNextValue(item)
            #print "adding %s"%item
        array.SetName(name)
        return array
    
    def get_struct_metric(self,struct_name,code,metric='volume'):
        try:
            model=reader.get('model',code,name=struct_name)
        except:
            print "%s not found for subject %s"%(struct_name,code)
            return float('nan')
        area,volume=braviz.interaction.compute_volume_and_area(model)
        if metric=='volume':
            return volume
        elif metric=='area':
            return area
        elif metric=='nfibers':
            return self.get_fibers_metric(struct_name,code,'number')
        elif metric=='lfibers':
            return self.get_fibers_metric(struct_name,code,'mean_length')
        elif metric=='fa_fibers':
            return self.get_fibers_metric(struct_name,code,'mean_fa')
        else:
            print "unknown metric %s"%metric
            return None
        
    def get_fibers_metric(self,struct_name,code,metric='number'):
    #print "calculating for subject %s"%code
        try:
            fibers=reader.get('fibers',code,waypoint=struct_name,color='fa')
        except:
            n=float('nan')
        else:
            if fibers == None:
                print "Problem loading fibers for subject %s"%code
                n=float('nan')
            elif metric=='number':
                n=fibers.GetNumberOfLines()
            elif metric=='mean_length':
                desc=braviz.interaction.get_fiber_bundle_descriptors(fibers)
                n=float(desc[1])
            elif metric=='mean_fa':
                desc=braviz.interaction.aggregate_fiber_scalar(fibers, component=0, norm_factor=1/255)
                del fibers
                n=float(desc[1])
            else:
                print 'unknowm fiber metric %s'%metric
                return float('nan')
        print '%s : %f'%(code,n)
        return n
    def loadQueryListResults(self):
        self.myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
        listResults=self.myManager.loadQuery('File\\rdfqueries\EvaluationTestSubTestSubSubTestNames.txt')
        subsubtestlist = list()
        for miItem in listResults:
            print miItem
            subsubtestitem = ''
            if 'SubTest' in miItem:
                wValue = miItem['SubTest']['value']
                wVal,wSep,wAft = wValue.partition('#')
                subTestName=' '
                if 'SubTestName' in miItem:
                    subTestName = miItem['SubTestName']['value']
                subsubtestitem = wAft + '-' + subTestName 
                if subsubtestitem not in subsubtestlist:
                    subsubtestlist.append(subsubtestitem)
            if 'SubSubTest' in miItem:
                wValue = miItem['SubSubTest']['value']
                wVal,wSep,wAft = wValue.partition('#')
                subsubTestName=' '
                if 'SubSubTestName' in miItem:
                    subsubTestName = miItem['SubSubTestName']['value']
                subsubtestitem = wAft + '-' + subsubTestName 
                if subsubtestitem not in subsubtestlist:
                    subsubtestlist.append(subsubtestitem)
            print subsubtestitem
        return subsubtestlist
    
    def get_struct_metrics_col(self, struct_name, metric,codes):
        key='column_%s_%s'%(struct_name,metric)
        cache_file_name=path_join(reader.getDataRoot(),'pickles','%s.pickle'%key)
        try:
            cachef=open(cache_file_name,'rb')
        except IOError:
            pass
        else:
            column=cPickle.Unpickler(cachef).load()
            cachef.close()
            return column
        print "Calculating %s for structure %s"%(metric,struct_name)
        col=map(lambda code: self.get_struct_metric(struct_name,code,metric) ,codes)
        try:
            cachef=open(cache_file_name,'wb')
            cPickle.Pickler(cachef,2).dump(col)
            cachef.close()
        except:
            print "cache write failed"
            pass
        return col
    
    def refresh_table(self, tab_column, tab_var_name, struct_metrics_col, struct_name, metric):
        self.table.RemoveColumn(2)
        self.table.RemoveColumn(1)
        
        self.table.AddColumn(self.column_to_vtk_array(tab_column,tab_var_name))
        self.table.AddColumn(self.column_to_vtk_array(struct_metrics_col,'%s - %s'%(struct_name,metric) ))
        
         
        #for c,t,s in zip(codes,tab_column,struct_metrics_col):
        #    print "%s: %f , %f"%(c,t,s)
        
        self.points.SetInputData(self.table,1,2)
        self.points.Update()
        self.chart.RecalculateBounds()
        xaxis=self.chart.GetAxis(1)
        xaxis.SetTitle(tab_var_name)
        yaxis=self.chart.GetAxis(0)
        if metric=='volume':
            yaxis.SetTitle('%s - Volume (mm3)'%struct_name)
        elif metric=='area':
            yaxis.SetTitle('%s - Area (mm2)'%struct_name)
        elif metric=='nfibers':
            yaxis.SetTitle('Number of fibers crossing %s'%struct_name)
        elif metric=='lfibers':
            yaxis.SetTitle('Mean length of fibers crossing %s (mm)'%struct_name)
        elif metric=='fa_fibers':
            yaxis.SetTitle('Mean FA of fibers crossing %s '%struct_name)
        else:
            yaxis.SetTitle('unknown')

    def getRDFDBManager(self):
        return self.myManager
     
reader=braviz.readAndFilter.kmc40AutoReader(max_cache=500)
data_root=reader.getDataRoot()
myVis=TestVis('File\\baseFinal.csv') ##Crear objeto del tipo TestVis 
#print myVis.get_headers()
#print myVis.get_column('GENDE', numeric=True)
#print myVis.column_to_vtk_array('CODE', 'unknown')
#print myVis.get_struct_metric('CC_Anterior', '093', 'volume')
#print myVis.get_struct_metric('CC_Anterior', '093', 'area')
#print myVis.get_struct_metric('CC_Anterior', '093', 'nfibers')
#print myVis.get_struct_metric('CC_Anterior', '093', 'lfibers')
#print myVis.get_struct_metric('CC_Anterior', '093', 'fa_fibers')
#print myVis.loadQueryListResults()
codes=myVis.get_column('CODE', False)
print myVis.get_struct_metrics_col('CC_Anterior', 'volume', codes)


testIds = myVis.loadQueryListResults()

tab_var_name=testIds[0]
#para recortar el nombre hasta que encuentre el primer guion
regexIndex=tab_var_name.find('-');
tab_var_name=tab_var_name[0:regexIndex]
tab_column=myVis.get_column(tab_var_name, True)

#print codes

struct_name='CC_Anterior'
metric='volume'

struct_metrics_col=map(lambda code: myVis.get_struct_metric(struct_name,code,'volume') ,codes)

view=vtk.vtkContextView()
view.GetRenderer().SetBackground(1.0,1.0,1.0)
view.GetRenderWindow().SetSize(400,300)
view.GetScene().AddItem(myVis.chart)

points = myVis.points
points.SetMarkerStyle(vtk.vtkPlotPoints.CIRCLE)
points.SetIndexedLabels(myVis.column_to_vtk_array(codes,'CODE'))
points.SetTooltipLabelFormat('code=%i')

myVis.table.AddColumn(myVis.column_to_vtk_array(codes,'CODE'))
if tab_column!=None:
    myVis.refresh_table(tab_column, tab_var_name, struct_metrics_col, struct_name, metric)

root = tk.Tk()
root.withdraw()
top = tk.Toplevel(root)
top.title('BraViz-tab V.S. struct')

control_frame = tk.Frame(top,width=100,border=1)#,relief='raised')
control_frame.grid(row=0,column=0,sticky='nsew')
top.columnconfigure(0, minsize=100)
top.rowconfigure(0, weight=1)

tab_frame=tk.Frame(control_frame)
sep=ttk.Separator(control_frame,orient=tk.HORIZONTAL)
struct_frame=tk.Frame(control_frame)

tab_frame.grid(column=0,row=0,sticky='nsew')
sep.grid(column=0,row=1,sticky='ew')

control_frame.rowconfigure(0,weight=1)
control_frame.rowconfigure(2,weight=1)
control_frame.columnconfigure(0,weight=1,minsize=120)
struct_frame.grid(column=0,row=2,sticky='snew')

#===========================Tabular================================
tab_frame.columnconfigure(0, weight=1)
tab_frame.rowconfigure(1, weight=1)
Tabular_label=tk.Label(tab_frame,text='Tabular Data')
Tabular_label.grid(row=0,column=0,sticky='ew',pady=10)

tab_list_frame=tk.LabelFrame(tab_frame,text='Select Variable')


tab_list_and_bar=tk.Frame(tab_list_frame)
tab_list_and_bar.pack(side='top',fill='both',expand=1)
tab_scrollbar=tk.Scrollbar(tab_list_and_bar,orient=tk.VERTICAL)
tab_list=tk.Listbox(tab_list_and_bar,selectmode=tk.BROWSE,yscrollcommand=tab_scrollbar.set,exportselection=0)
tab_scrollbar.config(command=tab_list.yview)
tab_scrollbar.pack(side=tk.RIGHT,fill=tk.Y,expand=1)
tab_list.pack(side="left",fill='both',expand=1)
#headers=myVis.get_headers()
headers=myVis.loadQueryListResults()

for h in headers:
    tab_list.insert(tk.END,h)

tab_list.select_set(0,0) #Selecciona en la interfaz el primero de la lista siempre


def change_tabular(event=None):
    global tab_column,tab_var_name
    for w in widgets:
        w['state']='disabled'
    var_idx=tab_list.curselection()
    tab_var_name=tab_list.get(var_idx)
    regexIndex=tab_var_name.find('-');
    tab_var_name=tab_var_name[0:regexIndex]
    tab_column=myVis.get_column(tab_var_name, True)
    if tab_column!=None:
        #print tab_column
        myVis.refresh_table(tab_column, tab_var_name, struct_metrics_col, struct_name, metric)
    else:
        tkMessageBox.showwarning(
            "Warning",
            "The %s does not have data" % tab_var_name
        )
    
    manager = myVis.getRDFDBManager()
    
    children = manager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch', tab_var_name, 'isRelatedWith')
    
    tab_list_size = tab_list.size()
    intList = list()
    for child in children:
        for i in range(0, tab_list_size):
            item = tab_list.get(i)
            regexIndex=item.find('-');
            item=item[0:regexIndex]
            if i not in intList:
                if item == child:
                    tab_list.itemconfig(i, bg='red', fg='black')
                    intList.append(i)
                    scatterPlot = ScatterPlotClass(500,400)
                    wmi = scatterPlot.get_columnFromCSV('File\\baseFinal.csv', item, True)
                    if wmi is not None:
                        codes = scatterPlot.get_columnFromCSV('File\\baseFinal.csv', 'CODE', False)
                        volumes=map(lambda code: scatterPlot.get_struct_volume(reader, 'CC_Anterior',code) ,codes)
                        
                        scatterPlot.addAxes(wmi, item, volumes, 'volume', codes, 'code')
                        scatterPlot.render()
                else:
                    tab_list.itemconfig(i, bg='white', fg='black')
            print item

    refresh_display()


tab_list.bind('<<ListboxSelect>>',change_tabular)

tab_list_frame.grid(row=1,column=0,sticky='nsew')
#===========================Structure Metrics=================================
struct_frame.columnconfigure(0, weight=1)
struct_frame.rowconfigure(1, weight=1)
struct_label=tk.Label(struct_frame,text='Structure Metric')
struct_label.grid(row=0,column=0,sticky='ew',pady=10)

select_model_frame=tk.LabelFrame(struct_frame,text='Select Model',padx=1,pady=10)


model_list_and_bar=tk.Frame(select_model_frame)
model_list_and_bar.pack(side='top',fill='both',expand=1)
model_scrollbar=tk.Scrollbar(model_list_and_bar,orient=tk.VERTICAL)
model_list=tk.Listbox(model_list_and_bar,selectmode=tk.BROWSE,yscrollcommand=model_scrollbar.set,exportselection=0)
model_scrollbar.config(command=model_list.yview)
model_scrollbar.pack(side=tk.RIGHT,fill=tk.Y,expand=1)
model_list.pack(side="left",fill='both',expand=1)
models=reader.get('model','093',index='t')

for m in sorted(models):
    model_list.insert(tk.END,m)

model_list.select_set(3,3)


select_model_frame.grid(row=1,column=0,sticky='snew',pady=5)

metric_buttons=tk.Frame(struct_frame)
metric_buttons.grid(row=2,column=0,sticky='ew')

metric_var=tk.StringVar()
metric_var.set('area')

def change_struct(event=None):
    global struct_name,metric,struct_metrics_col
    for w in widgets:
        w['state']='disabled'
    metric= metric_var.get()
    #print calculating_volume
    struct_idx=model_list.curselection()
    struct_name=model_list.get(struct_idx)
    struct_metrics_col=myVis.get_struct_metrics_col(struct_name, metric,codes)
    #print struct_metrics_col
    myVis.refresh_table(tab_column, tab_var_name, struct_metrics_col, struct_name, metric)
    refresh_display()


area_button=tk.Radiobutton(metric_buttons,text='Surface Area',variable=metric_var,value='area',command=change_struct)
volume_button=tk.Radiobutton(metric_buttons,text='Volume',variable=metric_var,value='volume',command=change_struct)
nfibers_button=tk.Radiobutton(metric_buttons,text='Number of fibers crossing',variable=metric_var,value='nfibers',command=change_struct)
lfibers_button=tk.Radiobutton(metric_buttons,text='Mean length of fibers crossing',variable=metric_var,value='lfibers',command=change_struct)
fafibers_button=tk.Radiobutton(metric_buttons,text='Mean FA of fibers crossing',variable=metric_var,value='fa_fibers',command=change_struct)
model_list.bind('<<ListboxSelect>>',change_struct)
area_button.grid(row=0,column=0)
volume_button.grid(row=0,column=1)
nfibers_button.grid(row=1,column=0,columnspan=2)
lfibers_button.grid(row=2,column=0,columnspan=2)
fafibers_button.grid(row=3,column=0,columnspan=2)
#=====================================================================
renderer_frame = tk.Frame(top)
renderer_frame.grid(row=0,column=1,sticky='ewsn')
top.columnconfigure(1, weight=1)



renWin=vtk.vtkRenderWindow()
render_widget = vtkTkRenderWindowInteractor(renderer_frame,rw=renWin,width=600, height=600)  

iact=render_widget.GetRenderWindow().GetInteractor()                            
view.SetRenderWindow(render_widget.GetRenderWindow())
view.SetInteractor(iact)




renderer_frame.columnconfigure(0, weight=1)
renderer_frame.rowconfigure(0, weight=1)
render_widget.grid(row=0,column=0,sticky='ewsn')

view.GetRenderWindow().SetMultiSamples(0)
iact.Initialize()


view.GetRenderWindow().Render()
iact.Start()

widgets=[tab_list, model_list, area_button, volume_button, nfibers_button, lfibers_button,fafibers_button]

def refresh_display():
    view.Update()
    view.GetRenderWindow().Render()
    for w in widgets:
        w['state']='normal'

def clean_exit():
    global renWin
    print "adios"
    renWin.FastDelete()
    #renWin.Finalize()
    del renWin
    #render_widget.destroy()
    #root.quit()
    #root.destroy()
    quit(0)
top.protocol("WM_DELETE_WINDOW", clean_exit)


#========================VTK INERACTION==================

def listen_and_print(obj,event):
    print
    print event
    print "================"
    #print obj
    print
    
    
#chart.AddObserver(vtk.vtkCommand.SelectionChangedEvent,listen_and_print)

# Start Tkinter event loop
root.mainloop()