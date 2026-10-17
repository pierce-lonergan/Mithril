/* xed_tables.c -- dump XED's own iform/iclass/extension/isa-set/category/attribute/exception and
 * operand tables (X0 classify.py / baseline.py input). Not Hearth code. Links against libxed. */
#include "xed/xed-interface.h"
#include <stdio.h>

int main(void) {
    unsigned i, j, a, k;
    const xed_inst_t *base;
    xed_tables_init();
    printf("VERSION\t%s\n", xed_get_version());
    for (i = 1; i < (unsigned)XED_IFORM_LAST; i++) {
        xed_iform_enum_t f = (xed_iform_enum_t)i;
        printf("IFORM\t%s\t%s\t%s\t%s\t%s\n", xed_iform_enum_t2str(f),
               xed_iclass_enum_t2str(xed_iform_to_iclass(f)),
               xed_category_enum_t2str(xed_iform_to_category(f)),
               xed_extension_enum_t2str(xed_iform_to_extension(f)),
               xed_isa_set_enum_t2str(xed_iform_to_isa_set(f)));
    }
    for (i = 1; i < (unsigned)XED_ICLASS_LAST; i++)
        printf("ICLASS\t%s\n", xed_iclass_enum_t2str((xed_iclass_enum_t)i));
    base = xed_inst_table_base();
    for (j = 0; j < XED_MAX_INST_TABLE_NODES; j++) {
        const xed_inst_t *p = base + j;
        xed_iform_enum_t f = xed_inst_iform_enum(p);
        if (f == XED_IFORM_INVALID) continue;
        printf("INST\t%u\t%s\t%s\tATTR:", j, xed_iform_enum_t2str(f), xed_exception_enum_t2str(xed_inst_exception(p)));
        for (a = 1; a < (unsigned)XED_ATTRIBUTE_LAST; a++)
            if (xed_inst_get_attribute(p, (xed_attribute_enum_t)a)) printf(" %s", xed_attribute_enum_t2str((xed_attribute_enum_t)a));
        printf("\tOPS:");
        for (k = 0; k < xed_inst_noperands(p); k++) {
            const xed_operand_t *o = xed_inst_operand(p, k);
            printf(" %s/%s/%s/%s/%s", xed_operand_enum_t2str(xed_operand_name(o)),
                   xed_operand_visibility_enum_t2str(xed_operand_operand_visibility(o)),
                   xed_operand_action_enum_t2str(xed_operand_rw(o)),
                   xed_operand_element_xtype_enum_t2str(xed_operand_xtype(o)),
                   xed_operand_width_enum_t2str(xed_operand_width(o)));
        }
        printf("\n");
    }
    for (a = 1; a < (unsigned)XED_EXCEPTION_LAST; a++)
        printf("EXCEPTION\t%s\n", xed_exception_enum_t2str((xed_exception_enum_t)a));
    for (a = 1; a < (unsigned)XED_ATTRIBUTE_LAST; a++)
        printf("ATTRIBUTE\t%s\n", xed_attribute_enum_t2str((xed_attribute_enum_t)a));
    return 0;
}
