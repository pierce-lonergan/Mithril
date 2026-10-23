/* Minimal <math.h> for the CRT-free X3 test DLL: only what the extracted Hearth scalar code uses.
 * fabsf is a compiler builtin (lowered to a sign-bit mask); no libm call is made. */
#ifndef X3_SHIM_MATH_H
#define X3_SHIM_MATH_H
float fabsf(float x);
#endif
