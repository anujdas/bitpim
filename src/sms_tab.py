### BITPIM
###
### Copyright (C) 2005 Joe Pham <djpham@netzero.net>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""
Code to handle the SMS Tab of the BitPim main display.
The read flag is not required for outbox and saved message, delivery
status is not needed for saved and inbox message, from is not required for
save and outbox, to is not required for inbox etc.

"""
# standard modules
import copy

# wx modules
import wx
import wx.gizmos as gizmos
import wx.lib.scrolledpanel as scrolled

# BitPim modules
import database
import guiwidgets
import phonebookentryeditor as pb_editor
import phonenumber
import pubsub
import sms
import today

#-------------------------------------------------------------------------------
class StaticText(wx.StaticText):
    def __init__(self, parent, _=None):
        super(StaticText, self).__init__(parent, -1)
    def SetValue(self, v):
        self.SetLabel(v)

#-------------------------------------------------------------------------------
class TimeStamp(wx.StaticText):
    def __init__(self, parent, _=None):
        super(TimeStamp, self).__init__(parent, -1)
    def SetValue(self, v):
        if v:
            self.SetLabel('%04d-%02d-%2d %02d:%02d:%02d'%(
                int(v[:4]), int(v[4:6]), int(v[6:8]),
                int(v[9:11]), int(v[11:13]), int(v[13:])))
        else:
            self.SetLabel('')

#-------------------------------------------------------------------------------
class DeliveryStatus(wx.StaticText):
    def __init__(self, parent, _=None):
        super(DeliveryStatus, self).__init__(parent, -1)
    def SetValue(self, v):
        self.SetLabel('\n'.join(v))

#-------------------------------------------------------------------------------
class SMSInfo(pb_editor.DirtyUIBase):
    _dict_key_index=0
    _label_index=1
    _class_index=2
    _get_index=3
    _set_index=4
    _w_index=5
    _flg_index=6
    _not_used_fields={
        sms.SMSEntry.Folder_Inbox: ('delivery_status', '_to'),
        sms.SMSEntry.Folder_Sent: ('read', '_from'),
        sms.SMSEntry.Folder_Saved: ('delivery_status',) }
    def __init__(self, parent, _=None):
        super(SMSInfo, self).__init__(parent)
        self._fields=[
            ['_from', 'From:', StaticText, None, None, None, 0],
            ['_to', 'To:', StaticText, None, None, None, 0],
            ['callback', 'Callback #:', StaticText, None, None, None, 0],
            ['subject', 'Subj:', StaticText, None, None, None, 0],
            ['datetime', 'Date:', TimeStamp, None, None, None, 0],
            ['priority_str', 'Priority:', StaticText, None, None, None, 0],
            ['read', 'Read?:', wx.CheckBox, None, None, None, 0],
            ['locked', 'Locked:', wx.CheckBox, None, None, None, 0],
            ['delivery_status', 'Delivery Status:', DeliveryStatus, None, None,
             None, wx.EXPAND],
            ]
        gs=wx.FlexGridSizer(-1, 2, 5, 5)
        gs.AddGrowableCol(1)
        for n in self._fields:
            gs.Add(wx.StaticText(self, -1, n[self._label_index],
                                 style=wx.ALIGN_LEFT),0, wx.EXPAND|wx.BOTTOM, 0)
            w=n[self._class_index](self, -1)
            gs.Add(w, 0, n[self._flg_index]|wx.BOTTOM, 0)
            n[self._w_index]=w
        # all done
        self.SetSizer(gs)
        self.SetAutoLayout(True)
        gs.Fit(self)
        self._gs=gs

    def OnMakeDirty(self, evt):
        self.OnDirtyUI(evt)

    def Set(self, data):
        self.ignore_dirty=True
        if data is None:
            for n in self._fields:
                n[self._w_index].Enable(False)
        else:
            _bad_fields=self._not_used_fields.get(data.folder, ())
            for i,n in enumerate(self._fields):
                w=n[self._w_index]
                if n[self._dict_key_index] in _bad_fields:
                    self._gs.Show(i*2, False)
                    self._gs.Show(i*2+1, False)
                else:
                    self._gs.Show(i*2, True)
                    self._gs.Show(i*2+1, True)
                    w.Enable(True)
                    w.SetValue(getattr(data, n[self._dict_key_index]))
        self._gs.Layout()
        self.ignore_dirty=self.dirty=False

    def Clear(self):
        self.Set(None)
        self.Enable(False)

#-------------------------------------------------------------------------------
class FolderPage(wx.Panel):
    canned_msg_key='canned_msg'
    def __init__(self, parent):
        super(FolderPage, self).__init__(parent, -1)
        self._data=self._data_map=self._name_map={}
        self.canned_data=sms.CannedMsgEntry()
        # main box sizer
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # the tree
        scrolled_panel=scrolled.ScrolledPanel(self, -1)
        vbs0=wx.BoxSizer(wx.VERTICAL)
        self._item_list=wx.TreeCtrl(scrolled_panel, wx.NewId(),
                                    style=wx.TR_MULTIPLE|wx.TR_HAS_BUTTONS)
        vbs0.Add(self._item_list, 1, wx.EXPAND|wx.ALL, 5)
        self._root=self._item_list.AddRoot('SMS')
        self._nodes={}
        for s in sms.SMSEntry.Valid_Folders:
            self._nodes[s]=self._item_list.AppendItem(self._root, s)
        # and the canned message
        canned_node=self._item_list.AppendItem(self._root, 'Canned')
        self._item_list.AppendItem(canned_node, 'Built-In')
        self._item_list.AppendItem(canned_node, 'User')
        scrolled_panel.SetSizer(vbs0)
        scrolled_panel.SetAutoLayout(True)
        vbs0.Fit(scrolled_panel)
        scrolled_panel.SetupScrolling()
        hbs.Add(scrolled_panel, 1, wx.EXPAND|wx.BOTTOM, border=5)
        # the detailed info pane as a scrolled panel
        vbs1=wx.BoxSizer(wx.VERTICAL)
        self._item_info=SMSInfo(self)
        vbs1.Add(self._item_info, 0, wx.EXPAND|wx.ALL, 5)
        self._item_text=pb_editor.MemoEditor(self, -1)
        vbs1.Add(self._item_text, 1, wx.EXPAND|wx.ALL, 5)
        self.canned_list=gizmos.EditableListBox(self, -1, 'Canned Messages')
        vbs1.Add(self.canned_list, 1, wx.EXPAND|wx.ALL, 5)
        vbs1.Show(self.canned_list, False)
        self.builtin_canned_list=wx.ListBox(self, -1)
        vbs1.Add(self.builtin_canned_list, 1, wx.EXPAND|wx.ALL, 5)
        vbs1.Show(self.builtin_canned_list, False)
        self.save_btn=wx.Button(self, wx.NewId(), 'Save')
        vbs1.Add(self.save_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        vbs1.Show(self.save_btn, False)
        self.info_bs=vbs1
        hbs.Add(vbs1, 3, wx.EXPAND|wx.ALL, border=5)
        # context menu
        self._bgmenu=wx.Menu()
        context_menu_data=(
            ('Expand All', self._OnExpandAll),
            ('Collapse All', self._OnCollapseAll))
        for e in context_menu_data:
            id=wx.NewId()
            self._bgmenu.Append(id, e[0])
            wx.EVT_MENU(self, id, e[1])
        # all done
        self.SetSizer(hbs)
        self.SetAutoLayout(True)
        hbs.Fit(self)
        # event handlers
        wx.EVT_TREE_SEL_CHANGED(self, self._item_list.GetId(),
                                self._OnSelChanged)
        pubsub.subscribe(self._OnPBLookup, pubsub.RESPONSE_PB_LOOKUP)
        wx.EVT_RIGHT_UP(self._item_list, self._OnRightClick)
        # populate data
        self._populate()
        # expand the whole tree
        self._OnExpandAll(None)

    def _OnExpandAll(self, _):
        sel_ids=self._item_list.GetSelections()
        if not sel_ids:
            sel_ids=[self._root]
        for sel_id in sel_ids:
            self._item_list.Expand(sel_id)
            id, cookie=self._item_list.GetFirstChild(sel_id)
            while id.IsOk():
                self._item_list.Expand(id)
                id, cookie=self._item_list.GetNextChild(sel_id, cookie)
    def _OnCollapseAll(self, _):
        sel_ids=self._item_list.GetSelections()
        if not sel_ids:
            sel_ids=[self._root]
        for sel_id in sel_ids:
            self._item_list.Collapse(sel_id)
            id, cookie=self._item_list.GetFirstChild(sel_id)
            while id.IsOk():
                self._item_list.Collapse(id)
                id, cookie=self._item_list.GetNextChild(sel_id, cookie)
    def _OnRightClick(self, evt):
        self._item_list.PopupMenu(self._bgmenu, evt.GetPosition())

    def _OnSelChanged(self, evt):
        # an item was clicked on/selected
        item=evt.GetItem()
        if item.IsOk():
            item_text=self._item_list.GetItemText(item)
            if item_text=='Built-In':
                self.info_bs.Show(self._item_info, False)
                self.info_bs.Show(self._item_text, False)
                self.info_bs.Show(self.canned_list, False)
                self.info_bs.Show(self.builtin_canned_list, True)
                self.info_bs.Show(self.save_btn, False)
                self.info_bs.Layout()
            elif item_text=='User':
                self.info_bs.Show(self._item_info, False)
                self.info_bs.Show(self._item_text, False)
                self.info_bs.Show(self.canned_list, True)
                self.info_bs.Show(self.builtin_canned_list, False)
                self.info_bs.Show(self.save_btn, True)
                self.info_bs.Layout()
            else:
                self.info_bs.Show(self._item_info, True)
                self.info_bs.Show(self._item_text, True)
                self.info_bs.Show(self.canned_list, False)
                self.info_bs.Show(self.builtin_canned_list, False)
                self.info_bs.Show(self.save_btn, False)
                k=self._item_list.GetPyData(evt.GetItem())
                self._populate_each(k)
                self.info_bs.Layout()

    def _OnPBLookup(self, msg):
        d=msg.data
        k=d.get('item', None)
        name=d.get('name', None)
        if k is None:
            return
        self._name_map[k]=name

    def _clear_info(self):
        self._item_info.Clear()
        self._item_text.Set(None)

    def _clear(self):
        for k,e in self._nodes.items():
            self._item_list.DeleteChildren(e)
        self._clear_info()

    def _populate(self):
        # populate new data
        self._clear()
        self._data_map={}
        # populate the list with data
        keys=[(x.datetime, k) for k,x in self._data.items()]
        keys.sort()
        for (_,k) in keys:
            n=self._data[k]
            i=self._item_list.AppendItem(self._nodes[n.folder], n.subject)
            self._item_list.SetItemPyData(i, k)
            self._data_map[k]=i
            if len(n._from) and not self._name_map.has_key(n._from):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n._from } )
            if len(n._to) and not self._name_map.has_key(n._to):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n._to } )
            if len(n.callback) and not self._name_map.has_key(n.callback):
                pubsub.publish(pubsub.REQUEST_PB_LOOKUP,
                               { 'item': n.callback } )
        # populate the canned data
        self.canned_list.SetStrings(
            self.canned_data.user_list)
        self.builtin_canned_list.Set(self.canned_data.builtin_list)

    def _populate_each(self, k):
        # populate the detailed info of the item keyed k
        if k is None:
            # clear out all the subfields
            self._item_info.Clear()
            self._item_text.Set(None)
            return
        entry=self._data.get(k, None)
        if entry is None:
            return
        # there're data, first enable the widgets
        self._item_info.Enable(True)
        # set the general detail
        e=copy.deepcopy(entry)
        # lookup names if available
        s=self._name_map.get(e._from, None)
        if s is None:
            e._from=phonenumber.format(e._from)
        else:
            e._from=s
        s=self._name_map.get(e._to, None)
        if s is None:
            e._to=phonenumber.format(e._to)
        else:
            e._to=s
        s=self._name_map.get(e.callback, None)
        if s is None:
            e.callback=phonenumber.format(e.callback)
        else:
            e.callback=s
        self._item_info.Set(e)
        self._item_text.Set({'memo': e.text})

    def Set(self, data, canned_data):
        self._data=data
        self.canned_data=canned_data
        self._populate()
    def Get(self):
        self.canned_data.user_list=self.canned_list.GetStrings()
        return self._data, self.canned_data

    def delete_selection(self, data):
        # try to delete an item, return True of successful
        sel_ids=self._item_list.GetSelections()
        if not sel_ids:
            return False
        for sel_idx in sel_ids:
            k=self._item_list.GetPyData(sel_idx)
            if k is None:
                # this is not a leaf node
                continue
            self._item_list.Delete(sel_idx)
            self._clear_info()
            del data[k]
            del self._data_map[k]
        # check for new selection
        sel_ids=self._item_list.GetSelections()
        if sel_ids and sel_ids[0].Ok():
            self._populate_each(self._item_list.GetPyData(sel_ids[0]))
        return True

    def publish_today_data(self):
        keys=[(x.datetime,k) for k,x in self._data.items()]
        keys.sort()
        keys.reverse()
        today_event=today.TodaySMSEvent()
        for _,k in keys:
            if self._data[k].folder==sms.SMSEntry.Folder_Inbox:
                today_event.append(self._data[k].text,
                                   { 'id': self._data_map[k] } )
        today_event.broadcast()

    def OnTodaySelection(self, evt):
        if evt.data:
            self._item_list.SelectItem(evt.data['id'])

    def get_sel_data(self):
        # return a dict of selected data
        res={}
        for sel_idx in self._item_list.GetSelections():
            k=self._item_list.GetPyData(sel_idx)
            if k:
                res[k]=self._data[k]
        return res

#-------------------------------------------------------------------------------
class SMSWidget(wx.Panel):
    _data_key='sms'
    _canned_data_key='canned_msg'
    def __init__(self, mainwindow, parent):
        super(SMSWidget, self).__init__(parent, -1)
        self._main_window=mainwindow
        self._data=self._canned_data={}
        # main box sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        # data date adjuster
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        self.read_only=False
        self.historical_date=None
        static_bs=wx.StaticBoxSizer(wx.StaticBox(self, -1,
                                                 'Historical Data Status:'),
                                    wx.VERTICAL)
        self.historical_data_label=wx.StaticText(self, -1, 'Current Data')
        static_bs.Add(self.historical_data_label, 1, wx.EXPAND|wx.ALL, 5)
        hbs.Add(static_bs, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        # the notebook with the tabs
        self._sms=FolderPage(self)
        # Event Handling
        wx.EVT_BUTTON(self, self._sms.save_btn.GetId(), self.OnSaveCannedMsg)
        # all done
        vbs.Add(self._sms, 1, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)
        # register for Today selection
        today.bind_notification_event(self._sms.OnTodaySelection,
                                      today.Today_Group_IncomingSMS)

    def _populate(self):
        self._sms.Set(self._data, self._canned_data)
        self._sms.publish_today_data()

    def OnSaveCannedMsg(self, _):
        if self.read_only:
            wx.MessageBox('You are viewing historical data which cannot be changed or saved',
                          'Cannot Save SMS Data',
                          style=wx.OK|wx.ICON_ERROR)
            return
        self._data, self._canned_data=self._sms.Get()
        self._save_to_db(canned_msg_dict=self._canned_data)

    def OnDelete(self, _):
        if self.read_only:
            return
        if self._sms.delete_selection(self._data):
            self._save_to_db(sms_dict=self._data)

    def getdata(self,dict,want=None):
        dict[self._data_key]=copy.deepcopy(self._data, {})
        dict[self._canned_data_key]=self._canned_data.get().get(
            self._canned_data_key, {})

    def get_selected_data(self):
        # return a dict of selected items
        return self._sms.get_sel_data()
    def get_data(self):
        return self._data

    def populate(self, dict, force=False):
        if self.read_only and not force:
            return
        if not self.read_only:
            self._canned_data=sms.CannedMsgEntry()
            self._canned_data.set({ self._canned_data_key: dict.get(self._canned_data_key, [])})
        self._data=dict.get(self._data_key, {})
        self._populate()

    def _save_to_db(self, sms_dict=None, canned_msg_dict=None):
        if self.read_only:
            return
        if sms_dict is not None:
            db_rr={}
            for k, e in sms_dict.items():
                db_rr[k]=sms.SMSDataObject(e)
            database.ensurerecordtype(db_rr, sms.smsobjectfactory)
            self._main_window.database.savemajordict(self._data_key, db_rr)
        if canned_msg_dict is not None:
            db_rr={}
            db_rr[self._canned_data_key]=sms.CannedMsgDataObject(
                canned_msg_dict)
            database.ensurerecordtype(db_rr, sms.cannedmsgobjectfactory)
            self._main_window.database.savemajordict(self._canned_data_key,
                                                      db_rr)
    def populatefs(self, dict):
        if self.read_only:
            wx.MessageBox('You are viewing historical data which cannot be changed or saved',
                          'Cannot Save SMS Data',
                          style=wx.OK|wx.ICON_ERROR)
            return
        canned_msg=sms.CannedMsgEntry()
        canned_msg.set({ self._canned_data_key: dict.get(self._canned_data_key, [])})
        self._save_to_db(sms_dict=dict.get(self._data_key, []),
                          canned_msg_dict=canned_msg)
        return dict

    def getfromfs(self, result, timestamp=None):
        # read data from the database
        sms_dict=self._main_window.database.\
                   getmajordictvalues(self._data_key, sms.smsobjectfactory,
                                      at_time=timestamp)
        r={}
        for k,e in sms_dict.items():
            ce=sms.SMSEntry()
            ce.set_db_dict(e)
            r[ce.id]=ce
        result.update({ self._data_key: r })
        # read the canned messages
        canned_msg_dict=self._main_window.database.\
                         getmajordictvalues(self._canned_data_key,
                                            sms.cannedmsgobjectfactory)
        for k,e in canned_msg_dict.items():
            ce=sms.CannedMsgEntry()
            ce.set_db_dict(e)
            result.update(ce.get())
        return result

    def merge(self, dict):
        # merge this data with our data
        # the merge criteria is simple: reject if msg_id's are same
        if self.read_only:
            wx.MessageBox('You are viewing historical data which cannot be changed or saved',
                          'Cannot Save SMS Data',
                          style=wx.OK|wx.ICON_ERROR)
            return
        existing_id=[e.msg_id for k,e in self._data.items()]
        d=dict.get(self._data_key, {})
        for k,e in d.items():
            if e.msg_id not in existing_id:
                self._data[e.id]=e
        # save the canned data
        self._canned_data=sms.CannedMsgEntry()
        self._canned_data.set({ self._canned_data_key: dict.get(self._canned_data_key, []) } )
        # populate the display and save the data
        self._populate()
        self._save_to_db(sms_dict=self._data,
                         canned_msg_dict=self._canned_data)

    def OnHistoricalData(self):
        """Display current or historical data"""
        if self.read_only:
            current_choice=guiwidgets.HistoricalDataDialog.Historical_Data
        else:
            current_choice=guiwidgets.HistoricalDataDialog.Current_Data
        dlg=guiwidgets.HistoricalDataDialog(self,
                                            current_choice=current_choice,
                                            historical_date=self.historical_date,
                                            historical_events=\
                                            self._main_window.database.getchangescount(self._data_key))
        if dlg.ShowModal()==wx.ID_OK:
            self._main_window.OnBusyStart()
            current_choice, self.historical_date=dlg.GetValue()
            r={}
            if current_choice==guiwidgets.HistoricalDataDialog.Current_Data:
                self.read_only=False
                msg_str='Current Data'
                self.getfromfs(r)
            else:
                self.read_only=True
                msg_str='Historical Data as of %s'%\
                         str(wx.DateTimeFromTimeT(self.historical_date))
                self.getfromfs(r, self.historical_date)
            self.populate(r, True)
            self.historical_data_label.SetLabel(msg_str)
            self._main_window.OnBusyEnd()
        dlg.Destroy()
