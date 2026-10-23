/* Minimal <string.h> for the CRT-free X3 test DLL (laptop has no Windows SDK); see rt.c. */
#ifndef X3_SHIM_STRING_H
#define X3_SHIM_STRING_H
#include <stddef.h>
void *memcpy(void *dst, const void *src, size_t n);
void *memmove(void *dst, const void *src, size_t n);
void *memset(void *dst, int c, size_t n);
int memcmp(const void *a, const void *b, size_t n);
#endif
