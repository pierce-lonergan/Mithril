// MUTANT loading_ignored: slots that are still loading are treated as candidates. CANARY: expected FAIL.
use crate::prelude::*;

pub fn pick_victim(slots: &[SlotView], now: u64) -> Option<u32> {
    let mut best: Option<(u64, u32)> = None;
    for s in slots {
        if s.pinned || s.refs > 0 {
            continue;
        }
        let age = now - s.last_use;
        best = match best {
            None => Some((age, s.id)),
            Some((ba, bid)) => {
                if age > ba || (age == ba && s.id < bid) { Some((age, s.id)) } else { Some((ba, bid)) }
            }
        };
    }
    best.map(|(_, id)| id)
}
