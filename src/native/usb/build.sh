PYTHONVER=python2.3
INCLUDEDIR=`$PYTHONVER -c "import distutils.sysconfig; print distutils.sysconfig.get_python_inc()"`

swig -python -I/usr/include libusb.i

gcc -Wall -fno-strict-aliasing -O2 -g  -shared  -I $INCLUDEDIR -o _libusb.so libusb_wrap.c -lusb 
strip _libusb.so
