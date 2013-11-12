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
    try:
        yield
    except exceptions:
        pass


def recursive_default_dict():
    return defaultdict(recursive_default_dict)

def get_leafs(rec_dict,name):
    if len(rec_dict) == 0:
        return [name]
    leafs=[]
    for k,sub_d in rec_dict.iteritems():
        sub_leafs=get_leafs(sub_d,k)
        sub_leafs=map(lambda x:':'.join((name,x)),sub_leafs)
        leafs.extend(sub_leafs)
    return leafs
