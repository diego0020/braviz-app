##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

from __future__ import print_function
import os
import logging
import csv
from braviz.utilities import working_directory, recursive_default_dict


__author__ = 'Diego'


def get_free_surfer_pretty_names_dict_from_rdf():
    from kernel.RDFDBManagerClass import RDFDBManager

    yoyis_dir = os.path.abspath(os.path.dirname(__file__))
    yoyis_dir = os.path.join(yoyis_dir, '..', '..', 'braint')
    log = logging.getLogger(__name__)
    with working_directory(yoyis_dir):
        if not os.path.isfile('File/rdfqueries/FreeNames'):
            manager = RDFDBManager('pythonBD',
                                   'http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53',
                                   'http://guitaca.uniandes.edu.co:8080')

            manager.loadPre_FreeNames('File/PreferredFreeCodeNames')
        log.info(os.getcwd())
        with open('File/rdfqueries/FreeNames') as rdf_names:
            out_dict = {}
            for l in rdf_names.readlines():
                l = l.rstrip('\n')
                code, long_name, fs_name = l.split('#')
                out_dict[fs_name] = long_name
        return out_dict


def get_free_surfer_long_names():
    path = os.path.join(
        os.path.dirname(__file__), "data", "free_surfer_long_names.csv")
    with open(path, "rb") as f:
        r = csv.reader(f)
        pretty_names = dict(t for t in r)
    return pretty_names


def cached_get_free_surfer_dict(reader=None):
    from braviz.readAndFilter import BravizAutoReader

    if reader is None:
        reader = BravizAutoReader()
    key = 'free_surfer_long_names_dict'
    names_dict = reader.load_from_cache(key)
    if names_dict is not None:
        return names_dict
    names_dict = get_free_surfer_long_names()
    reader.save_into_cache(key, names_dict)
    return names_dict


def get_braint_hierarchy():
    from kernel.RDFDBManagerClass import RDFDBManager
    yoyis_dir = os.path.abspath(os.path.dirname(__file__))
    yoyis_dir = os.path.join(yoyis_dir, '..', '..', 'braint')
    with working_directory(yoyis_dir):
        manager = RDFDBManager('pythonBD',
                               'http://www.semanticweb.org/jc.forero47/ontologies/2013/7/untitled-ontology-53',
                               'http://guitaca.uniandes.edu.co:8080')
        list_results = manager.loadQuery('File\\rdfqueries\IdAndNames')
        hierarchy_dict = recursive_default_dict()
        for my_item in list_results:
            evaluation_name = my_item['Evaluation']['value']
            test_name = my_item.get('TestName', {}).get('value', None)
            subtest_name = my_item.get('SubTestName', {}).get('value', None)
            subsubtest_name = my_item.get(
                'SubSubTestName', {}).get('value', None)

            if subsubtest_name is not None:
                hierarchy_dict[evaluation_name][test_name][
                    subtest_name][subsubtest_name]
            elif subtest_name is not None:
                hierarchy_dict[evaluation_name][test_name][subtest_name]
            elif test_name is not None:
                hierarchy_dict[evaluation_name][test_name]
            else:
                hierarchy_dict[evaluation_name]
        return hierarchy_dict


if __name__ == '__main__':
    print(cached_get_free_surfer_dict())
    evaluations_dict = get_braint_hierarchy()
    print(evaluations_dict)
