'''
Created on 24/09/2013

@author: jc.forero47
'''
import urllib
import httplib2
import json

class RDFDBManager:
    def __init__(self,repositoryName, graphName, RepositoryEndPoint): ##Constructor donde inicializo mis atributos de repositorio y grafo
       self.repository=repositoryName
       self.graph=graphName
       self.RepEndPoint=RepositoryEndPoint
       
    def loadRdf(self,filename):
        print "Loading %s into %s in Sesame" % (filename, self.graph)
        params = { 'context': '<' + self.graph + '>' }
        endpoint= "%s/openrdf-sesame/repositories/%s/statements?%s" % (self.RepEndPoint, self.repository, urllib.urlencode(params))
        #endpoint = "http://gambita.uniandes.edu.co:8080/openrdf-sesame/repositories/%s/statements?%s" % (self.repository, urllib.urlencode(params))
        data = open(filename, 'r').read()
        (response, content) = httplib2.Http().request(endpoint, 'PUT', body=data, headers={ 'content-type': 'text/turtle' })
        print "Response %s" % response.status
        print content
    def loadQuery(self,filename):
        data = open(filename, 'r').read()
        endpoint = "%s/openrdf-sesame/repositories/%s" % (self.RepEndPoint, self.repository)
        print "POSTing SPARQL query to %s" % (endpoint)
        params = { 'query': data }
        headers = { 
                   'content-type': 'application/x-www-form-urlencoded', 
                   'accept': 'application/sparql-results+json' 
                   }
        (response, content) = httplib2.Http().request(endpoint, 'POST', urllib.urlencode(params), headers=headers)
        print "Response %s" % response.status
        results = json.loads(content)
        print results
        print results['results']['bindings']
       #print len(results['results']['bindings'])
        miLista = results['results']['bindings']
        #=======================================================================
        # for miItem in miLista:
        #     xValue = miItem['x']['value']
        #     xVal,xSep,xAft = xValue.partition('#')
        #     yValue = miItem['y']['value']
        #     yVal,ySep,yAft = yValue.partition('#')
        #     zValue = miItem['z']['value']
        #     zVal,zSep,zAft = zValue.partition('#')
        #     print xAft  + '\t' + yAft + '\t' + zAft
        #=======================================================================
        return miLista #ME devuelve el diccionario con los resultados
    def loadQueryParentChildren(self,filename, parent, relation):
        data= open(filename, 'r').read()
        data=data.replace('PARENT_CODE', parent).replace('RELATION', relation)
        endpoint = "%s/openrdf-sesame/repositories/%s" % (self.RepEndPoint, self.repository)
        #print "POSTing SPARQL query to %s" % (endpoint)       
        params = { 'query': data }
        headers = { 
                   'content-type': 'application/x-www-form-urlencoded', 
                   'accept': 'application/sparql-results+json' 
                   }
        (response, content) = httplib2.Http().request(endpoint, 'POST', urllib.urlencode(params), headers=headers)
        #print "Response %s" % response.status
        results = json.loads(content)
       # print results
        #print results['results']['bindings']
        #print len(results['results']['bindings'])
        miLista = results['results']['bindings']
        childrenList = list()
        for miItem in miLista:
            xValue = miItem['Result']['value']
            xVal,xSep,xAft = xValue.partition('#')
            childrenList.append(xAft)
        return childrenList
        
myManager=RDFDBManager('pythonBD','http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53','http://gambita.uniandes.edu.co:8080') ##Crear objeto del tipo RDFDBmanager
#myManager.loadRdf('File\\RDFFiles\\Cascaron.ttl') ##LLamo la funcion a traves de la instancia que se creo arriba para subir al repo un archivo ttl
#myManager.loadRdf('File\\RDFFiles\\JerarquiasComp.ttl')##LLamo la funcion a traves de la instancia que se creo arriba para subir al repo un archivo ttl
#myManager.loadQuery('C:\Users\jc.forero47\Documents\JohanaForero\Repositorios\\braviz\\braint\java\\braint_v_1.0\File\\rdfqueries\EvaluationIdTestIdSubtestIdSubSubTest') #Lanza una query que entra como parametro en el archi ve entrada
#myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch','CLINI', 'hasSubTest' )
#myManager.loadQueryParentChildren('File\\rdfqueries\\ChildrenSearch','FSIQ', 'isRelatedWith' )