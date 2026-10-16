#include <immintrin.h>
__m512i vnni_probe(__m512i acc, __m512i a, __m512i b) { return _mm512_dpbusd_epi32(acc, a, b); }
float fpc(float a, float b, float c) { return a * b + c; }
