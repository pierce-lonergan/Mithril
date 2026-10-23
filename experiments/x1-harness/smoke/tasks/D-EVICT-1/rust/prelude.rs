//! D-EVICT-1 prelude (read-only; the crate's `prelude` module). Slot views as the store shows them.
#![allow(dead_code)]

#[derive(Clone, Copy)]
pub struct SlotView {
    pub id: u32,
    pub pinned: bool,
    pub refs: u32,
    pub loading: bool,
    pub last_use: u64,
}
