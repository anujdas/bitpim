# THIS FILE IS AUTOMATICALLY GENERATED.  EDIT THE SOURCE FILE NOT THIS ONE

from prototypes import *

# Make all lg stuff available in this module as well
from p_lg import *

# we are the same as lgvx9900 except as noted below
from p_lgvx9900 import *
from p_lgvx8500 import t9udbfile
 
# We use LSB for all integer like fields
UINT=UINTlsb
BOOL=BOOLlsb

BREW_FILE_SYSTEM=2

T9USERDBFILENAME='t9udb/t9udb_eng.dat'

class pbgroup(BaseProtogenClass):
    __fields=['name']

    def __init__(self, *args, **kwargs):
        dict={}
        # What was supplied to this function
        dict.update(kwargs)
        # Parent constructor
        super(pbgroup,self).__init__(**dict)
        if self.__class__ is pbgroup:
            self._update(args,dict)


    def getfields(self):
        return self.__fields


    def _update(self, args, kwargs):
        super(pbgroup,self)._update(args,kwargs)
        keys=kwargs.keys()
        for key in keys:
            if key in self.__fields:
                setattr(self, key, kwargs[key])
                del kwargs[key]
        # Were any unrecognized kwargs passed in?
        if __debug__:
            self._complainaboutunusedargs(pbgroup,kwargs)
        if len(args):
            dict2={'sizeinbytes': 36, 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False }
            dict2.update(kwargs)
            kwargs=dict2
            self.__field_name=USTRING(*args,**dict2)
        # Make all P fields that haven't already been constructed


    def writetobuffer(self,buf,autolog=True,logtitle="<written data>"):
        'Writes this packet to the supplied buffer'
        self._bufferstartoffset=buf.getcurrentoffset()
        self.__field_name.writetobuffer(buf)
        self._bufferendoffset=buf.getcurrentoffset()
        if autolog and self._bufferstartoffset==0: self.autologwrite(buf, logtitle=logtitle)


    def readfrombuffer(self,buf,autolog=True,logtitle="<read data>"):
        'Reads this packet from the supplied buffer'
        self._bufferstartoffset=buf.getcurrentoffset()
        if autolog and self._bufferstartoffset==0: self.autologread(buf, logtitle=logtitle)
        self.__field_name=USTRING(**{'sizeinbytes': 36, 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False })
        self.__field_name.readfrombuffer(buf)
        self._bufferendoffset=buf.getcurrentoffset()


    def __getfield_name(self):
        return self.__field_name.getvalue()

    def __setfield_name(self, value):
        if isinstance(value,USTRING):
            self.__field_name=value
        else:
            self.__field_name=USTRING(value,**{'sizeinbytes': 36, 'encoding': PHONE_ENCODING, 'raiseonunterminatedread': False, 'raiseontruncate': False })

    def __delfield_name(self): del self.__field_name

    name=property(__getfield_name, __setfield_name, __delfield_name, None)

    def iscontainer(self):
        return True

    def containerelements(self):
        yield ('name', self.__field_name, None)




class pbgroups(BaseProtogenClass):
    "Phonebook groups"
    __fields=['groups']

    def __init__(self, *args, **kwargs):
        dict={}
        # What was supplied to this function
        dict.update(kwargs)
        # Parent constructor
        super(pbgroups,self).__init__(**dict)
        if self.__class__ is pbgroups:
            self._update(args,dict)


    def getfields(self):
        return self.__fields


    def _update(self, args, kwargs):
        super(pbgroups,self)._update(args,kwargs)
        keys=kwargs.keys()
        for key in keys:
            if key in self.__fields:
                setattr(self, key, kwargs[key])
                del kwargs[key]
        # Were any unrecognized kwargs passed in?
        if __debug__:
            self._complainaboutunusedargs(pbgroups,kwargs)
        if len(args):
            dict2={'elementclass': pbgroup}
            dict2.update(kwargs)
            kwargs=dict2
            self.__field_groups=LIST(*args,**dict2)
        # Make all P fields that haven't already been constructed


    def writetobuffer(self,buf,autolog=True,logtitle="<written data>"):
        'Writes this packet to the supplied buffer'
        self._bufferstartoffset=buf.getcurrentoffset()
        try: self.__field_groups
        except:
            self.__field_groups=LIST(**{'elementclass': pbgroup})
        self.__field_groups.writetobuffer(buf)
        self._bufferendoffset=buf.getcurrentoffset()
        if autolog and self._bufferstartoffset==0: self.autologwrite(buf, logtitle=logtitle)


    def readfrombuffer(self,buf,autolog=True,logtitle="<read data>"):
        'Reads this packet from the supplied buffer'
        self._bufferstartoffset=buf.getcurrentoffset()
        if autolog and self._bufferstartoffset==0: self.autologread(buf, logtitle=logtitle)
        self.__field_groups=LIST(**{'elementclass': pbgroup})
        self.__field_groups.readfrombuffer(buf)
        self._bufferendoffset=buf.getcurrentoffset()


    def __getfield_groups(self):
        try: self.__field_groups
        except:
            self.__field_groups=LIST(**{'elementclass': pbgroup})
        return self.__field_groups.getvalue()

    def __setfield_groups(self, value):
        if isinstance(value,LIST):
            self.__field_groups=value
        else:
            self.__field_groups=LIST(value,**{'elementclass': pbgroup})

    def __delfield_groups(self): del self.__field_groups

    groups=property(__getfield_groups, __setfield_groups, __delfield_groups, None)

    def iscontainer(self):
        return True

    def containerelements(self):
        yield ('groups', self.__field_groups, None)




class ULReq(BaseProtogenClass):
    ""
    __fields=['cmd', 'unlock_code', 'unlock_key', 'zero']

    def __init__(self, *args, **kwargs):
        dict={}
        # What was supplied to this function
        dict.update(kwargs)
        # Parent constructor
        super(ULReq,self).__init__(**dict)
        if self.__class__ is ULReq:
            self._update(args,dict)


    def getfields(self):
        return self.__fields


    def _update(self, args, kwargs):
        super(ULReq,self)._update(args,kwargs)
        keys=kwargs.keys()
        for key in keys:
            if key in self.__fields:
                setattr(self, key, kwargs[key])
                del kwargs[key]
        # Were any unrecognized kwargs passed in?
        if __debug__:
            self._complainaboutunusedargs(ULReq,kwargs)
        if len(args): raise TypeError('Unexpected arguments supplied: '+`args`)
        # Make all P fields that haven't already been constructed


    def writetobuffer(self,buf,autolog=True,logtitle="<written data>"):
        'Writes this packet to the supplied buffer'
        self._bufferstartoffset=buf.getcurrentoffset()
        try: self.__field_cmd
        except:
            self.__field_cmd=UINT(**{'sizeinbytes': 1,  'default': 0xFE })
        self.__field_cmd.writetobuffer(buf)
        try: self.__field_unlock_code
        except:
            self.__field_unlock_code=UINT(**{'sizeinbytes': 1,  'default': 0x00 })
        self.__field_unlock_code.writetobuffer(buf)
        self.__field_unlock_key.writetobuffer(buf)
        try: self.__field_zero
        except:
            self.__field_zero=UINT(**{'sizeinbytes': 1,  'default': 0x00 })
        self.__field_zero.writetobuffer(buf)
        self._bufferendoffset=buf.getcurrentoffset()
        if autolog and self._bufferstartoffset==0: self.autologwrite(buf, logtitle=logtitle)


    def readfrombuffer(self,buf,autolog=True,logtitle="<read data>"):
        'Reads this packet from the supplied buffer'
        self._bufferstartoffset=buf.getcurrentoffset()
        if autolog and self._bufferstartoffset==0: self.autologread(buf, logtitle=logtitle)
        self.__field_cmd=UINT(**{'sizeinbytes': 1,  'default': 0xFE })
        self.__field_cmd.readfrombuffer(buf)
        self.__field_unlock_code=UINT(**{'sizeinbytes': 1,  'default': 0x00 })
        self.__field_unlock_code.readfrombuffer(buf)
        self.__field_unlock_key=UINT(**{'sizeinbytes': 4})
        self.__field_unlock_key.readfrombuffer(buf)
        self.__field_zero=UINT(**{'sizeinbytes': 1,  'default': 0x00 })
        self.__field_zero.readfrombuffer(buf)
        self._bufferendoffset=buf.getcurrentoffset()


    def __getfield_cmd(self):
        try: self.__field_cmd
        except:
            self.__field_cmd=UINT(**{'sizeinbytes': 1,  'default': 0xFE })
        return self.__field_cmd.getvalue()

    def __setfield_cmd(self, value):
        if isinstance(value,UINT):
            self.__field_cmd=value
        else:
            self.__field_cmd=UINT(value,**{'sizeinbytes': 1,  'default': 0xFE })

    def __delfield_cmd(self): del self.__field_cmd

    cmd=property(__getfield_cmd, __setfield_cmd, __delfield_cmd, None)

    def __getfield_unlock_code(self):
        try: self.__field_unlock_code
        except:
            self.__field_unlock_code=UINT(**{'sizeinbytes': 1,  'default': 0x00 })
        return self.__field_unlock_code.getvalue()

    def __setfield_unlock_code(self, value):
        if isinstance(value,UINT):
            self.__field_unlock_code=value
        else:
            self.__field_unlock_code=UINT(value,**{'sizeinbytes': 1,  'default': 0x00 })

    def __delfield_unlock_code(self): del self.__field_unlock_code

    unlock_code=property(__getfield_unlock_code, __setfield_unlock_code, __delfield_unlock_code, None)

    def __getfield_unlock_key(self):
        return self.__field_unlock_key.getvalue()

    def __setfield_unlock_key(self, value):
        if isinstance(value,UINT):
            self.__field_unlock_key=value
        else:
            self.__field_unlock_key=UINT(value,**{'sizeinbytes': 4})

    def __delfield_unlock_key(self): del self.__field_unlock_key

    unlock_key=property(__getfield_unlock_key, __setfield_unlock_key, __delfield_unlock_key, None)

    def __getfield_zero(self):
        try: self.__field_zero
        except:
            self.__field_zero=UINT(**{'sizeinbytes': 1,  'default': 0x00 })
        return self.__field_zero.getvalue()

    def __setfield_zero(self, value):
        if isinstance(value,UINT):
            self.__field_zero=value
        else:
            self.__field_zero=UINT(value,**{'sizeinbytes': 1,  'default': 0x00 })

    def __delfield_zero(self): del self.__field_zero

    zero=property(__getfield_zero, __setfield_zero, __delfield_zero, None)

    def iscontainer(self):
        return True

    def containerelements(self):
        yield ('cmd', self.__field_cmd, None)
        yield ('unlock_code', self.__field_unlock_code, None)
        yield ('unlock_key', self.__field_unlock_key, None)
        yield ('zero', self.__field_zero, None)




class ULRes(BaseProtogenClass):
    ""
    __fields=['cmd', 'unlock_code', 'unlock_key', 'unlock_ok']

    def __init__(self, *args, **kwargs):
        dict={}
        # What was supplied to this function
        dict.update(kwargs)
        # Parent constructor
        super(ULRes,self).__init__(**dict)
        if self.__class__ is ULRes:
            self._update(args,dict)


    def getfields(self):
        return self.__fields


    def _update(self, args, kwargs):
        super(ULRes,self)._update(args,kwargs)
        keys=kwargs.keys()
        for key in keys:
            if key in self.__fields:
                setattr(self, key, kwargs[key])
                del kwargs[key]
        # Were any unrecognized kwargs passed in?
        if __debug__:
            self._complainaboutunusedargs(ULRes,kwargs)
        if len(args): raise TypeError('Unexpected arguments supplied: '+`args`)
        # Make all P fields that haven't already been constructed


    def writetobuffer(self,buf,autolog=True,logtitle="<written data>"):
        'Writes this packet to the supplied buffer'
        self._bufferstartoffset=buf.getcurrentoffset()
        self.__field_cmd.writetobuffer(buf)
        self.__field_unlock_code.writetobuffer(buf)
        self.__field_unlock_key.writetobuffer(buf)
        self.__field_unlock_ok.writetobuffer(buf)
        self._bufferendoffset=buf.getcurrentoffset()
        if autolog and self._bufferstartoffset==0: self.autologwrite(buf, logtitle=logtitle)


    def readfrombuffer(self,buf,autolog=True,logtitle="<read data>"):
        'Reads this packet from the supplied buffer'
        self._bufferstartoffset=buf.getcurrentoffset()
        if autolog and self._bufferstartoffset==0: self.autologread(buf, logtitle=logtitle)
        self.__field_cmd=UINT(**{'sizeinbytes': 1})
        self.__field_cmd.readfrombuffer(buf)
        self.__field_unlock_code=UINT(**{'sizeinbytes': 1})
        self.__field_unlock_code.readfrombuffer(buf)
        self.__field_unlock_key=UINT(**{'sizeinbytes': 4})
        self.__field_unlock_key.readfrombuffer(buf)
        self.__field_unlock_ok=UINT(**{'sizeinbytes': 1})
        self.__field_unlock_ok.readfrombuffer(buf)
        self._bufferendoffset=buf.getcurrentoffset()


    def __getfield_cmd(self):
        return self.__field_cmd.getvalue()

    def __setfield_cmd(self, value):
        if isinstance(value,UINT):
            self.__field_cmd=value
        else:
            self.__field_cmd=UINT(value,**{'sizeinbytes': 1})

    def __delfield_cmd(self): del self.__field_cmd

    cmd=property(__getfield_cmd, __setfield_cmd, __delfield_cmd, None)

    def __getfield_unlock_code(self):
        return self.__field_unlock_code.getvalue()

    def __setfield_unlock_code(self, value):
        if isinstance(value,UINT):
            self.__field_unlock_code=value
        else:
            self.__field_unlock_code=UINT(value,**{'sizeinbytes': 1})

    def __delfield_unlock_code(self): del self.__field_unlock_code

    unlock_code=property(__getfield_unlock_code, __setfield_unlock_code, __delfield_unlock_code, None)

    def __getfield_unlock_key(self):
        return self.__field_unlock_key.getvalue()

    def __setfield_unlock_key(self, value):
        if isinstance(value,UINT):
            self.__field_unlock_key=value
        else:
            self.__field_unlock_key=UINT(value,**{'sizeinbytes': 4})

    def __delfield_unlock_key(self): del self.__field_unlock_key

    unlock_key=property(__getfield_unlock_key, __setfield_unlock_key, __delfield_unlock_key, None)

    def __getfield_unlock_ok(self):
        return self.__field_unlock_ok.getvalue()

    def __setfield_unlock_ok(self, value):
        if isinstance(value,UINT):
            self.__field_unlock_ok=value
        else:
            self.__field_unlock_ok=UINT(value,**{'sizeinbytes': 1})

    def __delfield_unlock_ok(self): del self.__field_unlock_ok

    unlock_ok=property(__getfield_unlock_ok, __setfield_unlock_ok, __delfield_unlock_ok, None)

    def iscontainer(self):
        return True

    def containerelements(self):
        yield ('cmd', self.__field_cmd, None)
        yield ('unlock_code', self.__field_unlock_code, None)
        yield ('unlock_key', self.__field_unlock_key, None)
        yield ('unlock_ok', self.__field_unlock_ok, None)




