//! Run-time meaning after the review of 2026-10-16: `format!` placeholders with Rust's results
//! (std::fmt's documented behaviour; rustc was not run [inference]), and labelled blocks.

mod common;

const FMT: &str = r#"
#[derive(Debug)] struct P { a: u32, b: (u8, u8) }
fn t1() -> String { format!("{:+}", 5) }
fn t2() -> String { format!("{:e}", 1234.5f32) }
fn t3() -> String { format!("{:E}", 1500.0f32) }
fn t4() -> String { format!("{:#?}", (1, 2)) }
fn t5() -> String { format!("{:*^7}", "ab") }
fn t6() -> String { format!("{0}-{1}-{0}", 1, 2) }
fn t7() -> String { format!("{:>1$}", 7, 4) }
fn t8() -> String { format!("{:.*}", 2, 1.23456f64) }
fn t9() -> String { format!("{:#?}", P { a: 1, b: (2, 3) }) }
fn t10() -> String { format!("{:08.3}", -3.14159f64) }
fn t11() -> String { format!("{:#010x}", 255u32) }
fn t12() -> String { format!("{:<5}|{:^5}|{:>5}", 1, 2, 3) }
fn t13() -> String { format!("{:.3}", "abcdef") }
fn t14() -> String { format!("{:+.1}", 0.05f32) }
fn t15() -> String { format!("{:5}|", true) }
fn t16() -> String { format!("{:?}", vec![Some(1u8), None]) }
"#;

#[test]
fn format_placeholders_have_rusts_meaning() {
    let want = [
        ("t1", "+5"),
        ("t2", "1.2345e3"),
        ("t3", "1.5E3"),
        ("t4", "(\n    1,\n    2,\n)"),
        ("t5", "**ab***"),
        ("t6", "1-2-1"),
        ("t7", "   7"),
        ("t8", "1.23"),
        ("t9", "P {\n    a: 1,\n    b: (\n        2,\n        3,\n    ),\n}"),
        ("t10", "-003.142"),
        ("t11", "0x000000ff"),
        ("t12", "1    |  2  |    3"),
        ("t13", "abc"),
        ("t14", "+0.1"),
        ("t15", "true |"),
        ("t16", "[Some(1), None]"),
    ];
    let mut bad = vec![];
    for (f, w) in want {
        let got = common::run_entry(FMT, "", f).unwrap();
        // run_entry prints a String with Debug quoting
        let shown = format!("{w:?}");
        if got != shown {
            bad.push(format!("{f}: got {got}, want {shown}"));
        }
    }
    assert!(bad.is_empty(), "{}", bad.join("\n"));
}

#[test]
fn labelled_blocks_are_one_trip_loops() {
    let src = "fn a() -> u32 { let r = 'a: { if true { break 'a 5u32; } 6u32 }; r }
fn b() -> u32 { let mut n = 0u32; for i in 0..4u32 { 'x: { if i == 1 { continue; } n += i; } } n }
fn c() -> u32 { 'x: { break 'x; } 3 }
fn d() -> u32 { let r = 'a: { if false { break 'a 5u32; } 6u32 }; r }";
    assert_eq!(common::run_entry(src, "", "a").unwrap(), "5");
    assert_eq!(common::run_entry(src, "", "b").unwrap(), "5");
    assert_eq!(common::run_entry(src, "", "c").unwrap(), "3");
    assert_eq!(common::run_entry(src, "", "d").unwrap(), "6");
}
