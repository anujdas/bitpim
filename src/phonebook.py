### BITPIM
###
### Copyright (C) 2003 Roger Binns <rogerb@rogerbinns.com>
###
### This software is under the Artistic license.
### Please see the accompanying LICENSE file
###
### $Id$

"""A widget for displaying/editting the phone information

The format for a phonebook entry is standardised.  It is a
dict with the following fields.  Each field is a list, most
important first, with each item in the list being a dict.

names:

   - title      ??Job title or salutation??
   - first
   - middle
   - last
   - full       You should specify the fullname or the 4 above
   - nickname   

categories:

  - category    User defined category name

emails:

  - email       Email address
  - type        (optional) 'home' or 'business'

urls:

  - url         URL
  - type        (optional) 'home' or 'business'

ringtones:

  - ringtone    Name of a ringtone
  - use         'call', 'message'

addresses:

  - type        'home' or 'business'
  - company     (only for type of 'business')
  - street      Street part of address
  - street2     Second line of street address
  - city
  - state
  - postalcode
  - country     Can also be the region

wallpapers:

  - wallpaper   Name of wallpaper
  - index       Index number of the wallpaper (fill out one of these two, not both)
  - use         see ringtones.use

flags:

  - secret     Boolean if record is private/secret

memos:

  - memo       Note

numbers:

  - number     Phone number as ascii string
  - type       'home', 'office', 'cell', 'fax', 'pager', 'data', 'none'  (if you have home2 etc, list
               them without the digits.  The second 'home' is implicitly home2 etc)
  - speeddial  (optional) Speed dial number

serials:

  - sourcetype        identifies source driver in bitpim (eg "lgvx4400", "windowsaddressbook")
  - sourceuniqueid    identifier for where the serial came from (eg ESN of phone, wab host/username)
  - *                 other names of use to sourcetype
"""

# Standard imports
import os
import cStringIO
import webbrowser

# GUI
import wx
import wx.grid
import wx.html
import wx.stc

# My imports
import common
import xyaptu
import guihelper

###
###  Enhanced HTML Widget
###

class HTMLWindow(wx.html.HtmlWindow):
    """BitPim customised HTML Window

       - You can press Ctrl-Alt-S to get a source view
       - Clicking on a link opens a window in your browser
       - Shift-clicking on a link copies it to the clipboard
    """
    def __init__(self, parent, id):
        wx.html.HtmlWindow.__init__(self, parent, id)
        wx.EVT_KEY_UP(self, self.OnKeyUp)
        self.thetext=""

    def OnLinkClicked(self, event):
        # see ClickableHtmlWindow in wxPython source for inspiration
        # :::TODO::: redirect bitpim images and audio to correct
        # player
        if event.GetEvent().ShiftDown():
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(event.GetHref())
            wx.TheClipboard.Close()
        else:
            webbrowser.open(event.GetHref())

    def SetPage(self, text):
        self.thetext=text
        wx.html.HtmlWindow.SetPage(self,text)

    def OnKeyUp(self, evt):
        keycode=evt.GetKeyCode()        
        if keycode==ord('S') and evt.ControlDown() and evt.AltDown():
            print "got ctrl alt s"
            vs=ViewSourceFrame(None, self.thetext)
            vs.Show(True)
            evt.Skip()

###
###  View Source Window
###            

class ViewSourceFrame(wx.Frame):
    def __init__(self, parent, text, id=-1):
        wx.Frame.__init__(self, parent, id, "HTML Source")
        stc=wx.stc.StyledTextCtrl(self, -1)
        stc.SetLexer(wx.stc.STC_LEX_HTML)
        stc.SetText(text)
        stc.Colourise(0,-1)


###
### Phonebook entry display (Derived from HTML)
###

class PhoneEntryDetailsView(HTMLWindow):

    def __init__(self, parent, id, stylesfile, layoutfile):
        HTMLWindow.__init__(self, parent, id)
        self.stylesfile=guihelper.getresourcefile(stylesfile)
        self.stylesfilestat=None
        self.pblayoutfile=guihelper.getresourcefile(layoutfile)
        self.pblayoutfilestat=None
        self.xcp=None
        self.xcpstyles=None

    def ShowEntry(self, entry):
        if self.xcp is None or self.pblayoutfilestat!=os.stat(self.pblayoutfile):
            f=open(self.pblayoutfile, "rt")
            template=f.read()
            f.close()
            self.pblayoutfilestat=os.stat(self.pblayoutfile)
            self.xcp=xyaptu.xcopier(None)
            self.xcp.setupxcopy(template)
        if self.xcpstyles is None or self.stylesfilestat!=os.stat(self.stylesfile):
            self.xcpstyles={}
            execfile(self.stylesfile,  self.xcpstyles, self.xcpstyles)
            self.stylesfilestat=os.stat(self.stylesfile)
        self.xcpstyles['entry']=entry
        self.SetPage(self.xcp.xcopywithdns(self.xcpstyles))

###
### Functions used to extra data from a record
###

def getdata(column, entry, default=None):
    if column=="Name":
        names=entry.get("names", [{}])
        name=names[0]
        x=formatname(name)
        if len(x)==0:
            return default
        return x

    if column=="Home":
        for number in entry.get("numbers", []):
            if number.get("type", "")=="home":
                return number['number']
        return default

    if column=="Email":
        for email in entry.get("emails", []):
            return email['email']
        return default

    assert False, "Unknown column type "+column
    return default


def formatname(name):
    # Returns a string of the name in name.
    # Since there can be many fields, we try to make sense of them
    res=""
    res+=name.get("full", "")
    f=name.get("first", "")
    m=name.get("middle", "")
    l=name.get("last", "")
    if len(f) or len(m) or len(l):
        if len(res):
            res+=" | "
        # severe abuse of booleans
        res+=f+(" "*bool(len(f)))
        res+=m+(" "*bool(len(m)))
        res+=l+(" "*bool(len(l)))
    if name.has_key("nickname"):
        res+=" ("+name["nickname"]+")"
    return res


###
### We use a table for speed
###

class PhoneDataTable(wx.grid.PyGridTableBase):

    def __init__(self, widget):
        self.main=widget
        self.rowkeys=self.main._data.keys()
        self.rowkeys.sort()
        wx.grid.PyGridTableBase.__init__(self)
        self.oddattr=wx.grid.GridCellAttr()
        self.oddattr.SetBackgroundColour("OLDLACE")
        self.evenattr=wx.grid.GridCellAttr()
        self.evenattr.SetBackgroundColour("ALICE BLUE")
        self.columns=['Name', 'Home', 'Email']

    def GetColLabelValue(self, col):
        return self.columns[col]

    def OnDataUpdated(self):
        newkeys=self.main._data.keys()
        newkeys.sort()
        oldrows=self.rowkeys
        print oldrows
        self.rowkeys=newkeys
        lo=len(oldrows)
        ln=len(self.rowkeys)
        if ln>lo:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, ln-lo)
        elif lo>ln:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, lo-ln)
        else:
            msg=None
        if msg is not None:
            self.GetView().ProcessTableMessage(msg)
        msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().AutoSizeColumns()


    def IsEmptyCell(self, row, col):
        return False

    def GetNumberRows(self):
        return len(self.rowkeys)

    def GetNumberCols(self):
        return len(self.columns)

    def GetValue(self, row, col):
        try:
            entry=self.main._data[self.rowkeys[row]]
        except:
            print "bad row", row
            return "<error>"

        return getdata(self.columns[col], entry, "")

    def GetAttr(self, row, col, _):
        r=[self.evenattr, self.oddattr][row%2]
        r.IncRef()
        return r

class PhoneWidget(wx.SplitterWindow):
    """Main phone editing/displaying widget"""
    CURRENTFILEVERSION=2
    def __init__(self, mainwindow, parent, id=-1):
        wx.SplitterWindow.__init__(self, parent, id, style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        self.mainwindow=mainwindow
        self._data={}
        self.groupdict={}
        self.modified=False
        self.table=wx.grid.Grid(self, -1)
        self.table.EnableGridLines(False)
        self.dt=PhoneDataTable(self)
        # 1 is GridSelectRows.  The symbol pathologically refused to be defined
        self.table.SetTable(self.dt, False, 1)
        self.table.SetRowLabelSize(0)
        self.table.EnableEditing(False)
        self.table.EnableDragRowSize(False)
        self.table.SetSelectionMode(1)
        self.table.SetMargins(1,0)
        self.preview=PhoneEntryDetailsView(self, -1, "styles.xy", "pblayout.xy")
        self.preview.ShowEntry({})
        self.SplitVertically(self.table, self.preview, -300)
        wx.EVT_IDLE(self, self.OnIdle)
        wx.grid.EVT_GRID_SELECT_CELL(self, self.OnCellSelect)


    def OnIdle(self, _):
        "We save out changed data"
        if self.modified:
            print "Saving phonebook"
            self.modified=False
            self.populatefs(self.getdata({}))

    def OnCellSelect(self, event):
        row=event.GetRow()
        self.SetPreview(self._data[self.dt.rowkeys[row]]) # bad breaking of abstraction referencing dt!

    def SetPreview(self, entry):
        self.preview.ShowEntry(entry)

    def getdata(self, dict):
        dict['phonebook']=self._data.copy()
        dict['groups']=self.groupdict.copy()
        return dict


    def versionupgrade(self, dict, version):
        """Upgrade old data format read from disk

        @param dict:  The dict that was read in
        @param version: version number of the data on disk
        """

        # version 0 to 1 upgrade
        if version==0:
            version=1  # they are the same

        # 1 to 2 etc
        if version==1:
            wx.MessageBox("BitPim can't upgrade your old phone data stored on disk, and has discarded it.  Please re-read your phonebook from the phone.  If you downgrade, please delete the phonebook directory in the BitPim data directory first", "Phonebook file format not supported", wx.OK|wx.ICON_EXCLAMATION)
            version=2
            dict['phonebook']={}
            
    def clear(self):
        self._data={}
        self.dt.OnDataUpdated()


    def populatefs(self, dict):
        self.thedir=self.mainwindow.phonebookpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for phonebook '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all!
            os.remove(os.path.join(self.thedir, f))
        d={}
        d['phonebook']=dict['phonebook']
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, self.CURRENTFILEVERSION)
        return dict

    def getfromfs(self, dict):
        self.thedir=self.mainwindow.phonebookpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for phonebook '"+self.thedir+"'")
        if os.path.exists(os.path.join(self.thedir, "index.idx")):
            d={'result': {}}
            common.readversionedindexfile(os.path.join(self.thedir, "index.idx"), d, self.versionupgrade, self.CURRENTFILEVERSION)
            dict.update(d['result'])
        else:
            dict['phonebook']={}
        return dict

    def populate(self, dict):
        self.clear()
        pb=dict['phonebook']
        k=pb.keys()
        k.sort()
        self.clear()
        self._data=pb.copy()
        self.dt.OnDataUpdated()

    def populatefs(self, dict):
        self.thedir=self.mainwindow.phonebookpath
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for phonebook '"+self.thedir+"'")
        for f in os.listdir(self.thedir):
            # delete them all!
            os.remove(os.path.join(self.thedir, f))
        d={}
        d['phonebook']=dict['phonebook']
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, self.CURRENTFILEVERSION)
        return dict
    
    def converttophone(self, data):
        self.mainwindow.phoneprofile.convertphonebooktophone(self, data)


    class ConversionFailed(Exception):
        pass

    def _getentries(self, list, min, max, name):
        candidates=[]
        for i in list:
            # ::TODO:: possibly ensure that a key appears in each i
            candidates.append(i)
        if len(candidates)<min:
            # ::TODO:: log this
            raise ConversionFailed("Too few %s.  Need at least %d but there were only %d" % (name,min,len(candidates)))
        if len(candidates)>max:
            # ::TODO:: mention this to user
            candidates=candidates[:max]
        return candidates

    def _getfield(self,list,name):
        res=[]
        for i in list:
            res.append(i[name])
        return res

    def _truncatefields(self, list, truncateat):
        if truncateat is None:
            return list
        res=[]
        for i in list:
            if len(i)>truncateat:
                # ::TODO:: log truncation
                res.append(i[:truncateat])
            else:
                res.append(i)
        return res

    def _findfirst(self, candidates, required, key, default):
        """Find first match in candidates that meets required and return value of key

        @param candidates: list of dictionaries to search through
        @param required: a dict of what key/value pairs must exist in an entry
        @param key: for a matching entry, which key's value to return
        @param default: what value to return if there is no match
        """
        for dict in candidates:
            ok=True
            for k in required:
                if dict[k]!=required[k]:
                   ok=False
                   break # really want break 2
            if not ok:
                continue
            return dict[key]
        return default

    def getfullname(self, names, min, max, truncateat=None):
        "Return at least min and at most max fullnames from the names list"
        # ::TODO:: possibly deal with some names having the fields, and some having full
        return self._truncatefields(self._getfield(self._getentries(names, min, max, "names"), "full"), truncateat)

    def getcategory(self, categories, min, max, truncateat=None):
        "Return at least min and at most max categories from the categories list"
        return self._truncatefields(self._getfield(self._getentries(categories, min, max, "categories"), "category"), truncateat)

    def getemails(self, emails, min, max, truncateat=None):
        "Return at least min and at most max emails from the emails list"
        return self._truncatefields(self._getfield(self._getentries(emails, min, max, "emails"), "email"), truncateat)

    def geturls(self, urls, min, max, truncateat=None):
        "Return at least min and at most max urls from the urls list"
        return self._truncatefields(self._getfield(self._getentries(urls, min, max, "urls"), "url"), truncateat)
        

    def getmemos(self, memos, min, max, truncateat=None):
        "Return at least min and at most max memos from the memos list"
        return self._truncatefields(self._getfield(self._getentries(memos, min, max, "memos"), "memo"), truncateat)

    def getnumbers(self, numbers, min, max):
        "Return at least min and at most max numbers from the numbers list"
        return self._getentries(numbers, min, max, "numbers")

    def getserial(self, serials, sourcetype, id, key, default):
        "Gets a serial if it exists"
        return self._findfirst(serials, {'sourcetype': sourcetype, 'sourceuniqueid': id}, key, default)
        
    def getringtone(self, ringtones, use, default):
        "Gets a ringtone of type use"
        return self._findfirst(ringtones, {'use': use}, 'ringtone', default)

    def getwallpaper(self, wallpapers, use, default):
        "Gets a wallpaper of type use"
        return self._findfirst(wallpapers, {'use': use}, 'wallpaper', default)

    def getwallpaperindex(self, wallpapers, use, default):
        "Gets a wallpaper index of type use"
        return self._findfirst(wallpapers, {'use': use}, 'index', default)

    def getflag(self, flags, name, default):
        "Gets value of flag named name"
        for i in flags:
            if i.has_key(name):
                return i[name]
        return default

    def importdata(self, importdata):
        dlg=ImportDialog(self, self._data, importdata)
        dlg.ShowModal()
        print dlg.resultdata


class ImportDataTable(wx.grid.PyGridTableBase):
    ADDED=0
    UNALTERED=1
    CHANGED=2
    DELETED=3
    
    def __init__(self, widget):
        self.main=widget
        self.rowkeys=[]
        wx.grid.PyGridTableBase.__init__(self)
        self.columns=['Confidence', 'Name', 'Home', 'Email']
        self.addedattr=wx.grid.GridCellAttr()
        self.addedattr.SetBackgroundColour("HONEYDEW")
        self.unalteredattr=wx.grid.GridCellAttr()
        self.unalteredattr.SetBackgroundColour("WHITE")
        self.changedattr=wx.grid.GridCellAttr()
        self.changedattr.SetBackgroundColour("LEMON CHIFFON")
        self.deletedattr=wx.grid.GridCellAttr()
        self.deletedattr.SetBackgroundColour("ROSYBROWN1")

    def GetColLabelValue(self, col):
        return self.columns[col]

    def IsEmptyCell(self, row, col):
        return False

    def GetNumberCols(self):
        return len(self.columns)

    def GetNumberRows(self):
        return len(self.rowkeys)

    def GetAttr(self, row, col, _):
        try:
            # it likes to ask for non-existent cells
            row=self.main.rowdata[self.rowkeys[row]]
        except:
            return None
        v=None
        if row[3] is None:
            v=self.DELETED
        if v is None and (row[1] is not None and row[2] is not None):
            v=self.CHANGED
        if v is None and (row[1] is not None and row[2] is None):
            v=self.ADDED
        if v is None:
            v=self.UNALTERED
        r=[self.addedattr, self.unalteredattr, self.changedattr, self.deletedattr][v]
        r.IncRef()
        return r
                
    def GetValue(self, row, col):
        try:
            row=self.main.rowdata[self.rowkeys[row]]
        except:
            print "bad row", row
            return "<error>"
        
        if self.columns[col]=='Confidence':
            return row[0]

        for i,ptr in (3,self.main.resultdata), (1,self.main.importdata), (2, self.main.existingdata):
            if row[i] is not None:
                res=getdata(self.columns[col], ptr[row[i]], None)
                if res is not None:
                    return res
        return ""
            
    def OnDataUpdated(self):
        newkeys=self.main.rowdata.keys()
        newkeys.sort()
        oldrows=self.rowkeys
        self.rowkeys=newkeys
        lo=len(oldrows)
        ln=len(self.rowkeys)
        if ln>lo:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, ln-lo)
        elif lo>ln:
            msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, 0, lo-ln)
        else:
            msg=None
        if msg is not None:
            self.GetView().ProcessTableMessage(msg)
        msg=wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.GetView().AutoSizeColumns()
    

class ImportDialog(wx.Dialog):
    "The dialog for mixing new (imported) data with existing data"

    def __init__(self, parent, existingdata, importdata):
        wx.Dialog.__init__(self, parent, id=-1, title="Import Phonebook data", style=wx.CAPTION|
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.NO_FULL_REPAINT_ON_RESIZE,
                           size=(740,680))

        # the data already in the phonebook
        self.existingdata=existingdata
        # the data we are importing
        self.importdata=importdata
        # the resulting data
        self.resultdata={}
        # each row to display showing what happened, with ids pointing into above data
        self.rowdata={}

        vbs=wx.BoxSizer(wx.VERTICAL)
        
        bg=self.GetBackgroundColour()
        w=wx.html.HtmlWindow(self, -1, size=wx.Size(600,50), style=wx.html.HW_SCROLLBAR_NEVER)
        w.SetPage('<html><body BGCOLOR="#%02X%02X%02X">Your data is being imported and BitPim is showing what will happen below so you can confirm its actions.</body></html>' % (bg.Red(), bg.Green(), bg.Blue()))
        vbs.Add(w, 0, wx.EXPAND|wx.ALL, 5)

        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Show entries"), 0, wx.EXPAND|wx.ALL,3)

        self.cbunaltered=wx.CheckBox(self, wx.NewId(), "Unaltered")
        self.cbadded=wx.CheckBox(self, wx.NewId(), "Added")
        self.cbchanged=wx.CheckBox(self, wx.NewId(), "Changed")
        self.cbdeleted=wx.CheckBox(self, wx.NewId(), "Deleted")

        for i in self.cbunaltered, self.cbadded, self.cbchanged, self.cbdeleted:
            i.SetValue(True)
            hbs.Add(i, 0, wx.ALIGN_CENTRE|wx.LEFT|wx.RIGHT, 7)

        hbs.Add(wx.StaticText(self, -1, " "), 0, wx.EXPAND|wx.LEFT, 10)

        self.details=wx.CheckBox(self, wx.NewId(), "Details")
        self.details.SetValue(True)
        hbs.Add(self.details, 0, wx.EXPAND|wx.LEFT, 5)

        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)

        splitterstyle=wx.SP_3DBORDER|wx.SP_LIVE_UPDATE
        self.splitterstyle=splitterstyle

        hsplit=wx.SplitterWindow(self,-1, style=splitterstyle)
        hsplit.SetMinimumPaneSize(20)

        self.resultpreview=PhoneEntryDetailsView(hsplit, -1, "styles.xy", "pblayout.xy")

        vsplit=wx.SplitterWindow(hsplit, -1, style=splitterstyle)
        vsplit.SetMinimumPaneSize(20)

        self.grid=wx.grid.Grid(vsplit, -1)
        self.grid.EnableGridLines(False)
        self.table=ImportDataTable(self)
        self.grid.SetTable(self.table, False, 1)
        self.grid.SetRowLabelSize(0)
        self.grid.EnableEditing(False)
        self.grid.SetMargins(1,0)

        hhsplit=wx.SplitterWindow(vsplit, -1, style=splitterstyle)
        hhsplit.SetMinimumPaneSize(20)

        self.origpreview=PhoneEntryDetailsView(hhsplit, -1, "styles.xy", "pblayout.xy")
        self.importpreview=PhoneEntryDetailsView(hhsplit, -1, "styles.xy", "pblayout.xy")

        self.origpreview.ShowEntry( { 'names': [ {'name': 'origpreview'} ] } )
        self.importpreview.ShowEntry( { 'names': [ {'name': 'importpreview'} ] } )

        hhsplit.SplitVertically(self.origpreview, self.importpreview, 0)
        vsplit.SplitHorizontally(self.grid, hhsplit, -200)
        hsplit.SplitVertically(vsplit, self.resultpreview, -250)

        # save these for OnDetailChanged
        self.vsplit=vsplit
        self.hhsplit=hhsplit
        self.vsplitpos=-200
        self.hhsplitpos=0

        vbs.Add(hsplit, 1, wx.EXPAND|wx.ALL,5)
        vbs.Add(wx.StaticLine(self, -1, style=wx.LI_HORIZONTAL), 0, wx.EXPAND|wx.ALL, 5)

        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP), 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.SetSizer(vbs)
        self.SetAutoLayout(True)

        wx.EVT_CHECKBOX(self, self.details.GetId(), self.OnDetailChanged)

        wx.CallAfter(self.DoMerge)

    def DoMerge(self):
        count=0
        row={}
        results={}
        for i in self.importdata:
            results[count]=self.importdata[i]
            row[count]=(100, i, None, count)
            count+=1
        for i in self.existingdata:
            results[count]=self.existingdata[i]
            row[count]=(100, None, i, count)
            count+=1
        self.rowdata=row
        self.resultdata=results
        self.table.OnDataUpdated()

    def OnDetailChanged(self, _):
        "Show or hide the exiting/imported data previews"
        # We destroy and recreate the bottom splitter with the two previews in
        # them.  If that isn't done then the window doesn't draw properly amongst
        # other issues
        if self.details.GetValue():
            hhsplit=wx.SplitterWindow(self.vsplit, -1, style=self.splitterstyle)
            hhsplit.SetMinimumPaneSize(20)
            self.origpreview=PhoneEntryDetailsView(hhsplit, -1, "styles.xy", "pblayout.xy")
            self.importpreview=PhoneEntryDetailsView(hhsplit, -1, "styles.xy", "pblayout.xy")
            hhsplit.SplitVertically(self.origpreview, self.importpreview, self.hhsplitpos)
            self.hhsplit=hhsplit
            self.vsplit.SplitHorizontally(self.grid, self.hhsplit, self.vsplitpos)
        else:
            self.vsplitpos=self.vsplit.GetSashPosition()
            self.hhsplitpos=self.hhsplit.GetSashPosition()
            self.vsplit.Unsplit()
            self.hhsplit.Destroy()
                        

