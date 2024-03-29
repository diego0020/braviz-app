# Mac installation

## Dependencies

### Home Brew

If you don't have home brew installed, install it using:

    ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
    
For more information look at the [homebrew page](http://brew.sh/)

It is possible that it will give you warning about not having xcode, in this case you should install xcode from the apple app store and open it to accept the license.

It is also a good idea to put the homebrew path (by default `/usr/local/bin` ) at the start of your path so that homebrew tools take precedence over osx. This can be done by

    export PATH=/usr/local/bin:$PATH

Add this line to your `.bash_profile` file so that it is executed automatically when starting the shell.

### Python

It is recomended to use the python version from homebrew, this can be installed by doing

    brew install python

### Homebrew Python packages

The following python packages should also be installed from homebrew

- Numpy
- SciPy
- Matplotlib
- PyQt

This packages can be found in homebrew-python, and they can be installed by doing

    brew tap Homebrew/python
    brew install numpy
    brew install scipy
    brew install matplotlib
    brew install pyqt

### R

R can also be installed from homebrew, it is located in homebre-science. The commands are

    brew tap homebrew/science
    brew install r

After installing r, some additional r libraries should be installed, this can be done by opening R

    r

and then typing

    install.packages("arm")
    install.packages("car")
    install.packages("randomForest")
    quit()

### VTK

vtk can also be installed from homebrew-science. This should be done after installing PyQt. The command is

    brew tap homebrew/science
    brew install vtk --with-qt

### Mercurial

Mercurial is the version control software used by braviz, and the easyest way to be up to date

     brew install mercurial

## Additional python packages

All this packages can be installed through pip, the basic syntax is

    pip install <package_name>

The following is the list of required packages

- nibabel
- colorbrewer
- rdflib
- httplib2
- psutil
- pandas
- mpltools
- seaborn
- rpy2
- tornado
- futures
- savReaderWriter
- xlrd
- XlsxWriter
- pyzmq

You can install all of these by typing

    pip install --allow-external savReaderWriter nibabel colorbrewer rdflib httplib2 psutil pandas mpltools seaborn rpy2 tornado futures savReaderWriter xlrd XlsxWriter pyzmq

## Get braviz

Go to the directory where you would like braviz files downloaded and do

    hg clone https://bitbucket.org/dieg0020/braviz


You should now add the braviz directory containing the file setup.py to your *PYTHONPATH* environment variable

    export PYTHONPATH = $PYTHONPATH:<braviz_dict>

You can add that line to your `.bash_profile` file in order to have braviz always available when you start a terminal


## Configuring

The ``braviz/applications`` directory contains several configuration files. First there should be a ``braviz.cfg`` file,
if it doesn't exist it will be automatically created when you first run the system. The second one is a file named
``<project>_hosts.cfg where <project>`` is the name of the project you will use (for example kmc400); this file contains
the locations of the project files for different computers. Be sure your computer is there with the correct paths. For
more information see  [braviz configuration](http://diego0020.github.io/braviz/graphical/configuration.html) and 
[host configuration](http://diego0020.github.io/braviz/library/configuring.html#host-configuration)



## Run braviz
After meeting all the requirements, and having the code, you should be able to run braviz by doing

    python -m braviz.application.braviz_menu2

the first time you launch the system you may require multiple attempts.
