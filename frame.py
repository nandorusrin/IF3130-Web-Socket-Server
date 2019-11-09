import random
import struct

class Frame:

	# OPCODE : define the interpretation of Payload Data (4 bits)
	con_frame = 0x0	# continue
	txt_frame = 0x1 # text frame
	bin_frame = 0x2 # binary frame
	cls_frame = 0x8 # close
	ping_frame = 0x9 # ping 
	pong_frame = 0xa # pong

	# MASK
	UNMASKED_BIT = 0x0
	MASKED_BIT = 0x1

	#MAX UINT
	SIZE_UINT16 = 65535
	SIZE_UINT64 = 18446744073709551615

	'''
	Atribut Kelas
	1. FIN (1 bit)
	2. RSV1 (1 bit)
	3. RSV2 (1 bit)
	4. RSV3 (1 bit)
	5. opcode (4 bit)
	6. MASK (1 bit)
	7. payload length (7 bit)
	8. Mask Key (32 bit)
	9. extended payload data
	10. payload data (maks 125 byte)

	'''
	def __init__ (self, _final=0, _opcode=0x0, _payload=b'', _masked=False, _rsv1=0, _rsv2=0, _rsv3=0):
		# set FIN
		self.FIN = _final
		self.rsv1 = _rsv1
		self.rsv2 = _rsv2
		self.rsv3 = _rsv3
		self.opcode = _opcode

		if (_masked):	# frame is masked
			self.MASK = self.MASKED_BIT
			self.MASK_KEY = random.getrandbits(32)
		else:	# frame is not masked
			self.MASK = self.UNMASKED_BIT

		self.payload_len = len(_payload)
		self.payload = _payload

	# MASKING, return a binary var
	def toMask(self):
		# PRECONDITION
		#  - self.MASKED
		#  - self.payload

		tempKey = struct.pack('>I', self.MASK_KEY)
		result = b''
		for i in range (0, len(self.payload), 1):
			# print(ord(self.payload[i]))
			if (self.opcode == Frame.txt_frame):
				temp = ord(self.payload[i]) ^ tempKey[i % 4]
			elif (self.opcode == Frame.bin_frame):
				temp = self.payload[i] ^ tempKey[i % 4]
			temp = struct.pack('>B', temp)
			result += temp

		# print("this is masked")
		return result

	@staticmethod
	def toUnmask(mask_key, param):
		tempKey = struct.pack('>I', mask_key)
		result = b''
		for i in range (0, len(param), 1):
			temp = param[i] ^ tempKey[i % 4]
			result += struct.pack('>B', temp)

		# print("this is unmasked")
		return result


	def toFrame(self):
		# concatenate FIN, RSV1, RSV2, RSV3, and opcode
		# assuming RSV1, RSV2, RSV3 = 0 all
		concat_1 = (self.FIN << 7) | (self.rsv1 << 6) | (self.rsv2 << 5) | (self.rsv3 << 4) | self.opcode
		# print(self.FIN, self.opcode)
		concat_1 = bytearray(struct.pack('>B', concat_1))

		result = concat_1

		# concatenate MASK and payload len
		# categorized into 3 part
		concat_2 = self.MASK << 7

		if (self.payload_len >= 0 and self.payload_len <= 125):
			concat_2 = concat_2 | self.payload_len
			# print(self.MASK, self.payload_len)
			concat_2 = bytearray(struct.pack('>B', concat_2))

		elif (self.payload_len <= Frame.SIZE_UINT16):
			concat_2 = concat_2 | 0x7e
			# print(self.MASK, self.payload_len)
			concat_2 = bytearray(struct.pack('>B', concat_2))
			concat_2_ext = bytearray(struct.pack('>H', self.payload_len))
			concat_2 = concat_2 + concat_2_ext

		elif (self.payload_len <= Frame.SIZE_UINT64):
			concat_2 = concat_2 | 0x7f
			# print(self.MASK, self.payload_len)
			concat_2 = bytearray(struct.pack('>B', concat_2))
			concat_2_ext = bytearray(struct.pack('>Q', self.payload_len))
			concat_2 = concat_2 + concat_2_ext

		result += concat_2

		# packing MASK_KEY
		if (self.MASK == self.MASKED_BIT):
			concat_3 = struct.pack('>I', self.MASK_KEY)
			# print('concat 3 : ', self.MASK_KEY)
			concat_3 = bytearray(concat_3)

			result += concat_3

		# packing payload
		if (self.MASK == self.MASKED_BIT):
			concat_4 = self.toMask()
			result += concat_4
		else:
			concat_4 =  self.payload
			# print(concat_4[2:10])
			if (self.opcode == Frame.txt_frame):
				concat_4 = concat_4.encode(encoding = 'UTF-8', errors='strict')
			result += concat_4

		return result
	
	def getPayload(self):
		return self.payload

	@staticmethod
	def toUnframe(recv):
		# Unpack FIN, RSV1, RSV2, RSV3, and opcode
		concat_1 = bytearray(recv)[0]
		_FIN = concat_1 >> 7
		rsv1 = concat_1 >> 6 & 0x1
		rsv2 = concat_1 >> 5 & 0x1
		rsv3 = concat_1 >> 4 & 0x1
		_opcode = concat_1 & 0xf
		# print(_FIN, _opcode)

		# Unpack MASK and Payload_len
		concat_2 = bytearray(recv)[1]
		_MASK = concat_2 >> 7
		_payload_len = concat_2 & 127

		appendedBase = 2
		# looking for extended payload len
		if (_payload_len == 126):
			_payload_len = (struct.unpack('>H', bytearray(recv[2:4])))[0]
			appendedBase = 4

		elif (_payload_len == 127):
			_payload_len = (struct.unpack('>Q', bytearray(recv[2:10])))[0]
			appendedBase = 10

		# Unpack the MASK KEY and Payload
		_MASK_KEY = -1
		if (_MASK == Frame.MASKED_BIT):
			_MASK_KEY = (struct.unpack('>I', bytearray(recv[appendedBase : appendedBase + 4])))[0]
			appendedBase += 4

		_payload = recv[appendedBase : appendedBase + _payload_len]

		if (_MASK == Frame.MASKED_BIT):
			_payload = Frame.toUnmask(_MASK_KEY, _payload)

		if (_opcode == Frame.txt_frame):
			_payload = _payload.decode(encoding='UTF-8', errors='strict')
		else:
			_payload = bytes(_payload)

		# print(_payload[2:10])
		# print(_MASK, _payload_len)
		# self, _final, _opcode, _payload, _mask=-1
		return Frame(_FIN, _opcode, _payload, _MASK_KEY, rsv1, rsv2, rsv3)

	def getMaskKey():
		return self.MASK_KEY

	def toPrint(self):
		print('FIN		: ', self.FIN)
		print('RSV:', self.rsv1, self.rsv2, self.rsv3)
		print('OP		: ', self.opcode)
		if (self.MASK == self.MASKED_BIT):
			print('MASK KEY	: ', self.MASK_KEY)
		print('LEN		: ', self.payload_len)

	# function for assertion
	def isMasked(self):
		return (self.MASK == self.MASKED_BIT)
	