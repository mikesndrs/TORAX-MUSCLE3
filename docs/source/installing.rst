.. _`installing`:

Installing the PDS
=================================

SDCC setup
----------

.. note::
  A module will become available on SDCC after the first release of PDS.
  Use the following instructions to work with the latest development version.

.. 
  Update SDCC setup on first release

* Setup a project folder and clone git repository

  .. code-block:: bash

    mkdir projects
    cd projects
    git clone ssh://git@git.iter.org/scen/torax-m3.git
    cd torax-m3

* Setup a python virtual environment and install python dependencies

  .. code-block:: bash

    # load IMAS and IMASPy before install
    module load IMAS/3.40.1-5.1.0-intel-2020b IMASPy MUSCLE3
    python3 -m venv ./venv
    . venv/bin/activate
    pip install --upgrade pip
    pip install --upgrade wheel setuptools
    # For development an installation in editable mode may be more convenient
    pip install -e .[all]

* Load IMAS and IMASPy

  .. code-block:: bash

    # Load modules every time you use torax-m3
    module load IMAS/3.40.1-5.1.0-intel-2020b IMASPy MUSCLE3
    # And activate the Python virtual environment
    . venv/bin/activate

* Test the installation

  .. code-block:: bash

    python3 -c "import torax-m3; print(torax-m3.__version__)"
    pytest


Ubuntu installation
-------------------

* Install system packages

  .. code-block:: bash

    sudo apt update
    sudo apt install build-essential git-all python3-dev python-is-python3 \
      python3 python3-venv python3-pip python3-setuptools

* Setup a project folder and clone git repository

  .. code-block:: bash

    mkdir projects
    cd projects
    git clone ssh://git@git.iter.org/scen/torax-m3.git
    cd torax-m3

* Setup a python virtual environment and install python dependencies

  .. code-block:: bash

    python3 -m venv ./venv
    . venv/bin/activate
    pip install --upgrade pip
    pip install --upgrade wheel setuptools
    # For development an installation in editable mode may be more convenient
    pip install .[all]

* Install IMASPy.

  Follow the instructions from `IMASPy installation docs <https://git.iter.org/projects/IMAS/repos/imaspy/browse/docs/source/installing.rst>`_

* Test the installation

  .. code-block:: bash

    python3 -c "import torax-m3; print(torax-m3.__version__)"
    pytest

* To build the torax-m3 documentation, execute:

  .. code-block:: bash

    make -C docs html
