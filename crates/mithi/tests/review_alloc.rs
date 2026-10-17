//! C-ALLOC (note section 12): every std operation that may allocate from `Global` carries
//! `alloc(Global)` in its row. Review 2026-10-16: `collect`, `to_vec`, `clone` of a Vec or String
//! and `format!` did not, so a `policy fn` could allocate. This test lists the builtins: a new one
//! that returns or grows a heap value fails here until it is classified.

use mithi::check::{check, Config};
use mithi::program::Label;

/// Builtins that allocate (their declared row must contain alloc(Global)).
const ALLOCATING: &[&str] = &[
    "vec_from_array", "vec_repeat", "string_write_fmt", "vec_with_capacity", "vec_push", "vec_insert",
    "vec_extend_from_slice", "vec_resize", "string_push_str", "str_to_string", "slice_to_vec", "iter_collect",
];

/// Builtins whose signature mentions a heap type but do not allocate (Rust's own behaviour:
/// `Vec::new` and `String::new` do not allocate; the others move or view existing storage).
const NON_ALLOCATING: &[&str] = &[
    "vec_new", "string_new", "buf_from_vec", "vec_into_iter", "vec_pop", "vec_clear", "vec_truncate", "vec_remove",
    "vec_swap_remove", "vec_retain", "vec_as_slice", "vec_as_mut_slice", "string_len", "string_as_str", "clone",
    "eq", "ne", "partial_cmp", "cmp", "default", "into", "drop", "mem_swap", "mem_replace", "mem_take", "mem_forget",
];

#[test]
fn heap_builtins_carry_alloc_global() {
    let c = check(&Config::default());
    let mut bad = vec![];
    for (fid, f) in c.program.fns.iter().enumerate() {
        let Some(b) = f.builtin.as_deref() else { continue };
        let row = c.facts.rows.get(&(fid as u32)).cloned().unwrap_or_default();
        let has = row.contains(&Label::Alloc("Global".into()));
        if ALLOCATING.contains(&b) {
            if !has {
                bad.push(format!("{b} ({}) allocates but its row lacks alloc(Global)", f.path));
            }
            continue;
        }
        let mut heap = false;
        let mut tys = vec![f.ret.clone()];
        tys.extend(f.params.iter().map(|p| p.ty.clone()));
        for t in &tys {
            t.walk(&mut |x| {
                if let mithi::types::Ty::Adt(a, _) = x {
                    if matches!(c.program.adts[*a as usize].lang.as_deref(), Some("Vec") | Some("String") | Some("Buf")) {
                        heap = true;
                    }
                }
            });
        }
        if heap && !has && !NON_ALLOCATING.contains(&b) {
            bad.push(format!("{b} ({}) mentions a heap type: classify it as allocating or not", f.path));
        }
    }
    assert!(bad.is_empty(), "{}", bad.join("\n"));
}
