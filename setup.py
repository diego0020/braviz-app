import os

from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "PyTanic",
    version = "2.0.1",
    author = "Imagine",
    author_email = "da.angulo39@uniandes.edu.co",
    description = "A framework for interactive analysis of brain data",
    license = "?",
    keywords = "visual analytics brain data",
    url = "imagine.uniandes.edu.co",
    packages=['braviz', 'braint'],
    long_description=read('README.txt'),
    install_requires=['nibabel','colorbrewer','numpy',
                      'scipy','rdflib','httplib2','psutil',
                      'matplotlib','PyQt4','sip','pandas', 'mpltools', 'seaborn','rpy2'],
    r_libraries=["car","randomforest"],
)