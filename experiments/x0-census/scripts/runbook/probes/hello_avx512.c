#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <immintrin.h>
int main(void) {
    __m512 a = _mm512_set1_ps(2.0f);
    __m512 b = _mm512_sqrt_ps(a);
    float out[16];
    _mm512_storeu_ps(out, b);
    uint64_t u = 42;
    printf("sqrt(2)=%.6f libm=%.6f u=%llu\n", out[0], sqrt(2.0), (unsigned long long)u);
    return 0;
}
