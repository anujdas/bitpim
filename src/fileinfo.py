### BITPIM
###
### Copyright (C) 2005 Roger Binns <rogerb@rogerbinns.com>
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the BitPim license as detailed in the LICENSE file.
###
### $Id$

"Returns information about files"

import os

class FailedFile:
    def GetBytes(*args):   return None
    def GetLSBUint32(*args): return None
    def GetLSBUint16(*args): return None
    def GetByte(*args): return None
    def GetMSBUint32(*args): return None
    def GetMSBUint16(*args): return None

class SafeFileWrapper:
    """Wraps a file object letting you get various parts without exceptions"""

    READAHEAD=1024

    def __init__(self, filename):
        try:
            self.file=open(filename, "rb")
            self.size=os.stat(filename).st_size
            self.data=self.file.read(self.READAHEAD)
        except (OSError,IOError):
            # change our class
            self.size=-1
            self.__class__=FailedFile

    def GetBytes(self, offset, length):
        if offset+length<len(self.data):
            return self.data[offset:offset+length]
        if offset+length>=self.size:
            return None
        self.file.seek(offset)
        res=self.file.read(length)
        if len(res)<length: return None
        return res

    def GetLSBUint32(self, offset):
        v=self.GetBytes(offset, 4)
        if v is None: return v
        return ord(v[0])+(ord(v[1])<<8)+(ord(v[2])<<16)+(ord(v[3])<<24)

    def GetLSBUint16(self, offset):
        v=self.GetBytes(offset, 2)
        if v is None: return v
        return ord(v[0])+(ord(v[1])<<8)

    def GetMSBUint32(self, offset):
        v=self.GetBytes(offset, 4)
        if v is None: return v
        return ord(v[3])+(ord(v[2])<<8)+(ord(v[1])<<16)+(ord(v[0])<<24)

    def GetMSBUint16(self, offset):
        v=self.GetBytes(offset, 2)
        if v is None: return v
        return ord(v[1])+(ord(v[0])<<8)

    def GetByte(self, offset):
        v=self.GetBytes(offset,1)
        if v is None: return v
        return ord(v)

class ImgFileInfo:
    "Wraps information about an image file"

    # These will always be present
    attrnames=("width", "height", "format", "bpp", "size", "MAXSIZE")

    def __init__(self, f, **kwds):
        for a in self.attrnames:
            setattr(self, a, None)
        self.size=f.size
        self.__dict__.update(kwds)

    def shortdescription(self):
        v=getattr(self, "_shortdescription", None)
        if v is not None:
            return v(self)        
        res=[]
        if self.width is not None and self.height is not None:
            res.append( "%d x %d" % (self.width, self.height) )
        if self.format is not None:
            res.append( self.format)
        if self.bpp is not None:
            res.append( "%d bpp" % (self.bpp,))

        if len(res):
            return " ".join(res)
        return "Unknown format"

    def longdescription(self):
        v=getattr(self, "_longdescription", None)
        if v is not None:
            return v(self)
        return self.shortdescription()

def idimg_BMP(f):
    "Identify a Windows bitmap"
    # 40 is header size for windows bmp, different numbers are used by OS/2
    if f.GetBytes(0,2)=="BM" and f.GetLSBUint16(14)==40:
        d={'format': "BMP"}
        d['width']=f.GetLSBUint32(18)
        d['height']=f.GetLSBUint32(22)
        d['bpp']=f.GetLSBUint16(28)
        d['compression']=f.GetLSBUint32(30)
        d['ncolours']=f.GetLSBUint32(46)
        d['nimportantcolours']=f.GetLSBUint32(50)
        d['_longdescription']=fmt_BMP
        for i in d.itervalues():
            if i is None:  return None
        ifi=ImgFileInfo(f,**d)
        return ifi
    return None

def fmt_BMP(ifi):
    "Long description for BMP"
    res=[ifi.shortdescription()]
    if ifi.compression==0:
        res.append("No compression")
    elif ifi.compression==1:
        res.append("8 bit run length encoding")
    elif ifi.compression==2:
        res.append("4 bit run length encoding")
    elif ifi.compression==3:
        res.append("RGB bitmap with mask")
    else:
        res.append("Unknown compression "+`ifi.compression`)
    if ifi.ncolours:
        res.append("%d colours" % (ifi.ncolours,))
        if ifi.nimportantcolours:
            res[-1]=res[-1]+(" (%d important)" % (ifi.nimportantcolours,))
    return "\n".join(res)
    
def idimg_PNG(f):
    "Identify a PNG"
    if f.GetBytes(0,8)=="\x89PNG\r\n\x1a\n" and f.GetBytes(12,4)=="IHDR":
        d={'format': "PNG"}
        d['width']=f.GetMSBUint32(16)
        d['height']=f.GetMSBUint32(20)
        d['bitdepth']=f.GetByte(24)
        d['colourtype']=f.GetByte(25)
        d['compression']=f.GetByte(26)
        d['filter']=f.GetByte(27)
        d['interlace']=f.GetByte(28)
        d['_shortdescription']=fmts_PNG
        d['_longdescription']=fmt_PNG
        for i in d.itervalues():
            if i is None:  return None
        ifi=ImgFileInfo(f,**d)
        return ifi
    return None

def fmts_PNG(ifi, short=True):
    res=[]
    res.append( "%d x %d" % (ifi.width, ifi.height) )
    res.append( ifi.format)
    if ifi.colourtype in (0,4):
        res.append("%d bit grayscale" % (ifi.bitdepth,))
    elif ifi.colourtype in (2,6):
        res.append("truecolour (%d bit)" % (ifi.bitdepth*3,))
    elif ifi.colourtype==3:
        res.append("%d colours" % (2**ifi.bitdepth,))
    if not short and ifi.colourtype in (4,6):
            res.append("with transparency")
    return " ".join(res)

def fmt_PNG(ifi):
    "Long description for PNG"
    res=[fmts_PNG(ifi, False)]

    if ifi.compression==0:
        res.append("Deflate compressed")
    else:
        res.append("Unknown compression "+`ifi.compression`)

    if ifi.filter==0:
        res.append("Adaptive filtering")
    else:
        res.append("Unknown filtering "+`ifi.filter`)

    if ifi.interlace==0:
        res.append("No interlacing")
    elif ifi.interlace==1:
        res.append("Adam7 interlacing")
    else:
        res.append("Unknown interlacing "+`ifi.interlace`)
    return "\n".join(res)
                   
def idimg_BCI(f):
    "Identify a Brew Compressed Image"
    if f.GetBytes(0,4)=="BCI\x00":
        d={'format': "BCI"}
        d['width']=f.GetLSBUint16(0x0e)
        d['height']=f.GetLSBUint16(0x10)
        d['bpp']=8
        d['ncolours']=f.GetLSBUint16(0x1a)
        d['_longdescription']=fmt_BCI
        for i in d.itervalues():
            if i is None:  return None
        ifi=ImgFileInfo(f,**d)
        return ifi
    return None

def fmt_BCI(ifi):
    "Long description for BCI"
    res=[ifi.shortdescription()]
    res.append("%d colour palette" % (ifi.ncolours,))
    return "\n".join(res)

def idimg_JPG(f):
    "Identify a JPEG image"
    # The people who did jpeg decided to see just how complicated an image
    # format they could make.
    if f.GetBytes(0,2)=="\xff\xd8":
        # in theory we could also parse EXIF information
        offset=2
        while True:
            # we just skip the segments until we find SOF0 (0xc0)
            # I can't figure out from the docs if we should also care about SOF1/SOF2 etc
            if f.GetByte(offset)!=0xff:
                return None
            id=f.GetByte(offset+1)
            offset+=2
            seglen=f.GetMSBUint16(offset)
            if seglen is None or id is None: return None
            if id!=0xc0:
                offset+=seglen
                continue
            offset+=2
            d={'format': 'JPEG'}
            d['bpp']=3*f.GetByte(offset)
            d['height']=f.GetMSBUint16(offset+1)
            d['width']=f.GetMSBUint16(offset+3)
            d['components']=f.GetByte(offset+5)
            d['_shortdescription']=fmts_JPG
            for i in d.itervalues():
                if i is None:  return None
            ifi=ImgFileInfo(f,**d)
            return ifi            
    return None

def fmts_JPG(ifi):
    res=[]
    res.append( "%d x %d" % (ifi.width, ifi.height) )
    res.append( ifi.format)
    if ifi.components==1:
        res.append("(greyscale)")
    elif ifi.components==3:
        res.append("(RGB)") # technically it is YcbCr ...
    elif ifi.components==4:
        res.append("(CMYK)")
    else:
        res.append("Unknown components "+`ifi.components`)
    return " ".join(res)

imageids=[globals()[f] for f in dir() if f.startswith("idimg_")]
def identify_imagefile(filename):
    fo=SafeFileWrapper(filename)
    for f in imageids:
        obj=f(fo)
        if obj is not None:
            return obj
    return ImgFileInfo(fo)

class AudioFileInfo:
    "Wraps information about an audio file"

    # These will always be present
    attrnames=("format", "size", "duration", "MAXSIZE")

    def __init__(self, f, **kwds):
        for a in self.attrnames:
            setattr(self, a, None)
        self.size=f.size
        self.__dict__.update(kwds)

    def shortdescription(self):
        v=getattr(self, "_shortdescription", None)
        if v is not None:
            return v(self)        
        res=[]
        if self.format is not None:
            res.append( self.format)
        if self.duration is not None:
            res.append( "%d seconds" % (self.duration,))

        if len(res):
            return " ".join(res)
        return "Unknown format"

    def longdescription(self):
        v=getattr(self, "_longdescription", None)
        if v is not None:
            return v(self)
        return self.shortdescription()

def idaudio_MIDI(f):
    "Identify a midi file"
    # http://www.borg.com/~jglatt/tech/midifile.htm
    #
    # You can't work out the length without working out
    # which track is the longest which you have to do by
    # parsing each note.
    if f.GetBytes(0,4)=="MThd" and f.GetMSBUint32(4)==6:
        d={'format': "MIDI"}
        d['type']=f.GetMSBUint16(8)
        d['numtracks']=f.GetMSBUint16(10)
        d['division']=f.GetMSBUint16(12)
        d['_shortdescription']=fmts_MIDI
        for i in d.itervalues():
            if i is None:  return None
        afi=AudioFileInfo(f,**d)
        return afi
    return None

def fmts_MIDI(afi):
    res=[]
    res.append( afi.format)
    res.append( "type "+`afi.type`)
    if afi.type!=0 and afi.numtracks>1:
        res.append("(%d tracks)" % (afi.numtracks,))
    # res.append("%04x" % (afi.division,))
    return " ".join(res)

def _getbits(start, length, value):
    assert length>0
    return (value>>(start-length+1)) & ((2**length)-1)

def getmp3fileinfo(filename):
    f=SafeFileWrapper(filename)
    return idaudio_MP3(f, True)


twooheightzeros="\x00"*208
def idaudio_MP3(f, returnframes=False):
    # http://mpgedit.org/mpgedit/mpeg_format/mpeghdr.htm

    idv3present=False
    id3v1present=False

    header=f.GetMSBUint32(0)

    # there may be ffmpeg output with 208 leading zeros for no apparent reason
    if header==0 and f.data.startswith(twooheightzeros):
        offset=208
    # there may be an id3 header at the begining
    elif header==0x49443303:
        sz=[f.GetByte(x) for x in range(6,10)]
        if len([zz for zz in sz if zz<0 or zz>=0x80]):
            return None
        sz=(sz[0]<<21)+(sz[1]<<14)+(sz[2]<<7)+sz[3]
        offset=10+sz
        idv3present=True
        header=f.GetMSBUint32(offset)
    else:
        offset=0

    frames=[]
    while offset<f.size:
        if offset==f.size-128 and f.GetBytes(offset,3)=="TAG":
            offset+=128
            id3v1present=True
            continue
        frame=MP3Frame(f, offset)
        if not frame.OK or frame.nextoffset>f.size:  break
        offset=frame.nextoffset
        frames.append(frame)

    if len(frames)==0: return

    if offset!=f.size:
        print "MP3 offset is",offset,"size is",f.size

    # copy some information from the first frame
    f0=frames[0]
    d={'format': 'MP3',
       'id3v1present': id3v1present,  # badly named ...
       'idv3present': idv3present,
       'unrecognisedframes': offset!=f.size,
       'version': f0.version,
       'layer': f0.layer,
       'bitrate': f0.bitrate,
       'samplerate': f0.samplerate,
       'channels': f0.channels,
       'copyright': f0.copyright,
       'original': f0.original}

    duration=f0.duration
    vbrmin=vbrmax=f0.bitrate
    
    for frame in frames[1:]:
        duration+=frame.duration
        if frame.bitrate!=f0.bitrate:
            d['bitrate']=0
        if frame.samplerate!=f0.samplerate:
            d['samplerate']=0
            vbrmin=min(frame.bitrate,vbrmin)
            vbrmax=max(frame.bitrate,vbrmax)
        if frame.channels!=f0.channels:
            d['channels']=0
      
    d['duration']=duration
    d['vbrmin']=vbrmin
    d['vbrmax']=vbrmax
    d['_longdescription']=fmt_MP3
    d['_shortdescription']=fmts_MP3

    if returnframes:
        d['frames']=frames

    return AudioFileInfo(f, **d)

def fmt_MP3(afi):
    res=[]
    res.append("MP3 (Mpeg Version %d Layer %d)" % (afi.version, afi.layer))
    res.append("%s %.1f Khz %0.1f seconds" % (["Variable!!", "Mono", "Stereo"][afi.channels], afi.samplerate/1000.0, afi.duration,))
    if afi.bitrate:
        res.append(`afi.bitrate`+" kbps")
    else:
        res.append("VBR (min %d kbps, max %d kbps)" % (afi.vbrmin, afi.vbrmax))
    if afi.unrecognisedframes:
        res.append("There are unrecognised frames in this file")
    if afi.idv3present:
        res.append("IDV3 tag present at begining of file")
    if afi.id3v1present:
        res.append("IDV3.1 tag present at end of file")
    if afi.copyright:
        res.append("Marked as copyrighted")
    if afi.original:
        res.append("Marked as the original")

    return "\n".join(res)

def fmts_MP3(afi):
    return "MP3 %s %dKhz %d sec" % (["Variable!!", "Mono", "Stereo"][afi.channels], afi.samplerate/1000.0, afi.duration,)


class MP3Frame:

    bitrates={
        # (version, layer): bitrate mapping
        (1, 1): [None, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448, None],
        (1, 2): [None, 32, 48, 56,  64,  80,  96, 112, 128, 160, 192, 224, 256, 320, 384, None],
        (1, 3): [None, 32, 40, 48,  56,  64,  80,  96, 112, 128, 160, 192, 224, 256, 320, None],
        (2, 1): [None, 32, 48, 56,  64,  80,  96, 112, 128, 144, 160, 176, 192, 224, 256, None],
        (2, 2): [None,  8, 16, 24,  32,  40,  48,  56,  64,  80,  96, 112, 128, 144, 160, None],
        (2, 3): [None,  8, 16, 24,  32,  40,  48,  56,  64,  80,  96, 112, 128, 144, 160, None],
        }

    samplerates={
        1: [44100, 48000, 32000, None],
        2: [22050, 24000, 16000, None]
        }

    def __init__(self, f, offset):
        self.OK=False
        header=f.GetMSBUint32(offset)
        if header is None: return
        # first 11 buts must all be set
        if _getbits(31,11, header)!=2047:
            return
        self.header=header
        # Version
        version=_getbits(20,2,header)
        if version not in (2,3):  # we don't support 'reserved' or version 2.5
            return
        if version==3: # yes, version 1 is encoded as 3
            version=1
        self.version=version
        # Layer
        layer=_getbits(18,2,header)
        if layer==0: return # reserved which we don't support
        if layer==1:
            self.layer=3
        elif layer==2:
            self.layer=2
        elif layer==3:
            self.layer=1
        self.crc=_getbits(16,1,header)
        self.bitrate=self.bitrates[(self.version, self.layer)][_getbits(15,4,header)]
        self.samplerate=self.samplerates[self.version][_getbits(11,2,header)]
        self.padding=_getbits(9,1,header)
        if self.layer==1:
            self.framelength=(12000*self.bitrate/self.samplerate+self.padding)*4
        else:
            self.framelength=144000*self.bitrate/self.samplerate+self.padding
        self.duration=self.framelength*8*1.0/(self.bitrate*1000)
        self.private=_getbits(8,1,header)
        self.channelmode=_getbits(7,2,header)
        if self.channelmode in (0,1,2):
            self.channels=2
        else:
            self.channels=1
        
        self.modeextenstion=_getbits(5,2,header)
        self.copyright=_getbits(3,1,header)
        self.original=_getbits(2,1, header)
        self.emphasis=_getbits(1,2, header)


        self.offset=offset
        self.nextoffset=offset+self.framelength
        if f.GetByte(self.nextoffset)!=0xff:
            # sometimes this ends up being off by one and I can't figure out why
            if f.GetBytes(self.nextoffset-1,2)=="\xff\xf3":
                self.nextoffset-=1
                self.framelength-=1
        self.OK=True

def idaudio_QCP(f):
    "Identify a Qualcomm Purevoice file"
    # http://www.faqs.org/rfcs/rfc3625.html
    #
    # Sigh, another format where you have no hope of being able to work out the length
    if f.GetBytes(0,4)=="RIFF" and f.GetBytes(8,4)=="QLCM":
        d={'format': "QCP"}
        
        # fmt section
        if f.GetBytes(12,4)!="fmt ":
            return None
        # chunksize is at 16, len 4
        d['qcpmajor']=f.GetByte(20)
        d['qcpminor']=f.GetByte(21)
        # guid is at 22
        d['codecguid']=(f.GetLSBUint32(22), f.GetLSBUint16(26), f.GetLSBUint16(28), f.GetMSBUint16(30), (long(f.GetMSBUint16(32))<<32)+f.GetMSBUint32(34))
        d['codecversion']=f.GetLSBUint16(38)
        name=f.GetBytes(40,80)
        zero=name.find('\x00')
        if zero>=0:
            name=name[:zero]
        d['codecname']=name
        d['averagebps']=f.GetLSBUint16(120)
        # packetsize is at 122, len 2
        # block size is at 124, len 2
        d['samplingrate']=f.GetLSBUint16(126)
        d['samplesize']=f.GetLSBUint16(128)

        d['_longdescription']=fmt_QCP
        for i in d.itervalues():
            if i is None:  return None
        afi=AudioFileInfo(f,**d)
        return afi
    return None

def fmt_QCP(afi):
    res=["QCP %s" % (afi.codecname,)]
    res.append("%d bps %d Hz %d bits/sample" % (afi.averagebps, afi.samplingrate, afi.samplesize))
    codecguid=afi.codecguid
    if   codecguid==( 0x5e7f6d41, 0xb115, 0x11d0, 0xba91, 0x00805fb4b97e ):
        res.append("QCELP-13K V"+`afi.codecversion` + "  (guid 1)")
    elif codecguid==( 0x5e7f6d42, 0xb115, 0x11d0, 0xba91, 0x00805fb4b97e ):
        res.append("QCELP-13K V"+`afi.codecversion` + "  (guid 2)")
    elif codecguid==( 0xe689d48d, 0x9076, 0x46b5, 0x91ef, 0x736a5100ceb4 ):
        res.append("EVRC V"+`afi.codecversion`)
    elif codecguid==( 0x8d7c2b75, 0xa797, 0xed49, 0x985e, 0xd53c8cc75f84 ):
        res.append("SMV V"+`afi.codecversion`)
    else:
        res.append("Codec Guid {%08X-%04X-%04X-%04X-%012X} V%d" % (afi.codecguid+(afi.codecversion,)))
    res.append("QCP File Version %d.%d" % (afi.qcpmajor, afi.qcpminor))
    
    return "\n".join(res)

def idaudio_PMD(f):
    "Identify a PMD/CMX file"
    # There are no specs for this file format.  From 10 minutes of eyeballing, it seems like below.
    # Each section is a null terminated string followed by a byte saying how long the data is.
    # The length is probably some sort of variable length encoding such as the high bit indicating
    # the last byte and using 7 bits.
    #
    # offset contents -- comment
    #      0 cmid     -- file type id
    #      4 \0\0     -- no idea
    #      6 7*?      -- file lengths and pointers
    #     13 vers\0   -- version section
    #     18 \x04     -- length of version section
    #     19 "string" -- a version number that has some correlation with the pmd version number
    #
    #  Various other sections that cover the contents that don't matter for identification
    if f.GetBytes(0,4)=="cmid" and f.GetBytes(13,5)=="vers\0":
        verlen=f.GetByte(18)
        verstr=f.GetBytes(19,verlen)

        return AudioFileInfo(f, **{'format': 'PMD', 'fileversion': verstr, '_shortdescription': fmts_PMD} )

def fmts_PMD(afi):
    return "%s v %s" % (afi.format, afi.fileversion)
    

audioids=[globals()[f] for f in dir() if f.startswith("idaudio_")]
def identify_audiofile(filename):
    fo=SafeFileWrapper(filename)
    for f in audioids:
        obj=f(fo)
        if obj is not None:
            return obj
    return AudioFileInfo(fo)
