//! D-FMT-1 prelude (read-only; the crate's `prelude` module).
#![allow(dead_code)]

#[derive(Clone, Copy, PartialEq, Debug)]
pub enum TraceError {
    Truncated,
    BadMagic,
    BadVersion,
    Mismatch,
    BadId,
}

pub struct ModelDims {
    pub n_experts: u32,
    pub top_k: u32,
    pub n_moe_layers: u32,
}

#[derive(Debug)]
pub struct TraceHeader {
    pub n_layers: u32,
    pub n_experts: u32,
    pub top_k: u32,
    pub n_moe_layers: u32,
    pub n_tokens: u64,
}
