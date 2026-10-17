//! Deterministic traps (note section 6.3): kind, definition and anchor of each trap site, the
//! lowest-index rule of `par for` (section 6.4), and abandonment of live Linear values.

use mithi::check::{check, Config};
use mithi::diag::FileRole;
use mithi::lower::SourceInput;

fn checked() -> mithi::check::Checked {
    let text = std::fs::read_to_string(std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("tests/corpus/traps.mith")).unwrap();
    let mut cfg = Config::default();
    cfg.inputs.push(SourceInput { name: "traps.mith".into(), text, role: FileRole::User, module: String::new() });
    let c = check(&cfg);
    let errs: Vec<String> = c.errors().iter().map(|d| mithi::diag::render_text(c.sm(), d)).collect();
    assert!(errs.is_empty(), "{}", errs.join("\n"));
    c
}

fn outcome(c: &mithi::check::Checked, f: &str) -> Result<String, String> {
    mithi::interp::run_entry(c, f)
}

#[test]
fn trap_sites_are_named() {
    let c = checked();
    let cases = [
        ("t_ovf_add", "trap ovf(add) in t_ovf_add at `x + 100`"),
        ("t_ovf_sub", "trap ovf(sub) in t_ovf_sub at `a - 2`"),
        ("t_ovf_mul", "trap ovf(mul) in t_ovf_mul at `a * 65536`"),
        ("t_div0", "trap div0 in t_div0 at `7 / z`"),
        ("t_divovf", "trap divovf in t_divovf at `m / n`"),
        ("t_shift", "trap shift in t_shift at `1u32 << s`"),
        ("t_idx", "trap idx in t_idx at `v[i]`"),
        ("t_slice", "trap slice in t_slice at `v[1..4]`"),
        ("t_unwrap", "trap unwrap in t_unwrap at `o.unwrap()`"),
        ("t_hole", "trap hole(later) in t_hole at `todo!(\"later\")`"),
        ("t_assert", "trap assert in t_assert"),
        ("t_unreachable", "trap unreachable in t_unreachable"),
    ];
    for (f, want) in cases {
        let got = outcome(&c, f).expect_err(f);
        assert!(got.starts_with(want), "{f}: got `{got}`, want prefix `{want}`");
    }
}

#[test]
fn par_for_lowest_index_wins() {
    let c = checked();
    assert_eq!(outcome(&c, "t_par_lowest").unwrap(), "1");
    let t = outcome(&c, "t_par_trap_lowest").unwrap_err();
    // iterations 2 and 4 trap with the same kind: the report must name index 2 (§6.4 m·ī)
    assert!(t.starts_with("trap ovf(add) in t_par_trap_lowest at `xs[i] + 1` [par i=2]"), "{t}");
}

#[test]
fn traps_abandon_live_linear_values_newest_first() {
    let c = checked();
    let t = outcome(&c, "t_abandon").unwrap_err();
    assert!(t.starts_with("trap div0"), "{t}");
    assert!(t.ends_with("abandoned (newest first): b in t_abandon, a in t_abandon"), "{t}");
    // a Linear argument already evaluated when a later argument traps is abandoned too (F-42)
    let t = outcome(&c, "t_abandon_temp").unwrap_err();
    assert!(t.starts_with("trap div0 in t_abandon_temp"), "{t}");
    assert!(t.ends_with("abandoned (newest first): <arg 0 of two> in t_abandon_temp"), "{t}");
}

#[test]
fn deep_recursion_ends_in_the_frame_limit_not_a_crash() {
    // the CLI runs on a 1 GiB stack; the interpreter's own limit (2000 frames) must fire first
    // (review 2026-10-16: about 300 frames overflowed the 1 MB main-thread stack)
    let h = std::thread::Builder::new()
        .stack_size(1 << 30)
        .spawn(|| {
            let src = "fn r(n: u32) -> u32 { if n == 0 { 0 } else { 1 + r(n - 1) } }\nfn deep() -> u32 { r(2500) }\nfn ok() -> u32 { r(1500) }\n";
            let mut cfg = Config::default();
            cfg.inputs.push(SourceInput { name: "rec.mith".into(), text: src.into(), role: FileRole::User, module: String::new() });
            let c = check(&cfg);
            assert!(c.errors().is_empty());
            (outcome(&c, "ok"), outcome(&c, "deep"))
        })
        .unwrap();
    let (ok, deep) = h.join().unwrap();
    assert_eq!(ok.unwrap(), "1500");
    let d = deep.unwrap_err();
    assert!(d.contains("stack depth limit"), "{d}");
}

#[test]
fn f16_widening_is_exact_on_all_inputs() {
    // compare with an independent bit-level construction for every f16 that is not NaN
    for h in 0u32..=0xffff {
        let h = h as u16;
        let f = mithi::interp::f16_to_f32(h);
        let exp = (h >> 10) & 0x1f;
        let man = h & 0x3ff;
        let sign = if h & 0x8000 != 0 { -1.0f64 } else { 1.0 };
        let want: f64 = if exp == 0x1f {
            if man == 0 {
                sign * f64::INFINITY
            } else {
                assert!(f.is_nan());
                continue;
            }
        } else if exp == 0 {
            sign * (man as f64) * 2f64.powi(-24)
        } else {
            sign * (1.0 + (man as f64) / 1024.0) * 2f64.powi(exp as i32 - 15)
        };
        assert_eq!(f as f64, want, "f16 {h:#06x}");
        assert_eq!(f.is_sign_negative(), h & 0x8000 != 0);
    }
}

#[test]
fn canon_sum16_tree_order() {
    // lanes i & 15, then s = 8, 4, 2, 1 (02 section 5)
    let mut v = vec![0.0f32; 32];
    v[0] = 1.0e8;
    for x in v.iter_mut().skip(1) {
        *x = 1.0;
    }
    assert_eq!(mithi::interp::canon_sum16(&v), 100000024.0);
}
