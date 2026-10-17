/* x2sha256.h -- minimal SHA-256 (FIPS 180-4) for stream hashes and file hashes. Checked against the
 * FIPS known answers ("", "abc", the 448-bit message) by `x2fuzz selftest`. */
#ifndef X2SHA256_H
#define X2SHA256_H
#include <stddef.h>
#include <stdint.h>

typedef struct { uint32_t h[8]; uint64_t len; uint8_t buf[64]; size_t n; } x2sha;

void x2sha_init(x2sha *s);
void x2sha_update(x2sha *s, const void *p, size_t n);
void x2sha_final(x2sha *s, uint8_t out[32]);
void x2sha_hex(const uint8_t d[32], char out[65]);

#endif
