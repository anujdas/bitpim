
"Deals with Outlook calendar import stuff"

# System modules
import pywintypes
import sys
import time

# wxPython modules
import wx
import wx.calendar
import wx.lib.mixins.listctrl as listmix

# Others

# My modules
import bpcalendar
import common
import guiwidgets
import native.outlook

# common convertor functions
no_end_date=(4000, 1, 1, 0, 0)
def to_bp_date(dict, v, oc):
    # convert a pyTime to (y, m, d, h, m)
    if not isinstance(v, pywintypes.TimeType):
        raise TypeError, 'illegal type'
    try:
        return time.localtime(int(v))[:5]
    except:
        pass
    # check for no end date
    if dict.get('NoEndDate', False):
        return no_end_date
    else:
        raise ValueError, 'illegal value'

def bp_date_str(dict, v):
    if dict.get('allday', False):
        return '%04d-%02d-%02d'%v[:3]
    else:
        return '%04d-%02d-%02d  %02d:%02d'% v

def bp_repeat_str(dict, v):
    if v is None:
        return ''
    elif v==OutlookCalendarImportData.olRecursDaily:
        return 'Daily'
    elif v==OutlookCalendarImportData.olRecursWeekly:
        return 'Weekly'
    elif v==OutlookCalendarImportData.olRecursMonthly:
        return 'Monthly'
    elif v==OutlookCalendarImportData.olRecursYearly:
        return 'Yearly'
    else:
        return '<Unknown Value>'

def bp_alarm_str(dict, v):
    if dict.get('alarm', False):
        v=dict.get('alarm_value', 0)
        if v:
            return '-%d min'%v
        else:
            return 'Ontime'
    else:
        return ''

def category_str(dict, v):
    s=''
    for d in v:
        if len(d):
            if len(s):
                s+=', '+d
            else:
                s=d
    return s

def convert_categories(dict, v, oc):
    return [x.strip() for x in v.split(",") if len(x)]

def set_recurrence(item, dict, oc):
    oc.update_display()
    if not dict['repeat']:
        # no reccurrence, ignore
        dict['repeat']=None
        return True
    # get the recurrence pattern and map it to BP Calendar
    return oc.process_repeat(item, dict)

#-------------------------------------------------------------------------------
class OutlookCalendarImportData:
    __calendar_keys=[
        # (Outlook field, BP Calendar field, convertor function)
        ('Subject', 'description', None),
        ('Location', 'location', None),
        ('Start', 'start', to_bp_date),
        ('End', 'end', to_bp_date),
        ('Categories', 'categories', convert_categories),
        ('IsRecurring', 'repeat', None),
        ('ReminderSet', 'alarm', None),
        ('ReminderMinutesBeforeStart', 'alarm_value', None),
        ('Importance', 'priority', None),
        ('Body', 'notes', None),
        ('AllDayEvent', 'allday', None)
        ]
    __recurrence_keys=[
        # (Outlook field, BP Calendar field, convertor function)
        ('NoEndDate', 'NoEndDate', None),
        ('PatternStartDate', 'PatternStartDate', to_bp_date),
        ('PatternEndDate', 'PatternEndDate', to_bp_date),
        ('Instance', 'Instance', None),
        ('DayOfWeekMask', 'DayOfWeekMask', None),
        ('Interval', 'Interval', None),
        ('Occurrences', 'Occurrences', None),
        ('RecurrenceType', 'RecurrenceType', None)
        ]
    __exception_keys=[
        # (Outlook field, BP Calendar field, convertor function)
        ('OriginalDate', 'exception_date', to_bp_date),
        ('Deleted', 'deleted', None)
        ]
    __default_filter={
        'start': None,
        'end': None,
        'categories': None
        }

    # Outlook constants
    olRecursDaily    = native.outlook.outlook_com.constants.olRecursDaily
    olRecursMonthNth = native.outlook.outlook_com.constants.olRecursMonthNth
    olRecursMonthly  = native.outlook.outlook_com.constants.olRecursMonthly
    olRecursWeekly   = native.outlook.outlook_com.constants.olRecursWeekly
    olRecursYearNth  = native.outlook.outlook_com.constants.olRecursYearNth
    olRecursYearly   = native.outlook.outlook_com.constants.olRecursYearly
    olImportanceHigh = native.outlook.outlook_com.constants.olImportanceHigh
    olImportanceLow  = native.outlook.outlook_com.constants.olImportanceLow
    olImportanceNormal = native.outlook.outlook_com.constants.olImportanceNormal

    def __init__(self, outlook):
        self.__outlook=outlook
        self.__data=[]
        self.__folder=None
        self.__filter=self.__default_filter
        self.__total_count=0
        self.__current_count=0
        self.__update_dlg=None
        self.__exception_list=[]

    def __accept(self, entry):
        # start & end time within specified filter
        if self.__filter['start']is not None and \
           entry['start'][:3]<self.__filter['start'][:3]:
            return False
        if self.__filter['end'] is not None and \
           entry['end'][:3]>self.__filter['end'][:3] and \
           entry['end'][:3]!=no_end_date[:3]:
            return False
        # check the catefory
        c=self.__filter['categories']
        if c is None or not len(c):
            # no categories specified => all catefories allowed.
            return True
        if len([x for x in entry['categories'] if x in c]):
            return True
        return False

    def __populate_entry(self, e, ce):
        # populate an calendar entry with outlook data
        ce.description=e.get('description', None)
        ce.location=e.get('location', None)
        v=e.get('priority', None)
        if v is not None:
            if v==self.olImportanceNormal:
                ce.priority=ce.priority_normal
            elif v==self.olImportanceLow:
                ce.priority=ce.priority_low
            elif v==self.olImportanceHigh:
                ce.priority=ce.priority_high
        if e.get('alarm', False):
            ce.alarm=e.get('alarm_value', 0)
        ce.allday=e.get('allday', False)
        ce.start=e['start']
        ce.end=e['end']
        ce.notes=e.get('notes', None)
        v=[]
        for k in e.get('categories', []):
            v.append({ 'category': k })
        ce.categories=v
        # look at repeat events
        if not e.get('repeat', False):
            # not a repeat event, just return
            return
        rp=bpcalendar.RepeatEntry()
        rt=e['repeat_type']
        r_interval=e.get('repeat_interval', 0)
        r_dow=e.get('repeat_dow', 0)
        if rt==self.olRecursDaily:
            rp.repeat_type=rp.daily
        elif rt==self.olRecursWeekly:
            if r_interval:
                # weekly event
                rp.repeat_type=rp.weekly
            else:
                # mon-fri event
                rp.repeat_type=rp.daily
        elif rt==self.olRecursMonthly:
            rp.repeat_type=rp.monthly
        else:
            rp.repeat=rp.yearly
        if rp.repeat_type==rp.daily:
            rp.interval=r_interval
        elif rp.repeat_type==rp.weekly:
            rp.interval=r_interval
            rp.dow=r_dow
        # add the list of exceptions
        for k in e.get('exceptions', []):
            rp.add_suppressed(*k[:3])
        ce.repeat=rp
        
    def get(self):
        res={}
        for k in self.__data:
            if self.__accept(k):
                ce=bpcalendar.CalendarEntry()
                self.__populate_entry(k, ce)
                res[ce.id]=ce
        return res

    def get_display_data(self):
        cnt=0
        res={}
        for k in self.__data:
            if self.__accept(k):
                d=k.copy()
                res[cnt]=d
                cnt += 1
        return res

    def get_category_list(self):
        l=[]
        for e in self.__data:
            l+=[x for x in e.get('categories', []) if x not in l]
        return l
            
    def pick_folder(self):
        return self.__outlook.pickfolder()

    def set_folder(self, f):
        if f is None:
            # default folder
            self.__folder=self.__outlook.getfolderfromid('', True, 'calendar')
        else:
            self.__folder=f

    def set_filter(self, filter):
        self.__filter=filter

    def get_filter(self):
        return self.__filter

    def get_folder_name(self):
        if self.__folder is None:
            return '<None>'
        return self.__outlook.getfoldername(self.__folder)

    def read(self, folder=None, update_dlg=None):
        # folder from which to read
        if folder is not None:
            self.__folder=folder
        if self.__folder is None:
            self.__folder=self.__outlook.getfolderfromid('', True, 'calendar')
        self.__update_dlg=update_dlg
        self.__total_count=self.__folder.Items.Count
        self.__current_count=0
        self.__exception_list=[]
        self.__data=self.__outlook.getdata(self.__folder,
                                    self.__calendar_keys,
                                    {}, self,
                                    set_recurrence)
        # add in the exception list, .. or shoule we keep it separate ??
        self.__data+=self.__exception_list

    def __set_repeat_dates(self, dict, r):
        dict['start']=r['PatternStartDate'][:3]+dict['start'][3:]
        dict['end']=r['PatternEndDate'][:3]+dict['end'][3:]
        dict['repeat_type']=r['RecurrenceType']

    def __is_daily_or_weekly(self, dict, r):
        if r['RecurrenceType']==self.olRecursDaily or \
           r['RecurrenceType']==self.olRecursWeekly:
            self.__set_repeat_dates(dict, r)
            dict['repeat_interval']=r['Interval']
            dict['repeat_dow']=r['DayOfWeekMask']
            return True
        return False

    def __is_monthly(self, dict, r):
        if r['RecurrenceType']==self.olRecursMonthly and \
           r['Interval']==1:
            self.__set_repeat_dates(dict, r)
            return True
        return False

    def __is_yearly(self, dict, r):
        if r['RecurrenceType']==self.olRecursYearly and \
           r['Interval']==12:
            self.__set_repeat_dates(dict, r)
            return True
        return False

    def __process_exceptions(self, dict, r):
        # check for and process exceptions for this event
        r_ex=r.Exceptions
        if not r_ex.Count:
            # no exception, bail
            return
        for i in range(1, r_ex.Count+1):
            ex=self.__outlook.getitemdata(r_ex.Item(i), {},
                                          self.__exception_keys, self)
            dict.setdefault('exceptions', []).append(ex['exception_date'])
            if not ex['deleted']:
                # if this instance has been changed, then need to get it
                appt=self.__outlook.getitemdata(r_ex.Item(i).AppointmentItem,
                                                {}, self.__calendar_keys, self)
                # by definition, this instance cannot be a repeat event
                appt['repeat']=False
                appt['end']=appt['start'][:3]+appt['end'][3:]
                # and add it to the exception list
                self.__exception_list.append(appt)
                
    def process_repeat(self, item, dict):
        # get the recurrence info that we need.
        rec_pat=item.GetRecurrencePattern()
        r=self.__outlook.getitemdata(rec_pat, {},
                                     self.__recurrence_keys, self)
        if self.__is_daily_or_weekly(dict, r) or \
           self.__is_monthly(dict, r) or \
           self.__is_yearly(dict, r):
            self.__process_exceptions(dict, rec_pat)
            return True
        # invalide repeat type, turn this event into a regular event
        dict['repeat']=False
        dict['end']=dict['start'][:3]+dict['end'][3:]
        dict['notes']+=' [BITPIM: Unrecognized repeat event, repeat event discarded]'
        return True

    def update_display(self):
        # update the progress dialog if specified
        self.__current_count += 1
        if self.__update_dlg is not None:
            self.__update_dlg.Update(100*self.__current_count/self.__total_count)
        
#-------------------------------------------------------------------------------
class PreviewDialog(wx.Dialog, listmix.ColumnSorterMixin):
    def __init__(self, parent, id, title, col_labels, data={},
                 config_name=None,
                 style=wx.CAPTION|wx.MAXIMIZE_BOX| \
                 wx.SYSTEM_MENU|wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER):

        wx.Dialog.__init__(self, parent, id=id, title=title, style=style)
        
        self.__col_labels=col_labels
        self.__config_name=config_name
        self.itemDataMap={}
        # main boxsizer
        main_bs=wx.BoxSizer(wx.VERTICAL)
        # add custom controls here
        self.getcontrols(main_bs)
        # create a data preview list with supplied column labels
        self.__list=wx.ListView(self, wx.NewId())
        self.__image_list=wx.ImageList(16, 16)
        self.__ig_up=self.__image_list.Add(wx.ArtProvider_GetBitmap(wx.ART_GO_UP,
                                                             wx.ART_OTHER,
                                                             (16, 16)))
        self.__ig_dn=self.__image_list.Add(wx.ArtProvider_GetBitmap(wx.ART_GO_DOWN,
                                                             wx.ART_OTHER,
                                                             (16, 16)))
        self.__list.SetImageList(self.__image_list, wx.IMAGE_LIST_SMALL)
        li=wx.ListItem()
        li.m_mask=wx.LIST_MASK_TEXT | wx.LIST_MASK_IMAGE
        li.m_image=-1
        for i, d in enumerate(self.__col_labels):
            # insert a column with specified name and width
            li.m_text=d[1]
            self.__list.InsertColumnInfo(i, li)
            self.__list.SetColumnWidth(i, d[2])
        main_bs.Add(self.__list, 1, wx.EXPAND, 0)
        self.populate(data)
        # the Mixin sorter
        listmix.ColumnSorterMixin.__init__(self, len(col_labels))
        # now the buttons
        self.getpostcontrols(main_bs)
        # handle events
        # all done
        self.SetSizer(main_bs)
        self.SetAutoLayout(True)
        main_bs.Fit(self)
        # save my own size, if specified
        if config_name is not None:
            guiwidgets.set_size(config_name, self)
            wx.EVT_SIZE(self, self.__save_size)

    def getcontrols(self, main_bs):
        # controls to be placed above the preview pane
        # by default, put nothing.
        pass

    def getpostcontrols(self, main_bs):
        # control to be placed below the preview pane
        # by default, just add the OK & CANCEL button
        main_bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        main_bs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        
    def populate(self, data):
        self.__list.DeleteAllItems()
        m={}
        m_count=0
        for k in data:
            d=data[k]
            col_idx=None
            mm={}
            for i, l in enumerate(self.__col_labels):
                entry=d.get(l[0], None)
                s=''
                if l[3] is None:
                    s=str(entry)
                else:
                    s=l[3](d, entry)
                mm[i]=s
                if i:
                    self.__list.SetStringItem(col_idx, i, s)
                else:
                    col_idx=self.__list.InsertImageStringItem(sys.maxint, s, -1)
            self.__list.SetItemData(col_idx, m_count)
            m[m_count]=mm
            m_count += 1
        self.itemDataMap=m

    def GetListCtrl(self):
        return self.__list

    def GetSortImages(self):
        return (self.__ig_dn, self.__ig_up)

    def __save_size(self, evt):
        if self.__config_name is not None:
            guiwidgets.save_size(self.__config_name, self.GetRect())
        evt.Skip()

#-------------------------------------------------------------------------------
class OutlookImportCalDialog(PreviewDialog):
    __column_labels=[
        ('description', 'Description', 400, None),
        ('start', 'Start', 150, bp_date_str),
        ('end', 'End', 150, bp_date_str),
        ('repeat_type', 'Repeat', 80, bp_repeat_str),
        ('alarm', 'Alarm', 80, bp_alarm_str),
        ('categories', 'Category', 150, category_str)
        ]
    def __init__(self, parent, id, title):
        self.__oc=OutlookCalendarImportData(native.outlook)
        self.__oc.set_folder(None)
        PreviewDialog.__init__(self, parent, id, title,
                               self.__column_labels,
                               self.__oc.get_display_data(),
                               config_name='import/calendar/outlookdialog')
        
    def getcontrols(self, main_bs):
        hbs=wx.BoxSizer(wx.HORIZONTAL)
        # label
        hbs.Add(wx.StaticText(self, -1, "Outlook Calendar Folder:"), 0, wx.ALL|wx.ALIGN_CENTRE, 2)
        # where the folder name goes
        self.folderctrl=wx.TextCtrl(self, -1, "", style=wx.TE_READONLY)
        self.folderctrl.SetValue(self.__oc.get_folder_name())
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
        hbs.Add(wx.Button(self, wx.ID_CANCEL, 'Cancel'), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        id_filter=wx.NewId()
        hbs.Add(wx.Button(self, id_filter, 'Filter'), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)       
        main_bs.Add(hbs, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        wx.EVT_BUTTON(self, id_import, self.OnImport)
        wx.EVT_BUTTON(self, id_filter, self.OnFilter)

    def OnImport(self, evt):
        wx.BeginBusyCursor()
        dlg=wx.ProgressDialog('Outlook Calendar Import',
                              'Importing Outlook Data, please wait ...\n(Please also watch out for the Outlook Permission Request dialog)',
                              parent=self)
        self.__oc.read(None, dlg)
        self.populate(self.__oc.get_display_data())
        dlg.Destroy()
        wx.EndBusyCursor()

    def OnBrowseFolder(self, evt):
        f=self.__oc.pick_folder()
        if f is None:
            return # user hit cancel
        self.__oc.set_folder(f)
        self.folderctrl.SetValue(self.__oc.get_folder_name())

    def OnFilter(self, evt):
        cat_list=self.__oc.get_category_list()
        dlg=FilterDialog(self, -1, 'Filtering Parameters', cat_list)
        dlg.set(self.__oc.get_filter())
        if dlg.ShowModal()==wx.ID_OK:
            print dlg.get()
            self.__oc.set_filter(dlg.get())
            self.populate(self.__oc.get_display_data())

    def get(self):
        return self.__oc.get()

    def get_categories(self):
        return self.__oc.get_category_list()
            
#-------------------------------------------------------------------------------
class FilterDialog(wx.Dialog):
    def __init__(self, parent, id, caption, categories, style=wx.DEFAULT_DIALOG_STYLE):
        wx.Dialog.__init__(self, parent, id,
                           title=caption, style=style)
        # the main box sizer
        bs=wx.BoxSizer(wx.VERTICAL)
        # the flex grid sizers for the editable items
        fgs=wx.FlexGridSizer(3, 3, 0, 5)
        fgs.Add(wx.StaticText(self, -1, 'Start Date:'), 0, wx.ALIGN_CENTRE, 0)
        self.__start_date_chkbox=wx.CheckBox(self, id=wx.NewId())
        fgs.Add(self.__start_date_chkbox, 0, wx.ALIGN_CENTRE, 0)
        self.__start_date=wx.calendar.CalendarCtrl(self, -1, wx.DateTime_Now(),
                                          style = wx.calendar.CAL_SUNDAY_FIRST
                                          | wx.calendar.CAL_SEQUENTIAL_MONTH_SELECTION)
        self.__start_date.Disable()
        fgs.Add(self.__start_date, 1, wx.ALIGN_LEFT, 5)
        fgs.Add(wx.StaticText(self, -1, 'End Date:'), 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE, 0)
        self.__end_date_chkbox=wx.CheckBox(self, id=wx.NewId())
        fgs.Add(self.__end_date_chkbox, 0, wx.ALIGN_CENTRE, 0)
        self.__end_date=wx.calendar.CalendarCtrl(self, -1, wx.DateTime_Now(),
                                          style = wx.calendar.CAL_SUNDAY_FIRST
                                          | wx.calendar.CAL_SEQUENTIAL_MONTH_SELECTION)
        self.__end_date.Disable()
        fgs.Add(self.__end_date, 1, wx.ALIGN_LEFT, 5)
        fgs.Add(wx.StaticText(self, -1, 'Categories:'), 0, wx.ALIGN_LEFT|wx.ALIGN_CENTRE, 0)
        self.__cat_chkbox=wx.CheckBox(self, id=wx.NewId())
        fgs.Add(self.__cat_chkbox, 0, wx.ALIGN_CENTRE, 0)
        for i,c in enumerate(categories):
            if not len(c):
                categories[i]='<None>'
        self.__cats=wx.CheckListBox(self, choices=categories, size=(180, 50))
        self.__cats.Disable()
        fgs.Add(self.__cats, 0, wx.ALIGN_LEFT, 5)
        bs.Add(fgs, 1, wx.EXPAND|wx.ALL, 5)
        # the buttons
        bs.Add(wx.StaticLine(self, -1), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        bs.Add(self.CreateButtonSizer(wx.OK|wx.CANCEL), 0, wx.ALIGN_CENTRE|wx.ALL, 5)
        # event handles
        wx.EVT_CHECKBOX(self, self.__start_date_chkbox.GetId(), self.OnCheckBox)
        wx.EVT_CHECKBOX(self, self.__end_date_chkbox.GetId(), self.OnCheckBox)
        wx.EVT_CHECKBOX(self, self.__cat_chkbox.GetId(), self.OnCheckBox)
        # all done
        self.SetSizer(bs)
        self.SetAutoLayout(True)
        bs.Fit(self)

    def __set_date(self, chk_box, cal, d):
        if d is None:
            chk_box.SetValue(False)
            cal.Disable()
        else:
            chk_box.SetValue(True)
            cal.Enable()
            dt=wx.DateTime()
            dt.Set(d[2], year=d[0], month=d[1]-1)
            cal.SetDate(dt)

    def __set_cats(self, chk_box, c, data):
        if data is None:
            chk_box.SetValue(False)
            c.Disable()
        else:
            chk_box.SetValue(True)
            c.Enable()
            for i,d in enumerate(data):
                if not len(d):
                    data[i]='<None>'
            for i in range(c.GetCount()):
                c.Check(i, c.GetString(i) in data)
          
    def set(self, data):
        self.__set_date(self.__start_date_chkbox, self.__start_date,
                        data.get('start', None))
        self.__set_date(self.__end_date_chkbox, self.__end_date,
                        data.get('end', None))
        self.__set_cats(self.__cat_chkbox, self.__cats, data.get('categories', None))

    def get(self):
        r={}
        if self.__start_date_chkbox.GetValue():
            dt=self.__start_date.GetDate()
            r['start']=(dt.GetYear(), dt.GetMonth()+1, dt.GetDay())
        else:
            r['start']=None
        if self.__end_date_chkbox.GetValue():
            dt=self.__end_date.GetDate()
            r['end']=(dt.GetYear(), dt.GetMonth()+1, dt.GetDay())
        else:
            r['end']=None
        if self.__cat_chkbox.GetValue():
            c=[]
            for i in range(self.__cats.GetCount()):
                if self.__cats.IsChecked(i):
                    s=self.__cats.GetString(i)
                    if s=='<None>':
                        c.append('')
                    else:
                        c.append(s)
            r['categories']=c
        else:
            r['categories']=None
        return r
    
    def OnCheckBox(self, evt):
        evt_id=evt.GetId()
        if evt_id==self.__start_date_chkbox.GetId():
            w1,w2=self.__start_date_chkbox, self.__start_date
        elif evt_id==self.__end_date_chkbox.GetId():
            w1,w2=self.__end_date_chkbox, self.__end_date
        else:
            w1,w2=self.__cat_chkbox, self.__cats
        if w1.GetValue():
            w2.Enable()
        else:
            w2.Disable()