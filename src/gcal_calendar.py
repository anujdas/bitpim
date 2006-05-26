### BITPIM
###
### Copyright (C) 2006 Joe Pham <djpham@bitpim.org>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id:  $

"Deals with Google Calendar (gCalendar) import stuff"

# system modules
import copy
import datetime
import urllib2

# site modules
import wx

# local modules
import bpcalendar
import bptime
import common_calendar
import database
import ical_calendar as ical
import vcal_calendar as vcal

module_debug=False

#-------------------------------------------------------------------------------
URLDictKey='URLs'
URLDictName='gCalURL'
class URLDataObject(database.basedataobject):
    # object to store a list of URLs & names in the DB
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    _knownlistproperties.update( { 'urls': [ 'url', 'name'] })
    def __init__(self, data=None):
        if data:
            self.update(data)
urlobjectfactory=database.dataobjectfactory(URLDataObject)

#-------------------------------------------------------------------------------
class gCalendarServer(vcal.vCalendarFile):

    def _open(self, name):
        return urllib2.urlopen(name)

#-------------------------------------------------------------------------------
parentclass=ical.iCalendarImportData
class gCalendarImportData(parentclass):
    
    def read(self, file_name=None, update_dlg=None):
        try:
            if file_name is not None:
                self._file_name=file_name
            if self._file_name is None:
                # no file name specified
                return
            v=gCalendarServer(self._file_name)
            v.read()
            self._convert(v.data, self._data)
        except urllib2.URLError:
            raise IOError

#-------------------------------------------------------------------------------
class gCalImportDialog(ical.iCalImportCalDialog):
    _filetype_label='Google Calendar iCal URL:'
    _data_type='Google Calendar'
    def __init__(self, parent, id, title):
        self._db=parent.GetActiveDatabase()
        self._oc=gCalendarImportData()
        common_calendar.PreviewDialog.__init__(self, parent, id, title,
                               self._column_labels,
                               self._oc.get_display_data(),
                               config_name='import/calendar/vcaldialog')

    def OnBrowseFolder(self, _):
        dlg=SelectURLDialog(self, 'Select a Google Calendar iCal URL', self._db)
        if dlg.ShowModal()==wx.ID_OK:
            self.folderctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

#-------------------------------------------------------------------------------
class SelectURLDialog(wx.Dialog):
    def __init__(self, parent, message, database):
        super(SelectURLDialog, self).__init__(parent, -1, 'URL Selection')
        self._db=database
        self._data=[]
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, message), 0, wx.EXPAND|wx.ALL, 5)
        self._choices=wx.ListBox(self, -1,
                                 style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        wx.EVT_LISTBOX_DCLICK(self, self._choices.GetId(), self.OnOK)
        vbs.Add(self._choices, 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.Button(self, wx.ID_OK, 'OK'), 0, wx.EXPAND|wx.ALL, 5)
        hbs.Add(wx.Button(self, wx.ID_CANCEL, 'Cancel'), 0, wx.EXPAND|wx.ALL, 5)
        _btn=wx.Button(self, -1, 'New')
        wx.EVT_BUTTON(self, _btn.GetId(), self.OnNew)
        hbs.Add(_btn, 0, wx.EXPAND|wx.ALL, 5)
        _btn=wx.Button(self, -1, 'Delete')
        wx.EVT_BUTTON(self, _btn.GetId(), self.OnDel)
        hbs.Add(_btn, 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)

        self._get_from_fs()
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def _get_from_fs(self):
        # retrieve data from the DB
        _db_data=self._db.getmajordictvalues(URLDictName, urlobjectfactory)
        self.set(_db_data.get(URLDictKey, {}).get('urls', []))
    def _save_to_fs(self, data):
        _dict={ URLDictKey: { 'urls': data } }
        database.ensurerecordtype(_dict, urlobjectfactory)
        self._db.savemajordict(URLDictName, _dict)
    def set(self, data):
        self._data=data
        self._choices.Clear()
        for _item in self._data:
            self._choices.Append(_item['name'], _item['url'])
    def OnDel(self, _):
        _idx=self._choices.GetSelection()
        if _idx==wx.NOT_FOUND:
            return
        self._choices.Delete(_idx)
        del self._data[_idx]
        self._save_to_fs(self._data)
    def OnNew(self, _):
        _dlg=NewURLDialog(self)
        if _dlg.ShowModal()==wx.ID_OK:
            _name, _url=_dlg.get()
            self._choices.Append(_name, _url)
            self._data.append({ 'name': _name,
                                'url': _url })
            self._save_to_fs(self._data)
        _dlg.Destroy()
    def OnOK(self, evt):
        self.EndModal(wx.ID_OK)
    def GetPath(self):
        _idx=self._choices.GetSelection()
        if _idx==wx.NOT_FOUND:
            return ''
        return self._choices.GetClientData(_idx)

#-------------------------------------------------------------------------------
class NewURLDialog(wx.Dialog):
    def __init__(self, parent):
        super(NewURLDialog, self).__init__(parent, -1, 'New URL Entry')
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, 'URL:'), 0, wx.EXPAND|wx.ALL, 5)
        self._url=wx.TextCtrl(self, -1, '')
        vbs.Add(self._url, 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticText(self, -1, 'Name:'), 0, wx.EXPAND|wx.ALL, 5)
        self._name=wx.TextCtrl(self, -1, '')
        vbs.Add(self._name, 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(self.CreateStdDialogButtonSizer(wx.OK|wx.CANCEL),
                0, wx.EXPAND|wx.ALL, 5)
        
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def get(self):
        return self._name.GetValue(), self._url.GetValue()