#! /usr/bin/env python
# -*- coding: utf-8; -*-

# Copyright (c) 2009–2015, Émilien Tlapale <emilien@tlapale.com>
# Release under the Simplified BSD License (see LICENSE file)


'''
A source code syntax highlighter plugin for Inkscape.
'''

__version__ = '0.2'

import os
import platform
import sys
from subprocess import PIPE, Popen
import traceback

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
    from pygments import highlight
    import pygments.lexers
    from pygments.formatters import SvgFormatter
    pygments_langs = {}
    for cls in pygments.lexers.LEXERS:
        if cls.endswith('Lexer'):
            pygments_langs[cls[:-5]] = getattr(pygments.lexers, cls)
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

INKSYNTAX_NS = u"http://inkscape.atelo.org"
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

# Gtk3 GUI to edit code fragment and its properties
from gi.repository import Gdk, Gtk

# TODO: use a property argument for old properties

def edit_fragment(text, callback):
  '''
  Edit a text fragment.

  :param callback:	Called when the edit is finished.
  '''

  # Setup a dialog to edit fragment
  win = Gtk.Window.new(Gtk.WindowType.TOPLEVEL)
  win.set_title("InkSyntax – Fragment editor")
  win.set_default_size(600, 400)
  win.set_keep_above(True)
  win.set_type_hint(Gdk.WindowTypeHint.DIALOG)
  grid = Gtk.Grid()
  grid.set_column_spacing(8)
  grid.set_column_homogeneous(False)
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
    Callback when the language selection entry is modified.
    '''
    print('lang set to ' + ed.get_text())
    found = False
    for row in liststore:
      # Language description found (entry is valid)
      if row[0] == ed.get_text():
        print('found it:', row)
        found = True
        break
    lang_edit.set_icon_from_stock(Gtk.EntryIconPosition.PRIMARY,
                                  Gtk.STOCK_YES if found \
                                  else Gtk.STOCK_DIALOG_WARNING)
  lang_edit.connect('changed', on_lang_edit_changed)
  lang_edit.set_hexpand(True)
  grid.attach_next_to(lang_edit, label, Gtk.PositionType.RIGHT, 1, 1)
  
    #win.add_buttons(Gtk.STOCK_CANCEL, 0, Gtk.STOCK_OK, 1)

  # Handler for button press
  #def on_response(dlg, resp_id):
  #  print(dlg, resp_id)
  #  Gtk.main_quit()
  #win.connect("response", on_response)
  
  # Launch the dialog
  win.activate_focus()
  win.show_all()
  Gtk.main()

  
  
#---------------------------------------------------------------
# GUI from TexText by Pauli Virtanen <pav@iki.fi> (BSD licensed)
#---------------------------------------------------------------

if False:
            # Fill the syntax list
            label3 = gtk.Label(u"Text:")
            
            self._text = gtk.TextView()
            self._text.get_buffer().set_text(self.text)
	    # Use monospaced font for input
	    self._text.modify_font(pango.FontDescription('monospace'))

            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.add(self._text)
            
            self._ok = gtk.Button(stock=gtk.STOCK_OK)
            self._cancel = gtk.Button(stock=gtk.STOCK_CANCEL)

            self.line_number = gtk.CheckButton('Line numbers')

	    # Font selector
	    fd = pango.FontDescription('monospace 12')
	    self.font_field = gtk.FontButton(fd.to_string())
    
            # layout
            table = gtk.Table(4, 2, False)
            table.attach(self.line_number,     0,2,1,2,xoptions=0,yoptions=gtk.FILL)
            table.attach(gtk.Label('Font:'),   0,1,2,3,xoptions=0,yoptions=gtk.FILL)
            table.attach(self.font_field,      1,2,2,3,xoptions=0,yoptions=gtk.FILL)
            table.attach(label3,               0,1,3,4,xoptions=0,yoptions=gtk.FILL)
            table.attach(sw,                   1,2,3,4)
    
    
            window.connect("key-press-event", self.cb_key_press)
            self._ok.connect("clicked", self.cb_ok)
            self._cancel.connect("clicked", self.cb_cancel)
    

            self._text.grab_focus()



            #def cb_key_press(self, widget, event, data=None):
            # ctrl+return clicks the ok button
            #if gtk.gdk.keyval_name(event.keyval) == 'Return' \
            #       and gtk.gdk.CONTROL_MASK & event.state:
            #    self._ok.clicked()
            #    return True
            #return False
        
            #def cb_ok(self, widget, data=None):
            #buf = self._text.get_buffer()
            #self.text = buf.get_text(buf.get_start_iter(),
            #                         buf.get_end_iter())
            
            try:
                # Fetch back the selected syntax
                act = self.combobox.get_active()
                if HAVE_PYGMENTS:
                    pyglen = len(pygments_langs)
                    if act < pyglen:
                        stx = ('pygments', self.liststore[act][1])
                    else:
                        stx = ('highlight', self.liststore[act][1])
                else:
                    stx = ('highlight', self.liststore[act][1])
		props = {
		    'lines': self.line_number.get_active(),
		    'font': self.font_field.get_font_name(),
		}
                self.callback(stx, self.text, props)
            except StandardError, e:
                err_msg = traceback.format_exc()
                dlg = gtk.Dialog("InkSyntax Error", self._window, 
                                 gtk.DIALOG_MODAL)
                dlg.set_default_size(600, 400)
                btn = dlg.add_button(gtk.STOCK_OK, gtk.RESPONSE_CLOSE)
                btn.connect("clicked", lambda w, d=None: dlg.destroy())
                msg = gtk.Label()
                msg.set_markup("<b>Error occurred while converting text to SVG:</b>")
                
                txtw = gtk.ScrolledWindow()
                txtw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
                txtw.set_shadow_type(gtk.SHADOW_IN)
                txt = gtk.TextView()
                txt.set_editable(False)
                txt.get_buffer().set_text(err_msg)
                txtw.add(txt)
                
                dlg.vbox.pack_start(msg, expand=False, fill=True)
                dlg.vbox.pack_start(txtw, expand=True, fill=True)
                dlg.show_all()
                dlg.run()


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
        edit_fragment(text, self.inserter)

    def inserter(self, syntax, text, props):
    	line_number = props['lines']

        stx_backend, stx = syntax

        # Get SVG highlighted output as character string
        if stx_backend == 'highlight':
	    # For highlight 2.x
            #cmd = ["highlight", "--syntax", stx, "--svg"]
	    # For highlight 3.x
            cmd = ["highlight", "--syntax",
                   hl_lang (stx), # Fix for hl 3.9
                   "-O", "svg"]
            if line_number:
                cmd.append("--line-number")
            p = Popen(cmd,
                      stdin=PIPE, stdout=PIPE)
            out = p.communicate(text)[0]
        else:
            out = highlight(text, stx(), SvgFormatter())

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
        if stx_backend == 'highlight':
            self.apply_style_highlight(group)
        else:
            self.apply_style_pygments(group)

        # Set the attributes for modification
        group.attrib['{%s}text' % INKSYNTAX_NS] = text.encode('string-escape')

        # Add the SVG group to the document
        svg = self.document.getroot()
        self.current_layer.append(group)

	# Try to apply properties
	if 'font' in props:
	    fd = pango.FontDescription(props['font'])
	    group.set('style', formatStyle({'font-size': '%fpt' % (fd.get_size()/pango.SCALE),
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
    edit_fragment('hello world\n', None)
  # Called as a plugin
  else:
    effect = InkSyntaxEffect()
    effect.affect()
