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
    
#r=braviz.readAndFilter.kmc40.kmc40Reader(r'C:\Users\da.angulo39\Documents\Kanguro')
#r=braviz.readAndFilter.kmc40.kmc40Reader(r'K:\JohanaForero\KAB-db')
#r=r=braviz.readAndFilter.kmc40AutoReader()
r=braviz.readAndFilter.BravizAutoReader()

# Sacar lista de pacientes
subjects_list=r.get('ids')

# Sacar lista de estructuras para el 093
model_list=r.get('model',subject,index=1)


#leer putamen
putamen=r.get('model',subject,name='Left-Putamen',space=espacio)

#crear visualizador
v= simpleVtkViewer()

#agregar putamen al visualizador
v.addPolyData(putamen)


#Agregar amygdala
amygdala=r.get('model',subject,name='Right-Amygdala',space=espacio)
v.addPolyData(amygdala)

#Agregar imagen
mri=r.get('aparc',subject,format='vtk',space=espacio)
v.addImg(mri)
v.start()



