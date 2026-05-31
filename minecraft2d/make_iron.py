import struct, zlib

def create_png(width, height, pixels):
    def chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    raw = b''
    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            r, g, b, a = pixels[y * width + x]
            raw += struct.pack('BBBB', r, g, b, a)
    idat = chunk(b'IDAT', zlib.compress(raw))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

w, h = 16, 16
colors = {
    '.': (0,0,0,0),
    '#': (40,40,48,255),
    '@': (180,184,192,255),
    '+': (160,164,172,255),
    '-': (120,124,132,255),
}

rows = [
    '................',
    '.....#####......',
    '....@@@@@@@.....',
    '....@@@@@@@.....',
    '...@@@@@@@@@....',
    '...@@@-@@@@@....',
    '...@@@@@@-@@....',
    '...@@@@@@@@@....',
    '...@@@-@@@@@....',
    '...@@@@@@-@@....',
    '....@@@@@@@.....',
    '....@@@@@@@.....',
    '.....#####......',
    '................',
    '................',
    '................',
]

pix = []
for row in rows:
    for ch in row:
        pix.append(colors[ch])

png = create_png(w, h, pix)
with open('static/img/iron.png', 'wb') as f:
    f.write(png)
print('OK')
