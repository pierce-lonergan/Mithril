//! X4 measurement service v0 -- the orchestrator's statistical and control core (F0; trusted, frozen,
//! <= 1500 line-reviewed lines [target], 03 section 14). MEASUREMENT-SERVICE.md.
//!
//! The platform-independent core (quantity, eprocess, stats, scheduler, proto, profile) is fully unit
//! tested and differentially tested against the Python reference (tests/golden_diff.rs). The Windows
//! launcher (sandbox) and the profile reader (profile_win) are thin adapters compiled only on Windows.

pub mod eprocess;
pub mod profile;
pub mod proto;
pub mod quantity;
pub mod scheduler;
pub mod selftest;
pub mod stats;

#[cfg(windows)]
pub mod profile_win;
#[cfg(windows)]
pub mod sandbox;

/// Build a signed-shape measurement Quantity for an accepted run's wall time.
pub fn run_time_quantity(delta_ns: u64, fingerprint: &str) -> quantity::Quantity<quantity::Nanoseconds> {
    quantity::Quantity::measured(delta_ns as f64, fingerprint)
}
