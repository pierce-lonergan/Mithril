//! X4 measurement service v0 -- the orchestrator's statistical and control core (F0; trusted, frozen,
//! <= 1500 line-reviewed lines [target], 03 section 14). MEASUREMENT-SERVICE.md.
//!
//! The platform-independent core (eprocess, stats, scheduler, session, proto, profile, quantity,
//! runenv, sha256) is unit tested and differentially tested against the Python reference
//! (tests/golden_diff.rs). The Windows launcher (sandbox) and the profile reader (profile_win) are
//! thin adapters compiled only on Windows.
//!
//! Noise-pilot readiness (X4 pilot track, 2026-10-23): `observe` (the observe-mode ceilings and
//! per-run values), `pilotcfg` (the night configuration, schedule and Pacific-time rules) and
//! `hygiene` (the three-tier, sensor-only void rules) are pure and unit-tested; `sensors_win` (the
//! read-only sensors) and `pilot` (the night driver and the dry run) are Windows adapters.

pub mod eprocess;
pub mod hygiene;
pub mod observe;
pub mod pilotcfg;
pub mod profile;
pub mod proto;
pub mod quantity;
pub mod runenv;
pub mod scheduler;
pub mod selftest;
pub mod session;
pub mod sha256;
pub mod stats;

#[cfg(windows)]
pub mod pilot;
#[cfg(windows)]
pub mod profile_win;
#[cfg(windows)]
pub mod sandbox;
#[cfg(windows)]
pub mod sensors_win;
