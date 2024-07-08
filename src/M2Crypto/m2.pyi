from typing import Optional

from M2Crypto import ASN1, BIO, types as C

def asn1_integer_cmp(a1: C.ASN1_Integer, a2: C.ASN1_Integer) -> int: ...

def asn1_integer_free(a: C.ASN1_Integer) -> None: ...

def asn1_integer_get(a: C.ASN1_Integer) -> Optional[C.ASN1_Integer,int]: ...

def asn1_integer_set(a: C.ASN1_Integer, v: int) -> int: ...

def asn1_object_free(a: C.ASN1_Object) -> None: ...

def asn1_string_free(a: C.ASN1_String) -> None: ...

def asn1_string_print(out: C.BIO, s: C.ASN1_String) -> int: ...

def asn1_string_print_ex(out: C.BIO, s: C.ASN1_String, flags: int) -> int: ...

def asn1_time_free(a: C.ASN1_TIME) -> None: ...

def asn1_time_new() -> C.ASN1_TIME: ...

def asn1_time_print(out: C.BIO, s: C.ASN1_TIME) -> int: ...

def asn1_time_set(a: C.ASN1_TIME, t: int) -> C.ASN1_TIME: ...

def asn1_time_set_string(a: C.ASN1_TIME, s: str) -> int: ...

def asn1_time_type_check(a: C.ASN1_TIME) -> int: ...

bio_close: int = 0x01

def bio_ctrl_get_write_guarantee(a: C.BIO) -> int: ...

def bio_ctrl_pending(a: C.BIO) -> int: ...

def bio_do_handshake(a: C.BIO) -> int: ...

def bio_f_buffer() -> C.BIO_METHOD: ...  # FIXME

def bio_f_cipher() -> C.BIO_METHOD: ...  # FIXME

def bio_flush(b: C.BIO) -> int: ...

# See gl#m2crypto/m2crypto#228 and gl#m2crypto/m2cryptor#205
def engine_ctrl_cmd_string(e: Engine.ENGINE, cmd_name: str, arg: str, cmd_optional: int) -> None: ...

def x509_free(a: C.X509) -> None: ...

def x509_new() -> C.X509: ...
