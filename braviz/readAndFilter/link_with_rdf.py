from kernel.RDFDBManagerClass import RDFDBManager
import os
from braviz.utilities import working_directory,ignored,recursive_default_dict
__author__ = 'Diego'



def get_free_surfer_pretty_names_dict():
    yoyis_dir = os.path.abspath(os.path.dirname(__file__))
    yoyis_dir=os.path.join(yoyis_dir, '..','..', 'braint')
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


def get_braint_hierarchy():
    yoyis_dir = os.path.abspath(os.path.dirname(__file__))
    yoyis_dir = os.path.join(yoyis_dir, '..', '..', 'braint')
    with working_directory(yoyis_dir):
        manager = RDFDBManager('pythonBD',
                               'http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53',
                               'http://guitaca.uniandes.edu.co:8080')
        list_results = manager.loadQuery('File\\rdfqueries\IdAndNames')
        hierarchy_dict=recursive_default_dict()
        for my_item in list_results:
            evaluation_name = my_item['Evaluation']['value']
            test_name = my_item.get('TestName',{}).get('value',None)
            subtest_name = my_item.get('SubTestName',{}).get('value',None)
            subsubtest_name = my_item.get('SubSubTestName',{}).get('value',None)

            if subsubtest_name is not None:
                hierarchy_dict[evaluation_name][test_name][subtest_name][subsubtest_name]
            elif subtest_name is not None:
                hierarchy_dict[evaluation_name][test_name][subtest_name]
            elif test_name is not None:
                hierarchy_dict[evaluation_name][test_name]
            else:
                hierarchy_dict[evaluation_name]
        return hierarchy_dict

if __name__=='__main__':
    print cached_get_free_surfer_dict()
    evaluations_dict=get_braint_hierarchy()
    print evaluations_dict



