#!/usr/bin/env python

### BITPIM
###
### Copyright (C) 2003-2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"""Most of the graphical user interface elements making up BitPim"""

# standard modules
import os
import sys
import time
import copy
import StringIO
import getpass
import sha,md5
import zlib
import base64
import thread
import Queue
import shutil
import time

# wx. modules
import wx
import wx.html
import wx.lib.mixins.listctrl
import wx.lib.intctrl
import wx.lib.newevent

# my modules
import common
import version
import helpids
import comscan
import usbscan
import comdiagnose
import analyser
import guihelper
import pubsub
import bphtml
import bitflingscan
import aggregatedisplay
import phone_media_codec
import pubsub

###
### BitFling cert stuff
###

BitFlingCertificateVerificationEvent, EVT_BITFLINGCERTIFICATEVERIFICATION = wx.lib.newevent.NewEvent()

####
#### A simple text widget that does nice pretty logging.
####        

    
class LogWindow(wx.Panel):

    theanalyser=None
    
    def __init__(self, parent):
        wx.Panel.__init__(self,parent, -1)
        # have to use rich2 otherwise fixed width font isn't used on windows
        self.tb=wx.TextCtrl(self, 1, style=wx.TE_MULTILINE| wx.TE_RICH2|wx.TE_DONTWRAP|wx.TE_READONLY)
        f=wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL )
        ta=wx.TextAttr(font=f)
        self.tb.SetDefaultStyle(ta)
        self.sizer=wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.tb, 1, wx.EXPAND)
        self.SetSizer(self.sizer)
        self.SetAutoLayout(True)
        self.sizer.Fit(self)
        wx.EVT_IDLE(self, self.OnIdle)
        wx.EVT_SHOW(self, self.OnShow)
        self.outstandingtext=StringIO.StringIO()

        wx.EVT_KEY_UP(self.tb, self.OnKeyUp)

    def Clear(self):
        self.tb.Clear()

    def OnSelectAll(self, _):
        self.tb.SetSelection(-1, -1)

    def OnShow(self, show):
        if show.GetShow():
            wx.CallAfter(self.CleanupView)

    def CleanupView(self):
        self.tb.SetInsertionPoint(0)
        self.tb.SetInsertionPointEnd()
        self.tb.Refresh()

    def OnIdle(self,_):
        if self.outstandingtext.tell():
            # this code is written to be re-entrant
            newt=self.outstandingtext.getvalue()
            self.outstandingtext.seek(0)
            self.outstandingtext.truncate()
            self.tb.AppendText(newt)

    def log(self, str, nl=True):
        now=time.time()
        t=time.localtime(now)
        self.outstandingtext.write("%d:%02d:%02d.%03d " % ( t[3], t[4], t[5],  int((now-int(now))*1000)))
        self.outstandingtext.write(str)
        if nl:
            self.outstandingtext.write("\n")

    def logdata(self, str, data, klass=None):
        o=self.outstandingtext
        self.log(str, nl=False)
        if data is not None:
            o.write(" Data - "+`len(data)`+" bytes\n")
            if klass is not None:
                try:
                    o.write("<#! %s.%s !#>\n" % (klass.__module__, klass.__name__))
                except:
                    klass=klass.__class__
                    o.write("<#! %s.%s !#>\n" % (klass.__module__, klass.__name__))
            o.write(common.datatohexstring(data))
        o.write("\n")

    def OnKeyUp(self, evt):
        keycode=evt.GetKeyCode()
        if keycode==ord('P') and evt.ControlDown() and evt.AltDown():
            # analyse what was selected
            data=self.tb.GetStringSelection()
            # or the whole buffer if it was nothing
            if data is None or len(data)==0:
                data=self.tb.GetValue()
            try:
                self.theanalyser.Show()
            except:
                self.theanalyser=None
                
            if self.theanalyser is None:
                self.theanalyser=analyser.Analyser(data=data)

            self.theanalyser.Show()
            self.theanalyser.newdata(data)
            evt.Skip()
            


###
### Dialog asking what you want to sync
###

class GetPhoneDialog(wx.Dialog):
    # sync sources ("Pretty Name", "name used to query profile")
    sources= ( ('PhoneBook', 'phonebook'),
               ('Calendar', 'calendar'),
               ('Wallpaper', 'wallpaper'),
               ('Ringtone', 'ringtone'),
               ('Memo', 'memo'),
               ('Todo', 'todo'),
               ('SMS', 'sms'),
               ('Call History', 'call_history'),
               ('Play List', 'playlist'))
    
    # actions ("Pretty Name", "name used to query profile")
    actions = (  ("Get", "read"), )

    NOTREQUESTED=0
    MERGE=1
    OVERWRITE=2

    # type of action ("pretty name", "name used to query profile")
    types= ( ("Add", MERGE),
             ("Replace All", OVERWRITE))

    HELPID=helpids.ID_GET_PHONE_DATA

    def __init__(self, frame, title, id=-1):
        wx.Dialog.__init__(self, frame, id, title,
                          style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE)
        gs=wx.FlexGridSizer(2+len(self.sources), 1+len(self.types),5 ,10)
        gs.AddGrowableCol(1)
        gs.AddMany( [
            (wx.StaticText(self, -1, "Source"), 0, wx.EXPAND),])

        for pretty,_ in self.types:
            gs.Add(wx.StaticText(self, -1, pretty), 0, wx.ALIGN_CENTRE)


        self.cb=[]
        self.rb=[]

        for desc, source in self.sources:
            self.cb.append(wx.CheckBox(self, wx.NewId(), desc))
            wx.EVT_CHECKBOX(self, self.cb[-1].GetId(), self.DoOkStatus)
            gs.Add(self.cb[-1], 0, wx.EXPAND)
            first=True
            for tdesc,tval in self.types:
                if first:
                    style=wx.RB_GROUP
                    first=0
                else:
                    style=0
                self.rb.append( wx.RadioButton(self, -1, "", style=style) )
                if not self._dowesupport(source, self.actions[0][1], tval):
                    self.rb[-1].Enable(False)
                    self.rb[-1].SetValue(False)
                gs.Add(self.rb[-1], 0, wx.ALIGN_CENTRE)

        bs=wx.BoxSizer(wx.VERTICAL)
        bs.Add(gs, 0, wx.EXPAND|wx.ALL, 10)
        bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 7)
        
        but=self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP)
        bs.Add(but, 0, wx.EXPAND|wx.ALL, 10)
        
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

        wx.EVT_BUTTON(self, wx.ID_HELP, self.OnHelp)

    def _setting(self, type):
        for index in range(len(self.sources)):
            if self.sources[index][1]==type:
                if not self.cb[index].GetValue():
                    print type,"not requested"
                    return self.NOTREQUESTED
                for i in range(len(self.types)):
                    if self.rb[index*len(self.types)+i].GetValue():
                        print type,self.types[i][1]
                        return self.types[i][1]
                assert False, "No selection for "+type
        assert False, "No such type "+type

    def GetPhoneBookSetting(self):
        return self._setting("phonebook")

    def GetCalendarSetting(self):
        return self._setting("calendar")

    def GetWallpaperSetting(self):
        return self._setting("wallpaper")

    def GetRingtoneSetting(self):
        return self._setting("ringtone")

    def GetMemoSetting(self):
        return self._setting("memo")

    def GetTodoSetting(self):
        return self._setting("todo")

    def GetSMSSetting(self):
        return self._setting("sms")
    def GetCallHistorySetting(self):
        return self._setting("call_history")
    def GetPlaylistSetting(self):
        return self._setting('playlist')

    def OnHelp(self,_):
        wx.GetApp().displayhelpid(self.HELPID)

    # this is what BitPim itself supports - the phones may support a subset
    _notsupported=(
        # ('phonebook', 'read', MERGE), # sort of is
        ('calendar', 'read', MERGE),
        ('wallpaper', 'read', MERGE),
        ('ringtone', 'read', MERGE),
        ('memo', 'read', MERGE),
        ('todo', 'read', MERGE),
        ('playlist', 'read', MERGE))

    def _dowesupport(self, source, action, type):
        if (source,action,type) in self._notsupported:
            return False
        return True

    def UpdateWithProfile(self, profile):
        for cs in range(len(self.sources)):
            source=self.sources[cs][1]
            # we disable the checkbox
            self.cb[cs].Enable(False)
            # are any radio buttons enabled
            count=0
            for i in range(len(self.types)):
                assert len(self.types)==2
                if self.types[i][1]==self.MERGE:
                    type="MERGE"
                elif self.types[i][1]==self.OVERWRITE:
                    type="OVERWRITE"
                else:
                    assert False
                    continue
                if self._dowesupport(source, self.actions[0][1], self.types[i][1]) and \
                       profile.SyncQuery(source, self.actions[0][1], type):
                    self.cb[cs].Enable(True)
                    self.rb[cs*len(self.types)+i].Enable(True)
                    if self.rb[cs*len(self.types)+i].GetValue():
                        count+=1
                else:
                    self.rb[cs*len(self.types)+i].Enable(False)
                    self.rb[cs*len(self.types)+i].SetValue(False)
            if not self.cb[cs].IsEnabled():
                # ensure checkbox is unchecked if not enabled
                self.cb[cs].SetValue(False)
            else:
                # ensure one radio button is checked
                if count!=1:
                    done=False
                    for i in range(len(self.types)):
                        index=cs*len(self.types)+i
                        if self.rb[index].IsEnabled():
                            self.rb[index].SetValue(not done)
                            done=False
                            
    def ShowModal(self):
        # we ensure the OK button is in the correct state
        self.DoOkStatus()
        return wx.Dialog.ShowModal(self)

    def DoOkStatus(self, evt=None):
        # ensure the OK button is in the right state
        enable=False
        for i in self.cb:
            if i.GetValue():
                enable=True
                break
        self.FindWindowById(wx.ID_OK).Enable(enable)
        if evt is not None:
            evt.Skip()

class SendPhoneDialog(GetPhoneDialog):
    HELPID=helpids.ID_SEND_PHONE_DATA

    # actions ("Pretty Name", "name used to query profile")
    actions = (  ("Send", "write"), )
    
    def __init__(self, frame, title, id=-1):
        GetPhoneDialog.__init__(self, frame, title, id)

    # this is what BitPim itself doesn't supports - the phones may support less
    _notsupported=(
        ('call_history', 'write', None),)
        

###
###  The master config dialog
###

class ConfigDialog(wx.Dialog):
    phonemodels={ 'LG-G4015 (AT&T)': 'com_lgg4015',
                  'LG-C2000 (Cingular)': 'com_lgc2000',
                  'LG-VX3200': 'com_lgvx3200',
                  'LG-VX4400': 'com_lgvx4400',
                  'LG-VX4500': 'com_lgvx4500',
                  'LG-VX4600 (Telus Mobility)': 'com_lgvx4600',
                  'LG-VX4650 (Verizon Wireless)': 'com_lgvx4650',
                  'LG-VX5200 (Verizon Wireless)': 'com_lgvx5200',
                  'LG-LX5450 (Alltel)': 'com_lglx5450',
                  'LG-VX6000': 'com_lgvx6000',
                  'LG-VX6100': 'com_lgvx6100',
                  'LG-VX7000': 'com_lgvx7000',
                  'LG-VX8000 (Verizon Wireless)': 'com_lgvx8000',
                  'LG-VX8100 (Verizon Wireless)': 'com_lgvx8100',
                  'LG-VX9800 (Verizon Wireless)': 'com_lgvx9800',
                  'LG-PM225 (Sprint)': 'com_lgpm225',
                  'LG-PM325 (Sprint)': 'com_lgpm325',
                  'LG-TM520': 'com_lgtm520',
                  'LG-VX10': 'com_lgtm520',
                  'MM-7400': 'com_sanyo7400',
                  'MM-8300': 'com_sanyo8300',
                  'PM-8200': 'com_sanyo8200',
                  'RL-4920': 'com_sanyo4920',
                  'RL-4930': 'com_sanyo4930',
                  'SCP-4900': 'com_sanyo4900',
                  'SCP-5300': 'com_sanyo5300',
                  'SCP-5400': 'com_sanyo5400',
                  'SCP-5500': 'com_sanyo5500',
                  'SCP-7200': 'com_sanyo7200',
                  'SCP-7300': 'com_sanyo7300',
                  'SCP-8100': 'com_sanyo8100',
                  'SCP-8100 (Bell Mobility)': 'com_sanyo8100_bell',
                  'SCH-A310': 'com_samsungscha310',
                  'SPH-A460': 'com_samsungspha460',
                  'SPH-A620 (VGA1000)': 'com_samsungspha620',
                  'SPH-A660 (VI660)': 'com_samsungspha660',
                  'SPH-A740': 'com_samsungspha740',
                  'SPH-A840': 'com_samsungspha840',
                  'SPH-N200': 'com_samsungsphn200',
                  'SPH-N400': 'com_samsungsphn400',
                  'SCH-A650': 'com_samsungscha650',
                  'SCH-A670': 'com_samsungscha670',
                  'SK6100 (Pelephone)' : 'com_sk6100', 
                  'VM4050 (Sprint)' : 'com_toshibavm4050',
                  'VI-2300': 'com_sanyo2300',
                  'Other CDMA phone': 'com_othercdma',
                  }

    if __debug__:
        phonemodels.update( {'Audiovox CDM-8900': 'com_audiovoxcdm8900',     # phone is too fragile for normal use
                             })
    update_choices=('Never', 'Daily', 'Weekly', 'Monthly')
    setme="<setme>"
    ID_DIRBROWSE=wx.NewId()
    ID_COMBROWSE=wx.NewId()
    ID_RETRY=wx.NewId()
    ID_BITFLING=wx.NewId()
    def __init__(self, mainwindow, frame, title="BitPim Settings", id=-1):
        wx.Dialog.__init__(self, frame, id, title,
                          style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE)
        self.mw=mainwindow

        self.bitflingresponsequeues={}

        gs=wx.GridBagSizer(10, 10)
        gs.AddGrowableCol(1)
        _row=0
        # safemode
        gs.Add( wx.StaticText(self, -1, "Read Only"), pos=(_row,0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.safemode=wx.CheckBox(self, wx.NewId(), "Block writing anything to the phone")
        gs.Add( self.safemode, pos=(_row,1), flag=wx.ALIGN_CENTER_VERTICAL)
        _row+=1

        # where we store our files
        gs.Add( wx.StaticText(self, -1, "Disk storage"), pos=(_row,0), flag=wx.ALIGN_CENTER_VERTICAL)
        gs.Add(wx.StaticText(self, -1, self.mw.config.Read('path', '<Unknown>')),
               pos=(_row,1), flag=wx.ALIGN_CENTER_VERTICAL)
        _row+=1
        gs.Add(wx.StaticText(self, -1, 'Config File'), pos=(_row,0),
               flag=wx.ALIGN_CENTER_VERTICAL)
        gs.Add(wx.StaticText(self, -1, self.mw.config.Read('config')),
               pos=(_row,1), flag=wx.ALIGN_CENTER_VERTICAL)
        _row+=1

        # phone type
        gs.Add( wx.StaticText(self, -1, "Phone Type"), pos=(_row,0), flag=wx.ALIGN_CENTER_VERTICAL)
        keys=self.phonemodels.keys()
        keys.sort()
        self.phonebox=wx.ComboBox(self, -1, "LG-VX4400", style=wx.CB_DROPDOWN|wx.CB_READONLY,choices=keys)
        self.phonebox.SetValue("LG-VX4400")
        gs.Add( self.phonebox, pos=(_row,1), flag=wx.ALIGN_CENTER_VERTICAL)
        _row+=1

        # com port
        gs.Add( wx.StaticText(self, -1, "Com Port"), pos=(_row,0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.commbox=wx.TextCtrl(self, -1, self.setme, size=(200,-1))
        gs.Add( self.commbox, pos=(_row,1), flag=wx.ALIGN_CENTER_VERTICAL)
        gs.Add( wx.Button(self, self.ID_COMBROWSE, "Browse ..."), pos=(_row,2), flag=wx.ALIGN_CENTER_VERTICAL)
        _row+=1

        # Automatic check for update
        gs.Add(wx.StaticText(self, -1, 'Check for Update'), pos=(_row,0), flag=wx.ALIGN_CENTER_VERTICAL)
        self.updatebox=wx.ComboBox(self, -1, self.update_choices[0],
                                   style=wx.CB_DROPDOWN|wx.CB_READONLY,
                                   choices=self.update_choices)
        gs.Add(self.updatebox, pos=(_row,1), flag=wx.ALIGN_CENTER_VERTICAL)
        _row+=1

        # always start with the 'Today' tab
        gs.Add(wx.StaticText(self, -1, 'Startup'), pos=(_row,0),
               flag=wx.ALIGN_CENTER_VERTICAL)
        self.startup=wx.CheckBox(self, wx.NewId(), 'Always start with the Today tab')
        gs.Add(self.startup, pos=(_row,1), flag=wx.ALIGN_CENTER_VERTICAL)
        _row+=1

        # whether or not to use TaskBarIcon
        if guihelper.IsMSWindows():
            gs.Add(wx.StaticText(self, -1, 'Task Bar Icon'), pos=(_row,0),
                   flag=wx.ALIGN_CENTER_VERTICAL)
            self.taskbaricon=wx.CheckBox(self, wx.NewId(),
                                         'Place BitPim Icon in the System Tray')
            gs.Add(self.taskbaricon, pos=(_row, 1), flag=wx.ALIGN_CENTER_VERTICAL)
            _row+=1
        else:
            self.taskbaricon=None

        # whether or not to run autodetect at startup
        gs.Add(wx.StaticText(self, -1, 'Autodetect at Startup'), pos=(_row,0),
               flag=wx.ALIGN_CENTER_VERTICAL)
        self.autodetect_start=wx.CheckBox(self, wx.NewId(),
                                     'Detect phone at bitpim startup')
        gs.Add(self.autodetect_start, pos=(_row, 1), flag=wx.ALIGN_CENTER_VERTICAL)
        _row+=1

        # bitfling
        if bitflingscan.IsBitFlingEnabled():
            self.SetupBitFlingCertVerification()
            gs.Add( wx.StaticText( self, -1, "BitFling"), pos=(_row,0), flag=wx.ALIGN_CENTER_VERTICAL)
            self.bitflingenabled=wx.CheckBox(self, self.ID_BITFLING, "Enabled")
            gs.Add(self.bitflingenabled, pos=(_row,1), flag=wx.ALIGN_CENTER_VERTICAL)
            gs.Add( wx.Button(self, self.ID_BITFLING, "Settings ..."), pos=(_row,2), flag=wx.ALIGN_CENTER_VERTICAL)
            wx.EVT_BUTTON(self, self.ID_BITFLING, self.OnBitFlingSettings)
            wx.EVT_CHECKBOX(self, self.ID_BITFLING, self.ApplyBitFlingSettings)
            if self.mw.config.Read("bitfling/password","<unconfigured>") \
               == "<unconfigured>":
                self.mw.config.WriteInt("bitfling/enabled", 0)
                self.bitflingenabled.SetValue(False)
                self.bitflingenabled.Enable(False)
        else:
            self.bitflingenabled=None
        # crud at the bottom
        bs=wx.BoxSizer(wx.VERTICAL)
        bs.Add(gs, 0, wx.EXPAND|wx.ALL, 10)
        bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 7)
        
        but=self.CreateButtonSizer(wx.OK|wx.CANCEL|wx.HELP)
        bs.Add(but, 0, wx.CENTER|wx.ALL, 10)

        wx.EVT_BUTTON(self, wx.ID_HELP, self.OnHelp)
        wx.EVT_BUTTON(self, self.ID_COMBROWSE, self.OnComBrowse)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOK)

        self.setdefaults()

        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

        # Retrieve saved settings... (we only care about position)
        set_size("ConfigDialog", self, screenpct=-1,  aspect=3.5)

        wx.EVT_CLOSE(self, self.OnClose)

    def OnCancel(self, _):
        self.saveSize()

    def OnOK(self, _):
        self.saveSize()
        self.EndModal(wx.ID_OK)
        self.ApplyBitFlingSettings()

    def OnHelp(self, _):
        wx.GetApp().displayhelpid(helpids.ID_SETTINGS_DIALOG)

    def OnComBrowse(self, _):
        self.saveSize()
        if self.mw.wt is not None:
            self.mw.wt.clearcomm()
        # remember its size
        # w=self.mw.config.ReadInt("combrowsewidth", 640)
        # h=self.mw.config.ReadInt("combrowseheight", 480)
        p=self.mw.config.ReadInt("combrowsesash", 200)
        dlg=CommPortDialog(self, __import__('phones.'+self.phonemodels[self.phonebox.GetValue()], globals(), locals(), ['Profile']), defaultport=self.commbox.GetValue(), sashposition=p)
        # dlg.SetSize(wx.Size(w,h))
        # dlg.Centre()
        res=dlg.ShowModal()
        v=dlg.GetPort()
        
        # sz=dlg.GetSize()
        # self.mw.config.WriteInt("combrowsewidth", sz.GetWidth())
        # self.mw.config.WriteInt("combrowseheight", sz.GetHeight())

        self.mw.config.WriteInt("combrowsesash", dlg.sashposition)
        dlg.Destroy()
        if res==wx.ID_OK:
            self.commbox.SetValue(v)

    def ApplyBitFlingSettings(self, _=None):
        if self.bitflingenabled is not None:
            if self.bitflingenabled.GetValue():
                bitflingscan.flinger.configure(self.mw.config.Read("bitfling/username", "<unconfigured>"),
                                               bitflingscan.decode(self.mw.config.Read("bitfling/password",
                                                                                       "<unconfigured>")),
                                               self.mw.config.Read("bitfling/host", "<unconfigured>"),
                                               self.mw.config.ReadInt("bitfling/port", 12652))
            else:
                bitflingscan.flinger.unconfigure()

    def OnBitFlingSettings(self, _):
        dlg=BitFlingSettingsDialog(None, self.mw.config)
        if dlg.ShowModal()==wx.ID_OK:
            dlg.SaveSettings()
        dlg.Destroy()
        self.ApplyBitFlingSettings()
        if self.mw.config.Read("bitfling/password","<unconfigured>") \
               != "<unconfigured>":
            self.bitflingenabled.Enable(True)
        
    def SetupBitFlingCertVerification(self):
        "Setup all the voodoo needed for certificate verification to happen, not matter which thread wants it"
        EVT_BITFLINGCERTIFICATEVERIFICATION(self, self._wrapVerifyBitFlingCert)
        bitflingscan.flinger.SetCertVerifier(self.dispatchVerifyBitFlingCert)
        bitflingscan.flinger.setthreadeventloop(wx.SafeYield)

    def dispatchVerifyBitFlingCert(self, addr, key):
        """Handle a certificate verification from any thread

        The request is handed to the main gui thread, and then we wait for the
        results"""
        print thread.get_ident(),"dispatchVerifyBitFlingCert called"
        q=self.bitflingresponsequeues.get(thread.get_ident(), None)
        if q is None:
            q=Queue.Queue()
            self.bitflingresponsequeues[thread.get_ident()]=q
        print thread.get_ident(), "Posting BitFlingCertificateVerificationEvent"
        wx.PostEvent(self, BitFlingCertificateVerificationEvent(addr=addr, key=key, q=q))
        print thread.get_ident(), "After posting BitFlingCertificateVerificationEvent, waiting for response"
        res, exc = q.get()
        print thread.get_ident(), "Got response", res, exc
        if exc is not None:
            ex=exc[1]
            ex.gui_exc_info=exc[2]
            raise ex
        return res
        
    def _wrapVerifyBitFlingCert(self, evt):
        """Receive the event in the main gui thread for cert verification

        We unpack the parameters, call the verification method"""
        print "_wrapVerifyBitFlingCert"
        
        addr, hostkey, q = evt.addr, evt.key, evt.q
        self.VerifyBitFlingCert(addr, hostkey, q)

    def VerifyBitFlingCert(self, addr, key, q):
        print "VerifyBitFlingCert for", addr, "type",key.get_name()
        # ::TODO:: reject if not dsa
        # get fingerprint
        fingerprint=common.hexify(key.get_fingerprint())
        # do we already know about it?
        existing=wx.GetApp().config.Read("bitfling/certificates/%s" % (addr[0],), "")
        if len(existing):
            fp=existing
            if fp==fingerprint:
                q.put( (True, None) )
                return
        # throw up the dialog
        print "asking user"
        dlg=AcceptCertificateDialog(None, wx.GetApp().config, addr, fingerprint, q)
        dlg.ShowModal()

    def OnClose(self, evt):
        self.saveSize()
        # Don't destroy the dialong, just put it away...
        self.EndModal(wx.ID_CANCEL)

    def setfromconfig(self):
        if len(self.mw.config.Read("lgvx4400port")):
            self.commbox.SetValue(self.mw.config.Read("lgvx4400port", ""))
        if self.mw.config.Read("phonetype", "") in self.phonemodels:
            self.phonebox.SetValue(self.mw.config.Read("phonetype"))
        if self.bitflingenabled is not None:
            self.bitflingenabled.SetValue(self.mw.config.ReadInt("bitfling/enabled", 0))
            self.ApplyBitFlingSettings()
        self.safemode.SetValue(self.mw.config.ReadInt("Safemode", 0))
        self.updatebox.SetValue(self.mw.config.Read("updaterate",
                                                    self.update_choices[0]))
        self.startup.SetValue(self.mw.config.ReadInt("startwithtoday", 0))
        if self.taskbaricon:
            self.taskbaricon.SetValue(self.mw.config.ReadInt('taskbaricon', 0))
        self.autodetect_start.SetValue(self.mw.config.ReadInt("autodetectstart", 0))

    def setdefaults(self):
        if self.commbox.GetValue()==self.setme:
            comm="auto"
            self.commbox.SetValue(comm)

    def updatevariables(self):
        path=self.mw.config.Read('path')
        self.mw.configpath=path
        self.mw.ringerpath=self._fixup(os.path.join(path, "ringer"))
        self.mw.wallpaperpath=self._fixup(os.path.join(path, "wallpaper"))
        self.mw.phonebookpath=self._fixup(os.path.join(path, "phonebook"))
        self.mw.calendarpath=self._fixup(os.path.join(path, "calendar"))
        oldpath=self.mw.config.Read("path", "")
        self.mw.config.Write("path", path)
        self.mw.commportsetting=str(self.commbox.GetValue())
        self.mw.config.Write("lgvx4400port", self.mw.commportsetting)
        if self.mw.wt is not None:
            self.mw.wt.clearcomm()
        # comm parameters (retry, timeouts, flow control etc)
        commparm={}
        commparm['retryontimeout']=self.mw.config.ReadInt("commretryontimeout", False)
        commparm['timeout']=self.mw.config.ReadInt('commtimeout', 3)
        commparm['hardwareflow']=self.mw.config.ReadInt('commhardwareflow', False)
        commparm['softwareflow']=self.mw.config.ReadInt('commsoftwareflow', False)
        commparm['baud']=self.mw.config.ReadInt('commbaud', 115200)
        self.mw.commparams=commparm
        # phone model
        self.mw.config.Write("phonetype", self.phonebox.GetValue())
        self.mw.phonemodule=__import__('phones.'+self.phonemodels[self.phonebox.GetValue()], globals(), locals(), ['Profile'])
        self.mw.phoneprofile=self.mw.phonemodule.Profile()
        pubsub.publish(pubsub.PHONE_MODEL_CHANGED, self.mw.phonemodule)
        #  bitfling
        if self.bitflingenabled is not None:
            self.mw.bitflingenabled=self.bitflingenabled.GetValue()
            self.mw.config.WriteInt("bitfling/enabled", self.mw.bitflingenabled)
        # safemode - make sure you have to restart to disable
        self.mw.config.WriteInt("SafeMode", self.safemode.GetValue())
        if self.safemode.GetValue():
            wx.GetApp().SAFEMODE=True
        wx.GetApp().ApplySafeMode()
        # check for update rate
        self.mw.config.Write('updaterate', self.updatebox.GetValue())
        # startup option
        self.mw.config.WriteInt('startwithtoday', self.startup.GetValue())
        # Task Bar Icon option
        if self.taskbaricon:
            self.mw.config.WriteInt('taskbaricon', self.taskbaricon.GetValue())
        else:
            self.mw.config.WriteInt('taskbaricon', 0)
        # startup autodetect option
        self.mw.config.WriteInt('autodetectstart', self.autodetect_start.GetValue())
        # ensure config is saved
        self.mw.config.Flush()
        self.mw.EnsureDatabase(path, oldpath)
        # update the status bar
        self.mw.SetPhoneModelStatus()
        # update the cache path
        self.mw.update_cache_path()

    def _fixup(self, path):
        # os.path.join screws up adding root directory of a drive to
        # a directory.  eg join("c:\", "foo") gives "c:\\foo" whch
        # is invalid.  This function fixes that
        if len(path)>=3:
            if path[1]==':' and path[2]=='\\' and path[3]=='\\':
                return path[0:2]+path[3:]
        return path
        
    def needconfig(self):
        # Set base config
        self.setfromconfig()
        # do we know the phone?
        if self.mw.config.Read("phonetype", "") not in self.phonemodels:
            return True
        # are any at unknown settings
        if self.commbox.GetValue()==self.setme:
            # fill in and set defaults
            self.setdefaults()
            self.updatevariables()
            # any still unset?
            if self.commbox.GetValue()==self.setme:
                return True

        return False

    def ShowModal(self):
        self.setfromconfig()
        ec=wx.Dialog.ShowModal(self)
        if ec==wx.ID_OK:
            self.updatevariables()
        return ec

    def saveSize(self):
        save_size("ConfigDialog", self.GetRect())

###
### The select a comm port dialog box
###

class CommPortDialog(wx.Dialog):
    ID_LISTBOX=1
    ID_TEXTBOX=2
    ID_REFRESH=3
    ID_SASH=4
    ID_SAVE=5
    
    def __init__(self, parent, selectedphone, id=-1, title="Choose a comm port", defaultport="auto", sashposition=0):
        wx.Dialog.__init__(self, parent, id, title, style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.parent=parent
        self.port=defaultport
        self.sashposition=sashposition
        self.selectedphone=selectedphone
        
        p=self # parent widget

        # the listbox and textbox in a splitter
        splitter=wx.SplitterWindow(p, self.ID_SASH, style=wx.SP_3D|wx.SP_LIVE_UPDATE)
        self.lb=wx.ListBox(splitter, self.ID_LISTBOX, style=wx.LB_SINGLE|wx.LB_HSCROLL|wx.LB_NEEDED_SB)
        self.tb=wx.html.HtmlWindow(splitter, self.ID_TEXTBOX, size=wx.Size(400,400)) # default style is auto scrollbar
        splitter.SplitHorizontally(self.lb, self.tb, sashposition)

        # the buttons
        buttsizer=wx.GridSizer(1, 5)
        buttsizer.Add(wx.Button(p, wx.ID_OK, "OK"), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(p, self.ID_REFRESH, "Refresh"), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(p, self.ID_SAVE, "Save..."), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(p, wx.ID_HELP, "Help"), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(p, wx.ID_CANCEL, "Cancel"), 0, wx.ALL, 10)

        # vertical join of the two
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(splitter, 1, wx.EXPAND)
        vbs.Add(buttsizer, 0, wx.CENTER)

        # hook into self
        p.SetSizer(vbs)
        p.SetAutoLayout(True)
        vbs.Fit(p)

        # update dialog
        wx.CallAfter(self.OnRefresh)

        # hook in all the widgets
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnCancel)
        wx.EVT_BUTTON(self, wx.ID_HELP, self.OnHelp)
        wx.EVT_BUTTON(self, self.ID_REFRESH, self.OnRefresh)
        wx.EVT_BUTTON(self, self.ID_SAVE, self.OnSave)
        wx.EVT_BUTTON(self, wx.ID_OK, self.OnOk)
        wx.EVT_LISTBOX(self, self.ID_LISTBOX, self.OnListBox)
        wx.EVT_LISTBOX_DCLICK(self, self.ID_LISTBOX, self.OnListBox)
        wx.EVT_SPLITTER_SASH_POS_CHANGED(self, self.ID_SASH, self.OnSashChange)

        # Retrieve saved settings... Use 40% of screen if not specified
        set_size("CommDialog", self, screenpct=60)
        wx.EVT_CLOSE(self, self.OnClose)

    def OnSashChange(self, _=None):
        self.sashposition=self.FindWindowById(self.ID_SASH).GetSashPosition()

    def OnRefresh(self, _=None):
        self.tb.SetPage("<p><b>Refreshing</b> ...")
        self.lb.Clear()
        self.Update()
        ports=comscan.comscan()+usbscan.usbscan()
        if bitflingscan.IsBitFlingEnabled():
            ports=ports+bitflingscan.flinger.scan()
        self.portinfo=comdiagnose.diagnose(ports, self.selectedphone)
        if len(self.portinfo):
            self.portinfo=[ ("Automatic", "auto",
                             "<p>BitPim will try to detect the correct port automatically when accessing your phone"
                             ) ]+\
                           self.portinfo
        self.lb.Clear()
        sel=-1
        for name, actual, description in self.portinfo:
            if sel<0 and self.GetPort()==actual:
                sel=self.lb.GetCount()
            self.lb.Append(name)
        if sel<0:
            sel=0
        if self.lb.GetCount():
            self.lb.SetSelection(sel)
            self.OnListBox()
        else:
            self.FindWindowById(wx.ID_OK).Enable(False)
            self.tb.SetPage("<html><body>You do not have any com/serial ports on your system</body></html>")

    def OnListBox(self, _=None):
        # enable/disable ok button
        p=self.portinfo[self.lb.GetSelection()]
        if p[1] is None:
            self.FindWindowById(wx.ID_OK).Enable(False)
        else:
            self.port=p[1]
            self.FindWindowById(wx.ID_OK).Enable(True)
        self.tb.SetPage(p[2])
        

    def OnSave(self, _):
        html=StringIO.StringIO()
        
        print >>html, "<html><head><title>BitPim port listing - %s</title></head>" % (time.ctime(), )
        print >>html, "<body><h1>BitPim port listing - %s</h1><table>" % (time.ctime(),)

        for long,actual,desc in self.portinfo:
            if actual is None or actual=="auto": continue
            print >>html, '<tr  bgcolor="#77ff77"><td colspan=2>%s</td><td>%s</td></tr>' % (long,actual)
            print >>html, "<tr><td colspan=3>%s</td></tr>" % (desc,)
            print >>html, "<tr><td colspan=3><hr></td></tr>"
        print >>html, "</table></body></html>"
        dlg=wx.FileDialog(self, "Save port details as", defaultFile="bitpim-ports.html", wildcard="HTML files (*.html)|*.html",
                         style=wx.SAVE|wx.OVERWRITE_PROMPT|wx.CHANGE_DIR)
        if dlg.ShowModal()==wx.ID_OK:
            open(dlg.GetPath(), "wt").write(html.getvalue())
        dlg.Destroy()

    def OnCancel(self, _):
        self.saveSize()
        self.EndModal(wx.ID_CANCEL)

    def OnOk(self, _):
        self.saveSize()
        self.EndModal(wx.ID_OK)

    def OnHelp(self, _):
        wx.GetApp().displayhelpid(helpids.ID_COMMSETTINGS_DIALOG)

    def OnClose(self, evt):
        self.saveSize()
        # Don't destroy the dialong, just put it away...
        self.EndModal(wx.ID_CANCEL)

    def GetPort(self):
        return self.port

    def saveSize(self):
        save_size("CommDialog", self.GetRect())

###
###  Accept certificate dialog
###


class AcceptCertificateDialog(wx.Dialog):

    def __init__(self, parent, config, addr, fingerprint, q):
        parent=self.FindAGoodParent(parent)
        wx.Dialog.__init__(self, parent, -1, "Accept certificate?", style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.config=config
        self.q=q
        self.addr=addr
        self.fingerprint=fingerprint
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticText(self, -1, "Host:"), 0, wx.ALL, 5)
        hbs.Add(wx.StaticText(self, -1, addr[0]), 0, wx.ALL, 5)
        hbs.Add(wx.StaticText(self, -1, " Fingerprint:"), 0, wx.ALL, 5)
        hbs.Add(wx.StaticText(self, -1, fingerprint), 1, wx.ALL, 5)
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 7)
        but=self.CreateButtonSizer(wx.YES|wx.NO|wx.HELP)
        vbs.Add(but, 0, wx.ALIGN_CENTER|wx.ALL, 10)

        self.SetSizer(vbs)
        vbs.Fit(self)

        wx.EVT_BUTTON(self, wx.ID_YES, self.OnYes)
        wx.EVT_BUTTON(self, wx.ID_NO, self.OnNo)
        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.OnNo)



    def OnYes(self, _):
        wx.GetApp().config.Write("bitfling/certificates/%s" % (self.addr[0],), self.fingerprint)
        wx.GetApp().config.Flush()
        if self.IsModal():
            self.EndModal(wx.ID_YES)
        else:
            self.Show(False)
        wx.CallAfter(self.Destroy)
        print "returning true from AcceptCertificateDialog"
        self.q.put( (True, None) )

    def OnNo(self, _):
        if self.IsModal():
            self.EndModal(wx.ID_NO)
        else:
            self.Show(False)
        wx.CallAfter(self.Destroy)
        print "returning false from AcceptCertificateDialog"
        self.q.put( (False, None) )

    def FindAGoodParent(self, suggestion):
        win=wx.Window_FindFocus()
        while win is not None:
            try:
                if win.IsModal():
                    print "FindAGoodParent is",win
                    return win
            except AttributeError:
                parent=win.GetParent()
                win=parent
        return suggestion
        
###
###  BitFling settings dialog
###

class BitFlingSettingsDialog(wx.Dialog):

    ID_USERNAME=wx.NewId()
    ID_PASSWORD=wx.NewId()
    ID_HOST=wx.NewId()
    ID_PORT=wx.NewId()
    ID_TEST=wx.NewId()
    passwordsentinel="@+_-3@<,"

    def __init__(self, parent, config):
        wx.Dialog.__init__(self, parent, -1, "Edit BitFling settings", style=wx.CAPTION|wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.config=config
        gs=wx.FlexGridSizer(1, 2, 5, 5)
        gs.AddGrowableCol(1)
        gs.AddMany([
            (wx.StaticText(self, -1, "Username"), 0, wx.ALIGN_CENTER_VERTICAL),
            (wx.TextCtrl(self, self.ID_USERNAME), 1, wx.EXPAND),
            (wx.StaticText(self, -1, "Password"), 0, wx.ALIGN_CENTER_VERTICAL),
            (wx.TextCtrl(self, self.ID_PASSWORD, style=wx.TE_PASSWORD), 1, wx.EXPAND),
            (wx.StaticText(self, -1, "Host"), 0, wx.ALIGN_CENTER_VERTICAL),
            (wx.TextCtrl(self, self.ID_HOST), 1, wx.EXPAND),
            (wx.StaticText(self, -1, "Port"), 0, wx.ALIGN_CENTER_VERTICAL),
            (wx.lib.intctrl.IntCtrl(self, self.ID_PORT, value=12652, min=1, max=65535), 0)
            ])
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(gs, 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add((1,1), 1, wx.EXPAND)
        vbs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 10)

        gs=wx.GridSizer(1,4, 5,5)
        gs.Add(wx.Button(self, wx.ID_OK, "OK"))
        gs.Add(wx.Button(self, self.ID_TEST, "Test"))
        gs.Add(wx.Button(self, wx.ID_HELP, "Help"))
        gs.Add(wx.Button(self, wx.ID_CANCEL, "Cancel"))
        vbs.Add(gs, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        self.SetSizer(vbs)
        vbs.Fit(self)
        set_size("BitFlingConfigDialog", self, -20, 0.5)

        # event handlers
        wx.EVT_BUTTON(self, self.ID_TEST, self.OnTest)

        # fill in data
        defaultuser="user"
        try:
            defaultuser=getpass.getuser()
        except:
            pass
        self.FindWindowById(self.ID_USERNAME).SetValue(config.Read("bitfling/username", defaultuser))
        if len(config.Read("bitfling/password", "")):
            self.FindWindowById(self.ID_PASSWORD).SetValue(self.passwordsentinel)
        self.FindWindowById(self.ID_HOST).SetValue(config.Read("bitfling/host", ""))
        self.FindWindowById(self.ID_PORT).SetValue(config.ReadInt("bitfling/port", 12652))

    def ShowModal(self):
        res=wx.Dialog.ShowModal(self)
        save_size("BitFlingConfigDialog", self.GetRect())
        return res

    def GetSettings(self):
        username=self.FindWindowById(self.ID_USERNAME).GetValue()
        pwd=self.FindWindowById(self.ID_PASSWORD).GetValue()
        if pwd==self.passwordsentinel:
            pwd=bitflingscan.decode(self.config.Read("bitfling/password", self.passwordsentinel))
        host=self.FindWindowById(self.ID_HOST).GetValue()
        port=self.FindWindowById(self.ID_PORT).GetValue()
        return username, pwd, host, port

    def SaveSettings(self):
        "Copy settings from dialog fields into config object"
        username,pwd,host,port=self.GetSettings()
        self.config.Write("bitfling/username", username)
        self.config.Write("bitfling/password", bitflingscan.encode(pwd))
        self.config.Write("bitfling/host", host)
        self.config.WriteInt("bitfling/port", port)

    def OnTest(self, _):
        wx.CallAfter(self._OnTest)

    def _OnTest(self, _=None):
        try:
            bitflingscan.flinger.configure(*self.GetSettings())
            res=bitflingscan.flinger.getversion()
            dlg=wx.MessageDialog(self, "Succeeded. Remote version is %s" % (res,) , "Success", wx.OK|wx.ICON_INFORMATION)
            dlg.ShowModal()
            dlg.Destroy()
        except Exception,ex:
            res="Failed: %s: %s" % sys.exc_info()[:2]
            if hasattr(ex, "gui_exc_info"):
                print common.formatexception( ex.gui_exc_info)
            else:
                print common.formatexception()
            dlg=wx.MessageDialog(self, res, "Failed", wx.OK|wx.ICON_ERROR)
            dlg.ShowModal()
            dlg.Destroy()

###
### File viewer
###
media_codec=phone_media_codec.codec_name
class MyFileDropTarget(wx.FileDropTarget):
    def __init__(self, target, drag_over=False, enter_leave=False):
        wx.FileDropTarget.__init__(self)
        self.target=target
        self.drag_over=drag_over
        self.enter_leave=enter_leave
        
    def OnDropFiles(self, x, y, filenames):
        return self.target.OnDropFiles(x,y,filenames)

    def OnDragOver(self, x, y, d):
        if self.drag_over:
            return self.target.OnDragOver(x,y,d)
        return wx.FileDropTarget.base_OnDragOver(self, x, y, d)

    def OnEnter(self, x, y, d):
        if self.enter_leave:
            return self.target.OnEnter(x,y,d)
        return wx.FileDropTarget.base_OnEnter(self, x, y, d)

    def OnLeave(self):
        if self.enter_leave:
            return self.target.OnLeave()
        return wx.FileDropTarget.base_OnLeave(self)

class FileView(wx.Panel):

    # Various DC objects used for drawing the items.  We have to calculate them in the constructor as
    # the app object hasn't been constructed when this file is imported.
    item_selection_brush=None
    item_selection_pen=None
    item_line_font=None
    item_term="..."
    item_guardspace=None
    # Files we should ignore
    skiplist= ( 'desktop.ini', 'thumbs.db', 'zbthumbnail.info' )

    # how much data do we want in call to getdata
    NONE=0
    SELECTED=1
    ALL=2

    # maximum length of a filename
    maxlen=-1  # set via phone profile
    # acceptable characters in a filename
    filenamechars=None # set via phone profile
    # lisf of available origins that can be set
    origin_list=()

    def __init__(self, mainwindow, parent, watermark=None):
        wx.Panel.__init__(self,parent,style=wx.CLIP_CHILDREN)

        if not hasattr(self, "organizemenu"):
            self.organizemenu=None
        
        # item attributes
        if self.item_selection_brush is None:
            self.item_selection_brush=wx.TheBrushList.FindOrCreateBrush("MEDIUMPURPLE2", wx.SOLID)
            self.item_selection_pen=wx.ThePenList.FindOrCreatePen("MEDIUMPURPLE2", 1, wx.SOLID)
            f1=wx.TheFontList.FindOrCreateFont(10, wx.SWISS, wx.NORMAL, wx.BOLD)
            f2=wx.TheFontList.FindOrCreateFont(10, wx.SWISS, wx.NORMAL, wx.NORMAL)
            self.item_line_font=[f1, f2, f2, f2]
            dc=wx.MemoryDC()
            dc.SelectObject(wx.EmptyBitmap(100,100))
            self.item_guardspace=dc.GetTextExtent(self.item_term)[0]
            del dc

        # no redraw ickiness
        # wx.EVT_ERASE_BACKGROUND(self, lambda evt: None)
        
        self.mainwindow=mainwindow
        self.thedir=None
        self.wildcard="I forgot to set wildcard in derived class|*"
        self.__dragging=False
        self._in_context_menu=False

        # use the aggregatedisplay to do the actual item display
        self.aggdisp=aggregatedisplay.Display(self, self, watermark) # we are our own datasource
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(self.aggdisp, 1, wx.EXPAND|wx.ALL, 2)
        self.SetSizer(vbs)
        timerid=wx.NewId()
        self.thetimer=wx.Timer(self, timerid)
        wx.EVT_TIMER(self, timerid, self.OnTooltipTimer)
        self.motionpos=None
        wx.EVT_MOUSE_EVENTS(self.aggdisp, self.OnMouseEvent)
        self.tipwindow=None
        if guihelper.IsMSWindows():
            # turn on drag-and-drag for windows
            wx.EVT_MOTION(self.aggdisp, self.OnStartDrag)

        # Menus

        self.itemmenu=wx.Menu()
        self.itemmenu.Append(guihelper.ID_FV_OPEN, "Open")
        self.itemmenu.Append(guihelper.ID_FV_SAVE, "Save ...")
        self.itemmenu.AppendSeparator()
        if guihelper.IsMSWindows():
            self.itemmenu.Append(guihelper.ID_FV_COPY, "Copy")
        self.itemmenu.Append(guihelper.ID_FV_DELETE, "Delete")
        self.itemmenu.Append(guihelper.ID_FV_RENAME, "Rename")
        self.itemmenu.AppendSeparator()
        # set origin menu
        if self.origin_list:
            _origin_menu=wx.Menu()
            for o in self.origin_list:
                _id=wx.NewId()
                _origin_menu.Append(_id, o)
                wx.EVT_MENU(self, _id, self.OnSetOrigin)
            self._origin_menu_id=wx.NewId()
            self.itemmenu.AppendMenu(self._origin_menu_id,
                                     'Set Origin', _origin_menu)
            self.itemmenu.AppendSeparator()
        else:
            self._origin_menu_id=None
        # self.itemmenu.Append(guihelper.ID_FV_RENAME, "Rename")
        self.itemmenu.Append(guihelper.ID_FV_REFRESH, "Refresh")

        self.bgmenu=wx.Menu()
        if self.organizemenu is not None:
            self.bgmenu.AppendMenu(wx.NewId(), "Organize by", self.organizemenu)
        self.bgmenu.Append(guihelper.ID_FV_ADD, "Add ...")
        self.bgmenu.Append(guihelper.ID_FV_PASTE, "Paste")
        self.bgmenu.Append(guihelper.ID_FV_REFRESH, "Refresh")

        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_OPEN, self.OnLaunch)
        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_SAVE, self.OnSave)
        if guihelper.IsMSWindows():
            wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_COPY, self.OnCopy)
        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_DELETE, self.OnDelete)
        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_RENAME, self.OnRename)
        wx.EVT_MENU(self.itemmenu, guihelper.ID_FV_REFRESH, lambda evt: self.OnRefresh())
        wx.EVT_MENU(self.bgmenu, guihelper.ID_FV_ADD, self.OnAdd)
        wx.EVT_MENU(self.bgmenu, guihelper.ID_FV_PASTE, self.OnPaste)
        wx.EVT_MENU(self.bgmenu, guihelper.ID_FV_REFRESH, lambda evt: self.OnRefresh)

        wx.EVT_RIGHT_UP(self.aggdisp, self.OnRightClick)
        aggregatedisplay.EVT_ACTIVATE(self.aggdisp, self.aggdisp.GetId(), self.OnLaunch)

        self.droptarget=MyFileDropTarget(self)
        self.SetDropTarget(self.droptarget)

    def OnRightClick(self, evt):
        """Popup the right click context menu

        @param widget:  which widget to popup in
        @param position:  position in widget
        @param onitem: True if the context menu is for an item
        """
        if len(self.aggdisp.GetSelection()):
            menu=self.itemmenu
            item=self.GetSelectedItems()[0]
            menu.Enable(guihelper.ID_FV_RENAME, len(self.GetSelectedItems())==1)
            # we always launch on mac
            if not guihelper.IsMac():
                menu.FindItemById(guihelper.ID_FV_OPEN).Enable(guihelper.GetOpenCommand(item.fileinfo.mimetypes, item.filename) is not None)
            # check for set origin menu item
            if self._origin_menu_id:
                menu.Enable(self._origin_menu_id,
                            bool(len(self.GetSelectedItems())==1 and \
                            item.origin is None))
        else:
            menu=self.bgmenu
            menu.Enable(guihelper.ID_FV_PASTE, self.CanPaste())
        if menu is None:
            return
        # we're putting up the context menu, quit the tool tip timer.
        self._in_context_menu=True
        self.aggdisp.PopupMenu(menu, evt.GetPosition())
        self._in_context_menu=False

    def OnLaunch(self, _):
        item=self.GetSelectedItems()[0]
        if guihelper.IsMac():
            import findertools
            findertools.launch(item.filename)
            return
        cmd=guihelper.GetOpenCommand(item.fileinfo.mimetypes, item.filename)
        if cmd is None:
            wx.Bell()
        else:
            wx.Execute(cmd, wx.EXEC_ASYNC)

    if guihelper.IsMSWindows():
        # drag-and-drop files only works in Windows
        def OnStartDrag(self, evt):
            evt.Skip()
            if not evt.LeftIsDown():
                return
            items=self.GetSelectedItems()
            if not len(items):
                return
            drag_source=wx.DropSource(self)
            file_names=wx.FileDataObject()
            for item in items:
                file_names.AddFile(item.filename)
            drag_source.SetData(file_names)
            self.__dragging=True
            res=drag_source.DoDragDrop(wx.Drag_AllowMove)
            self.__dragging=False
            # check of any of the files have been removed,
            # can't trust result returned by DoDragDrop
            for item in items:
                # this used to use os.access function, but it does not
                # support unicode filenames
                if not os.path.isfile(item.filename):
                    item.RemoveFromIndex()

    def OnMouseEvent(self, evt):
        self.motionpos=evt.GetPosition()
        evt.Skip()
        self.thetimer.Stop()
        if evt.AltDown() or evt.MetaDown() or evt.ControlDown() or \
           evt.ShiftDown() or evt.Dragging() or evt.IsButton() or \
           self._in_context_menu:
            return
        self.thetimer.Start(1750, wx.TIMER_ONE_SHOT)

    def OnTooltipTimer(self, _):
        if self._in_context_menu:
            # we're putting up a context menu, forget this
            return
        x,y=self.aggdisp.CalcUnscrolledPosition(*self.motionpos)
        res=self.aggdisp.HitTest(x,y)
        if res.item is not None:
            try:    self.tipwindow.Destroy()
            except: pass
            self.tipwindow=res.item.DisplayTooltip(self.aggdisp, res.itemrectscrolled)

    def OnRefresh(self):
        self.aggdisp.UpdateItems()

    def GetSelectedItems(self):
        return [item for _,_,_,item in self.aggdisp.GetSelection()]

    def GetAllItems(self):
        return [item for _,_,_,item in self.aggdisp.GetAllItems()]

    def OnSelectAll(self, _):
        self.aggdisp.SelectAll()

    def EndSelectedFilesContext(self, context, deleteitems=False):
        # We have a fun additional problem.  By default Windows
        # returns a code that it is copying, when in fact it is
        # moving.  Consequently we do a delete if either the
        # source file is gone, or deleteitems is true
        if not deleteitems:
            for item in context:
                if not os.path.exists(item.filename):
                    print "Forcing EndSelectedFilesContext to delete mode even though not specified"
                    deleteitems=True
                    break
        if deleteitems:
            for item in context:
                if os.path.exists(item.filename):
                    os.remove(item.filename)
            for item in context:
                item.RemoveFromIndex()
            self.OnRefresh()

    def OnSave(self, _):
        # If one item is selected we ask for a filename to save.  If
        # multiple then we ask for a directory, and users don't get
        # the choice to affect the names of files.  Note that we don't
        # allow users to select a different format for the file - we
        # just copy it as is.
        items=self.GetSelectedItems()
        if len(items)==1:
            ext=getext(items[0].name)
            if ext=="": ext="*"
            else: ext="*."+ext
            dlg=wx.FileDialog(self, "Save item", wildcard=ext, defaultFile=items[0].name, style=wx.SAVE|wx.OVERWRITE_PROMPT|wx.CHANGE_DIR)
            if dlg.ShowModal()==wx.ID_OK:
                shutil.copyfile(items[0].filename, dlg.GetPath())
            dlg.Destroy()
        else:
            dlg=wx.DirDialog(self, "Save items to", style=wx.DD_DEFAULT_STYLE|wx.DD_NEW_DIR_BUTTON)
            if dlg.ShowModal()==wx.ID_OK:
                for item in items:
                    shutil.copyfile(item.filename, os.path.join(dlg.GetPath(), basename(item.filename)))
            dlg.Destroy()

    if guihelper.IsMSWindows():
        def OnCopy(self, _):
            items=self.GetSelectedItems()
            if not len(items):
                # nothing selected
                return
            file_names=wx.FileDataObject()
            for item in items:
                file_names.AddFile(item.filename)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(file_names)
                wx.TheClipboard.Close()
        def CanCopy(self):
            return len(self.GetSelectedItems())

    def OnPaste(self, _=None):
        if not wx.TheClipboard.Open():
            # can't access the clipboard
            return
        if wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME)):
            file_names=wx.FileDataObject()
            has_data=wx.TheClipboard.GetData(file_names)
        else:
            has_data=False
        wx.TheClipboard.Close()
        if has_data:
            self.OnAddFiles(file_names.GetFilenames())
    def CanPaste(self):
        """ Return True if can accept clipboard data, False otherwise
        """
        if not wx.TheClipboard.Open():
            return False
        r=wx.TheClipboard.IsSupported(wx.DataFormat(wx.DF_FILENAME))
        wx.TheClipboard.Close()
        return r

    def OnDelete(self,_):
        items=self.GetSelectedItems()
        for item in items:
            os.remove(item.filename)
        for item in items:
            item.RemoveFromIndex()
        self.OnRefresh()

    def OnSetOrigin(self, evt):
        _origin=evt.GetEventObject().GetLabel(evt.GetId())
        _items=self.GetSelectedItems()
        for _item in _items:
            _item.SetOrigin(_origin)
        self.OnRefresh()

    def genericpopulatefs(self, dict, key, indexkey, version):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")

        # delete all files we don't know about if 'key' contains replacements
        if dict.has_key(key):
            print key,"present - updating disk"
            for f in os.listdir(self.thedir):
                # delete them all except windows magic ones which we ignore
                if f.lower() not in self.skiplist:
                    os.remove(os.path.join(self.thedir, f))

            d=dict[key]
            for i in d:
                open(os.path.join(self.thedir, i.encode(media_codec)), "wb").write(d[i])
        d={}
        d[indexkey]=dict[indexkey]
        common.writeversionindexfile(os.path.join(self.thedir, "index.idx"), d, version)
        return dict

    def genericgetfromfs(self, result, key, indexkey, currentversion):
        try:
            os.makedirs(self.thedir)
        except:
            pass
        if not os.path.isdir(self.thedir):
            raise Exception("Bad directory for "+key+" '"+self.thedir+"'")
        dict={}
        for file in os.listdir(self.thedir):
            if file=='index.idx':
                d={}
                d['result']={}
                common.readversionedindexfile(os.path.join(self.thedir, file), d, self.versionupgrade, currentversion)
                result.update(d['result'])
            elif file.lower() in self.skiplist:
                # ignore windows detritus
                continue
            elif key is not None:
                dict[file.decode(media_codec)]=open(os.path.join(self.thedir, file), "rb").read()
        if key is not None:
            result[key]=dict
        if indexkey not in result:
            result[indexkey]={}
        return result

    def OnDropFiles(self, _, dummy, filenames):
        # There is a bug in that the most recently created tab
        # in the notebook that accepts filedrop receives these
        # files, not the most visible one.  We find the currently
        # viewed tab in the notebook and send the files there
        if self.__dragging:
            # I'm the drag source, forget 'bout it !
            return
        target=self # fallback
        t=self.mainwindow.nb.GetPage(self.mainwindow.nb.GetSelection())
        if isinstance(t, FileView):
            # changing target in dragndrop
            target=t
        target.OnAddFiles(filenames)

    def OnAdd(self, _=None):
        dlg=wx.FileDialog(self, "Choose files", style=wx.OPEN|wx.MULTIPLE, wildcard=self.wildcard)
        if dlg.ShowModal()==wx.ID_OK:
            self.OnAddFiles(dlg.GetPaths())
        dlg.Destroy()

    def CanRename(self):
        return len(self.GetSelectedItems())==1
    # subclass needs to define this
    media_notification_type=None
    def OnRename(self, _=None):
        items=self.GetSelectedItems()
        if len(items)!=1:
               # either none or more than 1 items selected
               return
        old_name=items[0].name
        dlg=wx.TextEntryDialog(self, "Enter a new name:", "Item Rename",
                               old_name)
        if dlg.ShowModal()==wx.ID_OK:
            new_name=dlg.GetValue()
            if len(new_name) and new_name!=old_name:
                old_file_name=items[0].filename
                new_file_name=self.getshortenedbasename(new_name)
                try:
                    os.rename(old_file_name, new_file_name)
                    items[0].RenameInIndex(os.path.basename(
                        str(new_file_name).decode(media_codec)))
                    pubsub.publish(pubsub.MEDIA_NAME_CHANGED,
                                   data={ pubsub.media_change_type: self.media_notification_type,
                                          pubsub.media_old_name: old_file_name,
                                          pubsub.media_new_name: new_file_name })
                except:
                    pass
        dlg.Destroy()
          
    def OnAddFiles(self,_):
        raise Exception("not implemented")

    def decodefilename(self, filename):
        path,filename=os.path.split(filename)
        decoded_file=str(filename).decode(media_codec)
        return os.path.join(path, decoded_file)

    def getshortenedbasename(self, filename, newext=''):
        filename=basename(filename)
        if not 'A' in self.filenamechars:
            filename=filename.lower()
        if not 'a' in self.filenamechars:
            filename=filename.upper()
        if len(newext):
            filename=stripext(filename)
        filename="".join([x for x in filename if x in self.filenamechars])
        filename=filename.replace("  "," ").replace("  ", " ")  # remove double spaces
        if len(newext):
            filename+='.'+newext
        if len(filename)>self.maxlen:
            chop=len(filename)-self.maxlen
            filename=stripext(filename)[:-chop].strip()+'.'+getext(filename)
        return os.path.join(self.thedir, filename.encode(media_codec))

    def genericgetdata(self,dict,want, mediapath, mediakey, mediaindexkey):
        # this was originally written for wallpaper hence using the 'wp' variable
        dict.update(self._data)
        items=None
        if want==self.SELECTED:
            items=self.GetSelectedItems()
            if len(items)==0:
                want=self.ALL

        if want==self.ALL:
            items=self.GetAllItems()

        if items is not None:
            wp={}
            i=0
            for item in items:
                data=open(item.filename, "rb").read()
                wp[i]={'name': item.name, 'data': data}
                v=item.origin
                if v is not None:
                    wp[i]['origin']=v
                i+=1
            dict[mediakey]=wp
                
        return dict

    def log(self, log_str):
        self.mainwindow.log(log_str)

class FileViewDisplayItem(object):

    datakey="Someone forgot to set me"
    PADDING=3

    def __init__(self, view, key, mediapath):
        self.view=view
        self.key=key
        self.thumbsize=10,10
        self.mediapath=mediapath
        self.setvals()
        self.lastw=None

    def setvals(self):
        me=self.view._data[self.datakey][self.key]
        self.name=me['name']
        self.origin=me.get('origin', None)
        self.filename=os.path.join(self.mediapath, self.name.encode(media_codec))
        self.fileinfo=self.view.GetFileInfo(self.filename)
        self.size=self.fileinfo.size
        self.short=self.fileinfo.shortdescription()
        self.long=self.fileinfo.longdescription()
        self.thumb=None
        self.selbbox=None
        self.lines=[self.name, self.short,
                    '%.1f kb' % (self.size/1024.0,)]
        if self.origin:
            self.lines.append(self.origin)

    def setthumbnailsize(self, thumbnailsize):
        self.thumbnailsize=thumbnailsize
        self.thumb=None
        self.selbox=None

    def Draw(self, dc, width, height, selected):
        if self.thumb is None:
            self.thumb=self.view.GetItemThumbnail(self.name, self.thumbnailsize[0], self.thumbnailsize[1])
        redrawbbox=False
        if selected:
            if self.lastw!=width or self.selbbox is None:
                redrawbbox=True
            else:
                oldb=dc.GetBrush()
                oldp=dc.GetPen()
                dc.SetBrush(self.view.item_selection_brush)
                dc.SetPen(self.view.item_selection_pen)
                dc.DrawRectangle(*self.selbbox)
                dc.SetBrush(oldb)
                dc.SetPen(oldp)
        dc.DrawBitmap(self.thumb, self.PADDING+self.thumbnailsize[0]/2-self.thumb.GetWidth()/2, self.PADDING, True)
        xoff=self.PADDING+self.thumbnailsize[0]+self.PADDING
        yoff=self.PADDING*2
        widthavailable=width-xoff-self.PADDING
        maxw=0
        old=dc.GetFont()
        for i,line in enumerate(self.lines):
            dc.SetFont(self.view.item_line_font[i])
            w,h=DrawTextWithLimit(dc, xoff, yoff, line, widthavailable, self.view.item_guardspace, self.view.item_term)
            maxw=max(maxw,w)
            yoff+=h
        dc.SetFont(old)
        self.lastw=width
        self.selbbox=(0,0,xoff+maxw+self.PADDING,max(yoff+self.PADDING,self.thumb.GetHeight()+self.PADDING*2))
        if redrawbbox:
            return self.Draw(dc, width, height, selected)
        return self.selbbox

    def DisplayTooltip(self, parent, rect):
        res=["Name: "+self.name, "Origin: "+(self.origin, "default")[self.origin is None],
             'File size: %.1f kb (%d bytes)' % (self.size/1024.0, self.size), "\n"+self.datatype+" information:\n", self.long]
        # tipwindow takes screen coordinates so we have to transform
        x,y=parent.ClientToScreen(rect[0:2])
        return wx.TipWindow(parent, "\n".join(res), 1024, wx.Rect(x,y,rect[2], rect[3]))

    def RemoveFromIndex(self):
        del self.view._data[self.datakey][self.key]
        self.view.modified=True
        self.view.OnRefresh()

    def RenameInIndex(self, new_name):
        self.view._data[self.datakey][self.key]['name']=new_name
        self.view.modified=True
        self.view.OnRefresh()

    def SetOrigin(self, new_origin):
        # set the origin of this item
        self.view._data[self.datakey][self.key]['origin']=new_origin
        self.view.modified=True
        self.view.OnRefresh()

###
### Various platform independent filename functions
###

basename=common.basename
stripext=common.stripext
getext=common.getext


###
### A dialog showing a message in a fixed font, with a help button
###

class MyFixedScrolledMessageDialog(wx.Dialog):
    """A dialog displaying a readonly text control with a fixed width font"""
    def __init__(self, parent, msg, caption, helpid, pos = wx.DefaultPosition, size = (850,600)):
        wx.Dialog.__init__(self, parent, -1, caption, pos, size, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        text=wx.TextCtrl(self, 1,
                        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 |
                        wx.TE_DONTWRAP  )
        # Fixed width font
        f=wx.Font(10, wx.MODERN, wx.NORMAL, wx.NORMAL )
        ta=wx.TextAttr(font=f)
        text.SetDefaultStyle(ta)

        text.AppendText(msg) # if i supply this in constructor then the font doesn't take
        text.SetInsertionPoint(0)
        text.ShowPosition(text.XYToPosition(0,0))

        # vertical sizer
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(text, 1, wx.EXPAND|wx.ALL, 10)

        # buttons
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.HELP), 0, wx.ALIGN_RIGHT|wx.ALL, 10)

        # plumb
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        wx.EVT_BUTTON(self, wx.ID_HELP, lambda _,helpid=helpid: wx.GetApp().displayhelpid(helpid))

###
###  Dialog that deals with exceptions
###
import StringIO

class ExceptionDialog(wx.Dialog):
    def __init__(self, parent, exception, title="Exception"):
        wx.Dialog.__init__(self, parent, title=title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER|wx.THICK_FRAME|wx.MAXIMIZE_BOX, size=(740, 580))
        self.maintext=wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2|wx.HSCROLL)
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(self.maintext, 1, wx.EXPAND|wx.ALL, 5)

        buttsizer=wx.GridSizer(1, 3)
        buttsizer.Add(wx.Button(self, wx.ID_CANCEL, "Abort BitPim"), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(self, wx.ID_HELP, "Help"), 0, wx.ALL, 10)
        buttsizer.Add(wx.Button(self, wx.ID_OK, "Continue"), 0, wx.ALL, 10)

        vbs.Add(buttsizer, 0, wx.ALIGN_RIGHT|wx.ALL, 5)

        wx.EVT_BUTTON(self, wx.ID_CANCEL, self.abort)
        wx.EVT_BUTTON(self, wx.ID_HELP, lambda _: wx.GetApp().displayhelpid(helpids.ID_EXCEPTION_DIALOG))
        
        self.SetSizer(vbs)
        self._text=""
        self.addexception(exception)

    def abort(self,_):
        import os
        os._exit(1)
        
    def addexception(self, exception):
        s=StringIO.StringIO()
        s.write("BitPim version: "+version.versionstring+"-"+version.vendor+"\nAn unexpected exception has occurred.\nPlease see the help for details on what to do.\n\n")
        if hasattr(exception, 'gui_exc_info'):
            s.write(common.formatexception(exception.gui_exc_info))
        else:
            s.write("Exception with no extra info.\n%s\n" % (exception.str(),))
        self._text=s.getvalue()
        self.maintext.SetValue(self._text)
        
    def getexceptiontext(self):
        return self._text

###
###  Too much freaking effort for a simple statusbar.  Mostly copied from the demo.
###

class MyStatusBar(wx.StatusBar):
    __total_panes=3
    __version_index=2
    __phone_model_index=2
    __app_status_index=0
    __gauge_index=1
    __major_progress_index=2
    __minor_progress_index=2
    __help_str_index=2
    __general_pane=2
    __pane_width=[50, 180, -1]
    def __init__(self, parent, id=-1):
        wx.StatusBar.__init__(self, parent, id)
        self.__major_progress_text=self.__version_text=self.__phone_text=''
        self.sizechanged=False
        wx.EVT_SIZE(self, self.OnSize)
        wx.EVT_IDLE(self, self.OnIdle)
        self.gauge=wx.Gauge(self, 1000, 1)
        self.SetFieldsCount(self.__total_panes)
        self.SetStatusWidths(self.__pane_width)
        self.Reposition()

    def OnSize(self,_):
        self.sizechanged=True

    def OnIdle(self,_):
        if not len(self.GetStatusText(self.__general_pane)):
            self.__set_version_phone_text()
        if self.sizechanged:
            try:
                self.Reposition()
            except:
                # this works around a bug in wx (on Windows only)
                # where we get a bogus exception.  See SF bug
                # 873155 
                pass

    def Reposition(self):
        self.sizeChanged = False
        rect=self.GetFieldRect(self.__gauge_index)
        self.gauge.SetPosition(wx.Point(rect.x+2, rect.y+2))
        self.gauge.SetSize(wx.Size(rect.width-4, rect.height-4))

    def progressminor(self, pos, max, desc=""):
        self.gauge.SetRange(max)
        self.gauge.SetValue(pos)
        if len(self.__major_progress_text):
            s=self.__major_progress_text
            if len(desc):
                s+=' - '+desc
        else:
            s=desc
        self.SetStatusText(s, self.__minor_progress_index)

    def progressmajor(self, pos, max, desc=""):
        if len(desc) and max:
            self.__major_progress_text="%d/%d %s" % (pos+1, max, desc)
        else:
            self.__major_progress_text=desc
        self.progressminor(0,1)

    def GetHelpPane(self):
        return self.__help_str_index
    def set_app_status(self, str=''):
        self.SetStatusText(str, self.__app_status_index)
    def set_phone_model(self, str=''):
        self.__phone_text=str
        self.__set_version_phone_text()
    def set_versions(self, current, latest=''):
        s='BitPim '+current
        if len(latest):
            s+='/Latest '+latest
        else:
            s+='/Latest <Unknown>'
        self.__version_text=s
        self.__set_version_phone_text()
    def __set_version_phone_text(self):
        if guihelper.IsMac():
            s = self.__version_text+'         '+self.__phone_text
        else:
            s = self.__version_text+'\t'+self.__phone_text
        self.SetStatusText(s, self.__general_pane)

###
###  A MessageBox with a help button
###

class AlertDialogWithHelp(wx.Dialog):
    """A dialog box with Ok button and a help button"""
    def __init__(self, parent, message, caption, helpfn, style=wx.DEFAULT_DIALOG_STYLE, icon=wx.ICON_EXCLAMATION):
        wx.Dialog.__init__(self, parent, -1, caption, style=style|wx.DEFAULT_DIALOG_STYLE)

        p=self # parent widget

        # horiz sizer for bitmap and text
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticBitmap(p, -1, wx.ArtProvider_GetBitmap(self.icontoart(icon), wx.ART_MESSAGE_BOX)), 0, wx.CENTER|wx.ALL, 10)
        hbs.Add(wx.StaticText(p, -1, message), 1, wx.CENTER|wx.ALL, 10)

        # the buttons
        buttsizer=self.CreateButtonSizer(wx.HELP|style)

        # Both vertical
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 10)
        vbs.Add(buttsizer, 0, wx.CENTER|wx.ALL, 10)

        # wire it in
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

        wx.EVT_BUTTON(self, wx.ID_HELP, helpfn)

    def icontoart(self, id):
        if id&wx.ICON_EXCLAMATION:
            return wx.ART_WARNING
        if id&wx.ICON_INFORMATION:
            return wx.ART_INFORMATION
        # ::TODO:: rest of these
        # fallthru
        return wx.ART_INFORMATION

###
### Yet another dialog with user selectable buttons
###

class AnotherDialog(wx.Dialog):
    """A dialog box with user supplied buttons"""
    def __init__(self, parent, message, caption, buttons, helpfn=None,
                 style=wx.DEFAULT_DIALOG_STYLE, icon=wx.ICON_EXCLAMATION):
        """Constructor

        @param message:  Text displayed in body of dialog
        @param caption:  Title of dialog
        @param buttons:  A list of tuples.  Each tuple is a string and an integer id.
                         The result of calling ShowModal() is the id
        @param helpfn:  The function called if the user presses the help button (wx.ID_HELP)
        """
        wx.Dialog.__init__(self, parent, -1, caption, style=style)

        p=self # parent widget

        # horiz sizer for bitmap and text
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        hbs.Add(wx.StaticBitmap(p, -1, wx.ArtProvider_GetBitmap(self.icontoart(icon), wx.ART_MESSAGE_BOX)), 0, wx.CENTER|wx.ALL, 10)
        hbs.Add(wx.StaticText(p, -1, message), 1, wx.CENTER|wx.ALL, 10)

        # the buttons
        buttsizer=wx.BoxSizer(wx.HORIZONTAL)
        for label,id in buttons:
            buttsizer.Add( wx.Button(self, id, label), 0, wx.ALL|wx.ALIGN_CENTER, 5)
            if id!=wx.ID_HELP:
                wx.EVT_BUTTON(self, id, self.OnButton)
            else:
                wx.EVT_BUTTON(self, wx.ID_HELP, helpfn)
                
        # Both vertical
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 10)
        vbs.Add(buttsizer, 0, wx.CENTER|wx.ALL, 10)

        # wire it in
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def OnButton(self, event):
        self.EndModal(event.GetId())

    def icontoart(self, id):
        if id&wx.ICON_EXCLAMATION:
            return wx.ART_WARNING
        if id&wx.ICON_INFORMATION:
            return wx.ART_INFORMATION
        # ::TODO:: rest of these
        # fallthru
        return wx.ART_INFORMATION

###
### Utility code
###

def DrawTextWithLimit(dc, x, y, text, widthavailable, guardspace, term="..."):
    """Draws text and if it will overflow the width available, truncates and  puts ... at the end

    @param x: start position for text
    @param y: start position for text
    @param text: the string to draw
    @param widthavailable: the total amount of space available
    @param guardspace: if the text is longer than widthavailable then this amount of space is
             reclaimed from the right handside and term put there instead.  Consequently
             this value should be at least the width of term
    @param term: the string that is placed in the guardspace if it gets truncated.  Make sure guardspace
             is at least the width of this string!
    @returns: The extent of the text that was drawn in the end as a tuple of (width, height)
    """
    w,h=dc.GetTextExtent(text)
    if w<widthavailable:
        dc.DrawText(text,x,y)
        return w,h
    extents=dc.GetPartialTextExtents(text)
    limit=widthavailable-guardspace
    # find out how many chars in we have to go before hitting limit
    for i,offset in enumerate(extents):
        if offset>limit:
            break
    # back off 1 in case the new text's a tad long
    if i:
        i-=1
    text=text[:i]+term
    w,h=dc.GetTextExtent(text)
    assert w<=widthavailable
    dc.DrawText(text, x, y)
    return w,h
    
        

###
###  Window geometry/positioning memory
###


def set_size(confname, window, screenpct=50, aspect=1.0):
    """Sets remembered/calculated dimensions/position for window

    @param confname: subkey to store/get this windows's settings from
    @param window:  the window object itself
    @param screenpct: percentage of the screen the window should occupy.
             If this value is negative then the window will not be resized,
             only repositioned (unless the current size is silly)
    @param aspect:  aspect ratio.  If greater than one then it is
             how much wider than tall the window is, and if less
             than one then the other way round
    """
    confobj=wx.GetApp().config

    # frig confname
    confname="windows/"+confname

    # Get screen size, scale according to percentage supplied
    screenSize = wx.GetClientDisplayRect()
    if (aspect >= 1):
        newWidth = screenSize.width * abs(screenpct) / 100
        newHeight = screenSize.height * abs(screenpct) / aspect / 100
    else:
        newWidth = screenSize.width * abs(screenpct) * aspect / 100
        newHeight = screenSize.height * abs(screenpct) / 100

    if screenpct<=0:
        rs_width,rs_height=window.GetSizeTuple()
    else:
        # Retrieve values (if any) from config database for this config object
        rs_width  = confobj.ReadInt(confname + "/width", int(newWidth))
        rs_height = confobj.ReadInt(confname + "/height", int(newHeight))

    # suitable magic number to show not configured.  it is an exercise for the reader
    # why it isn't -65536 (hint: virtual desktops)
    unconfigured=-65245

    rs_x = confobj.ReadInt(confname + "/x", unconfigured)
    rs_y = confobj.ReadInt(confname + "/y", unconfigured)

    # Check for small window
    if rs_height < 96:
        rs_height = newHeight
    if rs_width < 96:
        rs_width = newWidth

    # Make sure window is no larger than about screen size
    #
    # determine ratio of original oversized window so we keep the ratio if we resize...
    rs_aspect = rs_width/rs_height
    if rs_aspect >= 1:
        if rs_width > screenSize.width:
            rs_width = screenSize.width
        if rs_height > (screenSize.height):
            rs_height = (screenSize.height / rs_aspect) - screenSize.y 
    else:
        if rs_width > screenSize.width:
            rs_width = screenSize.width * rs_aspect
        if rs_height > screenSize.height - screenSize.y:
            rs_height = screenSize.height - screenSize.y

    # Off the screen?  Just pull it back a little bit so it's visible....
    if rs_x!=unconfigured and rs_x > screenSize.width:
        rs_x = screenSize.width - 50
    if rs_x!=unconfigured and rs_x + rs_width < screenSize.x:
        rs_x = screenSize.x
    if rs_y!=unconfigured and rs_y > screenSize.height:
        rs_y = screenSize.height - 50
    if rs_y!=unconfigured and rs_y + rs_height < screenSize.y:
        rs_y = screenSize.y
        

    if screenpct<=0 and (rs_width,rs_height)==window.GetSizeTuple():
        # set position only, and no need to resize
        if rs_x!=unconfigured and rs_y!=unconfigured:
            print "setting %s to position %d, %d" % (confname, rs_x, rs_y)
            window.SetPosition(wx.Point(rs_x, rs_y))
    else:
        if rs_x==unconfigured or rs_y==unconfigured:
            print "setting %s to size %d x %d" % (confname, rs_width, rs_height)
            window.SetSize(wx.Size(rs_width, rs_height))
        else:
            print "setting %s to position %d, %d - size %d x %d" % (confname, rs_x, rs_y, rs_width, rs_height)
            window.SetDimensions(rs_x, rs_y, rs_width, rs_height)

def save_size(confname, myRect):
    """Saves size to config.  L{set_size}

    @param confname: Same string as in set_size
    @param myRect:  Window size you want remembered, typically window.GetRect()
    """
    confobj=wx.GetApp().config
    
    confname="windows/"+confname

    x = myRect.x
    y = myRect.y
    width = myRect.width
    height = myRect.height

    confobj.WriteInt(confname + "/x", x)
    confobj.WriteInt(confname + "/y", y)
    confobj.WriteInt(confname + "/width", width)
    confobj.WriteInt(confname + "/height", height)
    confobj.Flush()

class LogProgressDialog(wx.ProgressDialog):
    """ display log string and progress bar at the same time
    """
    def __init__(self, title, message, maximum=100, parent=None,
                 style=wx.PD_AUTO_HIDE|wx.PD_APP_MODAL):
        super(LogProgressDialog, self).__init__(title, message, maximum,
                                                parent, style)
        self.__progress_value=0
    def Update(self, value, newmsg='', skip=None):
        self.__progress_value=value
        super(LogProgressDialog, self).Update(value, newmsg, skip)
    def log(self, msgstr):
        super(LogProgressDialog, self).Update(self.__progress_value, msgstr)

class AskPhoneNameDialog(wx.Dialog):
    def __init__(self, parent, message, caption="Enter phone owner's name", style=wx.DEFAULT_DIALOG_STYLE):
        """ Ask a user to enter an owner's name of a phone.
        Similar to the wx.TextEntryDialog but has 3 buttons, Ok, No Thanks, and
        Maybe latter.
        """
        super(AskPhoneNameDialog, self).__init__(parent, -1, caption, style=style)
        vbs=wx.BoxSizer(wx.VERTICAL)
        vbs.Add(wx.StaticText(self, -1, message), 0, wx.ALL, 5)
        self.__text_ctrl=wx.TextCtrl(self, -1, style=wx.TE_PROCESS_ENTER)
        vbs.Add(self.__text_ctrl,  0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        ok_btn=wx.Button(self, wx.ID_OK, 'OK')
        hbs.Add(ok_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        cancel_btn=wx.Button(self, wx.ID_CANCEL, 'No Thanks')
        hbs.Add(cancel_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        maybe_btn=wx.Button(self, wx.NewId(), 'Maybe next time')
        hbs.Add(maybe_btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        vbs.Add(hbs, 1, wx.ALL, 5)
        wx.EVT_BUTTON(self, maybe_btn.GetId(), self.__OnMaybe)
        wx.EVT_TEXT_ENTER(self, self.__text_ctrl.GetId(), self.__OnTextEnter)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)
    def GetValue(self):
        return self.__text_ctrl.GetValue()
    def __OnMaybe(self, evt):
        self.EndModal(evt.GetId())
    def __OnTextEnter(self, _):
        self.EndModal(wx.ID_OK)

class HistoricalDataDialog(wx.Dialog):
    Current_Data=0
    Historical_Data=1
    _Historical_Date=1
    _Historical_Event=2
    def __init__(self, parent, caption='Historical Data Selection',
                 current_choice=Current_Data,
                 historical_date=None,
                 historical_events=None):
        super(HistoricalDataDialog, self).__init__(parent, -1, caption)
        vbs=wx.BoxSizer(wx.VERTICAL)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        self.data_selector=wx.RadioBox(self, wx.NewId(),
                                       'Data Selection:',
                                       choices=('Current', 'Historical Date',
                                                'Historical Event'),
                                       style=wx.RA_SPECIFY_ROWS)
        self.data_selector.SetSelection(current_choice)
        wx.EVT_RADIOBOX(self, self.data_selector.GetId(), self.OnSelectData)
        hbs.Add(self.data_selector, 0, wx.ALL, 5)
        static_bs=wx.StaticBoxSizer(wx.StaticBox(self, -1,
                                                 'Historical Date:'),
                                    wx.VERTICAL)
        self.data_date=wx.DatePickerCtrl(self,
                                         style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        if historical_date is not None:
            self.data_date.SetValue(wx.DateTimeFromTimeT(historical_date))
        self.data_date.Enable(current_choice==self._Historical_Date)
        static_bs.Add(self.data_date, 1, wx.EXPAND, 0)
        hbs.Add(static_bs, 0, wx.ALL, 5)
        # historical events
        static_bs=wx.StaticBoxSizer(wx.StaticBox(self, -1, 'Historical Events:'),
                                    wx.VERTICAL)
        self.hist_events=wx.ListBox(self, -1, style=wx.LB_SINGLE)
        if historical_events:
            self._populate_historical_events(historical_events)
        self.hist_events.Enable(current_choice==self._Historical_Event)
        static_bs.Add(self.hist_events, 1, wx.EXPAND, 0)
        hbs.Add(static_bs, 0, wx.ALL, 5)

        vbs.Add(hbs, 1, wx.EXPAND|wx.ALL, 5)
        vbs.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.ALL, 5)
        vbs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL), 0,
                wx.ALIGN_CENTER|wx.ALL, 5)
        self.SetSizer(vbs)
        self.SetAutoLayout(True)
        vbs.Fit(self)

    def OnSelectData(self, evt):
        self.data_date.Enable(evt.GetInt()==self._Historical_Date)
        self.hist_events.Enable(evt.GetInt()==self._Historical_Event)
        
    def GetValue(self):
        choice=self.data_selector.GetSelection()
        if choice==self.Current_Data:
            mode=self.Current_Data
            time_t=None
        elif choice==self._Historical_Date:
            dt=self.data_date.GetValue()
            dt.SetHour(23)
            dt.SetMinute(59)
            dt.SetSecond(59)
            mode=self.Historical_Data
            time_t=dt.GetTicks()
        else:
            sel=self.hist_events.GetSelection()
            if sel==wx.NOT_FOUND:
                mode=self.Current_Data
                time_t=None
            else:
                mode=self.Historical_Data
                time_t=self.hist_events.GetClientData(sel)
        return mode, time_t

    def _populate_historical_events(self, historical_events):
        keys=historical_events.keys()
        keys.sort()
        keys.reverse()
        for k in keys:
            # build the string
            self.hist_events.Append('%s  %02d-Adds  %02d-Dels  %02d-Mods'%\
                                    (time.strftime('%b %d, %y %H:%M:%S',
                                                   time.localtime(k)),
                                     historical_events[k]['add'],
                                     historical_events[k]['del'],
                                     historical_events[k]['mod']),
                                    k)

