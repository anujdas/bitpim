### BITPIM
###
### Copyright (C) 2004 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"The magic developer console"

import wx
import wx.html
import wx.py

class DeveloperPanel(wx.Panel):

    def __init__(self, parent, locals=None):
        wx.Panel.__init__(self, parent)

        split=wx.SplitterWindow(self, style = wx.SP_3D| wx.SP_LIVE_UPDATE)

        if locals is None:
            self.locals={}
        else:
            self.locals=locals.copy()
        self.locals.update(self.getlocals())
        
        cmd=wx.py.shell.Shell(split, locals=self.locals)
        
        self.htmlw=wx.html.HtmlWindow(split)

        split.SetMinimumPaneSize(20)
        split.SplitHorizontally(cmd, self.htmlw)

        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(split, 1, wx.EXPAND)
        self.SetSizer(vbs)

    def getlocals(self):
        return {
            'sql': self.sql,
            'wx': wx,
            'app': wx.GetApp(),
            'tables': self.tables,
            'rows': self.rows,
            }

    def sql(self, cmd, bindings=()):
        "Executes sql statement and prints result"
        for row in self.locals['db'].sql(cmd,bindings):
            print row

    def tables(self):
        "Gets list of all tables"
        cursor=self.locals['db'].cursor
        html="<h1>All tables</h1>"
        html+="<table>"
        for name,s in cursor.execute("select name,sql from sqlite_master where type='table' order by name"):
            html+="<tr><td valign=top>&nbsp;<br><b>%s</b><td valign=top><pre>%s</pre></tr>" % (name, htmlify(s))
        html+="</table>"
        self.htmlw.SetPage(html)

    def rows(self, table):
        "Shows rows from table"
        cursor=self.locals['db'].cursor
        html="<h1>All rows in %s</h1>" % (htmlify(table),)
        cursor.execute("select * from "+table)
        try:
            cursor.getdescription()
        except:
            html+="<p>No data"
            self.htmlw.SetPage(html)
            return

        html+="<table border=1 cellpadding=3>"
        html+="<tr>"
        for col in cursor.getdescription():
            html+="<th>%s<br>%s" % (htmlify(col[0]), `col[1]`)
        html+="</tr>"
        for vals in cursor:
            html+="<tr>"
            for v in vals:
                html+="<td>%s" % (htmlify(str(v)),)
            html+="</tr>"
        html+="</table>"
        self.htmlw.SetPage(html)

def htmlify(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
