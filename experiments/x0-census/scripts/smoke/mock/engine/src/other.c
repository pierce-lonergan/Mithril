/* other.c -- X0 census MOCK, a translation unit outside the census (NOT Hearth code; see hx_quant.h).
 * It has no per-file options, so the Visual Studio generator compiles it in the same CL task as quant.c, as
 * Hearth's build compiles pool.c, quant.c and the other common-flag files in one CL invocation: the driver's
 * MSBuild records must then pick quant.c's own line, section of the output and object out of the batch. */
#include "hx_quant.h"

int x0mock_other(int x)
{
    return x * 3 + 1;
}
