import os

from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "Braviz",
    version = "3.0",
    author = "Diego Angulo",
    author_email = "da.angulo39@uniandes.edu.co",
    description = "A framework for interactive analysis of brain data",
    license = "LGPL",
    keywords = "visual analytics brain data",
    url = "imagine.uniandes.edu.co",
    packages=['braviz', 'braint'],
    long_description=read('README.md'),
    install_requires=['vtk','nibabel','numpy',
                      'scipy','pandas','psutil',
                      'matplotlib','PyQt4','sip','pandas', 'seaborn','rpy2','tornado',
                      ],
    r_libraries=["car","randomforest"],
)