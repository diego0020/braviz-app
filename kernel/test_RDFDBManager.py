'''
Created on 28/10/2013

@author: jc.forero47
'''
from kernel.RDFDBManagerClass import *


#myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://localhost:8080') ##Crear objeto del tipo RDFDBmanager
myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://guitaca.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
#myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
myManager.loadRdf('File\\RDFFiles\\Cascaron.ttl') ##LLamo la funcion a traves de la instancia que se creo arriba para subir al repo un archivo ttl
myManager.loadRdf('File\\RDFFiles\\JerarquiasComp.ttl')##LLamo la funcion a traves de la instancia que se creo arriba para subir al repo un archivo ttl
myManager.loadRdf('File\\RDFFiles\\volumesTriplets1.ttl')##LLamo la funcion a traves de la instancia que se creo arriba para subir al repo un archivo ttl
#myManager.loadQuery('C:\Users\jc.forero47\Documents\JohanaForero\Repositorios\\braviz\\braint\java\\braint_v_1.0\File\\rdfqueries\EvaluationIdTestIdSubtestIdSubSubTest') #Lanza una query que entra como parametro en el archi ve entrada
#myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch','CLINI', 'hasSubTest' )
#list=myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch','FSIQ', 'isRelatedWith' )
#myManager.loadFreeSurferNames('File\\rdfqueries\\StructureNames','G_frontal_inf-Orbital_part')
#myManager.loadPre_FreeNames('File\\rdfqueries\\PreferredFreeCodeNames')
#list_results = myManager.load_each_free_name('File\\rdfqueries\\Each_Free_Name.txt','RID17105')
#print list

