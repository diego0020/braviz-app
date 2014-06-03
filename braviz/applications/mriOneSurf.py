"Illustrate how to load and display freeSurfer surfaces"
import Tkinter as tk
import ttk
import thread
import threading
import math

import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import braviz.readAndFilter




#TODO Use vtkSelectPolyData to select a sub region
root = tk.Tk()
root.withdraw()

left_active=tk.BooleanVar()
right_active=tk.BooleanVar()
right_active.set(False)
left_active.set(True)

surface=tk.StringVar()
surface.set('pial')
scalar=tk.StringVar()
scalar.set('curv')

progress_internal=0
progress_lock=threading.Lock()

progress=tk.IntVar()
progress.set(progress_internal)
processing=False
processing_lock=threading.Lock()

lut_dict={}



reader=braviz.readAndFilter.BravizAutoReader()
subjects = reader.get("ids")
currSubj=subjects[0]
img=reader.get('MRI',currSubj,format='VTK',space='world')

picker = vtk.vtkCellPicker()
#picker = vtk.vtkPropPicker()
#print picker
picker.SetTolerance(0.0005)

#Visualization
ren=vtk.vtkRenderer()
renWin=vtk.vtkRenderWindow()
renWin.AddRenderer(ren)
config=braviz.interaction.get_config(__file__)
background= config.get_background()
ren.SetBackground(background)

planeWidget=braviz.visualization.persistentImagePlane()
planeWidget.SetInputData(img) 
planeWidget.SetPicker(picker)
renWin.SetSize(600, 600)

outline = vtk.vtkOutlineFilter()
outline.SetInputData(img)

outlineMapper = vtk.vtkPolyDataMapper()
outlineMapper.SetInputConnection(outline.GetOutputPort())

outlineActor = vtk.vtkActor()
outlineActor.SetMapper(outlineMapper)
outlineActor.SetPickable(0)
ren.AddActor(outlineActor)

r_surf_mapper=vtk.vtkPolyDataMapper()
r_surf_mapper.UseLookupTableScalarRangeOn()
r_surf_mapper.SetColorModeToMapScalars()
r_surf_mapper.InterpolateScalarsBeforeMappingOff()
r_surf_actor=vtk.vtkActor()
r_surf_actor.SetMapper(r_surf_mapper)
ren.AddActor(r_surf_actor)
r_locator=vtk.vtkCellTreeLocator()
r_locator.LazyEvaluationOn()

l_surf_mapper=vtk.vtkPolyDataMapper()
l_surf_mapper.UseLookupTableScalarRangeOn()
l_surf_mapper.SetColorModeToMapScalars()
l_surf_mapper.InterpolateScalarsBeforeMappingOff()
l_surf_actor=vtk.vtkActor()
l_surf_actor.SetMapper(l_surf_mapper)
ren.AddActor(l_surf_actor)
l_locator=vtk.vtkCellTreeLocator()
l_locator.LazyEvaluationOn()



props= {id(l_surf_actor): "Left Hemisphere", id(r_surf_actor): "Right Hemisphere"}


#Cone for exploring
# Based on VolumePicker VTK example
coneSource = vtk.vtkConeSource()
coneSource.CappingOn()
coneSource.SetHeight(12)
coneSource.SetRadius(5)
coneSource.SetResolution(31)
coneSource.SetCenter(6,0,0)
coneSource.SetDirection(-1,0,0)

coneMapper = vtk.vtkDataSetMapper()
coneMapper.SetInputConnection(coneSource.GetOutputPort())

redCone = vtk.vtkActor()
redCone.PickableOff()
redCone.SetMapper(coneMapper)
redCone.GetProperty().SetColor(1,0,0)

ren.AddActor(redCone)
#picker.AddLocator(vtkAbstractCellLocator)

def PointCone(actor,nx,ny,nz):
    actor.SetOrientation(0.0, 0.0, 0.0)
    n = math.sqrt(nx**2 + ny**2 + nz**2)
    if (nx < 0.0):
        actor.RotateWXYZ(180, 0, 1, 0)
        n = -n
    actor.RotateWXYZ(180, (nx+n)*0.5, ny*0.5, nz*0.5)

text2=vtk.vtkTextActor()
cor=text2.GetPositionCoordinate()
cor.SetCoordinateSystemToNormalizedDisplay()
text2.SetPosition([0.99,0.01])
text2.SetInput('probando')
tprop=text2.GetTextProperty()
tprop.SetJustificationToRight()
tprop.SetFontSize(18)
ren.AddActor(text2)
text2.SetVisibility(0)

#===============================================================================

def get_lut():
    out_lut=lut_dict.get(scalar.get())
    if out_lut:
        return out_lut
    #print scalar.get()
    out_lut=reader.get('SURF_SCALAR',currSubj,scalars=scalar.get(),hemi='l',lut='t')
    lut_dict[scalar.get()]=out_lut
    return out_lut
        

def update(event=None):  
    global processing,lut, la_internal, ra_internal
    progress.set(0)
    processing_lock.acquire()
    if processing:
        #ignore event, this shouldn't happen
        processing_lock.release()
        return
    processing=True
    for w in widgets:
        w.config(state='disabled')
    processing_lock.release()
    lut=get_lut()  
    if surface.get() in ('inflated','sphere'):
        planeWidget.Off()
        if left_active.get() and right_active.get():
            right_active.set(0)
            actors_visibility()
    else:
        planeWidget.On()
    
    text2.SetVisibility(0)
    redCone.SetVisibility(0)
    la_internal=left_active.get()
    ra_internal=right_active.get()
    #async_update()
    thread.start_new_thread(async_update,())
    progress_bar.after(20,refresh)

    
    
def async_update():
    global processing,r_surf_t,l_surf_t,progress_internal
    progress_lock.acquire()
    progress_internal=10
    progress_lock.release()
    if(not la_internal):
        progress_lock.acquire()
        progress_internal=60
        progress_lock.release()
    if(ra_internal):
        try:
            r_surf_t=reader.get('Surf',currSubj,name=surface.get(),hemi='r',scalars=scalar.get())
        except Exception:
            r_surf_t=None
    if(la_internal):
        progress_lock.acquire()
        progress_internal=40
        progress_lock.release()
        try:
            l_surf_t=reader.get('Surf',currSubj,name=surface.get(),hemi='l',scalars=scalar.get())
        except Exception:
            l_surf_t=None
    #time.sleep(10)
    progress_lock.acquire()
    progress_internal=100
    progress_lock.release()
    #print r_surf
    processing_lock.acquire()
    processing=False
    processing_lock.release()
    

    

def setSubj(event=None):
    global img, currSubj, surf
    subj=select_subj_frame.get()
    currSubj=subj
    img=reader.get('MRI',subj,format='VTK',space='world')
    planeWidget.SetInputData(img)
    update()

    

    
def refresh(event=None):
    global r_surf,l_surf
    progress_lock.acquire()
    if progress_internal>progress.get():
        progress.set(progress_internal)
    progress_lock.release()
    
    processing_lock.acquire()
    if processing:
        #Not finished yet
        progress_bar.after(20,refresh)
        #progress_bar.step()
    else:        
        if(right_active.get()):
            r_surf=r_surf_t
            if r_surf is not None:
                r_surf_mapper.SetInputData(r_surf)
                r_surf_mapper.SetLookupTable(lut)
                r_locator.SetDataSet(r_surf)
                r_surf_actor.SetVisibility(1)
            else:
                r_surf_actor.SetVisibility(0)
        if(left_active.get()):
            l_surf=l_surf_t
            if l_surf is not None:
                l_surf_mapper.SetInputData(l_surf)
                l_surf_mapper.SetLookupTable(lut)
                l_locator.SetDataSet(l_surf)
                l_surf_actor.SetVisibility(1)
            else:
                l_surf_actor.SetVisibility(0)
        renWin.Render()
        for w in widgets:
            w.config(state='normal')
    processing_lock.release()
    
    

#===============================================Inteface=================================


top = tk.Toplevel(root)
top.title('Braviz-MriSurf')
control_frame = tk.Frame(top,width=100)

#===========================subjects list====================


select_subj_frame=braviz.interaction.subjects_list(reader,setSubj,control_frame,text='Subject',padx=10,pady=5,height='100')
select_subj_frame.pack(side='top',fill='y',expand=1)



#========================Hemispheres frame=============================
def actors_visibility():
        if left_active.get():
            l_surf_actor.SetVisibility(1)
        else:
            l_surf_actor.SetVisibility(0)
        if right_active.get():
            r_surf_actor.SetVisibility(1)
        else:
            r_surf_actor.SetVisibility(0)

def left_command():
    if surface.get() in ('inflated','sphere') and left_active.get():
        #only one hemishpere may be active
        right_active.set(0)
    actors_visibility()
    update()

def right_command():
    if surface.get() in ('inflated','sphere') and right_active.get():
        #only one hemishpere may be active
        left_active.set(0)
    actors_visibility()
    update()

hemi_frame=tk.Frame(control_frame,borderwidth=1,relief='groove')
hemi_frame.columnconfigure(0, weight=1)
hemi_frame.columnconfigure(1, weight=1)
left_check=tk.Checkbutton(hemi_frame,text='left',variable=left_active, command=left_command )
right_check=tk.Checkbutton(hemi_frame,text='right',variable=right_active, command=right_command)
label=tk.Label(hemi_frame,text='Hemisphere')
label.grid(row=0,columnspan=2,column=0)
left_check.grid(row=1,column=0,sticky=tk.W+tk.E)
right_check.grid(row=1,column=1,sticky=tk.W+tk.E)

#=================representationFrame=================================

repr_frame=tk.Frame(control_frame,padx=20,pady=20 ,borderwidth=1,relief='groove')
repr_frame.columnconfigure(0,weight=1)
repr_frame.columnconfigure(1,weight=1)
surf_label=tk.Label(repr_frame,text='Surface:')
pial_radio=tk.Radiobutton(repr_frame,text='Pial',variable=surface,value='pial', command=update )
white_radio=tk.Radiobutton(repr_frame,text='White',variable=surface,value='white', command=update )
orig_radio=tk.Radiobutton(repr_frame,text='Orig',variable=surface,value='orig', command=update )
inflated_radio=tk.Radiobutton(repr_frame,text='Inflated',variable=surface,value='inflated', command=update )
sphere_radio=tk.Radiobutton(repr_frame,text='Sphere',variable=surface,value='sphere', command=update )
for r in [surf_label, pial_radio,white_radio,orig_radio,inflated_radio,sphere_radio]:
    r.grid(column=0,sticky='NW')

scalar_label=tk.Label(repr_frame,text='Scalars:')
curv_radio=tk.Radiobutton(repr_frame,text='Curv',variable=scalar,value='curv', command=update )
area_radio=tk.Radiobutton(repr_frame,text='Area',variable=scalar,value='area', command=update )
thickness_radio=tk.Radiobutton(repr_frame,text='Thickness',variable=scalar,value='thickness', command=update )
volume_radio=tk.Radiobutton(repr_frame,text='Volume',variable=scalar,value='volume', command=update )
sulc_radio=tk.Radiobutton(repr_frame,text='Sulc',variable=scalar,value='sulc', command=update )
avg_radio=tk.Radiobutton(repr_frame,text='Avg curv',variable=scalar,value='avg_curv', command=update )
aparc_radio=tk.Radiobutton(repr_frame,text='Parcellation',variable=scalar,value='aparc', command=update )
aparc2009_radio=tk.Radiobutton(repr_frame,text='Parcellation 2009',variable=scalar,value='aparc.a2009s', command=update )
ba_radio=tk.Radiobutton(repr_frame,text='Broadman area',variable=scalar,value='BA', command=update )


for i,r in enumerate([scalar_label,curv_radio,area_radio,thickness_radio,volume_radio,sulc_radio,avg_radio,
                      aparc_radio,aparc2009_radio,ba_radio]):
    r.grid(column=1,row=i,sticky='NW')

repr_frame.columnconfigure(0, pad=20,weight=1)
repr_frame.columnconfigure(1, pad=20,weight=1)

#======================progress bar===================================

progress_bar=ttk.Progressbar(control_frame,orient='horizontal',length='100',mode='determinate',variable=progress)
progress_bar.bind('<<finished>>',refresh)
#=====================================================================

widgets=[select_subj_frame,right_check,left_check,
         pial_radio,white_radio,orig_radio,inflated_radio,sphere_radio,
         curv_radio,area_radio,thickness_radio,volume_radio,sulc_radio,avg_radio,
                      aparc_radio,aparc2009_radio,ba_radio]

#select_subj_frame.pack(side='top',expand='false')
#hemi_frame.pack(side='top',fill='x',expand='false')
#repr_frame.pack(side='top',fill='x',expand='false')

for f in [select_subj_frame,hemi_frame,repr_frame]:
    f.grid(column=0,sticky="ew")
progress_bar.grid(column=0)
control_frame.rowconfigure(1, pad=20)
control_frame.columnconfigure(0, weight=1)

display_frame = tk.Frame(top)
control_frame.pack(side="left", anchor="n", fill="y", expand="false")
display_frame.pack(side="left", anchor="n", fill="both")
renderer_frame = tk.Frame(display_frame)
renderer_frame.pack(padx=3, pady=3,side="left", anchor="n",
                    fill="both", expand="true")

render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                            rw=renWin,width=600,
                                            height=600)
def clean_exit():
    global renWin
    print "adios"
    renWin.Finalize()
    del renWin
    render_widget.destroy()
    root.quit()
    root.destroy()
top.protocol("WM_DELETE_WINDOW", clean_exit)

render_widget.pack(fill='both', expand='true')                                            
display_frame.pack(side="top", anchor="n", fill="both", expand="true")

iact = render_widget.GetRenderWindow().GetInteractor()
custom_iact_style=config.get_interaction_style()
iact_style=getattr(vtk,custom_iact_style)()
planeWidget.SetInteractor(iact)
iact.SetInteractorStyle(iact_style)
#planeWidget.SetPickingManaged(True)
planeWidget.On()

cam1 = ren.GetActiveCamera()
cam1.Elevation(80)
cam1.SetViewUp(0, 0, 1)
cam1.Azimuth(80)
ren.ResetCameraClippingRange()
render_widget.Render()
#===========================Picking========================
def getMessage(picker):
    prop=props[id(picker.GetProp3D())]
    if prop[0]=='L':
        pd=l_surf
    else:
        pd=r_surf
    ptId=picker.GetPointId()
    #print points.GetPoint(ptId)
    #print pd.GetPoint(ptId)
    #point=pd.GetPoint(pointId)
    point_data=pd.GetPointData()
    scalars=point_data.GetScalars()
    t=scalars.GetTuple(ptId)
    annotations=['aparc','aparc.a2009s','BA']
    if scalar.get() in annotations:
        label=lut.GetAnnotation(int(t[0]))
        return "%s-Label: %s"%(scalar.get(),label)
    return "%s = %f"%(scalar.get(),t[0])

active_picking=False
def picking(caller,event,*args):
    global active_picking
    if event=='MouseMoveEvent' and not active_picking:
        return
    if event=='LeftButtonReleaseEvent':
        active_picking=False
        return
    x,y=caller.GetEventPosition()
    picked=picker.Pick(x,y,0,ren)
    p=picker.GetPickPosition()
    n=picker.GetPickNormal()
    picked_prop=picker.GetProp3D()
    if picked and props.has_key(id(picked_prop)) :
        active_picking=True
        redCone.SetPosition(p)
        PointCone(redCone,*n)
        text2.SetVisibility(1)
        redCone.SetVisibility(1)
        message=getMessage(picker)
        text2.SetInput(message)
        if event=='LeftButtonPressEvent':
            command=caller.GetCommand(mouse_press_event_id)
            command.SetAbortFlag(1)
    if event=='MouseMoveEvent':
        command=caller.GetCommand(mouse_move_event_id)
        command.SetAbortFlag(1)
    renWin.Render()
    
picker.SetPickFromList(0)
picker.AddLocator(l_locator)
picker.AddLocator(r_locator)
iact.SetPicker(picker)

mouse_press_event_id=iact.AddObserver(vtk.vtkCommand.LeftButtonPressEvent,picking,10)
iact.AddObserver(vtk.vtkCommand.LeftButtonReleaseEvent,picking,10)
mouse_move_event_id=iact.AddObserver(vtk.vtkCommand.MouseMoveEvent,picking,10)




def yayay(source,event):
    print source.__this__
    print 'yayay'

#l_surf_actor.AddObserver(vtk.vtkCommand.PickEvent,yayay)
#r_surf_actor.AddObserver(vtk.vtkCommand.PickEvent,yayay)
#===============================START=======================

iact.Initialize()
renWin.Render()
iact.Start()
renWin.Render()

#print iact.GetPicker()
root.after_idle(update)
# Start Tkinter event loop
root.mainloop()