//! mithi: the independent tree-walking interpreter and MCore checker for Mithril's X1 subset.
//!
//! DR-010 makes mithi the differential oracle and comptime evaluator; ROADMAP section 3.2 makes it
//! the X1 checker. Its rules are those of docs/m0/core-calculus.md (MCore v0.1). It shares no code
//! with mithc.

pub mod analysis;
pub mod ast;
pub mod captures;
pub mod check;
pub mod diag;
pub mod fmtspec;
pub mod infer;
pub mod interp;
pub mod json;
pub mod lexer;
pub mod lower;
pub mod manifest;
pub mod parser;
pub mod program;
pub mod sha256;
pub mod thir;
pub mod typeck;
pub mod types;
