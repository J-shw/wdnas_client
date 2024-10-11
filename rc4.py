import base64

def encRC4(uName, pwd):
    return base64.b64encode(rc4(uName, pwd).encode('utf-8')).decode('utf-8')

def decRC4(uName, pwd):
    return rc4(uName, base64.b64decode(pwd))

def rc4(key, text):
    s = [i for i in range(256)]
    j = 0
    for i in range(256):
        j = (j + s[i] + ord(key[i % len(key)])) % 256
        s[i], s[j] = s[j], s[i]
    i = j = 0
    result = []
    for char in text:
        i = (i + 1) % 256
        j = (j + s[i]) % 256
        s[i], s[j] = s[j], s[i]
        k = s[(s[i] + s[j]) % 256]
        result.append(chr(ord(char) ^ k))
    return ''.join(result)