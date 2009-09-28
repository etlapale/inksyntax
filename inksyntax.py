#! /usr/bin/env python
# -*- coding: utf-8; -*-

'''
A source code syntax highlighter plugin for Inkscape.

:author: Xīcò <xico@freeshell.org>
'''

__version__ = '0.1'

import os
import platform
import sys
from subprocess import PIPE, Popen
import traceback

# Update PYTHONPATH for Inkscape plugins
sys.path.append('/usr/share/inkscape/extensions')
sys.path.append(r'c:/Program Files/Inkscape/share/extensions')
sys.path.append(os.path.dirname(__file__))

import inkex
from simplestyle import *
from StringIO import StringIO

USE_GTK = False
try:
    import pygtk
    pygtk.require('2.0')
    import gtk
    USE_GTK = True
except ImportError:
    pass

USE_TK = False
try:
    import Tkinter as Tk
    USE_TK = True
except ImportError:
    pass

USE_WINDOWS = (platform.system() == "Windows")

INKSYNTAX_NS = u"http://www.lyua.org/inkscape/extensions/inksyntax/"
SVG_NS = u"http://www.w3.org/2000/svg"
XLINK_NS = u"http://www.w3.org/1999/xlink"
XML_NS = u"http://www.w3.org/XML/1998/namespace"

ID_PREFIX = "inksyntax-"

NSS = {
    u'textext': INKSYNTAX_NS,
    u'svg': SVG_NS,
    u'xlink': XLINK_NS,
}

#---------------------------------------------------------------
# GUI from TexText by Pauli Virtanen <pav@iki.fi> (BSD licensed)
#---------------------------------------------------------------

if USE_GTK:
    class AskText(object):
        """GUI for editing TexText objects"""
        def __init__(self, text):
            self.text = text
            self.callback = None
    
        def ask(self, callback):
            self.callback = callback
            
            window = gtk.Window(gtk.WINDOW_TOPLEVEL)
            window.set_title("InkSyntax")
            window.set_default_size(600, 400)

            self.syntax = gtk.Entry()
    
            label3 = gtk.Label(u"Text:")
            
            self._text = gtk.TextView()
            self._text.get_buffer().set_text(self.text)

            sw = gtk.ScrolledWindow()
            sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
            sw.set_shadow_type(gtk.SHADOW_IN)
            sw.add(self._text)
            
            self._ok = gtk.Button(stock=gtk.STOCK_OK)
            self._cancel = gtk.Button(stock=gtk.STOCK_CANCEL)

            self.line_number = gtk.CheckButton('Line numbers')
    
            # layout
            table = gtk.Table(3, 2, False)
            table.attach(gtk.Label('Syntax:'), 0,1,0,1,xoptions=0,yoptions=gtk.FILL)
            table.attach(self.syntax,          1,2,0,1,yoptions=gtk.FILL)
            table.attach(self.line_number,     0,2,1,2,xoptions=0,yoptions=gtk.FILL)
            table.attach(label3,               0,1,2,3,xoptions=0,yoptions=gtk.FILL)
            table.attach(sw,                   1,2,2,3)
    
            vbox = gtk.VBox(False, 5)
            vbox.pack_start(table)
            
            hbox = gtk.HButtonBox()
            hbox.add(self._ok)
            hbox.add(self._cancel)
            hbox.set_layout(gtk.BUTTONBOX_SPREAD)
            
            vbox.pack_end(hbox, expand=False, fill=False)
    
            window.add(vbox)
    
            # signals
            window.connect("delete-event", self.cb_delete_event)
            window.connect("key-press-event", self.cb_key_press)
            self._ok.connect("clicked", self.cb_ok)
            self._cancel.connect("clicked", self.cb_cancel)
    
            # show
            window.show_all()
            self._text.grab_focus()

            # run
            self._window = window
            gtk.main()
    
            return self.syntax.get_text(), self.text, \
                    self.line_number.get_active()
    
        def cb_delete_event(self, widget, event, data=None):
            gtk.main_quit()
            return False

        def cb_key_press(self, widget, event, data=None):
            # ctrl+return clicks the ok button
            if gtk.gdk.keyval_name(event.keyval) == 'Return' \
                   and gtk.gdk.CONTROL_MASK & event.state:
                self._ok.clicked()
                return True
            return False
        
        def cb_cancel(self, widget, data=None):
            raise SystemExit(1)
        
        def cb_ok(self, widget, data=None):
            buf = self._text.get_buffer()
            self.text = buf.get_text(buf.get_start_iter(),
                                     buf.get_end_iter())
            
            try:
                self.callback(self.syntax.get_text(), self.text,
                             self.line_number.get_active())
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
                return False
            
            gtk.main_quit()
            return False
else:
    raise RuntimeError("PyGTK is not installed!")

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
        asker = AskText(text)
        asker.ask(lambda s, t, l: self.inserter(s, t, l))

    def inserter(self, syntax, text, line_number=False):
        # Get SVG highlighted output
        cmd = ["highlight", "--syntax", syntax, "--svg"]
        if line_number:
            cmd.append("--line-number")
        p = Popen(cmd,
                  stdin=PIPE, stdout=PIPE)
        out = p.communicate(text)[0]
        tree = inkex.etree.parse(StringIO(out))
        group = tree.getroot()[1]

        # Remove the background rectangle
        del group[0]

        # Apply a CSS style
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

        # Set the attributes for modification
        group.attrib['{%s}text' % INKSYNTAX_NS] = text.encode('string-escape')

        # Add the SVG group to the document
        svg = self.document.getroot()
        self.current_layer.append(group)

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

if __name__ == '__main__':
    effect = InkSyntaxEffect()
    effect.affect()
