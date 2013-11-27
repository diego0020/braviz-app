import contextlib
import os
from collections import defaultdict


@contextlib.contextmanager
def working_directory(path):
    """A context manager which changes the working directory to the given
    path, and then changes it back to its previous value on exit.

    """
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)

from contextlib import contextmanager

@contextmanager
def ignored(*exceptions):
    #A context manager which ignores exceptions of specific types
    try:
        yield
    except exceptions:
        pass


def recursive_default_dict():
    #A default dict which by default contains default dicts which by default contain default dicts....
    return defaultdict(recursive_default_dict)

def get_leafs(rec_dict,name):
    #input should be a recursive dicitionary whose elements are dictionaries, and a base name
    #output will be a list of leafs, this is, elements which contain empty dictionaries as sons
    #names in the output list will have the structure name:grandparent:parent:leaf
    if len(rec_dict) == 0:
        return [name]
    leafs=[]
    for k,sub_d in rec_dict.iteritems():
        sub_leafs=get_leafs(sub_d,k)
        sub_leafs=map(lambda x:':'.join((name,x)),sub_leafs)
        leafs.extend(sub_leafs)
    return leafs
