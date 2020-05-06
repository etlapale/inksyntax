#! /usr/bin/env python
# -*- coding: utf-8; -*-

# Copyright (c) 2009–2015, Émilien Tlapale <emilien@tlapale.com>
# Release under the Simplified BSD License (see LICENSE file)


'''
A source code syntax highlighter plugin for Inkscape.
'''

import os
import platform
import sys
from subprocess import PIPE, Popen
import traceback

from gi.repository import Gdk, Gtk, Pango

__version__ = '0.2'

# Update PYTHONPATH for Inkscape plugins
try:
  # Ask inkscape for its extension directory
  p = Popen(['inkscape', '--extension-directory'], stdout=PIPE)
  out = p.communicate()[0]
  sys.path.append(out.strip())
except OSError:
  # Use some default directories
  sys.path.append('/usr/share/inkscape/extensions')
  sys.path.append(r'c:/Program Files/Inkscape/share/extensions')
sys.path.append(os.path.dirname(__file__))

import inkex
from simplestyle import *
from StringIO import StringIO

def hl_lang (s):
  '''Return the main highlight language name.'''
  if s.find ('(') < 0:
    return s
  return s[:s.find('(')].rstrip()

# Search for available highlighter backend and languages

HAVE_PYGMENTS = False
try:
    import pygments
    import pygments.lexers
    from pygments.formatters import SvgFormatter
    pygments_langs = {}
    for cls in pygments.lexers.get_all_lexers():
        pygments_langs[cls[0]] = pygments.lexers.find_lexer_class(cls[0])
    HAVE_PYGMENTS = True
except ImportError:
    pass

HAVE_HIGHLIGHT = False
try:
    p = Popen(['highlight', '--list-langs'], stdin=PIPE, stdout=PIPE)
    out = p.communicate()[0]
    # Get all available languages
    highlight_langs = {}
    for line in out.splitlines():
        if line.isspace() \
           or line.startswith('Installed language') \
           or line.startswith('Use name') \
           or not ':' in line:
            continue
        k, v = [x.strip() for x in line.split(':')]
        if k and not k.isspace():
            highlight_langs[k] = v
    HAVE_HIGHLIGHT = True
except OSError:
    pass

if not HAVE_PYGMENTS and not HAVE_HIGHLIGHT:
    raise RuntimeError("No source highlighter found!")

INKSYNTAX_NS = u"http://inksyntax.atelo.org"
INKSYNTAX_OLD_NS = u"http://www.lyua.org/inkscape/extensions/inksyntax/"
SVG_NS = u"http://www.w3.org/2000/svg"
XLINK_NS = u"http://www.w3.org/1999/xlink"
XML_NS = u"http://www.w3.org/XML/1998/namespace"

ID_PREFIX = "inksyntax-"

NSS = {
    u'textext': INKSYNTAX_NS,
    u'svg': SVG_NS,
    u'xlink': XLINK_NS,
}


def search_highlighter(liststore, name):
  '''
  Search an highlighter by name in a ListStore.
  '''
  for row in liststore:
    if row[0] == name:
      return liststore.get(row.iter, 1)[0]
  return None


def edit_fragment(text='', highlighter='', callback=None):
  '''
  Launch a GUI window to edit a text fragment.

  :param text:		Current text fragment content.
  :param highlighter:	Current highlighter name.
  :param callback:	Called when the edit is finished.
  '''

  # Setup a dialog to edit fragment
  win = Gtk.Window.new(Gtk.WindowType.TOPLEVEL)
  win.set_title("InkSyntax – Fragment editor")
  win.set_default_size(600, 400)
  win.set_keep_above(True)
  win.set_type_hint(Gdk.WindowTypeHint.DIALOG)
  grid = Gtk.Grid()
  grid.set_orientation(Gtk.Orientation.VERTICAL)
  grid.set_border_width(4)
  grid.set_column_spacing(16)
  grid.set_row_spacing(8)
  grid.set_column_homogeneous(False)
  grid.set_row_homogeneous(False)
  win.add(grid)
  win.connect('delete-event', Gtk.main_quit)

  # Language selector
  label = Gtk.Label()
  label.set_markup('<b>Language</b>')
  label.set_justify(Gtk.Justification.LEFT)
  grid.add(label)
  lang_edit = Gtk.Entry.new()
  completion = Gtk.EntryCompletion()
  liststore = Gtk.ListStore(str, object)
  if HAVE_PYGMENTS:
    langs = pygments_langs.keys()
    langs.sort()
    for name in langs:
      liststore.append([name + ' (Pygments)', pygments_langs[name]])
  if HAVE_HIGHLIGHT:
    langs = highlight_langs.keys()
    langs.sort()
    for name in langs:
      liststore.append([name + ' (Highlight)', highlight_langs[name]])
  completion.set_model(liststore)
  completion.set_text_column(0)
  lang_edit.set_completion(completion)
  def on_lang_edit_changed(ed):
    '''
    Search for the language/highlighter pair on entry edit.
    '''
    found = search_highlighter(liststore, lang_edit.get_text()) != None
    ok_but.set_sensitive(found)
    lang_edit.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY,
                                  Gtk.STOCK_YES if found \
                                  else Gtk.STOCK_DIALOG_WARNING)
  lang_edit.connect('changed', on_lang_edit_changed)
  lang_edit.set_hexpand(True)
  grid.attach_next_to(lang_edit, label, Gtk.PositionType.RIGHT, 1, 1)

  # Text area
  scroll = Gtk.ScrolledWindow()
  scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
  scroll.set_shadow_type(Gtk.ShadowType.IN)
  grid.attach_next_to(scroll, label, Gtk.PositionType.BOTTOM, 2, 1)
  view = Gtk.TextView()
  view.override_font(Pango.FontDescription.from_string('monospace 11'))
  view.set_border_width(4)
  view.get_buffer().set_text(text)
  view.set_vexpand(True)
  scroll.add(view)

  # Line numbering
  line_box = Gtk.CheckButton.new_with_label('Line numbering')
  grid.add(line_box)

  # Font
  font_button = Gtk.FontButton.new_with_font('monospace 12')
  font_button.set_hexpand(False)
  grid.attach_next_to(font_button, line_box, Gtk.PositionType.RIGHT, 1, 1)

  # Response buttons
  box = Gtk.Box()
  box.set_spacing(8)
  grid.attach_next_to(box, line_box, Gtk.PositionType.BOTTOM, 2, 1)
  ok_but = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
  ok_but.set_always_show_image(True)
  box.pack_end(ok_but, False, False, 0)
  cancel_but = Gtk.Button.new_from_stock(Gtk.STOCK_CANCEL)
  cancel_but.set_always_show_image(True)
  cancel_but.connect('clicked', Gtk.main_quit)
  box.pack_end(cancel_but, False, False, 0)

  # Disable Ok by default
  ok_but.set_sensitive(False)
  lang_edit.set_icon_from_stock(Gtk.EntryIconPosition.SECONDARY,
                                Gtk.STOCK_DIALOG_WARNING)

  # Callback on OK press
  def on_ok(*args):
    hname = lang_edit.get_text()
    highlighter = search_highlighter(liststore, hname)
    if highlighter is None:
      return
    backend = 'pygments' if hname.endswith('(Pygments)') else 'highlight'
    if callback is not None:
      buf = view.get_buffer()
      beg,end = buf.get_bounds()
      callback(buf.get_text(beg, end, False),
               backend=backend,
               highlighter=highlighter,
               line_numbers=line_box.get_active(),
               font=font_button.get_font_name())
    Gtk.main_quit()
  ok_but.connect('clicked', on_ok)
  
  # Launch the dialog
  win.activate_focus()
  win.show_all()
  Gtk.main()


class InkSyntaxEffect(inkex.Effect):
    def __init__(self):
        inkex.Effect.__init__(self)
        self.OptionParser.add_option('-s', '--src-lang', action='store',
                                     type='string', dest='src_lang',
                                     default='txt', help='Source language')
    def effect(self):
        src_lang = self.options.src_lang

        # Get previous highlighted text
        old_node, text = self.get_old()

        # Query missing information
        edit_fragment(text, callback=self.inserter)

    def inserter(self, text, backend, highlighter,
                 line_numbers=False, font=None):
        # Get SVG highlighted output as character string
        if backend == 'highlight':
	    # For highlight 2.x
            #cmd = ["highlight", "--syntax", stx, "--svg"]
	    # For highlight 3.x
            cmd = ["highlight", "--syntax",
                   hl_lang (highlighter), # Fix for hl 3.9
                   "-O", "svg"]
            if line_numbers:
                cmd.append("--line-number")
            p = Popen(cmd, stdin=PIPE, stdout=PIPE)
            out = p.communicate(text)[0]
        else:
            out = pygments.highlight(text, highlighter(), SvgFormatter())

        # Parse the SVG tree and get the group element
        try:
            tree = inkex.etree.parse(StringIO(out))
        except inkex.etree.XMLSyntaxError:
            # Hack for highlight 2.12
            out2 = out.replace('</span>', '</tspan>')
            tree = inkex.etree.parse(StringIO(out2))
        group = tree.getroot().find('{%s}g' % SVG_NS)

        # Remove the background rectangle
        if group[0].tag == '{%s}rect' % SVG_NS:
            del group[0]

        # Apply a CSS style
        if backend == 'highlight':
            self.apply_style_highlight(group)
        else:
            self.apply_style_pygments(group)

        # Set the attributes for modification
        group.attrib['{%s}text' % INKSYNTAX_NS] = text.encode('string-escape')

        # Add the SVG group to the document
        svg = self.document.getroot()
        self.current_layer.append(group)

	# Try to apply properties
	if font is not None:
	    fd = Pango.FontDescription.from_string(font)
	    group.set('style', formatStyle({'font-size': '%fpt' % (fd.get_size()/Pango.SCALE),
	                                    'font-family': fd.get_family()}))

    def get_old(self):
        # Search amongst all selected <g> nodes
        for node in [self.selected[i] for i in self.options.ids
                     if self.selected[i].tag == '{%s}g' % SVG_NS]:
            # Return first <g> with a inksyntax:text attribute
            if '{%s}text' % INKSYNTAX_NS in node.attrib:
                return (node,
                        node.attrib.get('{%s}text' %
                                        INKSYNTAX_NS).decode('string-escape'))
            # Pre 0.2 NS compatibility
            if '{%s}text' % INKSYNTAX_OLD_NS in node.attrib:
                return (node,
                        node.attrib.get('{%s}text' %
                                        INKSYNTAX_OLD_NS).decode('string-escape'))
        return None, ''

    def apply_style_highlight(self, group):
        group.set('style', formatStyle({'font-size': '10',
                                        'font-family': 'Monospace'}))
        style = {
            'com':   {'fill': '#838183', 'font-style': 'italic'},
            'dir':   {'fill': '#008200'},
            'dstr':  {'fill': '#818100'},
            'esc':   {'fill': '#ff00ff'},
            'kwa':   {'fill': '#000000', 'font-weight': 'bold'},
            'kwb':   {'fill': '#830000'},
            'kwc':   {'fill': '#000000', 'font-weight': 'bold'},
            'kwd':   {'fill': '#010181'},
            'line':  {'fill': '#555555'},
            'num':   {'fill': '#2228ff'},
            'slc':   {'fill': '#838183', 'font-style': 'italic'},
            'str':   {'fill': '#ff0000'},
            'sym':   {'fill': '#000000'},
        }
        for txt in [x for x in group if x.tag == '{%s}text' % SVG_NS]:
            # Modify the line spacing
            line_spacing_factor = 0.65
            txt.set('y', str(line_spacing_factor * float(txt.get('y'))))
            # Preserve white spaces
            txt.attrib['{%s}space' % XML_NS] = 'preserve'
            # Set the highlight color
            for tspan in [x for x in txt if x.tag == '{%s}tspan' % SVG_NS]:
                cls = tspan.get('class')
                if cls in style:
                    tspan.set('style', formatStyle(style[cls]))

    def apply_style_pygments(self, group):
        pass

if __name__ == '__main__':
  # Standalone
  if len(sys.argv) == 1:
    def cb(text, **kwds):
      print(text, kwds)
    edit_fragment('''#include <iostream>

int main()
{
  std::cout << "Hello world!" << std::endl;
  return 0;
}
''', callback=cb)
  # Called as a plugin
  else:
    effect = InkSyntaxEffect()
    effect.affect()
