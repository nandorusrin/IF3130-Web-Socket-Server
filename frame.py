class Frame:

	# OPCODE
	conFrame = 0x0
	txtFrame = 0x1
	binFrame = 0x2
	clsFrame = 0x8
	pingFrame = 0x9
	pongFrame = 0xa

	# MASK
	MASKED = 0x1

	'''
	Atribut Kelas
	1. FIN (1 bit)
	2. RSV1 (1 bit)
	3. RSV2 (1 bit)
	4. RSV
	'''