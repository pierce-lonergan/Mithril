#include <stdio.h>
#include <math.h>
#include <stdint.h>
#include <immintrin.h>
int main(void) {
    __m256 a = _mm256_set1_ps(2.0f);
    __m256 b = _mm256_sqrt_ps(a);
    float out[8];
    _mm256_storeu_ps(out, b);
    uint32_t u = 7;
    printf("sqrt(2)=%.6f lib=%.6f u=%u\n", out[0], sqrt(2.0), u);
    return 0;
}
