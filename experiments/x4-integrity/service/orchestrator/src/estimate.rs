//! The noise pilot's estimator command (docs/m0/prereg/X4-noise-pilot.md sections 4, 5 and 7;
//! revision 5, review round 5, 2026-10-23). Platform-independent and read-only: it reads the night
//! directories a pilot left and prints the section 4/5 estimators and the section 7(a) tolerance
//! fill-in; it writes nothing into the data. `x4svc pilot-estimate` is its command.
//!
//! **Inputs (record section 7).** Every night directory under the data directory (`night-*`; a
//! DRY-RUN acceptance test reads `dry-*` under `<scratch>\dry` and stamps its output as a test, never
//! as pilot data). Each night's manifest is `manifest-closed-after-interrupt.txt` when the driver or
//! `x4svc pilot-close` closed it after an interruption, else `manifest.txt`. The whole input is refused
//! when any night: has no manifest, or one with `status=open` (close it first); has another grade;
//! names another freeze commit or canonical configuration SHA-256 than the pre-night amendment's;
//! has a record file whose SHA-256 differs from its manifest line, or a progress.txt whose first
//! `bytes` no longer hash to the manifest's value (progress.txt only grows); or has a record line that
//! does not parse or whose `"grade"` is not the expected one. One exception: the last line of a record
//! file of a night closed after an interruption may be cut short (a power loss); it is skipped and
//! counted. Refused nights (`status=refused`) are checked and contribute nothing.
//!
//! **Counted set (record section 4, revision 5).** The non-discarded blocks (`blocks.jsonl`) of the
//! sessions whose end is `completed` in progress.txt. The blocks of sessions that ended `cut`,
//! `hygiene_void`, `integrity_stop`, `error` or `interrupted` (a started line with no end line counts
//! as interrupted) are excluded and reported by end; section 9's sensitivity adds the `cut` sessions'
//! blocks back for one extra sigma_d. A block holding a capped run is excluded from sigma_d and
//! sigma_run (sigma_d is estimated only from runs that reached their stopping point, section 8) and
//! counted as slow outliers in the R replay.

use crate::eprocess::{Arm, BlockScorer, Scorer};
use crate::sha256;
use crate::stats;
use std::path::{Path, PathBuf};

// ------------------------------------------------------------------------------- minimal JSON

/// A JSON value (the record files' own subset: objects, arrays, strings, numbers, booleans, null).
#[derive(Clone, Debug, PartialEq)]
pub enum J {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    Arr(Vec<J>),
    Obj(Vec<(String, J)>),
}

impl J {
    pub fn get(&self, k: &str) -> Option<&J> {
        match self {
            J::Obj(v) => v.iter().find(|(a, _)| a == k).map(|(_, b)| b),
            _ => None,
        }
    }
    pub fn f(&self) -> Option<f64> {
        match self {
            J::Num(x) => Some(*x),
            _ => None,
        }
    }
    pub fn s(&self) -> Option<&str> {
        match self {
            J::Str(x) => Some(x),
            _ => None,
        }
    }
    pub fn arr(&self) -> Option<&Vec<J>> {
        match self {
            J::Arr(v) => Some(v),
            _ => None,
        }
    }
    pub fn b(&self) -> Option<bool> {
        match self {
            J::Bool(x) => Some(*x),
            _ => None,
        }
    }
    fn fk(&self, k: &str) -> Option<f64> {
        self.get(k).and_then(|x| x.f())
    }
    fn sk(&self, k: &str) -> Option<&str> {
        self.get(k).and_then(|x| x.s())
    }
}

pub fn parse_json(s: &str) -> Result<J, String> {
    let mut p = Pj { b: s.as_bytes(), i: 0 };
    p.ws();
    let v = p.val(0)?;
    p.ws();
    if p.i != p.b.len() {
        return Err(format!("trailing characters at {}", p.i));
    }
    Ok(v)
}

struct Pj<'a> {
    b: &'a [u8],
    i: usize,
}

impl Pj<'_> {
    fn ws(&mut self) {
        while self.i < self.b.len() && matches!(self.b[self.i], b' ' | b'\t' | b'\r' | b'\n') {
            self.i += 1;
        }
    }
    fn peek(&self) -> Option<u8> {
        self.b.get(self.i).copied()
    }
    fn lit(&mut self, w: &str, v: J) -> Result<J, String> {
        if self.b[self.i..].starts_with(w.as_bytes()) {
            self.i += w.len();
            Ok(v)
        } else {
            Err(format!("bad literal at {}", self.i))
        }
    }
    fn val(&mut self, depth: usize) -> Result<J, String> {
        if depth > 32 {
            return Err("nesting too deep".into());
        }
        match self.peek() {
            Some(b'{') => {
                self.i += 1;
                let mut v = Vec::new();
                self.ws();
                if self.peek() == Some(b'}') {
                    self.i += 1;
                    return Ok(J::Obj(v));
                }
                loop {
                    self.ws();
                    let k = self.string()?;
                    self.ws();
                    if self.peek() != Some(b':') {
                        return Err(format!("expected ':' at {}", self.i));
                    }
                    self.i += 1;
                    self.ws();
                    let x = self.val(depth + 1)?;
                    v.push((k, x));
                    self.ws();
                    match self.peek() {
                        Some(b',') => self.i += 1,
                        Some(b'}') => {
                            self.i += 1;
                            return Ok(J::Obj(v));
                        }
                        _ => return Err(format!("expected ',' or '}}' at {}", self.i)),
                    }
                }
            }
            Some(b'[') => {
                self.i += 1;
                let mut v = Vec::new();
                self.ws();
                if self.peek() == Some(b']') {
                    self.i += 1;
                    return Ok(J::Arr(v));
                }
                loop {
                    self.ws();
                    v.push(self.val(depth + 1)?);
                    self.ws();
                    match self.peek() {
                        Some(b',') => self.i += 1,
                        Some(b']') => {
                            self.i += 1;
                            return Ok(J::Arr(v));
                        }
                        _ => return Err(format!("expected ',' or ']' at {}", self.i)),
                    }
                }
            }
            Some(b'"') => Ok(J::Str(self.string()?)),
            Some(b't') => self.lit("true", J::Bool(true)),
            Some(b'f') => self.lit("false", J::Bool(false)),
            Some(b'n') => self.lit("null", J::Null),
            Some(c) if c == b'-' || c.is_ascii_digit() => {
                let st = self.i;
                while self.i < self.b.len() && matches!(self.b[self.i], b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9') {
                    self.i += 1;
                }
                let t = std::str::from_utf8(&self.b[st..self.i]).map_err(|e| e.to_string())?;
                t.parse::<f64>().map(J::Num).map_err(|_| format!("bad number {:?}", t))
            }
            _ => Err(format!("unexpected input at {}", self.i)),
        }
    }
    fn string(&mut self) -> Result<String, String> {
        if self.peek() != Some(b'"') {
            return Err(format!("expected a string at {}", self.i));
        }
        self.i += 1;
        let mut out: Vec<u8> = Vec::new();
        loop {
            let c = *self.b.get(self.i).ok_or("unterminated string")?;
            self.i += 1;
            match c {
                b'"' => break,
                b'\\' => {
                    let e = *self.b.get(self.i).ok_or("unterminated escape")?;
                    self.i += 1;
                    match e {
                        b'"' => out.push(b'"'),
                        b'\\' => out.push(b'\\'),
                        b'/' => out.push(b'/'),
                        b'b' => out.push(8),
                        b'f' => out.push(12),
                        b'n' => out.push(b'\n'),
                        b'r' => out.push(b'\r'),
                        b't' => out.push(b'\t'),
                        b'u' => {
                            let h = self.b.get(self.i..self.i + 4).ok_or("short \\u escape")?;
                            let cp = u32::from_str_radix(std::str::from_utf8(h).map_err(|e| e.to_string())?, 16).map_err(|e| e.to_string())?;
                            self.i += 4;
                            let ch = char::from_u32(cp).unwrap_or('\u{fffd}');
                            let mut buf = [0u8; 4];
                            out.extend_from_slice(ch.encode_utf8(&mut buf).as_bytes());
                        }
                        _ => return Err(format!("bad escape at {}", self.i)),
                    }
                }
                c => out.push(c),
            }
        }
        String::from_utf8(out).map_err(|e| e.to_string())
    }
}

// ----------------------------------------------------------------------------------- inputs

/// What the estimator is told (the pre-night amendment's values; record section 7).
#[derive(Clone, Debug)]
pub struct EstimateOpts {
    pub data_dir: String,
    /// "PILOT", or "DRY-RUN" for the acceptance test on dry nights (output stamped as a test).
    pub grade: String,
    pub freeze_commit: Option<String>,
    pub config_sha256: Option<String>,
}

fn sha_hex(b: &[u8]) -> String {
    sha256::hex(&sha256::digest(b))
}

/// One night's records after every check.
struct Night {
    label: String,
    status: String,
    runs: Vec<J>,
    blocks: Vec<J>,
    sessions: Vec<J>,
    sensors: Vec<J>,
    truncated: usize,
    cleared: String,
}

fn kv(text: &str, key: &str) -> Option<String> {
    text.lines().find_map(|l| l.strip_prefix(&format!("{}=", key)).map(|s| s.trim().to_string()))
}

fn read_jsonl(path: &Path, grade: &str, allow_cut_last: bool, truncated: &mut usize) -> Result<Vec<J>, String> {
    let text = std::fs::read_to_string(path).map_err(|e| format!("{}: {}", path.display(), e))?;
    let lines: Vec<&str> = text.lines().collect();
    let mut v = Vec::new();
    for (i, l) in lines.iter().enumerate() {
        if l.trim().is_empty() {
            continue;
        }
        match parse_json(l) {
            Ok(j) => {
                if j.sk("grade") != Some(grade) {
                    return Err(format!("{} line {}: grade {:?}, not {} (the input is refused whole)", path.display(), i + 1, j.sk("grade"), grade));
                }
                v.push(j);
            }
            Err(e) if allow_cut_last && i + 1 == lines.len() => {
                let _ = e;
                *truncated += 1;
            }
            Err(e) => return Err(format!("{} line {}: {}", path.display(), i + 1, e)),
        }
    }
    Ok(v)
}

fn read_night(dir: &Path, progress: &Path, o: &EstimateOpts) -> Result<Night, String> {
    let name = dir.file_name().map(|n| n.to_string_lossy().to_string()).unwrap_or_default();
    let closure = dir.join("manifest-closed-after-interrupt.txt");
    let mpath = if closure.exists() { closure } else { dir.join("manifest.txt") };
    let m = std::fs::read_to_string(&mpath).map_err(|_| format!("night {} has no manifest (close it with `x4svc pilot-close` first)", name))?;
    let status = kv(&m, "status").unwrap_or_default();
    match status.as_str() {
        "closed" | "stopped" | "closed-after-interrupt" | "refused" => {}
        "open" => return Err(format!("night {} is open (a crash or a running night): start the next night or run `x4svc pilot-close`, then estimate", name)),
        s => return Err(format!("night {}: unknown status {:?}", name, s)),
    }
    if kv(&m, "grade").as_deref() != Some(o.grade.as_str()) {
        return Err(format!("night {}: grade {:?}, not {}", name, kv(&m, "grade"), o.grade));
    }
    if let Some(fc) = &o.freeze_commit {
        if !kv(&m, "freeze_commit").map_or(false, |x| x.eq_ignore_ascii_case(fc)) {
            return Err(format!("night {}: freeze_commit {:?}, not {}", name, kv(&m, "freeze_commit"), fc));
        }
    }
    if let Some(cs) = &o.config_sha256 {
        if !kv(&m, "config_canonical_sha256").map_or(false, |x| x.eq_ignore_ascii_case(cs)) {
            return Err(format!("night {}: canonical configuration SHA-256 {:?}, not the pre-night amendment's {}", name, kv(&m, "config_canonical_sha256"), cs));
        }
    }
    // every sha256[...] line, re-hashed
    let mut seen_files = 0;
    for l in m.lines() {
        let rest = match l.strip_prefix("sha256[") {
            Some(r) => r,
            None => continue,
        };
        let (f, v) = rest.split_once("]=").ok_or_else(|| format!("night {}: malformed line {:?}", name, l))?;
        let want = v.split_whitespace().next().unwrap_or("");
        if f == "progress.txt" {
            let n: usize = v.split_whitespace().find_map(|t| t.strip_prefix("bytes=")).and_then(|t| t.parse().ok()).ok_or_else(|| format!("night {}: the progress line has no bytes= (a pre-revision-5 manifest)", name))?;
            let b = std::fs::read(progress).map_err(|e| format!("{}: {}", progress.display(), e))?;
            if b.len() < n || sha_hex(&b[..n]) != want {
                return Err(format!("night {}: progress.txt's first {} bytes do not hash to the manifest's {} (progress.txt was rewritten, not appended)", name, n, want));
            }
        } else {
            let b = std::fs::read(dir.join(f)).map_err(|e| format!("night {}: {}: {}", name, f, e))?;
            if sha_hex(&b) != want {
                return Err(format!("night {}: {} does not match its manifest SHA-256 (changed after the manifest)", name, f));
            }
            seen_files += 1;
        }
    }
    if seen_files < 6 {
        return Err(format!("night {}: the manifest hashes {} of the 6 record files", name, seen_files));
    }
    let cut_ok = status == "closed-after-interrupt";
    let mut truncated = 0;
    let runs = read_jsonl(&dir.join("runs.jsonl"), &o.grade, cut_ok, &mut truncated)?;
    let blocks = read_jsonl(&dir.join("blocks.jsonl"), &o.grade, cut_ok, &mut truncated)?;
    let sessions = read_jsonl(&dir.join("sessions.jsonl"), &o.grade, cut_ok, &mut truncated)?;
    let sensors = read_jsonl(&dir.join("sensors.jsonl"), &o.grade, cut_ok, &mut truncated)?;
    let voids = std::fs::read_to_string(dir.join("voids.log")).map_err(|e| e.to_string())?;
    let vl: Vec<&str> = voids.lines().collect();
    for (i, l) in vl.iter().enumerate() {
        if !l.trim().is_empty() && !l.starts_with(&format!("{} ", o.grade)) {
            if cut_ok && i + 1 == vl.len() {
                truncated += 1;
                continue;
            }
            return Err(format!("night {}: voids.log line {} is not stamped {}", name, i + 1, o.grade));
        }
    }
    Ok(Night { label: kv(&m, "night").unwrap_or_else(|| name.clone()), status, runs, blocks, sessions, sensors, truncated, cleared: kv(&m, "integrity_cleared").unwrap_or_default() })
}

// ------------------------------------------------------------------------------- estimators

fn q(xs: &[f64], p: f64) -> String {
    match stats::quantile_nearest_rank(xs, p) {
        Some(x) => format!("{:.6}", x),
        None => "none".into(),
    }
}
fn fmt(x: Option<f64>) -> String {
    match x {
        Some(v) if v.is_finite() => format!("{:.6}", v),
        _ => "none".into(),
    }
}
fn maxf(xs: &[f64]) -> Option<f64> {
    xs.iter().copied().filter(|v| v.is_finite()).fold(None, |m, v| Some(m.map_or(v, |x: f64| x.max(v))))
}
fn run_type_of(session: &str) -> String {
    match session.rfind('-') {
        Some(i) if session[i + 1..].chars().all(|c| c.is_ascii_digit()) => session[..i].to_string(),
        _ => session.to_string(),
    }
}

struct Blk {
    night: String,
    session: String,
    seqs: Vec<Option<u64>>,
    arms: Vec<Arm>,
    ln: Vec<f64>,
    capped: Vec<bool>,
    d: f64,
}

fn blk(night: &str, j: &J) -> Result<Blk, String> {
    let session = j.sk("session").ok_or("a block without a session")?.to_string();
    let arr = |k: &str| j.get(k).and_then(|x| x.arr()).cloned().ok_or_else(|| format!("block of {}: no {}", session, k));
    let seqs: Vec<Option<u64>> = arr("seqs")?.iter().map(|x| x.f().map(|v| v as u64)).collect();
    let arms: Vec<Arm> = arr("arms")?.iter().map(|x| if x.s() == Some("B") { Arm::B } else { Arm::A }).collect();
    let ln: Vec<f64> = arr("ln_delta_h_ns")?.iter().map(|x| x.f().unwrap_or(f64::NAN)).collect();
    let capped: Vec<bool> = arr("capped")?.iter().map(|x| x.b().unwrap_or(true)).collect();
    if arms.len() != 4 || ln.len() != 4 || capped.len() != 4 || seqs.len() != 4 {
        return Err(format!("block of {}: not 4 runs", session));
    }
    Ok(Blk { night: night.to_string(), session, seqs, arms, ln, capped, d: j.fk("d").unwrap_or(f64::NAN) })
}

/// Run the estimator. Returns the report text (deterministic) or why the input is refused.
pub fn estimate(o: &EstimateOpts) -> Result<String, String> {
    let pilot = o.grade == "PILOT";
    if pilot && (o.freeze_commit.is_none() || o.config_sha256.is_none()) {
        return Err("PILOT needs the freeze commit and the canonical configuration SHA-256 of the pre-night amendment".into());
    }
    let root = PathBuf::from(&o.data_dir);
    let prefix = if pilot { "night-" } else { "dry-" };
    let mut dirs: Vec<PathBuf> = std::fs::read_dir(&root)
        .map_err(|e| format!("{}: {}", o.data_dir, e))?
        .filter_map(|e| e.ok())
        .map(|e| e.path())
        .filter(|p| p.is_dir() && p.file_name().map_or(false, |n| n.to_string_lossy().starts_with(prefix)))
        .collect();
    dirs.sort();
    if dirs.is_empty() {
        return Err(format!("no {}* night under {}", prefix, o.data_dir));
    }
    if !pilot && dirs.len() != 1 {
        // dry nights reuse session ids, so the acceptance test reads one dry night per directory
        return Err(format!("the DRY-RUN acceptance test reads exactly one dry night; {} has {}", o.data_dir, dirs.len()));
    }
    let mut nights = Vec::new();
    let mut progress_text = String::new();
    for d in &dirs {
        let progress = if pilot { root.join("progress.txt") } else { d.join("progress.txt") };
        nights.push(read_night(d, &progress, o)?);
        if !pilot {
            progress_text.push_str(&std::fs::read_to_string(&progress).unwrap_or_default());
        }
    }
    if pilot {
        progress_text = std::fs::read_to_string(root.join("progress.txt")).map_err(|e| format!("progress.txt: {}", e))?;
    }
    // session ends from progress.txt; a started session with no end line was interrupted
    let mut started: Vec<String> = Vec::new();
    let mut ends: Vec<(String, String)> = Vec::new();
    for l in progress_text.lines() {
        let f: Vec<&str> = l.split_whitespace().collect();
        if f.len() < 2 {
            continue;
        }
        if f[1] == "started" {
            if !started.contains(&f[0].to_string()) {
                started.push(f[0].to_string());
            }
        } else if !ends.iter().any(|(s, _)| s == f[0]) {
            ends.push((f[0].to_string(), f[1].to_string()));
            if !started.contains(&f[0].to_string()) {
                started.push(f[0].to_string());
            }
        }
    }
    let end_of = |s: &str| -> String { ends.iter().find(|(x, _)| x == s).map(|(_, e)| e.clone()).unwrap_or_else(|| "interrupted".into()) };
    // sessions.jsonl and progress.txt agree on every recorded end
    for n in &nights {
        for s in &n.sessions {
            let id = s.sk("session").unwrap_or("");
            let e = s.sk("end").unwrap_or("");
            if end_of(id) != e {
                return Err(format!("night {}: session {} ends {:?} in sessions.jsonl but {:?} in progress.txt", n.label, id, e, end_of(id)));
            }
        }
    }
    let mut out: Vec<String> = Vec::new();
    out.push(format!("# X4 noise pilot estimator (record sections 4, 5, 7(a)); x4svc pilot-estimate, revision 5"));
    if !pilot {
        out.push("# DRY-RUN ACCEPTANCE TEST: dry records, not pilot data; no value below is an estimate".into());
    }
    out.push(format!("grade = {}", o.grade));
    out.push(format!("data_dir = {}", o.data_dir));
    out.push(format!("freeze_commit = {}", o.freeze_commit.clone().unwrap_or_else(|| "(not checked)".into())));
    out.push(format!("config_canonical_sha256 = {}", o.config_sha256.clone().unwrap_or_else(|| "(not checked)".into())));
    out.push(format!("progress_sha256 = {}", sha_hex(progress_text.as_bytes())));
    for n in &nights {
        out.push(format!("night {} status={} runs={} blocks={} sessions={} truncated_last_lines={} integrity_cleared={}", n.label, n.status, n.runs.len(), n.blocks.len(), n.sessions.len(), n.truncated, if n.cleared.is_empty() { "-" } else { &n.cleared }));
    }
    // every block, every run (keyed by night and seq)
    let mut blocks: Vec<Blk> = Vec::new();
    for n in &nights {
        for b in &n.blocks {
            blocks.push(blk(&n.label, b)?);
        }
    }
    fn run_of<'a>(nights: &'a [Night], night: &str, seq: u64) -> Option<&'a J> {
        nights.iter().find(|n| n.label == night).and_then(|n| n.runs.iter().find(|r| r.fk("seq").map(|x| x as u64) == Some(seq)))
    }
    // run types in a fixed order: the record's, then any other
    let mut rts: Vec<String> = vec!["mb-q4-avx512".into(), "e2e-decode".into()];
    for s in &started {
        let r = run_type_of(s);
        if !rts.contains(&r) {
            rts.push(r);
        }
    }
    for rt in &rts {
        let sess: Vec<&String> = started.iter().filter(|s| &run_type_of(s) == rt).collect();
        if sess.is_empty() {
            continue;
        }
        out.push(format!("[{}]", rt));
        // tiers (record section 10): attempted sessions and how each ended
        let mut by_end: Vec<(String, usize)> = Vec::new();
        for s in &sess {
            let e = end_of(s);
            match by_end.iter_mut().find(|(x, _)| *x == e) {
                Some(c) => c.1 += 1,
                None => by_end.push((e, 1)),
            }
        }
        by_end.sort();
        out.push(format!("sessions_attempted = {}", sess.len()));
        out.push(format!("sessions_by_end = {}", by_end.iter().map(|(e, c)| format!("{}:{}", e, c)).collect::<Vec<_>>().join(", ")));
        let counted = |s: &str| end_of(s) == "completed";
        let rt_blocks: Vec<&Blk> = blocks.iter().filter(|b| &run_type_of(&b.session) == rt).collect();
        let mut excluded: Vec<(String, usize)> = Vec::new();
        for b in &rt_blocks {
            if !counted(&b.session) {
                let e = end_of(&b.session);
                match excluded.iter_mut().find(|(x, _)| *x == e) {
                    Some(c) => c.1 += 1,
                    None => excluded.push((e, 1)),
                }
            }
        }
        excluded.sort();
        out.push(format!("blocks_excluded_by_session_end = {}", if excluded.is_empty() { "none".to_string() } else { excluded.iter().map(|(e, c)| format!("{}:{}", e, c)).collect::<Vec<_>>().join(", ") }));
        let cb: Vec<&&Blk> = rt_blocks.iter().filter(|b| counted(&b.session)).collect();
        let uncapped: Vec<&&&Blk> = cb.iter().filter(|b| !b.capped.iter().any(|c| *c)).collect();
        out.push(format!("blocks_counted = {} (of which {} hold a capped run and are left out of sigma_d and sigma_run)", cb.len(), cb.len() - uncapped.len()));
        // sigma_d about 0, B, sigma_U
        let d: Vec<f64> = uncapped.iter().map(|b| b.d).collect();
        match stats::rms_about_zero(&d) {
            Some((s, b)) => {
                out.push(format!("sigma_d = {:.6}", s));
                out.push(format!("B = {}", b));
                out.push(format!("sigma_U = {:.6}", stats::sigma_upper_90(s, b)));
            }
            None => out.push("sigma_d = none (no counted block)".into()),
        }
        // section 9: with the cut sessions' blocks
        let d_cut: Vec<f64> = rt_blocks.iter().filter(|b| (counted(&b.session) || end_of(&b.session) == "cut") && !b.capped.iter().any(|c| *c)).map(|b| b.d).collect();
        let n_cut_sess = sess.iter().filter(|s| end_of(s) == "cut").count();
        out.push(format!(
            "sigma_d_with_cut_sessions = {} (B = {}, cut sessions = {})",
            fmt(stats::rms_about_zero(&d_cut).map(|x| x.0)),
            d_cut.len(),
            n_cut_sess
        ));
        // sigma_run: pooled within (session, arm) SD of per-run ln(delta_h)
        let mut groups: Vec<((String, bool), Vec<f64>)> = Vec::new();
        let mut all_ln: Vec<f64> = Vec::new();
        for b in &uncapped {
            for k in 0..4 {
                let key = (b.session.clone(), b.arms[k] == Arm::B);
                all_ln.push(b.ln[k]);
                match groups.iter_mut().find(|(g, _)| *g == key) {
                    Some(g) => g.1.push(b.ln[k]),
                    None => groups.push((key, vec![b.ln[k]])),
                }
            }
        }
        let gv: Vec<Vec<f64>> = groups.into_iter().map(|g| g.1).collect();
        let sigma_run = stats::pooled_sd(&gv);
        let median = stats::quantile_nearest_rank(&all_ln, 0.5);
        out.push(format!("sigma_run = {} (df = {})", fmt(sigma_run), gv.iter().map(|g| g.len().saturating_sub(1)).sum::<usize>()));
        out.push(format!("incumbent_median_ln_ns = {}", fmt(median)));
        // t_run = delta_h of the counted, uncapped runs
        let mut t: Vec<f64> = Vec::new();
        for b in &uncapped {
            for s in b.seqs.iter().flatten() {
                if let Some(r) = run_of(&nights, &b.night, *s) {
                    if let Some(h) = r.get("observe").and_then(|x| x.fk("delta_h_ns")) {
                        t.push(h);
                    }
                }
            }
        }
        out.push(format!("t_run_ns = median {} p01 {} p99 {} (n = {})", q(&t, 0.5), q(&t, 0.01), q(&t, 0.99), t.len()));
        // slow outliers: the R scorer replayed per counted session, c_run = 4 sigma_run (pass 2)
        match (sigma_run, median) {
            (Some(sr), Some(med)) => {
                let (mut slow, mut n) = (0u64, 0u64);
                let mut ids: Vec<&String> = sess.iter().copied().filter(|s| counted(s)).collect();
                ids.dedup();
                for id in ids {
                    let mut sc = BlockScorer::new(Scorer::R, 1.0, 4.0 * sr, med);
                    for b in cb.iter().filter(|b| &b.session == id) {
                        let runs: Vec<(Arm, f64)> = (0..4).map(|k| (b.arms[k], b.ln[k])).collect();
                        if sc.try_score(b.d, &runs, &b.capped).is_err() {
                            return Err(format!("session {}: a non-finite block", id));
                        }
                    }
                    slow += sc.slow_a + sc.slow_b;
                    n += sc.nruns_a + sc.nruns_b;
                }
                let rate = if n > 0 { slow as f64 / n as f64 } else { f64::NAN };
                out.push(format!("slow_outliers = {} of {} runs (rate {})", slow, n, fmt(Some(rate))));
                out.push(format!("p0 = {}", if n > 0 { format!("{:.6}", stats::clopper_pearson_upper(slow as i64, n as i64, 0.95)) } else { "none".into() }));
            }
            _ => out.push("slow_outliers = none (sigma_run or the median is undefined)".into()),
        }
        // observe-mode quantities over every accepted or capped run of a counted session, and the
        // section 7(a) fill-in: 2 x the maximum (tau floored at 1 ms, the extra-core slack at 0.05)
        let obs: Vec<&J> = nights
            .iter()
            .flat_map(|n| n.runs.iter())
            .filter(|r| r.sk("run_type") == Some(rt.as_str()) && counted(r.sk("session").unwrap_or("")) && matches!(r.sk("verdict"), Some("Accept") | Some("TimeCapped")))
            .filter_map(|r| r.get("observe"))
            .collect();
        out.push(format!("observe_runs = {}", obs.len()));
        let col = |k: &str| -> Vec<f64> { obs.iter().filter_map(|o| o.fk(k)).collect() };
        let ceil = |k: &str| -> Option<f64> { maxf(&col(k)) };
        let rows: [(&str, &str, Option<f64>, f64); 8] = [
            ("tau_clock_ns", "abs_diff_ns", None, 1e6),
            ("kappa_post_cycles", "post_stop_cycles", ceil("kappa_post_ceiling"), 0.0),
            ("eps_spin_us", "eps_spin_observed_us", Some(50.0), 0.0),
            ("eps_idle_us", "eps_idle_observed_us", Some(1000.0), 0.0),
            ("init_max_wall_ns", "init_wall_ns", ceil("init_wall_ceiling_ns"), 0.0),
            ("init_max_cycles", "init_cycles", ceil("init_cycles_ceiling"), 0.0),
            ("extra_cores", "extra_cores", ceil("extra_cores_ceiling"), 0.05),
            ("exit_grace_ns", "teardown_wall_ns", ceil("exit_grace_ns"), 0.0),
        ];
        for (name, key, ceiling, floor) in rows {
            let m = maxf(&col(key));
            let fill = m.map(|x| (2.0 * x).max(floor));
            let over = match (name, fill, ceiling) {
                // tau's ceiling is relative (0.1% of each run's delta_o): judged on the margins
                ("tau_clock_ns", _, _) => maxf(&col("tau_margin")).map_or(false, |mm| 2.0 * mm > 1.0),
                (_, Some(f), Some(c)) => f > c,
                _ => false,
            };
            out.push(format!(
                "observe {} max = {} fill_in_2x = {} ceiling = {}{}",
                name,
                fmt(m),
                fmt(fill),
                if name == "tau_clock_ns" { "0.1% of delta_o".to_string() } else { fmt(ceiling) },
                if over { " ABOVE THE CEILING: a design revisit before collection (record section 7(a))" } else { "" }
            ));
        }
        // the load gate: nearest-rank p99 of the pre-run 2-s load of the counted sessions' gates
        let loads: Vec<f64> = nights
            .iter()
            .flat_map(|n| n.sensors.iter())
            .filter(|s| s.get("for_seq").is_some() && counted(s.sk("session").unwrap_or("")) && &run_type_of(s.sk("session").unwrap_or("")) == rt)
            .filter_map(|s| s.fk("load_total_pct"))
            .collect();
        let p99 = stats::quantile_nearest_rank(&loads, 0.99);
        out.push(format!("load_2s_pct p50 {} p99 {} (n = {}); load_gate_threshold = {}", q(&loads, 0.5), fmt(p99), loads.len(), fmt(p99.map(|p| (p + 2.0).min(40.0)))));
        // start-state envelopes (descriptive; MEASUREMENT 4.1 maps them)
        let sv = |k: &str| -> Vec<f64> {
            nights.iter().flat_map(|n| n.sensors.iter()).filter(|s| s.get("for_seq").is_some() && counted(s.sk("session").unwrap_or("")) && &run_type_of(s.sk("session").unwrap_or("")) == rt).filter_map(|s| s.fk(k)).collect()
        };
        let mp = sv("modified_page_bytes");
        let dw = sv("disk_write_bps");
        let st = sv("settle_ms");
        out.push(format!("modified_page_bytes p50 {} p99 {}; disk_write_bps p99 {}; settle_ms p99 {}", q(&mp, 0.5), q(&mp, 0.99), q(&dw, 0.99), q(&st, 0.99)));
        let eff: Vec<f64> = nights.iter().flat_map(|n| n.sessions.iter()).filter(|s| s.sk("run_type") == Some(rt.as_str()) && counted(s.sk("session").unwrap_or(""))).filter_map(|s| s.fk("settle_eff_mhz_run_lps")).collect();
        out.push(format!("settle_eff_mhz_run_lps p01 {} p50 {}", q(&eff, 0.01), q(&eff, 0.5)));
        // discards (blocks) and productive block time
        let (mut disc, mut scored) = (0usize, 0usize);
        let mut causes: Vec<(String, usize)> = Vec::new();
        for s in nights.iter().flat_map(|n| n.sessions.iter()).filter(|s| s.sk("run_type") == Some(rt.as_str())) {
            disc += s.fk("discards").unwrap_or(0.0) as usize;
            scored += s.fk("blocks").unwrap_or(0.0) as usize;
            for r in s.get("discard_reasons").and_then(|x| x.arr()).into_iter().flatten() {
                let r = r.s().unwrap_or("");
                let cat = ["background activity", "2-s CPU load", "start state", "run core", "core parking"].iter().find(|c| r.contains(*c)).map(|c| c.to_string()).unwrap_or_else(|| "other".into());
                match causes.iter_mut().find(|(c, _)| *c == cat) {
                    Some(x) => x.1 += 1,
                    None => causes.push((cat, 1)),
                }
            }
        }
        causes.sort();
        out.push(format!(
            "blocks_attempted = {} discarded = {} (rate {}) causes: {}",
            disc + scored,
            disc,
            fmt(if disc + scored > 0 { Some(disc as f64 / (disc + scored) as f64) } else { None }),
            if causes.is_empty() { "none".to_string() } else { causes.iter().map(|(c, n)| format!("{}:{}", c, n)).collect::<Vec<_>>().join(", ") }
        ));
        // descriptive: within-session SD of d, s_between, carry-over
        let mut by_sess: Vec<(String, Vec<f64>)> = Vec::new();
        for b in &uncapped {
            match by_sess.iter_mut().find(|(s, _)| *s == b.session) {
                Some(x) => x.1.push(b.d),
                None => by_sess.push((b.session.clone(), vec![b.d])),
            }
        }
        let within = stats::pooled_sd(&by_sess.iter().map(|x| x.1.clone()).collect::<Vec<_>>());
        let means: Vec<f64> = by_sess.iter().map(|x| x.1.iter().sum::<f64>() / x.1.len() as f64).collect();
        let s_between = if means.len() >= 2 {
            let m = means.iter().sum::<f64>() / means.len() as f64;
            Some((means.iter().map(|v| (v - m) * (v - m)).sum::<f64>() / (means.len() - 1) as f64).sqrt())
        } else {
            None
        };
        let co: Vec<[(bool, f64); 4]> = uncapped.iter().map(|b| [(b.arms[0] == Arm::B, b.ln[0]), (b.arms[1] == Arm::B, b.ln[1]), (b.arms[2] == Arm::B, b.ln[2]), (b.arms[3] == Arm::B, b.ln[3])]).collect();
        let carry = stats::carry_over_contrast(&co);
        out.push(format!(
            "descriptive within_session_sd_d = {} s_between = {} carry_over = {} s3_trend_sessions = {}",
            fmt(within),
            fmt(s_between),
            carry.map(|(a, b)| format!("{:.6} (SE {:.6})", a, b)).unwrap_or_else(|| "none".into()),
            nights.iter().flat_map(|n| n.sessions.iter()).filter(|s| s.sk("run_type") == Some(rt.as_str()) && s.get("s3_trend_reported").and_then(|x| x.b()) == Some(true)).count()
        ));
    }
    // productive block-hours per night: the wall time of the counted blocks (sensors.jsonl block_cpu)
    let mut per_night: Vec<f64> = Vec::new();
    for n in &nights {
        let mut s = 0.0;
        for b in blocks.iter().filter(|b| b.night == n.label && end_of(&b.session) == "completed") {
            let first = b.seqs.first().copied().flatten();
            if let Some(w) = n.sensors.iter().find(|x| x.sk("kind") == Some("block_cpu") && x.sk("session") == Some(b.session.as_str()) && x.fk("first_seq").map(|v| v as u64) == first).and_then(|x| x.fk("wall_s")) {
                s += w;
            }
        }
        out.push(format!("night {} productive_block_hours = {:.4}", n.label, s / 3600.0));
        if s > 0.0 {
            per_night.push(s / 3600.0);
        }
    }
    out.push(format!("productive_block_hours median over nights with counted blocks = {}", q(&per_night, 0.5)));
    Ok(out.join("\n") + "\n")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn json_subset() {
        let j = parse_json(r#"{"a":1.5,"b":[true,false,null],"c":"x\"\\y\u0041","d":{"e":-2e3}}"#).unwrap();
        assert_eq!(j.fk("a"), Some(1.5));
        assert_eq!(j.get("b").unwrap().arr().unwrap()[0], J::Bool(true));
        assert_eq!(j.sk("c"), Some("x\"\\yA"));
        assert_eq!(j.get("d").unwrap().fk("e"), Some(-2000.0));
        assert!(parse_json(r#"{"a":1"#).is_err());
        assert!(parse_json(r#"{"a":1} x"#).is_err());
    }

    struct Fx {
        root: PathBuf,
    }
    impl Fx {
        fn new(tag: &str) -> Fx {
            let root = std::env::temp_dir().join(format!("x4est-{}-{}", tag, std::process::id()));
            let _ = std::fs::remove_dir_all(&root);
            std::fs::create_dir_all(&root).unwrap();
            Fx { root }
        }
        fn put(&self, rel: &str, text: &str) {
            let p = self.root.join(rel);
            std::fs::create_dir_all(p.parent().unwrap()).unwrap();
            std::fs::write(p, text).unwrap();
        }
        fn append(&self, rel: &str, text: &str) {
            use std::io::Write;
            let mut f = std::fs::OpenOptions::new().append(true).open(self.root.join(rel)).unwrap();
            f.write_all(text.as_bytes()).unwrap();
        }
        /// A manifest over the night's files as they are now.
        fn manifest(&self, night: &str, status: &str, file: &str, canon: &str) {
            let mut l = vec![format!("grade=PILOT"), format!("status={}", status), format!("night={}", night), format!("freeze_commit={}", "a".repeat(40)), format!("config_canonical_sha256={}", canon), "integrity_cleared=".to_string()];
            for f in ["voids.log", "runs.jsonl", "blocks.jsonl", "sessions.jsonl", "sensors.jsonl", "plants.jsonl"] {
                let b = std::fs::read(self.root.join(format!("night-{}", night)).join(f)).unwrap();
                l.push(format!("sha256[{}]={}", f, sha_hex(&b)));
            }
            let p = std::fs::read(self.root.join("progress.txt")).unwrap();
            l.push(format!("sha256[progress.txt]={} bytes={} (x)", sha_hex(&p), p.len()));
            self.put(&format!("night-{}/{}", night, file), &(l.join("\n") + "\n"));
        }
    }
    impl Drop for Fx {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.root);
        }
    }

    fn block(night: &str, session: &str, n: usize, seq0: u64, ln: [f64; 4], capped: bool) -> String {
        let _ = night;
        let arms = ["A", "B", "B", "A"];
        let d = 0.5 * ((ln[1] + ln[2]) - (ln[0] + ln[3]));
        format!(
            "{{\"grade\":\"PILOT\",\"night\":\"x\",\"session\":\"{}\",\"block\":{},\"order\":\"Abba\",\"seqs\":[{},{},{},{}],\"arms\":[\"{}\",\"{}\",\"{}\",\"{}\"],\"ln_delta_h_ns\":[{},{},{},{}],\"capped\":[{},false,false,false],\"d\":{}}}\n",
            session, n, seq0, seq0 + 1, seq0 + 2, seq0 + 3, arms[0], arms[1], arms[2], arms[3], ln[0], ln[1], ln[2], ln[3], capped, d
        )
    }
    fn run(session: &str, rt: &str, seq: u64, dh: f64) -> String {
        format!("{{\"grade\":\"PILOT\",\"session\":\"{}\",\"run_type\":\"{}\",\"seq\":{},\"verdict\":\"Accept\",\"observe\":{{\"delta_h_ns\":{},\"abs_diff_ns\":1000,\"tau_margin\":0.1,\"post_stop_cycles\":5e8,\"kappa_post_ceiling\":2e9,\"eps_spin_observed_us\":3,\"eps_idle_observed_us\":10,\"init_wall_ns\":8e8,\"init_wall_ceiling_ns\":2e9,\"init_cycles\":3e9,\"init_cycles_ceiling\":8.6e9,\"extra_cores\":0.01,\"extra_cores_ceiling\":0.25,\"teardown_wall_ns\":2e6,\"exit_grace_ns\":5e9}}}}\n", session, rt, seq, dh)
    }
    fn sess(id: &str, rt: &str, end: &str, blocks: usize) -> String {
        format!("{{\"grade\":\"PILOT\",\"session\":\"{}\",\"run_type\":\"{}\",\"end\":\"{}\",\"blocks\":{},\"discards\":1,\"discard_reasons\":[\"background activity over the block: msmpeng 2%\"],\"s3_trend_reported\":false,\"settle_eff_mhz_run_lps\":5300}}\n", id, rt, end, blocks)
    }

    /// One closed night: mb-01 completed (3 blocks), mb-02 integrity_stop (1), mb-03 cut (2),
    /// e2e-01 completed (2).
    fn night1(fx: &Fx) -> (String, Vec<f64>) {
        let mut b = String::new();
        let mut r = String::new();
        let mut seq = 1;
        let mut d1 = Vec::new();
        let lns = [[23.0, 23.01, 23.02, 23.0], [23.0, 22.99, 23.0, 23.01], [23.02, 23.0, 23.01, 23.0]];
        for (i, l) in lns.iter().enumerate() {
            b.push_str(&block("2026-10-25", "mb-q4-avx512-01", i + 1, seq, *l, false));
            d1.push(0.5 * ((l[1] + l[2]) - (l[0] + l[3])));
            for k in 0..4usize {
                r.push_str(&run("mb-q4-avx512-01", "mb-q4-avx512", seq + k as u64, l[k].exp()));
            }
            seq += 4;
        }
        b.push_str(&block("2026-10-25", "mb-q4-avx512-02", 1, seq, [23.0, 23.5, 23.5, 23.0], false));
        seq += 4;
        for i in 0..2 {
            b.push_str(&block("2026-10-25", "mb-q4-avx512-03", i + 1, seq, [23.0, 23.2, 23.2, 23.0], false));
            seq += 4;
        }
        for i in 0..2 {
            b.push_str(&block("2026-10-25", "e2e-decode-01", i + 1, seq, [25.0, 25.01, 25.0, 25.0], i == 1));
            seq += 4;
        }
        fx.put("night-2026-10-25/blocks.jsonl", &b);
        fx.put("night-2026-10-25/runs.jsonl", &r);
        fx.put(
            "night-2026-10-25/sessions.jsonl",
            &[sess("mb-q4-avx512-01", "mb-q4-avx512", "completed", 3), sess("mb-q4-avx512-02", "mb-q4-avx512", "integrity_stop", 1), sess("mb-q4-avx512-03", "mb-q4-avx512", "cut", 2), sess("e2e-decode-01", "e2e-decode", "completed", 2)].concat(),
        );
        fx.put("night-2026-10-25/sensors.jsonl", "{\"grade\":\"PILOT\",\"session\":\"mb-q4-avx512-01\",\"for_seq\":1,\"load_total_pct\":3.5,\"modified_page_bytes\":1e8,\"disk_write_bps\":1000,\"settle_ms\":1000}\n{\"grade\":\"PILOT\",\"session\":\"mb-q4-avx512-01\",\"kind\":\"block_cpu\",\"first_seq\":1,\"wall_s\":60}\n");
        fx.put("night-2026-10-25/voids.log", "PILOT 20261026T060000Z 2026-10-25 23:00:00 PDT [PRESTART-OK] session=- x\n");
        fx.put("night-2026-10-25/plants.jsonl", "");
        fx.put(
            "progress.txt",
            "mb-q4-avx512-01 started PILOT 2026-10-25 seed=s harness=h x4svc=x\nmb-q4-avx512-01 completed PILOT 2026-10-25\nmb-q4-avx512-02 started PILOT 2026-10-25 seed=s harness=h x4svc=x\nmb-q4-avx512-02 integrity_stop PILOT 2026-10-25\nmb-q4-avx512-03 started PILOT 2026-10-25 seed=s harness=h x4svc=x\nmb-q4-avx512-03 cut PILOT 2026-10-25\ne2e-decode-01 started PILOT 2026-10-25 seed=s harness=h x4svc=x\ne2e-decode-01 completed PILOT 2026-10-25\n",
        );
        let canon = "c".repeat(64);
        fx.manifest("2026-10-25", "stopped", "manifest.txt", &canon);
        (canon, d1)
    }
    fn opts(fx: &Fx, canon: &str) -> EstimateOpts {
        EstimateOpts { data_dir: fx.root.display().to_string(), grade: "PILOT".into(), freeze_commit: Some("a".repeat(40)), config_sha256: Some(canon.to_string()) }
    }

    #[test]
    fn the_counted_set_and_sigma_d() {
        let fx = Fx::new("counted");
        let (canon, d1) = night1(&fx);
        let rep = estimate(&opts(&fx, &canon)).unwrap_or_else(|e| panic!("{e}"));
        let want = stats::rms_about_zero(&d1).unwrap().0;
        assert!(rep.contains(&format!("sigma_d = {:.6}", want)), "{rep}");
        assert!(rep.contains("B = 3"), "{rep}");
        // the integrity_stop and cut sessions' blocks are excluded and reported
        assert!(rep.contains("blocks_excluded_by_session_end = cut:2, integrity_stop:1"), "{rep}");
        assert!(rep.contains("(B = 5, cut sessions = 1)"), "{rep}");
        // e2e: one of its two blocks holds a capped run
        assert!(rep.contains("blocks_counted = 2 (of which 1 hold a capped run"), "{rep}");
        assert!(rep.contains("load_gate_threshold = 5.500000"), "{rep}");
        assert!(rep.contains("productive_block_hours = 0.0167"), "{rep}");
        // progress.txt growing after the manifest is fine (its prefix still hashes)
        fx.append("progress.txt", "mb-q4-avx512-04 started PILOT 2026-10-26 seed=s harness=h x4svc=x\n");
        assert!(estimate(&opts(&fx, &canon)).is_ok());
    }

    #[test]
    fn every_refusal() {
        let fx = Fx::new("refuse");
        let (canon, _) = night1(&fx);
        assert!(estimate(&opts(&fx, &"d".repeat(64))).unwrap_err().contains("canonical configuration"));
        let mut o = opts(&fx, &canon);
        o.freeze_commit = Some("b".repeat(40));
        assert!(estimate(&o).unwrap_err().contains("freeze_commit"));
        // a record file changed after its manifest
        fx.append("night-2026-10-25/runs.jsonl", "\n");
        assert!(estimate(&opts(&fx, &canon)).unwrap_err().contains("runs.jsonl does not match"));
        // a DRY-RUN line inside PILOT data refuses the whole input
        let (canon, _) = night1(&fx);
        fx.append("night-2026-10-25/runs.jsonl", "{\"grade\":\"DRY-RUN\",\"seq\":99}\n");
        fx.manifest("2026-10-25", "stopped", "manifest.txt", &canon);
        assert!(estimate(&opts(&fx, &canon)).unwrap_err().contains("not PILOT"));
        // an open night is refused until it is closed
        let (canon, _) = night1(&fx);
        fx.manifest("2026-10-25", "open", "manifest.txt", &canon);
        assert!(estimate(&opts(&fx, &canon)).unwrap_err().contains("is open"));
        // progress.txt rewritten (not appended)
        let (canon, _) = night1(&fx);
        fx.put("progress.txt", "rewritten\n");
        assert!(estimate(&opts(&fx, &canon)).unwrap_err().contains("progress.txt"));
    }

    #[test]
    fn a_night_closed_after_an_interruption() {
        let fx = Fx::new("closed");
        let (canon, d1) = night1(&fx);
        // night 2: mb-04 started, one block written, then the power went (a cut-short runs line)
        fx.put("night-2026-10-26/blocks.jsonl", &block("2026-10-26", "mb-q4-avx512-04", 1, 1, [23.0, 24.0, 24.0, 23.0], false));
        fx.put("night-2026-10-26/runs.jsonl", &format!("{}{{\"grade\":\"PIL", run("mb-q4-avx512-04", "mb-q4-avx512", 1, 1e10)));
        fx.put("night-2026-10-26/sessions.jsonl", "");
        fx.put("night-2026-10-26/sensors.jsonl", "");
        fx.put("night-2026-10-26/voids.log", "");
        fx.put("night-2026-10-26/plants.jsonl", "");
        fx.append("progress.txt", "mb-q4-avx512-04 started PILOT 2026-10-26 seed=s harness=h x4svc=x\n");
        fx.manifest("2026-10-26", "open", "manifest.txt", &canon);
        assert!(estimate(&opts(&fx, &canon)).unwrap_err().contains("is open"));
        // the next night's driver (or pilot-close) writes the closure manifest and the interrupted line
        fx.manifest("2026-10-26", "closed-after-interrupt", "manifest-closed-after-interrupt.txt", &canon);
        fx.append("progress.txt", "mb-q4-avx512-04 interrupted PILOT 2026-10-27\n");
        let rep = estimate(&opts(&fx, &canon)).unwrap_or_else(|e| panic!("{e}"));
        assert!(rep.contains("truncated_last_lines=1"), "{rep}");
        assert!(rep.contains(&format!("sigma_d = {:.6}", stats::rms_about_zero(&d1).unwrap().0)), "{rep}");
        assert!(rep.contains("interrupted:1"), "{rep}");
        // a cut-short line in a night that was closed normally is refused
        fx.manifest("2026-10-26", "stopped", "manifest.txt", &canon);
        std::fs::remove_file(fx.root.join("night-2026-10-26/manifest-closed-after-interrupt.txt")).unwrap();
        assert!(estimate(&opts(&fx, &canon)).is_err());
    }
}
