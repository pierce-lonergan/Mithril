#include <stdatomic.h>
#include <stdint.h>
static atomic_int counter;
int atomic_probe(int x) {
    atomic_fetch_add_explicit(&counter, x, memory_order_relaxed);
    return atomic_load_explicit(&counter, memory_order_acquire);
}
