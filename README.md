# tubes-jarkom-2
Custom Web Server using WebSocket

# petunjuk pemakaian Frame

CTOR:
frame = Frame(a, b, c, d)
a = FIN
b = jenis fram
Frame.txt_frame = text frame
Frame.bin_frame = binary frame
Frame.con_frame = continuation frame (masih blum ngerti)
Frame.cls_frame = close-connection frame
Frame.ping_frame = ping frame
Frame.pong_frame = pong frame (untuk respon 'ping')

c = file biner, kalo mau text file, bisa, cuman jangan lupa ganti jenis frame jadi Frame.txt_frame, biar nnti di-encode

d = apakah sudah ada mask key, kalo awal buat frame, tulis '-1' tanpa kutip, nanti akan digenerate otomatis

Semua frame selagi belum dipacking, payload belum di-mask, TAPI sudah ada MASK KEY, mau liat pake getMaskKey()

kalo mau dapat frame yang siap kirim, pake method toFrame(True/False). True/False ini artinya "mau dimasking ga? kalo mau True"

frame_01 = Frame(bla bla bla)
ecek_ecek = frame_01.toFrame()

kalo mau dapat frame yang direceive, pake method static toUnframe(obj)

frame_02 = Frame.toUnframe(ecek_ecek)

Kalo mau liat dalamnya isi apa aja, pake method toPrint()

frame_02.toPrint()

dalam ini ada 6 file utk testing, 3 file binary, 3 file text, masing2 dengan size yang berbeda utk skenario beda2.

testing ada di testFile.py

Sumber
https://tools.ietf.org/html/rfc6455
https://pypi.org/project/websockets/
