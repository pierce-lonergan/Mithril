//! `Quantity<Unit, Origin>` -- every emitted number carries its unit and the origin of its value
//! (MEASUREMENT-SERVICE.md section 9; 01 section 4.4; ARCHITECTURE section 5.2). An unlabelled
//! performance number does not format, and origins never silently mix.
//!
//! - `Unit` is a marker type parameter, so `/tok` vs `*tok` is a compile-time type error.
//! - A `Measured` quantity can only be built from a `VerifiedProfile` (profile.rs), which exists only
//!   when the quiet-machine profile is met **and** its fingerprint hash equals the pinned one. A dev run
//!   on an unverified machine therefore cannot emit a Measured fact.
//! - `combine_add` succeeds only for identical origins (same kind and same fingerprint/model). Anything
//!   else needs an explicit `weaken` to a named weaker origin first (review R2-10).

use crate::profile::VerifiedProfile;
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

/// Where a value came from.
#[derive(Clone, Debug, PartialEq)]
pub enum Origin {
    /// Measured on hardware under a verified profile; carries that profile's fingerprint hash.
    Measured { fingerprint: String },
    /// Produced by a named simulator model (e.g. "hearth.sim").
    Simulated { model: String },
    /// Derived from other quantities by a stated formula.
    Estimated,
    /// An assumption with no measurement behind it.
    Assumed,
}

impl Origin {
    /// Strength rank; higher is stronger (less uncertain).
    pub fn rank(&self) -> u8 {
        match self {
            Origin::Measured { .. } => 3,
            Origin::Estimated => 2,
            Origin::Simulated { .. } => 1,
            Origin::Assumed => 0,
        }
    }
}

/// A number with a compile-time unit and a runtime origin.
#[derive(Clone, Debug)]
pub struct Quantity<U: Unit> {
    value: f64,
    origin: Origin,
    _unit: PhantomData<U>,
}

impl<U: Unit> Quantity<U> {
    fn new(value: f64, origin: Origin) -> Self {
        Quantity { value, origin, _unit: PhantomData }
    }
    /// The only way to make a Measured quantity: from a verified profile.
    pub fn measured(value: f64, profile: &VerifiedProfile) -> Self {
        Self::new(value, Origin::Measured { fingerprint: profile.hash().to_string() })
    }
    pub fn simulated(value: f64, model: &str) -> Self {
        Self::new(value, Origin::Simulated { model: model.to_string() })
    }
    pub fn estimated(value: f64) -> Self {
        Self::new(value, Origin::Estimated)
    }
    pub fn assumed(value: f64) -> Self {
        Self::new(value, Origin::Assumed)
    }
    pub fn value(&self) -> f64 {
        self.value
    }
    pub fn origin(&self) -> &Origin {
        &self.origin
    }
    /// Add two quantities of the same unit. Only identical origins add; mixing needs `weaken` first,
    /// so the weaker origin is always named at the call site (01 section 4.4).
    pub fn combine_add(a: &Quantity<U>, b: &Quantity<U>) -> Result<Quantity<U>, String> {
        if a.origin != b.origin {
            return Err(format!("origins differ ({:?} vs {:?}); weaken both to a named origin first", a.origin, b.origin));
        }
        Ok(Quantity::new(a.value + b.value, a.origin.clone()))
    }
    /// Relabel to a strictly weaker origin (Measured -> Estimated, ...). Never strengthens.
    pub fn weaken(&self, to: Origin) -> Result<Quantity<U>, String> {
        if to.rank() >= self.origin.rank() {
            return Err(format!("{:?} is not weaker than {:?}", to, self.origin));
        }
        Ok(Quantity::new(self.value, to))
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
    use crate::profile::VerifiedProfile;

    #[test]
    fn unit_symbol_in_format() {
        let q = Quantity::<LogRatio>::simulated(0.03, "x");
        assert!(q.format().contains("log-ratio"));
        assert!(q.format().contains("Simulated"));
    }

    #[test]
    fn measured_from_different_profiles_do_not_mix() {
        // review R2-10 (reviewer spec test spec_measured_quantities_from_different_profiles_do_not_mix)
        let pa = VerifiedProfile::for_unit_tests("fp-A");
        let pb = VerifiedProfile::for_unit_tests("fp-B");
        let a = Quantity::<Nanoseconds>::measured(1.0, &pa);
        let b = Quantity::<Nanoseconds>::measured(2.0, &pb);
        assert!(Quantity::combine_add(&a, &b).is_err());
        let a2 = Quantity::<Nanoseconds>::measured(2.0, &pa);
        assert_eq!(Quantity::combine_add(&a, &a2).unwrap().value(), 3.0);
    }

    #[test]
    fn measured_and_simulated_never_add_without_a_named_conversion() {
        let p = VerifiedProfile::for_unit_tests("fp-abc");
        let m = Quantity::<Bytes>::measured(10.0, &p);
        let s = Quantity::<Bytes>::simulated(5.0, "hearth.sim");
        assert!(Quantity::combine_add(&m, &s).is_err());
        // explicit: both weakened to Assumed, named at the call site
        let m2 = m.weaken(Origin::Assumed).unwrap();
        let s2 = s.weaken(Origin::Assumed).unwrap();
        let r = Quantity::combine_add(&m2, &s2).unwrap();
        assert_eq!(r.value(), 15.0);
        assert_eq!(r.origin(), &Origin::Assumed);
        // never strengthens
        assert!(s.weaken(Origin::Estimated).is_err());
    }

    #[test]
    fn measured_fingerprint_truncates_in_format() {
        let p = VerifiedProfile::for_unit_tests("0123456789abcdefghij");
        let q = Quantity::<Nanoseconds>::measured(1234.0, &p);
        assert!(q.format().contains("Measured{0123456789ab}"));
    }
}
