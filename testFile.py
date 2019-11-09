import os
import random
from frame import Frame

# stringTest = open("125.txt", "rb").read()

# testing payload length to be exact number as printed string
# binaryTest = open("0", "rb").read()

# statInfo = os.stat("126.txt")
# print(len(stringTest)/1000, ' ', statInfo.st_size)
# testing randomizing 32-bit MASK KEY
# x = random.getrandbits(32)
# print(bin(x))
# print(bin((x & 0xff000000) >> 24))
# print(bin(x >> 24))


# y = x >> 24
# z = y ^ ord('o')
# print(bin(y), bin(ord('u')))
# print(z)
# z = z ^ y
# print(bin(y), bin(z))
# print(chr(z))

objFrame = Frame(1, Frame.bin_frame, b'halo', _masked=True)

print('objFrame')
objFrame.toPrint()
print(objFrame.getPayload())
binFrame= objFrame.toFrame()
print()

print('clsFrame')
clsFrame = Frame.toUnframe(binFrame)
clsFrame.toPrint()
print(clsFrame.getPayload())
