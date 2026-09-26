"""Windows user-bound DPAPI storage. No plaintext credentials on disk."""
import ctypes
from ctypes import wintypes
from pathlib import Path
TOKEN=Path(__file__).resolve().parents[1]/'local-data'/'github.dpapi'

class Blob(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]

def protect(data,decrypt=False):
    buffer=ctypes.create_string_buffer(data)
    source=Blob(len(data),ctypes.cast(buffer,ctypes.POINTER(ctypes.c_ubyte)))
    output=Blob()
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[ctypes.c_void_p]
    fn=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(output)):
        raise OSError('Windows güvenli anahtar deposu açılamadı')
    try:
        return ctypes.string_at(output.data,output.size)
    finally:
        kernel.LocalFree(output.data)

def save_token(token):
    TOKEN.parent.mkdir(exist_ok=True)
    encrypted=protect(token.encode())
    temp=TOKEN.with_suffix('.tmp');temp.write_bytes(encrypted);temp.replace(TOKEN)

def load_token():
    return protect(TOKEN.read_bytes(),True).decode() if TOKEN.exists() else ''
