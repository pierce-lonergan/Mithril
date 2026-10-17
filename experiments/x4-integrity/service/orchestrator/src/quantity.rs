//! `Quantity<Unit, Origin>` -- every emitted number carries its unit and the origin of its value
//! (MEASUREMENT-SERVICE.md section 9; 01 section 4.4; ARCHITECTURE section 5.2). An unlabelled
//! performance number does not format, and origins never silently mix: a `Measured` and a `Simulated`
//! quantity combine only through an explicit conversion that names the weaker origin.
//!
//! `Unit` is a const type parameter (a marker type) so `/tok` vs `*tok` is a *type* error at compile
//! time (the Hearth `/tok` vs `*tok` class, RV: D2-C), not a runtime check.

use core::marker::PhantomData;

/// A unit marker. Implementors are zero-sized types naming the dimension and how it prints.
pub trait Unit {
    const SYMBOL: &'static str;
}

macro_rules! unit {
    ($name:ident, $sym:literal) => {
        #[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
        pub struct $name;
        impl Unit for $name {
            const SYMBOL: &'static str = $sym;
        }
    };
}

unit!(Nanoseconds, "ns");
unit!(Seconds, "s");
unit!(LogRatio, "log-ratio");
unit!(Ratio, "ratio");
unit!(EValue, "e");
unit!(Bytes, "B");
unit!(BytesPerSecond, "B/s");
unit!(Percent, "%");
unit!(Count, "");
unit!(Hertz, "Hz");
unit!(Cycles, "cyc");
unit!(Celsius, "degC");

/// Where a value came from. The ordering weak>strong is used when two quantities combine: the result
/// takes the weaker (more uncertain) origin, and that must be named explicitly (`convert`).
#[derive(Clone, Debug, PartialEq)]
pub enum Origin {
    /// Measured on hardware; carries the fingerprint hash of the machine profile (MEASUREMENT 5.2).
    Measured { fingerprint: String },
    /// Produced by a named simulator model (e.g. "hearth.sim"); never adds to a Measured quantity.
    Simulated { model: String },
    /// Derived from other quantities by a stated formula.
    Estimated,
    /// An assumption with no measurement behind it.
    Assumed,
}

impl Origin {
    /// Strength rank; higher is stronger (less uncertain).
    fn rank(&self) -> u8 {
        match self {
            Origin::Measured { .. } => 3,
            Origin::Estimated => 2,
            Origin::Simulated { .. } => 1,
            Origin::Assumed => 0,
        }
    }
    /// The weaker of two origins (used by explicit conversions).
    pub fn weaker(a: &Origin, b: &Origin) -> Origin {
        if a.rank() <= b.rank() { a.clone() } else { b.clone() }
    }
}

/// A number with a compile-time unit and a runtime origin. `U` is a marker type, not stored.
#[derive(Clone, Debug)]
pub struct Quantity<U: Unit> {
    value: f64,
    origin: Origin,
    _unit: PhantomData<U>,
}

impl<U: Unit> Quantity<U> {
    pub fn new(value: f64, origin: Origin) -> Self {
        Quantity { value, origin, _unit: PhantomData }
    }
    pub fn measured(value: f64, fingerprint: &str) -> Self {
        Self::new(value, Origin::Measured { fingerprint: fingerprint.to_string() })
    }
    pub fn simulated(value: f64, model: &str) -> Self {
        Self::new(value, Origin::Simulated { model: model.to_string() })
    }
    pub fn value(&self) -> f64 {
        self.value
    }
    pub fn origin(&self) -> &Origin {
        &self.origin
    }
    /// Add two quantities of the same unit; the result takes the weaker origin, named here explicitly.
    /// This is the only way origins mix (01 section 4.4): there is no `impl Add` that would hide it.
    pub fn combine_add(a: &Quantity<U>, b: &Quantity<U>) -> Quantity<U> {
        Quantity::new(a.value + b.value, Origin::weaker(&a.origin, &b.origin))
    }
    /// A labelled, human-readable form. There is no `Display` that would print an unlabelled number.
    pub fn format(&self) -> String {
        let o = match &self.origin {
            Origin::Measured { fingerprint } => format!("Measured{{{}}}", &fingerprint[..fingerprint.len().min(12)]),
            Origin::Simulated { model } => format!("Simulated{{{}}}", model),
            Origin::Estimated => "Estimated".to_string(),
            Origin::Assumed => "Assumed".to_string(),
        };
        format!("{} {} : {}", self.value, U::SYMBOL, o)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unit_symbol_in_format() {
        let q = Quantity::<LogRatio>::simulated(0.03, "x");
        assert!(q.format().contains("log-ratio"));
        assert!(q.format().contains("Simulated"));
    }

    #[test]
    fn combine_takes_weaker_origin() {
        let m = Quantity::<Bytes>::measured(10.0, "fp-abc");
        let s = Quantity::<Bytes>::simulated(5.0, "hearth.sim");
        let r = Quantity::combine_add(&m, &s);
        assert_eq!(r.value(), 15.0);
        // the weaker of Measured and Simulated is Simulated
        assert!(matches!(r.origin(), Origin::Simulated { .. }));
    }

    #[test]
    fn measured_fingerprint_truncates_in_format() {
        let q = Quantity::<Nanoseconds>::measured(1234.0, "0123456789abcdefghij");
        assert!(q.format().contains("Measured{0123456789ab}"));
    }
}
