// D-EVICT-1 (development item). Write the body; keep the signature.
use crate::prelude::*;

/// Precondition: every slot's last_use <= now. Must not read a clock.
pub fn pick_victim(slots: &[SlotView], now: u64) -> Option<u32> {
    todo!("pick_victim")
}
