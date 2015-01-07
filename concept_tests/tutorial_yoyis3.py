#Para correr desde la consola de windows
# C:\Python27_32\python.exe tutorial_yoyis.py [subject] [espacio] 

import sys

import braviz
from braviz import _test_arrow


subject='093'
#print sys.argv
#sys.argv = [ <nombre del programa> , <numero del paciente>  , <espacio> ,arg3 .... ]

espacios_validos=['world','dartel','talairach']

espacio='talairach'
if len(sys.argv) >1:
    subject=sys.argv[1]

if len(sys.argv) >2:
    if not sys.argv in espacios_validos:
        print "Ese espacio no es correcto"
        print "pintando en "+espacio
    else:
        espacio=sys.argv[2]
    
#reader=braviz.readAndFilter.kmc40.kmc40Reader(reader'C:\Users\da.angulo39\Documents\Kanguro')
#reader=braviz.readAndFilter.kmc40.kmc40Reader(reader'K:\JohanaForero\KAB-db')
#reader=reader=braviz.readAndFilter.kmc40AutoReader()
reader=braviz.readAndFilter.BravizAutoReader()


#crear visualizador
viewer= simpleVtkViewer()

#todas
# fibers=reader.get('fibers',subject,space=espacio)

#fibers=reader.get('fibers',subject,space=espacio,waypoint='CC_Central')

fibers_l=reader.get('fibers','325',color='fa',waypoint='CC_Central')
actor_fibras=viewer.addPolyData(fibers_l)
#actor_fibras.GetProperty().SetOpacity(0.1)


#Agregar imagen
mri=reader.get('mri',subject,format='vtk',space=espacio)
viewer.addImg(mri)

amygdala=reader.get('model',subject,name='Right-Amygdala',space=espacio)

#guardad actor
actor=viewer.addPolyData(amygdala)
#Cambiar color amygdala
actor.GetProperty().SetColor(0,1,0)
#color std de free surfer
#color=reader.get('model','093',name='Right-Amygdala',color=1)
#actor.GetProperty().SetColor(color[:-1])

viewer.ren.SetBackground(0.9,0.5,0.5)
viewer.start()



