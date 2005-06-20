### BITPIM
###
### Copyright (C) 2003-2004 Joe Pham <djpham@netzero.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

""" Module to handle BITPIM date & time """

import calendar
import datetime

class BPTime(object):
    def __init__(self, v=None):
        self._date=self._time=None
        # I guess this is how python handles overloading ctors
        if isinstance(v, (str, unicode)):
            self.set_iso_str(v)
        elif isinstance(v, (tuple, list)):
            self.set(v)
        elif isinstance(v, datetime.date):
            self._date=v

    def _get_date(self):
        return self._date
    date=property(fget=_get_date)
    def _get_time(self):
        return self._time
    time=property(fget=_get_time)

    def __sub__(self, rhs):
        if not isinstance(rhs, BPTime):
            raise TypeError
        return datetime.datetime(*self.get())-datetime.datetime(*rhs.get())
    def __add__(self, rhs):
        if not isinstance(rhs, datetime.timedelta):
            raise TypeError
        dt=datetime.datetime(*self.get())+rhs
        return BPTime((dt.year, dt.month, dt.day, dt.hour, dt.minute))
    def __eq__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date==rhs.date
        return False
    def __ne__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date!=rhs.date
        return False
    def __lt__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date<rhs.date
        return False
    def __le__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date<=rhs.date
        return False
    def __gt__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date>rhs.date
        return False
    def __ge__(self, rhs):
        if isinstance(rhs, BPTime):
            return self.date>=rhs.date
        return False

    def _utc_to_local(self, offset_str=None):
        # convert from utc time to local time
        if self._date is None or self._time is None:
            return
        gmt=calendar.timegm((self._date.year, self._date.month, self._date.day,
                             self._time.hour, self._time.minute, 0))
        if offset_str is not None:
            # need to apply offset
            offset_sec=int(offset_str[1:3])*3600.0+int(offset_str[3:5])*60.0
            if offset_str[0]=='-':
                gmt+=offset_sec
            else:
                gmt-=offset_sec
        dt=datetime.datetime.fromtimestamp(gmt)
        self._date=dt.date()
        self._time=dt.time()
    def set_iso_str(self, v):
        # set the date/time according to the ISO string
        # acceptable formats:
        # YYYYMMDD, YYYYMMDDThhmm, YYYYMMDDThhmmss, YYYYMMDDThhmmssZ,
        # YYYYMMDDThhmmss+hhmm, YYYYMMDDThhmmss-hhmm
        v=str(v)
        len_v=len(v)
        if len_v<8:
            # not long enough even for the date
            return
        # date componebt
        self._date=datetime.date(int(v[:4]), int(v[4:6]), int(v[6:8]))
        self._time=None
        if len_v>12:
            # time component specified
            self._time=datetime.time(hour=int(v[9:11]), minute=int(v[11:13]))
        # check if timezone info is specified
        if v[-1]=='Z':
            # UTC time
            self._utc_to_local()
        elif v[-5]=='-' or v[-5]=='+':
            self._utc_to_local(v[-5:])

    def iso_str(self, no_time=False):
        # return an ISO string representation
        s=''
        if self._date is not None:
            s='%04d%02d%02d'%(self._date.year, self._date.month,
                                   self._date.day)
        if self._time is not None and not no_time:
            s+='T%02d%02d'%(self._time.hour, self._time.minute)
        return s

    def date_str(self):
        if self._date is None:
            s=''
        else:
            s='%04d-%02d-%02d'%(self._date.year, self._date.month,
                                self._date.day)
        return s

    def time_str(self, am_pm=True, default=''):
        if self._time is None:
            s=default
        else:
            h=self._time.hour
            if am_pm:
                if h>11:
                    ampm_str='pm'
                else:
                    ampm_str='am'
                if h>12:
                    h-=12
                s='%02d:%02d%s'%(h, self._time.minute, ampm_str)
            else:
                s='%02d:%02d'%(h, self._time.minute)
        return s

    def get(self):
        if self._date is None:
            t=(0, 0, 0)
        else:
            t=(self._date.year, self._date.month, self._date.day)
        if self._time is None:
            t+=(0, 0)
        else:
            t+=(self._time.hour, self._time.minute)
        return t

    def set(self, v):
        self._date=self._time=None
        if len(v)>2:
            self._date=datetime.date(*v[:3])
        if len(v)==5:
            self._time=datetime.time(*v[3:])
