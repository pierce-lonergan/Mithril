// D-ROUTE-2 (development item). Write the body; keep the signature.
use crate::prelude::*;

/// Preconditions: 1 <= n_group <= 16; n_group <= sel.len() <= 256; sel.len() % n_group == 0;
/// 1 <= topk_group <= n_group; k <= sel.len(); ids.len() == k.
pub fn group_topk(sel: &[f32], n_group: usize, topk_group: usize, k: usize, ids: &mut [u32]) {
    todo!("group_topk")
}
