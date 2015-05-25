Installation
============

Requirements
------------
- Python bindings to Gtk3. That is the new introspection-based
  binding, not the old pygtk for Gtk2.
- lxml_ Python library.  The package is named
  ``python-lxml`` on Debian variants, or ``lxml`` in
  ``pip``/``easy_install``.
- A syntax highlighter (either pygments_ (preferred) or highlight_.

Installing
----------

To use Inkscape, copy the two extension files, ``inksyntax.inx`` and
``inksyntax.py`` into your Inkscape extension directory. If you can
modify Inkscape installation, the extension directory is given by:

.. code-block: console
   
   % inkscape --extension-directory
   /usr/share/inkscape/extensions

Otherwise, copy the files in your personal extension directory, such as
``~/.config/inkscape/extensions`` on Linux, and (re)start Inkscape.

Troubleshooting
---------------

Some clues in case it does not work:

- Make sure that the ``inksyntax.py`` file is executable (this was not
  the case in old releases).

.. _lxml: http://lxml.de
.. _pygments: http://pygments.org/
.. _highlight: http://www.andre-simon.de/doku/highlight/en/highlight.html
