//! The quiet-machine PROFILE VERIFIER and the hardware FINGERPRINT (MEASUREMENT-SERVICE.md sections
//! 5.2 and 7). It **only reads state** and **refuses to run** when the profile is not met, printing the
//! exact commands Pierce would run. It never edits a setting (DECISIONS.md, 06 section 6.7).
//!
//! A `VerifiedProfile` (the only thing a `Measured` quantity can be built from) exists only when every
//! *required* item is met, the dedicated plan's GUID is pinned, and the fingerprint hash equals the
//! hash pinned in the pre-registration. Advisory items (the Defender exclusion, section 7.3) are
//! reported but do not refuse (review R2-16). State is read through `StateReader` so the policy is
//! unit-tested; the Windows reader (profile_win.rs) issues read-only queries only.

use crate::sha256;
use std::collections::BTreeMap;

/// What the service reads, read-only. A None means "could not read" (unverifiable).
pub trait StateReader {
    fn active_power_scheme(&self) -> Option<String>;
    fn active_power_scheme_name(&self) -> Option<String>;
    /// AC value of SUB_PROCESSOR CPMINCORES and CPMAXCORES for the active scheme (percent).
    fn core_parking_min_max(&self) -> Option<(u32, u32)>;
    /// Defender exclusion paths, or None if unreadable (e.g. not elevated).
    fn defender_exclusion_paths(&self) -> Option<Vec<String>>;
}

/// Dev: report only, never emits Measured facts. Collection: refuses unless the GUID and the
/// fingerprint hash are pinned and match.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    Dev,
    Collection,
}

/// The expected profile, pinned in the pre-registration before collection.
#[derive(Clone, Debug)]
pub struct ProfileSpec {
    /// Expected active-scheme GUID (Pierce records it after `powercfg /duplicatescheme`).
    pub expected_scheme_guid: Option<String>,
    pub expected_scheme_name: String,
    pub data_dir: String,
    /// Expected fingerprint hash (64 hex), pinned in the pre-data fill-in amendment.
    pub expected_fingerprint_hash: Option<String>,
}

impl Default for ProfileSpec {
    fn default() -> Self {
        ProfileSpec {
            expected_scheme_guid: None,
            expected_scheme_name: "MITHRIL-MEASURE".to_string(),
            data_dir: "D:\\mithril-data".to_string(),
            expected_fingerprint_hash: None,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct ProfileItem {
    pub name: String,
    pub ok: bool,
    /// Advisory items are reported but never refuse the session.
    pub required: bool,
    pub observed: String,
    pub fix_command: String,
}

#[derive(Clone, Debug)]
pub struct ProfileReport {
    pub items: Vec<ProfileItem>,
}

impl ProfileReport {
    /// Every *required* item holds.
    pub fn met(&self) -> bool {
        self.items.iter().filter(|i| i.required).all(|i| i.ok)
    }
    pub fn refuses_to_run(&self) -> bool {
        !self.met()
    }
    /// A diagnostic naming every failing item and the command Pierce must run (never run by us).
    pub fn diagnostic(&self) -> String {
        let mut s = String::new();
        if self.met() {
            s.push_str("quiet-machine profile: required items MET (read-only check).\n");
        } else {
            s.push_str("quiet-machine profile: NOT MET -- the service refuses to run.\n");
            s.push_str("The service changes no system settings. Pierce runs the commands below (elevated where noted),\n");
            s.push_str("then re-runs `x4svc verify-profile`:\n\n");
        }
        for it in self.items.iter().filter(|i| !i.ok) {
            let tag = if it.required { "FAIL" } else { "advisory" };
            s.push_str(&format!("  [{}] {}\n", tag, it.name));
            s.push_str(&format!("         observed: {}\n", it.observed));
            s.push_str(&format!("         fix: {}\n\n", it.fix_command));
        }
        for it in self.items.iter().filter(|i| i.ok) {
            s.push_str(&format!("  [ ok ] {}  ({})\n", it.name, it.observed));
        }
        s
    }
}

/// Verify the profile against the spec, reading state only.
pub fn verify(spec: &ProfileSpec, mode: Mode, reader: &dyn StateReader) -> ProfileReport {
    let mut items = Vec::new();

    // 7.1 power plan: by pinned GUID; by name only in dev mode while the GUID is unpinned
    let name = reader.active_power_scheme_name();
    let guid = reader.active_power_scheme();
    let scheme_ok = match (&spec.expected_scheme_guid, &guid, &name) {
        (Some(want), Some(g), _) => g.eq_ignore_ascii_case(want),
        (None, _, Some(n)) => mode == Mode::Dev && n.eq_ignore_ascii_case(&spec.expected_scheme_name),
        _ => false,
    };
    items.push(ProfileItem {
        name: "7.1 active power scheme is the dedicated measurement plan (GUID pinned for collection)".into(),
        ok: scheme_ok,
        required: true,
        observed: format!("name={:?} guid={:?} pinned={:?}", name, guid, spec.expected_scheme_guid),
        fix_command: "powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c; powercfg /changename <GUID> MITHRIL-MEASURE; \
                      powercfg /setactive <GUID>   (elevated; record the printed GUID and pin it in the prereg)"
            .into(),
    });

    // 7.2 core parking off (CPMINCORES = CPMAXCORES = 100)
    let parking = reader.core_parking_min_max();
    items.push(ProfileItem {
        name: "7.2 core parking disabled (CPMINCORES=CPMAXCORES=100)".into(),
        ok: matches!(parking, Some((100, 100))),
        required: true,
        observed: format!("{:?}", parking),
        fix_command: "powercfg /setacvalueindex <GUID> SUB_PROCESSOR CPMINCORES 100; \
                      powercfg /setacvalueindex <GUID> SUB_PROCESSOR CPMAXCORES 100; powercfg /setactive <GUID>   (elevated)"
            .into(),
    });

    // 7.3 Defender exclusion of the data directory: recommended, not required (section 7.3)
    let excl = reader.defender_exclusion_paths();
    items.push(ProfileItem {
        name: "7.3 Defender real-time scan excludes the data directory (advisory)".into(),
        ok: matches!(&excl, Some(p) if p.iter().any(|x| x.eq_ignore_ascii_case(&spec.data_dir))),
        required: false,
        observed: match &excl {
            Some(p) => format!("{:?}", p),
            None => "unreadable (not elevated?)".into(),
        },
        fix_command: format!("Add-MpPreference -ExclusionPath '{}'   (elevated; security trade-off, Owner's call)", spec.data_dir),
    });

    if mode == Mode::Collection {
        items.push(ProfileItem {
            name: "collection mode: plan GUID and fingerprint hash pinned in the pre-registration".into(),
            ok: spec.expected_scheme_guid.is_some() && spec.expected_fingerprint_hash.is_some(),
            required: true,
            observed: format!("guid {:?}, fingerprint {:?}", spec.expected_scheme_guid, spec.expected_fingerprint_hash),
            fix_command: "pin both in the X4 record's pre-data fill-in amendment (lead engineer; Owner signs)".into(),
        });
    }
    ProfileReport { items }
}

/// The section 5.2 hardware fingerprint: stable identity fields only, as sorted key=value lines.
/// Volatile observations (free space, temperatures) are recorded beside it, not hashed.
#[derive(Clone, Debug, Default)]
pub struct Fingerprint {
    pub fields: BTreeMap<String, String>,
}

/// Fields the hash must contain; a missing one is filled with "unavailable" so the gap is explicit.
pub const FINGERPRINT_KEYS: &[&str] = &[
    "cpu.model",
    "cpu.microcode",
    "cpu.logical_processors",
    "bios.version",
    "board.product",
    "mem.configured_speed_mts",
    "mem.modules",
    "os.build",
    "power.scheme_guid",
    "disk.models_firmware",
    "job.affinity_mask",
    "job.priority_class",
    "env.block_sha256",
    "cpu.pbo_curve_optimizer",
    "cpu.fclk",
];

impl Fingerprint {
    pub fn set(&mut self, k: &str, v: &str) {
        self.fields.insert(k.to_string(), v.trim().to_string());
    }
    /// Sorted `key=value\n` lines over FINGERPRINT_KEYS (missing -> "unavailable").
    pub fn canonical(&self) -> String {
        let mut s = String::new();
        let mut keys: Vec<&str> = FINGERPRINT_KEYS.to_vec();
        keys.sort();
        for k in keys {
            let v = self.fields.get(k).map(|s| s.as_str()).unwrap_or("unavailable");
            let v = if v.is_empty() { "unavailable" } else { v };
            s.push_str(k);
            s.push('=');
            s.push_str(&v.replace('\n', " "));
            s.push('\n');
        }
        s
    }
    pub fn hash_hex(&self) -> String {
        sha256::hex(&sha256::digest(self.canonical().as_bytes()))
    }
    pub fn unavailable(&self) -> Vec<&'static str> {
        FINGERPRINT_KEYS
            .iter()
            .copied()
            .filter(|k| self.fields.get(*k).map_or(true, |v| v.is_empty() || v == "unavailable"))
            .collect()
    }
}

/// Values pinned before collection, read from a committed pins file (`verify-profile --pins FILE`).
/// Format: `key=value` lines; `#` comments and blank lines ignored; keys `power.scheme_guid` (the
/// GUID `powercfg /duplicatescheme` printed) and `fingerprint.sha256` (64 hex, from `x4svc
/// fingerprint` for the run type's affinity, priority and environment block). Unknown keys, duplicate
/// keys or malformed values are an error, never ignored.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Pins {
    pub scheme_guid: Option<String>,
    pub fingerprint_sha256: Option<String>,
}

pub fn parse_pins(text: &str) -> Result<Pins, String> {
    let mut p = Pins::default();
    for (i, raw) in text.lines().enumerate() {
        let line = raw.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let (k, v) = line.split_once('=').ok_or_else(|| format!("pins line {}: no '='", i + 1))?;
        let (k, v) = (k.trim(), v.trim().to_lowercase());
        let slot = match k {
            "power.scheme_guid" => {
                let ok = v.len() == 36
                    && v.chars().enumerate().all(|(j, c)| if [8, 13, 18, 23].contains(&j) { c == '-' } else { c.is_ascii_hexdigit() });
                if !ok {
                    return Err(format!("pins line {}: malformed GUID {:?}", i + 1, v));
                }
                &mut p.scheme_guid
            }
            "fingerprint.sha256" => {
                if v.len() != 64 || !v.chars().all(|c| c.is_ascii_hexdigit()) {
                    return Err(format!("pins line {}: fingerprint.sha256 must be 64 hex", i + 1));
                }
                &mut p.fingerprint_sha256
            }
            _ => return Err(format!("pins line {}: unknown key {:?}", i + 1, k)),
        };
        if slot.is_some() {
            return Err(format!("pins line {}: duplicate key {:?}", i + 1, k));
        }
        *slot = Some(v);
    }
    Ok(p)
}

/// Proof that the profile was verified for collection. Its only constructor checks every required
/// item and the pinned fingerprint hash; `Quantity::measured` requires one.
#[derive(Clone, Debug)]
pub struct VerifiedProfile {
    hash: String,
}

impl VerifiedProfile {
    pub fn hash(&self) -> &str {
        &self.hash
    }
    #[cfg(test)]
    pub(crate) fn for_unit_tests(h: &str) -> Self {
        VerifiedProfile { hash: h.to_string() }
    }
}

/// Collection-mode verification: Ok only if the report is met in Collection mode and the
/// fingerprint hash equals the pinned one.
pub fn verify_for_collection(spec: &ProfileSpec, reader: &dyn StateReader, fp: &Fingerprint) -> Result<VerifiedProfile, String> {
    let rep = verify(spec, Mode::Collection, reader);
    if !rep.met() {
        return Err(rep.diagnostic());
    }
    let h = fp.hash_hex();
    match &spec.expected_fingerprint_hash {
        Some(want) if want.eq_ignore_ascii_case(&h) => Ok(VerifiedProfile { hash: h }),
        Some(want) => Err(format!("fingerprint hash {} != pinned {}", h, want)),
        None => Err("no pinned fingerprint hash".into()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    struct FakeState {
        name: Option<String>,
        guid: Option<String>,
        parking: Option<(u32, u32)>,
        excl: Option<Vec<String>>,
    }
    impl StateReader for FakeState {
        fn active_power_scheme(&self) -> Option<String> {
            self.guid.clone()
        }
        fn active_power_scheme_name(&self) -> Option<String> {
            self.name.clone()
        }
        fn core_parking_min_max(&self) -> Option<(u32, u32)> {
            self.parking
        }
        fn defender_exclusion_paths(&self) -> Option<Vec<String>> {
            self.excl.clone()
        }
    }
    fn configured() -> FakeState {
        FakeState { name: Some("MITHRIL-MEASURE".into()), guid: Some("abc".into()), parking: Some((100, 100)), excl: None }
    }

    #[test]
    fn balanced_plan_is_refused_with_commands() {
        let state = FakeState {
            name: Some("Balanced".into()),
            guid: Some("381b4222-f694-41f0-9685-ff5bb260df2e".into()),
            parking: Some((5, 100)),
            excl: None,
        };
        let r = verify(&ProfileSpec::default(), Mode::Dev, &state);
        assert!(r.refuses_to_run());
        let d = r.diagnostic();
        assert!(d.contains("NOT MET") && d.contains("duplicatescheme") && d.contains("CPMINCORES"));
    }

    #[test]
    fn defender_exclusion_is_advisory() {
        // review R2-16: no exclusion, everything else met -> runs (dev), advisory reported
        let r = verify(&ProfileSpec::default(), Mode::Dev, &configured());
        assert!(r.met());
        assert!(r.diagnostic().contains("advisory"));
    }

    #[test]
    fn collection_refuses_unpinned_guid_and_hash() {
        let r = verify(&ProfileSpec::default(), Mode::Collection, &configured());
        assert!(r.refuses_to_run());
        let mut spec = ProfileSpec::default();
        spec.expected_scheme_guid = Some("ABC".into());
        let mut fp = Fingerprint::default();
        fp.set("cpu.model", "X");
        spec.expected_fingerprint_hash = Some(fp.hash_hex());
        assert!(verify_for_collection(&spec, &configured(), &fp).is_ok());
        let mut other = fp.clone();
        other.set("os.build", "26200.1");
        assert!(verify_for_collection(&spec, &configured(), &other).is_err());
    }

    #[test]
    fn pins_file_is_strict() {
        let h = "a".repeat(64);
        let ok = format!("# pins\npower.scheme_guid = 8C5E7FDA-E8BF-4A96-9A85-A6E23A8C635C\n\nfingerprint.sha256={}\n", h);
        let p = parse_pins(&ok).unwrap();
        assert_eq!(p.scheme_guid.as_deref(), Some("8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"));
        assert_eq!(p.fingerprint_sha256.as_deref(), Some(h.as_str()));
        assert!(parse_pins("power.scheme_guid=not-a-guid").is_err());
        assert!(parse_pins("fingerprint.sha256=abc").is_err());
        assert!(parse_pins("colour=blue").is_err());
        assert!(parse_pins(&format!("fingerprint.sha256={h}\nfingerprint.sha256={h}")).is_err());
        assert!(parse_pins("no equals sign").is_err());
        assert_eq!(parse_pins("").unwrap(), Pins::default());
    }

    #[test]
    fn fingerprint_canonical_form_is_sorted_and_explicit() {
        let mut a = Fingerprint::default();
        a.set("os.build", "26200");
        a.set("cpu.model", "AMD Ryzen 9 9950X");
        let c = a.canonical();
        assert!(c.starts_with("bios.version=unavailable\nboard.product=unavailable\ncpu.fclk="));
        assert!(c.contains("cpu.model=AMD Ryzen 9 9950X\n"));
        let mut b = Fingerprint::default();
        b.set("cpu.model", "AMD Ryzen 9 9950X");
        b.set("os.build", "26200");
        assert_eq!(a.hash_hex(), b.hash_hex());
        assert_eq!(a.hash_hex().len(), 64);
        assert!(a.unavailable().contains(&"bios.version"));
    }
}
