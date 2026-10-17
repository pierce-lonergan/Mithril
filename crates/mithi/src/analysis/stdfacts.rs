//! Checker facts about std builtins: may_trap, the NaN rule, NaN observers, false-friend classes.
//! Sources: note sections 5.0 (cls), 5.3 (nanrule, observers), 5.10 (may_trap), 12 (C-EXACT-STD).

/// May a builtin trap (given its `requires`, which callers assert)?
pub fn may_trap(name: &str) -> bool {
    matches!(
        name,
        "opt_unwrap" | "opt_expect" | "res_unwrap" | "res_expect" | "vec_remove" | "vec_insert" | "slice_swap" | "slice_copy_from_slice"
            | "slice_split_at" | "slice_split_at_mut" | "slice_chunks" | "slice_windows" | "vec_swap_remove" | "int_pow" | "int_abs" | "iter_step_by" | "string_write_fmt"
            // integer sums and products trap on overflow (FF-OVF: trap in every build)
            | "iter_sum" | "iter_product"
            // canon_v1::expf and cr::* are typed but not executed by mithi v0 (host limit, not a trap)
    )
}

/// The NaN rule of a float-producing builtin: Some(true) = canon, Some(false) = raw,
/// None = selection/copy (passes its inputs' bit through).
pub fn nanrule(name: &str) -> Option<bool> {
    match name {
        "canon_nan" => Some(true),
        // FF-NANMAX pins f32::max and f32::min: the result is a non-NaN operand or the canonical NaN
        "f32_max" | "f32_min" => Some(true),
        "f32_from_bits" | "f64_from_bits" => Some(false),
        // selection and copies pass the bit through
        "opt_unwrap" | "opt_expect" | "opt_unwrap_or" | "res_unwrap" | "res_expect" | "res_unwrap_or" | "slice_first" | "slice_last" | "slice_get" | "vec_pop"
        | "slice_get_mut" | "vec_swap_remove" | "opt_unwrap_or_else" | "res_unwrap_or_else"
        | "vec_remove" | "iter_next" | "iter_max_by" | "iter_min_by" | "iter_max_by_key" | "iter_min_by_key" | "iter_last" | "iter_nth" | "iter_find"
        | "mem_replace" | "mem_take" | "clone" | "hint_get" | "opt_take" | "cmp_min" | "cmp_max" | "ord_max" | "ord_min" => None,
        _ => Some(false),
    }
}

/// NaN observers (note section 5.3, F-13): they expose payload or sign of a raw NaN.
pub fn is_observer(name: &str) -> bool {
    matches!(
        name,
        "f32_to_bits" | "f64_to_bits" | "f32_is_sign_positive" | "f32_is_sign_negative" | "f32_copysign" | "f32_total_cmp" | "f64_total_cmp"
    )
}

/// Builtins whose reads carry `nondet` taint through the `time` label (FF-CLOCK; note section 5.3).
pub fn reads_clock(name: &str) -> bool {
    matches!(name, "instant_now" | "clock_now_ns")
}

/// FF rows whose class depends on the grade context (note section 5.0).
pub enum FfClass {
    Sum,
    Ties,
    Exp,
    Powi,
    Clock,
}

pub fn ff_class(name: &str) -> Option<FfClass> {
    Some(match name {
        "iter_sum" | "iter_product" | "iter_fold" => FfClass::Sum,
        "iter_max_by" | "iter_min_by" | "iter_min_by_key" | "iter_max_by_key" | "slice_sort_by" => FfClass::Ties,
        "f32_exp" | "f32_ln" | "f32_sin" | "f32_cos" | "f32_tanh" | "f32_powf" | "f64_exp" => FfClass::Exp,
        "f32_powi" => FfClass::Powi,
        "instant_now" | "clock_now_ns" => FfClass::Clock,
        _ => return None,
    })
}

/// Builtins that run a closure argument: (closure argument position, runs it under α_self).
pub fn runs_closure(name: &str) -> Option<usize> {
    match name {
        "mutex_with_lock" | "opt_map" | "opt_and_then" | "res_map_err" => Some(1),
        "opt_unwrap_or_else" | "opt_ok_or_else" | "res_unwrap_or_else" | "vec_retain" => Some(1),
        "opt_map_or" => Some(2),
        "iter_max_by_key" | "iter_min_by_key" | "iter_max_by" | "iter_min_by" | "iter_for_each" | "iter_any" | "iter_all" | "iter_position" | "iter_find" => Some(1),
        "iter_fold" => Some(2),
        "slice_sort_by" | "slice_sort_by_key" => Some(1),
        _ => None,
    }
}

/// Lazy adapters that store their closure (note section 5.7).
pub fn stores_closure(name: &str) -> Option<usize> {
    match name {
        "iter_map" | "iter_filter" | "iter_filter_map" => Some(1),
        _ => None,
    }
}

/// Builtins that discard elements and so keep the ¬Linear bound on the element type (F-41).
pub fn discards_elements(name: &str) -> bool {
    matches!(name, "drop" | "mem_forget" | "mem_take" | "vec_clear" | "vec_truncate" | "vec_retain")
        || name.starts_with("iter_")
}
