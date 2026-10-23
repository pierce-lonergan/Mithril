/* Declarations only, so that clang's <mm_malloc.h> parses in hosted mode; never called. */
#ifndef X3_SHIM_STDLIB_H
#define X3_SHIM_STDLIB_H
#include <stddef.h>
void *malloc(size_t n);
void free(void *p);
#endif
