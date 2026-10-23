/* Declarations only, so that clang's <mm_malloc.h> parses in hosted mode; never called. */
#ifndef X3_SHIM_MALLOC_H
#define X3_SHIM_MALLOC_H
#include <stddef.h>
void *_aligned_malloc(size_t n, size_t align);
void _aligned_free(void *p);
#endif
