// D-EVICT-1 correct-but-non-reference (Rust): iterator min_by_key on (Reverse(age), id).
// CANARY: expected PASS.
use crate::prelude::*;
use std::cmp::Reverse;

pub fn pick_victim(slots: &[SlotView], now: u64) -> Option<u32> {
    slots
        .iter()
        .filter(|s| !s.pinned && s.refs == 0 && !s.loading)
        .min_by_key(|s| (Reverse(now - s.last_use), s.id))
        .map(|s| s.id)
}
