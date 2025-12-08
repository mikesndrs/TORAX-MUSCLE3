.. _`index`:

.. 
   Main "index". This will be converted to a landing index.html by sphinx. We
   define TOC here, but it'll be put in the sidebar by the theme

=========================
IMAS PDS Manual
=========================

IMAS PDS is an integrated modeling tool for IMAS simulations.

README
------

The README is best read on the `git page <https://git.iter.org/projects/SCEN/repos/torax-m3/browse>`_.

Manual
------

.. toctree::
   :caption: Getting Started
   :maxdepth: 2

   self
   installing
   usage
   tips_and_tricks

.. toctree::
   :caption: API docs
   :maxdepth: 1

   api

.. toctree::
   :caption: Development
   :maxdepth: 1

   code_style
   ci_config



LICENSE
-------

.. literalinclude:: ../../LICENSE.md
   :language: text


Sitemap
-------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
