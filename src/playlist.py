### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@netzero.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$
"""
Code to handle Playlist items
The format of the Playlist items is standardized.  It is a list of dict whic has
the following standard fields:

name: string=the name of the play list
type: string=the type of this play list.  Current supported types are mp3 and wma.
songs: [ 'song name', ... ]

"""

import wx
import wx.gizmos as gizmos

import database

# module constants--------------------------------------------------------------
playlist_key='playlist'
masterlist_key='masterlist'
playlists_list='playlists'
mp3_type='mp3'
wma_type='wma'
playlist_type=(mp3_type, wma_type)
## testing data
_test_master_list=('tune 1', 'tune 2', 'tune 3', 'tune 4', 'tune 5', 'tune 6')
_test_playlist=(
    {'name': 'list 1', 'songs': ('tune 1', 'tune 3') },
    {'name': 'list 2', 'songs': ('tune 1', 'tune 2', 'tune 4') })
#-------------------------------------------------------------------------------
class MasterListDataObject(database.basedataobject):
    _knownproperties=[]
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    _knownlistproperties.update({ 'masterlist': ['name'] })
    def __init__(self, data=None):
        if data is None or not isinstance(data, (list, tuple)):
            return
        self.update({'masterlist': [{ 'name': x } for x in data] })
masterlistobjectfactory=database.dataobjectfactory(MasterListDataObject)

#-------------------------------------------------------------------------------
class PlaylistDataObject(database.basedataobject):
    _knownproperties=[]
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    _knownlistproperties.update( { 'playlist': ['name'] })
    def __init__(self, data=None):
        if data is None or not isinstance(data, (list, tuple)):
            return
        self.update({'playlist': [{'name': x} for x in data]})
playlistobjectfactory=database.dataobjectfactory(PlaylistDataObject)

#-------------------------------------------------------------------------------
class PlaylistEntryDataObject(database.basedataobject):
    _knownproperties=['type']
    _knownlistproperties=database.basedataobject._knownlistproperties.copy()
    _knownlistproperties.update({ 'songs': ['name']})
    def __init__(self, data=None):
        if data is None or not isinstance(data, PlaylistEntry):
            return
        self.update(data.get_db_dict())
playlistentryobjectfactory=database.dataobjectfactory(PlaylistEntryDataObject)

#-------------------------------------------------------------------------------
class PlaylistEntry(object):
    def __init__(self):
        self._data={ 'serials': [] }

    def get(self):
        return copy.deepcopy(self._data, {})
    def set(self, d):
        self._data={}
        self._data.update(d)

    def get_db_dict(self):
        return { 'type': self.pl_type,
                 'songs': [{ 'name': x } for x in self.songs] }
    def set_db_dict(self, d):
        # name needs to set separately
        self.pl_type=d.get('type', None)
        self.songs=[x['name'] for x in d.get('songs', [])]

    def _set_or_del(self, key, v, v_list=[]):
        if v is None or v in v_list:
            if self._data.has_key(key):
                del self._data[key]
        else:
            self._data[key]=v

    def _get_name(self):
        return self._data.get('name', '')
    def _set_name(self, v):
        self._set_or_del('name', v, [''])
    name=property(fget=_get_name, fset=_set_name)

    def _get_type(self):
        return self._data.get('type', '')
    def _set_type(self, v):
        self._set_or_del('type', v, [''])
    pl_type=property(fget=_get_type, fset=_set_type)

    def _get_songs(self):
        return self._data.get('songs', [])
    def _set_songs(self, v):
        self._set_or_del('songs', v, [[]])
    songs=property(fget=_get_songs, fset=_set_songs)

#-------------------------------------------------------------------------------
class PlaylistWidget(wx.Panel):
    def __init__(self, mainwindow, parent):
        super(PlaylistWidget, self).__init__(parent, -1)
        self._mw=mainwindow
        self._data=[]
        self._master=[]
        self.ignoredirty=False
        self.dirty=False
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        # horizontal sizer for the main contents
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # the list box
        self._item_list=gizmos.EditableListBox(self, -1, 'Play Lists:',
                                               style=gizmos.EL_ALLOW_NEW|\
                                               gizmos.EL_ALLOW_EDIT|\
                                               gizmos.EL_ALLOW_DELETE)
        self._item_list.GetUpButton().Show(False)
        self._item_list.GetDownButton().Show(False)
        self._item_list_w=self._item_list.GetListCtrl()
        hbs.Add(self._item_list, 1, wx.EXPAND|wx.ALL, border=5)
        hbs.Add(wx.StaticLine(self, -1, style=wx.LI_VERTICAL), 0,
                wx.EXPAND|wx.ALL, 5)
        # the detailed panel
        hbs1=wx.BoxSizer(wx.HORIZONTAL)
        # the playlist
        self._pl_list=gizmos.EditableListBox(self, -1, "Play List Content:",
                                             style=gizmos.EL_ALLOW_DELETE)
        self._pl_list_w=self._pl_list.GetListCtrl()
        hbs1.Add(self._pl_list, 1, wx.EXPAND|wx.ALL, 5)
        _add_btn=wx.Button(self, -1, '<-Add')
        hbs1.Add(_add_btn, 0, wx.ALL, 5)
        self._master_list=gizmos.EditableListBox(self, -1, 'Available Songs:', style=0)
        self._master_list_w=self._master_list.GetListCtrl()
        self._master_list.GetUpButton().Show(False)
        self._master_list.GetDownButton().Show(False)
        hbs1.Add(self._master_list, 1, wx.EXPAND|wx.ALL, 5)
        hbs.Add(hbs1, 3, wx.EXPAND|wx.ALL, 5)
        # the bottom buttons
        hbs1=wx.BoxSizer(wx.HORIZONTAL)
        self._save_btn=wx.Button(self, wx.NewId(), "Save")
        self._revert_btn=wx.Button(self, wx.NewId(), "Revert")
        help_btn=wx.Button(self, wx.ID_HELP, "Help")
        hbs1.Add(self._save_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hbs1.Add(help_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hbs1.Add(self._revert_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        # all done
        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        vbs.Add(hbs1, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)
        # event handlers
        wx.EVT_LIST_ITEM_SELECTED(self._item_list, self._item_list_w.GetId(),
                                  self.OnPlaylistSelected)
        wx.EVT_LIST_BEGIN_LABEL_EDIT(self._item_list, self._item_list_w.GetId(),
                                   self.OnStartLabelChanged)
        wx.EVT_LIST_END_LABEL_EDIT(self._item_list, self._item_list_w.GetId(),
                                   self.OnLabelChanged)
        wx.EVT_BUTTON(self, _add_btn.GetId(), self.OnAdd2Playlist)
        wx.EVT_BUTTON(self, self._save_btn.GetId(), self.OnSave)
        wx.EVT_BUTTON(self, self._revert_btn.GetId(), self.OnRevert)
        wx.EVT_LIST_DELETE_ITEM(self._item_list, self._item_list_w.GetId(),
                                self.OnMakeDirty)
        wx.EVT_LIST_DELETE_ITEM(self._pl_list, self._pl_list_w.GetId(),
                                self.OnMakeDirty)

##        wx.EVT_LISTBOX(self, self._item_list.GetId(), self._OnListBoxItem)
##        wx.EVT_BUTTON(self, self._save_btn.GetId(), self._OnSave)
##        wx.EVT_BUTTON(self, self._revert_btn.GetId(), self._OnRevert)
##        wx.EVT_BUTTON(self, wx.ID_HELP,
##                      lambda _: wx.GetApp().displayhelpid(helpids.ID_TAB_TODO))
        # populate data
        self._populate()
        # turn on dirty flag
        self.setdirty(False)
        # testing data
##        _test_pl=[]
##        for l in _test_playlist:
##            _e=PlaylistEntry()
##            _e.name=l['name']
##            _e.songs=l['songs']
##            _test_pl.append(_e)
##        self.populatefs({ masterlist_key: _test_master_list,
##                          playlist_key: _test_pl })

    def setdirty(self, val):
        if self.ignoredirty:
            return
        self.dirty=val
        self._item_list.Enable(not self.dirty)
        self._save_btn.Enable(self.dirty)
        self._revert_btn.Enable(self.dirty)

    def _clear(self, clear_master=True):
        self._item_list_w.DeleteAllItems()
        self._pl_list_w.DeleteAllItems()
        if clear_master:
            self._master_list_w.DeleteAllItems()

    def _populate_master(self):
        self._master_list.SetStrings(self._master)
    def _populate_pl_list(self):
        self._item_list_w.DeleteAllItems()
        if self._data:
            self._item_list.SetStrings([e.name for e in self._data])
        else:
            self._item_list.SetStrings([])
    def _name2idx(self, name):
        for i,e in enumerate(self._data):
            if e.name==name:
                return i
    def _populate_each(self, name):
        self._pl_list_w.DeleteAllItems()
        if name is None:
            return
        self.ignoredirty=True
        _list_idx=self._name2idx(name)
        if _list_idx is not None:
            self._pl_list.SetStrings(self._data[_list_idx].songs)
        self.ignoredirty=False
        if not self.dirty:
            self.setdirty(False)

    def _populate(self):
        self._populate_master()
        self._populate_pl_list()
        
    def populate(self, dict):
        self._data=dict.get(playlist_key, [])
        self._master=dict.get(masterlist_key, [])
        self._clear()
        self._populate()

    def _save_to_db(self, dict):
        # first, save the master list of songs.
        db_rr={ masterlist_key: MasterListDataObject(dict.get(masterlist_key, [])) }
        database.ensurerecordtype(db_rr, masterlistobjectfactory)
        self._mw.database.savemajordict(masterlist_key, db_rr)
        # now, save the list of playlists
        _pl_list=dict.get(playlist_key, [])
        db_rr={ playlists_list: PlaylistDataObject([x.name for x in _pl_list]) }
        database.ensurerecordtype(db_rr, playlistobjectfactory)
        self._mw.database.savemajordict(playlists_list, db_rr)
        # save the playlist entries
        db_rr={ }
        for e in _pl_list:
            db_rr[e.name]=PlaylistEntryDataObject(e)
        database.ensurerecordtype(db_rr, playlistentryobjectfactory)
        self._mw.database.savemajordict(playlist_key, db_rr)
        
    def populatefs(self, dict):
        self._save_to_db(dict)
        return dict

    def getfromfs(self, result):
        _master_dict=self._mw.database.getmajordictvalues(masterlist_key,
                                                          masterlistobjectfactory)
        _master_dict=_master_dict.get(masterlist_key, {})
        result.update( { masterlist_key: \
                         [x['name'] for x in _master_dict.get(masterlist_key, [])] })
        _pl_list_dict=self._mw.database.getmajordictvalues(playlists_list,
                                                           playlistobjectfactory)
        _pl_list_dict=_pl_list_dict.get(playlists_list, {})
        _pl_entries_dict=self._mw.database.getmajordictvalues(playlist_key,
                                                              playlistentryobjectfactory)
        _pl_list=[]
        for e in _pl_list_dict.get(playlist_key, []):
            _pl_entry=_pl_entries_dict.get(e['name'], None)
            if _pl_entry:
                _entry=PlaylistEntry()
                _entry.name=e['name']
                _entry.type=_pl_entry['type']
                _entry.songs=[x['name'] for x in _pl_entry['songs']]
                _pl_list.append(_entry)
        result.update({playlist_key: _pl_list })
        return result

    # called from various widget update callbacks
    def OnMakeDirty(self, _=None):
        """A public function you can call that will set the dirty flag"""
        if self.dirty or self.ignoredirty:
            # already dirty, no need to make it worse
            return
        print 'OnMakeDirty'
        self.setdirty(True)

    def OnPlaylistSelected(self, evt):
        self._populate_each(evt.GetLabel())
        evt.Skip()
    def OnDirty(self, _):
        self.setdirty(True)

    def _change_playlist_name(self, new_name):
        for e in self._data:
            if e.name==self._old_name:
                e.name=new_name
    def _add_playlist_name(self, new_name):
        _entry=PlaylistEntry()
        _entry.name=new_name
        self._data.append(_entry)

    def OnStartLabelChanged(self, evt):
        self._old_name=evt.GetLabel()
    def OnLabelChanged(self, evt):
        _new_name=evt.GetLabel()
        if _new_name:
            self.setdirty(True)
            if self._old_name:
                self._change_playlist_name(_new_name)
            else:
                self._add_playlist_name(_new_name)
        evt.Skip()

    def OnAdd2Playlist(self, _):
        _pl_idx=self._item_list_w.GetNextItem(-1, state=wx.LIST_STATE_SELECTED)
        _master_idx=self._master_list_w.GetNextItem(-1, state=wx.LIST_STATE_SELECTED)
        if _pl_idx==-1 or _master_idx==-1:
            # no selection
            return
        _entry_idx=self._name2idx(self._item_list_w.GetItemText(_pl_idx))
        if _entry_idx is not None:
            self.setdirty(True)
            self._pl_list_w.InsertStringItem(self._pl_list_w.GetItemCount()-1,
                                             self._master_list_w.GetItemText(_master_idx))

    def OnSave(self, _):
        # save the current playlist
        _pl_idx=self._item_list_w.GetNextItem(-1, state=wx.LIST_STATE_SELECTED)
        if _pl_idx!=-1:
            _entry_idx=self._name2idx(self._item_list_w.GetItemText(_pl_idx))
            if _entry_idx is not None:
                self._data[_entry_idx].songs=self._pl_list.GetStrings()
        # create data dicts & save them to db
        _pl_list=[]
        for _name in self._item_list.GetStrings():
            if _name:
                _idx=self._name2idx(_name)
                if _idx is not None:
                    _pl_list.append(self._data[_idx])
        self._save_to_db({ masterlist_key: self._master_list.GetStrings(),
                           playlist_key: _pl_list })
        self.setdirty(False)

    def OnRevert(self, _):
        _pl_idx=self._item_list_w.GetNextItem(-1, state=wx.LIST_STATE_SELECTED)
        # discard all changes
        _res={}
        self.getfromfs(_res)
        self.populate(_res)
        if _pl_idx!=-1:
            self._item_list_w.SetItemState(_pl_idx, wx.LIST_STATE_SELECTED,
                                           wx.LIST_MASK_STATE)
        self.setdirty(False)
