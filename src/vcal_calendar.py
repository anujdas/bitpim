### BITPIM
###
### Copyright (C) 2004 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Deals with vcard calendar import stuff"

# system modules
import copy
import datetime

# site modules
import wx

# local modules
import bpcalendar
import bptime
import common_calendar
import helpids
import vcard

module_debug=False

#-------------------------------------------------------------------------------
class vCalendarFile(object):
    def __init__(self, file_name=None):
        self.__data=[]
        self.__file_name=file_name

    def read(self, file_name=None):
        self.__data=[]
        if file_name is not None:
            self.__file_name=file_name
        if self.__file_name is None:
            # no file name specified
            return
        try:
            f=open(self.__file_name)
            vfile=vcard.VFile(f)
            has_data=False
            for n,l in vfile:
                if n[0]=='BEGIN' and l=='VEVENT':
                    # start of an event, turn on data loggin
                    d={}
                    has_data=True
                elif n[0]=='END' and l=='VEVENT':
                    self.__data.append(d)
                    d={}
                    has_data=False
                elif has_data:
                    d[n[0]]={ 'value': l }
            f.close()
        except:
            pass

    def __get_data(self):
        return copy.deepcopy(self.__data)
    data=property(fget=__get_data)
        
#-------------------------------------------------------------------------------
class VCalendarImportData(object):

    __default_filter={
        'start': None,
        'end': None,
        'categories': None,
        'rpt_events': False,
        'no_alarm': False
        }
    __rrule_dow={
        'SU': 0x01, 'MO': 0x02, 'TU': 0x04, 'WE': 0x08, 'TH': 0x10,
        'FR': 0x20, 'SA': 0x40 }
    __rrule_weekday=__rrule_dow['MO']|__rrule_dow['TU']|\
                  __rrule_dow['WE']|__rrule_dow['TH']|\
                  __rrule_dow['FR']

    def __init__(self, file_name=None):
        self.__calendar_keys=[
            ('CATEGORIES', 'categories', self.__conv_cat),
            ('DESCRIPTION', 'notes', None),
            ('DTEND', 'end', self.__conv_date),
            ('LOCATION', 'location', None),
            ('PRIORITY', 'priority', self.__conv_priority),
            ('DTSTART', 'start', self.__conv_date),
            ('SUMMARY', 'description', None),
            ('AALARM', 'alarm', self.__conv_alarm),
            ('DALARM', 'alarm', self.__conv_alarm),
            ('RRULE', 'repeat', self.__conv_repeat),
            ('EXDATE', 'exceptions', self.__conv_exceptions),
            ]
        self.__file_name=file_name
        self.__data=[]
        self.__filter=self.__default_filter
        self.read()

    def __accept(self, entry):
        # start & end time within specified filter
        if self.__filter['start'] is not None and \
           entry['start'][:3]<self.__filter['start'][:3]:
            return False
        if self.__filter['end'] is not None and \
           entry['end'][:3]>self.__filter['end'][:3] and \
           entry['end'][:3]!=common_calendar.no_end_date[:3]:
            return False
        # check the catefory
        c=self.__filter['categories']
        if c is None or not len(c):
            # no categories specified => all catefories allowed.
            return True
        if len([x for x in entry['categories'] if x in c]):
            return True
        return False

    def __populate_repeat_entry(self, e, ce):
        # populate repeat entry data
        if not e.get('repeat', False) or e.get('repeat_type', None) is None:
            #  not a repeat event
            return
        rp=bpcalendar.RepeatEntry()
        rp_type=e['repeat_type']
        rp_interval=e.get('repeat_interval', 1)
        rp_end=e.get('repeat_end', None)
        rp_num=e.get('repeat_num', None)
        rp_dow=e.get('repeat_dow', 0)
        if rp_type=='daily':
            # daily event
            rp.repeat_type=rp.daily
            rp.interval=rp_interval
        elif rp_type=='weekly':
            rp.repeat_type=rp.weekly
            rp.interval=rp_interval
            rp.dow=rp_dow
        elif rp_type=='monthly':
            rp.repeat_type=rp.monthly
        elif rp_type=='yearly':
            rp.repeat_type=rp.yearly
        else:
            # not yet supported
            return
        # setting the repeat duration/end-date of this event
        if rp_end is not None:
            # end date specified
            ce.end=rp_end[:3]+ce.end[3:]
        elif rp_num is not None and rp_num:
            # num of occurrences specified
            if rp_type=='daily':
                bp_t=bptime.BPTime(ce.start)+ \
                      datetime.timedelta(rp_interval*(rp_num-1))
                ce.end=bp_t.get()[:3]+ce.end[3:]
            elif rp_type=='weekly':
                bp_t=bptime.BPTime(ce.start)+ \
                      datetime.timedelta(7*rp_interval*(rp_num-1))
                ce.end=bp_t.get()[:3]+ce.end[3:]
            elif rp_type=='monthly':
                bp_t=bptime.BPTime(ce.start)+ \
                      datetime.timedelta(30*(rp_num-1))
                ce.end=bp_t.get()[:2]+ce.end[2:]
            else:                    
                bp_t=bptime.BPTime(ce.start)+ \
                      datetime.timedelta(365*(rp_num-1))
                ce.end=bp_t.get()[:1]+ce.end[1:]
        else:
            # forever duration
            ce.end=common_calendar.no_end_date[:3]+ce.end[3:]
        # add the list of exceptions
        for k in e.get('exceptions', []):
            rp.add_suppressed(*k[:3])
        # all done
        ce.repeat=rp
            
    def __populate_entry(self, e, ce):
        # populate an calendar entry with data
        ce.description=e.get('description', None)
        ce.location=e.get('location', None)
        v=e.get('priority', None)
        if v is not None:
            ce.priority=v
        if not self.__filter.get('no_alarm', False) and e.get('alarm', False):
            ce.alarm=e.get('alarm_value', 0)
        ce_start=e.get('start', None)
        ce_end=e.get('end', None)
        if ce_start is None and ce_end is None:
            raise ValueError, "No start or end datetime"
        if ce_start is not None:
            ce.start=ce_start
        if ce_end is not None:
            ce.end=ce_end
        if ce_start is None:
            ce.start=ce.end
        elif ce_end is None:
            ce.end=ce.start
        ce.notes=e.get('notes', None)
        v=[]
        for k in e.get('categories', []):
            v.append({ 'category': k })
        ce.categories=v
        # look at repeat
        self.__populate_repeat_entry(e, ce)

    def __generate_repeat_events(self, e):
        # generate multiple single events from this repeat event
        ce=bpcalendar.CalendarEntry()
        self.__populate_entry(e, ce)
        l=[]
        new_e=e.copy()
        new_e['repeat']=False
        for k in ('repeat_type', 'repeat_interval', 'repeat_dow'):
            if new_e.has_key(k):
                del new_e[k]
        s_date=datetime.datetime(*self.__filter['start'])
        e_date=datetime.datetime(*self.__filter['end'])
        one_day=datetime.timedelta(1)
        this_date=s_date
        while this_date<=e_date:
            date_l=(this_date.year, this_date.month, this_date.day)
            if ce.is_active(*date_l):
                new_e['start']=date_l+new_e['start'][3:]
                new_e['end']=date_l+new_e['end'][3:]
                l.append(new_e.copy())
            this_date+=one_day
        return l
        
    def get(self):
        res={}
        single_rpt=self.__filter.get('rpt_events', False)
        for k in self.__data:
            try:
                if self.__accept(k):
                    if k.get('repeat', False) and single_rpt:
                        d=self.__generate_repeat_events(k)
                    else:
                        d=[k]
                    for n in d:
                        ce=bpcalendar.CalendarEntry()
                        self.__populate_entry(n, ce)
                        res[ce.id]=ce
            except:
                if module_debug:
                    raise
        return res

    def get_category_list(self):
        l=[]
        for e in self.__data:
            l+=[x for x in e.get('categories', []) if x not in l]
        return l
            
    def set_filter(self, filter):
        self.__filter=filter

    def get_filter(self):
        return self.__filter

    def __conv_cat(self, v, _):
        return [x.strip() for x in v['value'].split(",") if len(x)]

    def __conv_alarm(self, v, dd):
        try:
            alarm_date=bptime.BPTime(v['value'].split(';')[0])
            start_date=bptime.BPTime(dd['start'])
            if alarm_date.get()<start_date.get():
                dd['alarm_value']=(start_date-alarm_date).seconds/60
                return True
            return False
        except:
            return False

    def __conv_date(self, v, _):
        return bptime.BPTime(v['value']).get()
    def __conv_priority(self, v, _):
        try:
            return int(v['value'])
        except:
            return None
    def __process_daily_rule(self, v, dd):
        # the rule is Dx #y or Dx YYYYMMDDTHHMM
        s=v['value'].split(' ')
        dd['repeat_interval']=int(s[0][1:])
        if len(s)==1:
            # no duration/end date
            return True
        if s[1][0]=='#':
            # duration
            dd['repeat_num']=int(s[1][1:])
        else:
            # end date
            dd['repeat_end']=bptime.BPTime(s[1]).get()
        dd['repeat_type']='daily'
        return True

    def __process_weekly_rule(self, v, dd):
        # the rule is Wx | Wx <#y|YYYYMMDDTHHMMSS> | Wx MO TU
        s=v['value'].split(' ')
        dd['repeat_interval']=int(s[0][1:])
        dow=0
        for i in range(1, len(s)):
            n=s[i]
            if n[0].isdigit():
                dd['repeat_end']=bptime.BPTime(n).get()
            elif n[0]=='#':
                dd['repeat_num']=int(n[1:])
            else:
                # day-of-week
                dow=dow|self.__rrule_dow.get(n, 0)
        if dow:
            dd['repeat_dow']=dow
        dd['repeat_type']='weekly'
        return True

    def __process_monthly_rule(self, v, dd):
        try:
            # acceptable format: MD1 <day number> <end date | #duration>
            s=v['value'].split(' ')
            if s[0]!='MD1':
                return False
            n=s[-1]
            if len(n)>7 and n[:8].isdigit():
                # end date/time specified
                dd['repeat_end']=bptime.BPTime(n).get()
            elif n[0]=='#':
                dd['repeat_num']=int(n[1:])
            dd['repeat_type']='monthly'
            return True
        except:
            if module_debug: raise
            return False
    def __process_yearly_rule(self, v, dd):
        try:
            # acceptable format YM1 <Month number> <end date | #duration>
            s=v['value'].split(' ')
            if s[0]!='YM1':
                return False
            n=s[-1]
            if len(n)>7 and n[:8].isdigit():
                # end date/time specified
                dd['repeat_end']=bptime.BPTime(n).get()
            elif n[0]=='#':
                dd['repeat_num']=int(n[1:])
            dd['repeat_type']='yearly'
            return True
        except:
            if module_debug: raise
            return False
    
    def __conv_repeat(self, v, dd):
        func_dict={
            'D': self.__process_daily_rule,
            'W': self.__process_weekly_rule,
            'M': self.__process_monthly_rule,
            'Y': self.__process_yearly_rule
            }
        c=v['value'][0]
        return func_dict.get(c, lambda *arg: False)(v, dd)
    def __conv_exceptions(self, v, _):
        try:
            l=v['value'].split(';')
            r=[]
            for n in l:
                r.append(bptime.BPTime(n).get())
            return r
        except:
            return []
    def __convert(self, vcal, d):
        for i in vcal:
            try:
                dd={'start': None, 'end': None }
                for j in self.__calendar_keys:
                    if i.has_key(j[0]):
                        k=i[j[0]]
                        if j[2] is not None:
                            dd[j[1]]=j[2](k, dd)
                        else:
                            dd[j[1]]=k['value']
                if dd['start'] is None and dd['end'] is None:
                    # no start or end, drop this one
                    continue
                if dd['start'] is None:
                    dd['start']=dd['end']
                elif dd['end'] is None:
                    dd['end']=dd['start']
                if module_debug: print dd
                d.append(dd)
            except:
                if module_debug: raise

    def get_display_data(self):
        cnt=0
        res={}
        single_rpt=self.__filter.get('rpt_events', False)
        for k in self.__data:
            if self.__accept(k):
                if k.get('repeat', False) and single_rpt:
                    d=self.__generate_repeat_events(k)
                else:
                    d=[k.copy()]
                for n in d:
                    if self.__filter.get('no_alarm', False):
                        n['alarm']=False
                    res[cnt]=n
                    cnt+=1
        return res

    def get_file_name(self):
        if self.__file_name is not None:
            return self.__file_name
        return ''

    def read(self, file_name=None):
        if file_name is not None:
            self.__file_name=file_name
        if self.__file_name is None:
            # no file name specified
            return
        v=vCalendarFile(self.__file_name)
        v.read()
        self.__convert(v.data, self.__data)

#-------------------------------------------------------------------------------
def bp_repeat_str(dict, v):
    if v is None:
        return ''
    return v
class VcalImportCalDialog(common_calendar.PreviewDialog):
    __column_labels=[
        ('description', 'Description', 400, None),
        ('start', 'Start', 150, common_calendar.bp_date_str),
        ('end', 'End', 150, common_calendar.bp_date_str),
        ('repeat_type', 'Repeat', 80, bp_repeat_str),
        ('alarm', 'Alarm', 80, common_calendar.bp_alarm_str),
        ('categories', 'Category', 150, common_calendar.category_str)
        ]
    ID_ADD=wx.NewId()
    def __init__(self, parent, id, title):
        self.__oc=VCalendarImportData()
        common_calendar.PreviewDialog.__init__(self, parent, id, title,
                               self.__column_labels,
                               self.__oc.get_display_data(),
                               config_name='import/calendar/vcaldialog')
        
    def getcontrols(self, main_bs):
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # label
        hbs.Add(wx.StaticText(self, -1, "VCalendar File:"), 0, wx.ALL|wx.ALIGN_CENTRE, 2)
        # where the folder name goes
        self.folderctrl=wx.TextCtrl(self, -1, "", style=wx.TE_READONLY)
        self.folderctrl.SetValue(self.__oc.get_file_name())
        hbs.Add(self.folderctrl, 1, wx.EXPAND|wx.ALL, 2)
        # browse button
        id_browse=wx.NewId()
        hbs.Add(wx.Button(self, id_browse, 'Browse ...'), 0, wx.EXPAND|wx.ALL, 2)
        main_bs.Add(hbs, 0, wx.EXPAND|wx.ALL, 5)
        main_bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        wx.EVT_BUTTON(self, id_browse, self.OnBrowseFolder)

    def getpostcontrols(self, main_bs):
        main_bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        id_import=wx.NewId()
        hbs.Add(wx.Button(self, id_import, 'Import'), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hbs.Add(wx.Button(self, wx.ID_OK, 'Replace All'), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hbs.Add(wx.Button(self, self.ID_ADD, 'Add'), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        hbs.Add(wx.Button(self, wx.ID_CANCEL, 'Cancel'), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        id_filter=wx.NewId()
        hbs.Add(wx.Button(self, id_filter, 'Filter'), 0, wx.ALIGN_CENTRE|wx.ALL, 5)       
        hbs.Add(wx.Button(self, wx.ID_HELP, 'Help'), 0,  wx.ALIGN_CENTRE|wx.ALL, 5)
        main_bs.Add(hbs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        wx.EVT_BUTTON(self, id_import, self.OnImport)
        wx.EVT_BUTTON(self, id_filter, self.OnFilter)
        wx.EVT_BUTTON(self, self.ID_ADD, self.OnAdd)
        wx.EVT_BUTTON(self, wx.ID_HELP, lambda *_: wx.GetApp().displayhelpid(helpids.ID_DLG_CALENDAR_IMPORT))

    def OnImport(self, evt):
        wx.BeginBusyCursor()
        dlg=wx.ProgressDialog('VCalendar Import',
                              'Importing vCalendar Data, please wait ...',
                              parent=self)
        self.__oc.read(self.folderctrl.GetValue())
        self.populate(self.__oc.get_display_data())
        dlg.Destroy()
        wx.EndBusyCursor()

    def OnBrowseFolder(self, evt):
        dlg=wx.FileDialog(self, "Pick a VCalendar File", wildcard='*.vcs')
        id=dlg.ShowModal()
        if id==wx.ID_CANCEL:
            dlg.Destroy()
            return
        self.folderctrl.SetValue(dlg.GetPath())
        dlg.Destroy()

    def OnFilter(self, evt):
        cat_list=self.__oc.get_category_list()
        dlg=common_calendar.FilterDialog(self, -1, 'Filtering Parameters', cat_list)
        dlg.set(self.__oc.get_filter())
        if dlg.ShowModal()==wx.ID_OK:
            self.__oc.set_filter(dlg.get())
            self.populate(self.__oc.get_display_data())

    def OnAdd(self, evt):
        self.EndModal(self.ID_ADD)

    def get(self):
        return self.__oc.get()

    def get_categories(self):
        return self.__oc.get_category_list()
            
#-------------------------------------------------------------------------------
