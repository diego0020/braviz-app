from __future__ import division
import braviz
import vtk
import random
import math

__author__ = 'Diego'
reader=braviz.readAndFilter.kmc40AutoReader()
viewer=braviz.visualization.simpleVtkViewer()

subj_ids=reader.get('ids')

amygdalas={}
for subj in subj_ids:
    amygdalas[subj]=reader.get('model',subj,name='Left-Amygdala',space='talairach')

actors_dict={}
subj_dir={}
for subj in subj_ids:
    actor=viewer.addPolyData(amygdalas[subj])
    actors_dict[actor]=subj
    subj_dir[subj]=actor

#color
def get_color(id):
    return [random.random() for i in range(3)]

for actor,id in actors_dict.iteritems():
    actor.GetProperty().SetColor(get_color(id))


#balloons

balloon_widget=vtk.vtkBalloonWidget()
balloon_rep=vtk.vtkBalloonRepresentation()
balloon_widget.SetRepresentation(balloon_rep)
balloon_widget.SetInteractor(viewer.iren)
balloon_widget.On()

for actor,id in actors_dict.iteritems():
    balloon_widget.AddBalloon(actor,id)
#order

#calculate bounds
def get_max_diagonal(actor):
    Xmin, Xmax, Ymin, Ymax, Zmin, Zmax=actor.GetBounds()
    return math.sqrt((Xmax-Xmin)**2+(Ymax-Ymin)**2+(Zmax-Zmin)**2)

max_space=max([get_max_diagonal(actor) for actor in actors_dict.keys()])
max_space*=0.8
#calculate renWin proportions
width,height=viewer.renWin.GetSize()
row_proportion=width/height
total_area=width*height
total_objects=len(subj_ids)
area_per_object=total_area/total_objects
n_row=round(math.sqrt(len(subj_ids)/row_proportion))
n_col=math.ceil(len(subj_ids)/n_row)

sorted_subj=sorted(subj_ids,key=lambda x:int(x))
for i,subj in enumerate(sorted_subj):
    actor=subj_dir[subj]
    column=i%n_col
    row=i//n_col
    x=column*max_space
    y=row*max_space
    actor.SetPosition(x ,y , 0)



#camera
cam1=viewer.ren.GetActiveCamera()
cam1.ParallelProjectionOn()
cam1.SetFocalPoint(n_col*max_space/2,n_row*max_space/2,0)
cam1.SetPosition(n_col*max_space/2,n_row*max_space/2,-200)
cam1.SetViewUp(0,-1,0)

#interaction
viewer.iren.SetInteractorStyle(vtk.vtkInteractorStyleImage())
viewer.start()