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
    license = "LGPLv3+",
    keywords = "visual analytics brain data",
    url = "http://imagine.uniandes.edu.co",
    packages=['braviz', 'braint'],
    long_description=read('README.md'),
    install_requires=['vtk','nibabel','numpy',
                      'scipy','pandas','psutil',
                      'matplotlib','PyQt4','pandas', 'seaborn','rpy2','tornado', 'futures',
                      'savReaderWriter','xlrd','XlsxWriter'],
    classifiers=["Development Status :: 3 - Alpha",
                 "Environment :: X11 Applications :: Qt",
                 "Intended Audience :: Science/Research",
                 "Intended Audience :: End Users/Desktop",
                 "License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)",
                 "Programming Language :: Python :: 2",
                 "Topic :: Scientific/Engineering :: Visualization",
                 "",
                 ],
    r_libraries=["car","randomforest"],
)