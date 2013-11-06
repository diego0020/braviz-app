from kernel.RDFDBManagerClass import RDFDBManager
import os
from braviz.utilities import working_directory,ignored
__author__ = 'Diego'

def get_free_surfer_pretty_names_dict():
    yoyis_dir = os.path.abspath(os.path.dirname(__file__))
    yoyis_dir=os.path.join(yoyis_dir, '..', 'braint')
    with working_directory(yoyis_dir):
        if not os.path.isfile('File/rdfqueries/FreeNames'):
            manager=RDFDBManager('pythonBD',
                                 'http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53',
                                 'http://guitaca.uniandes.edu.co:8080')

            manager.loadPre_FreeNames('File/PreferredFreeCodeNames')
        print os.getcwd()
        with open('File/rdfqueries/FreeNames') as rdf_names:
            out_dict={}
            for l in rdf_names.readlines():
                l=l.rstrip('\n')
                code,long_name,fs_name=l.split('#')
                out_dict[fs_name]=long_name
        return out_dict

def cached_get_free_surfer_dict(reader=None):
    from braviz.readAndFilter import kmc40AutoReader
    import cPickle
    if reader is None:
        reader=kmc40AutoReader()
    data_root=reader.getDataRoot()
    pickles_dir=os.path.join(data_root,'pickles')
    cache_file=os.path.join(pickles_dir,'free_surfer_long_names_dict.pickle')
    with ignored(IOError):
        with open(cache_file,'rb') as pickle_file:
            names_dict=cPickle.Unpickler(pickle_file).load()
            return names_dict
    names_dict=get_free_surfer_pretty_names_dict()
    with ignored(IOError):
        with open(cache_file,'wb') as pickle_file:
            cPickle.Pickler(pickle_file, 2).dump(names_dict)
    return names_dict



if __name__=='__main__':
    print cached_get_free_surfer_dict()




