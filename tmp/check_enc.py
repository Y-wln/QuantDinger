import sys
print("stdout:", sys.stdout.encoding)
print("fs:", sys.getfilesystemencoding())
print("default:", sys.getdefaultencoding())
print("locale:", __import__("locale").getpreferredencoding())
