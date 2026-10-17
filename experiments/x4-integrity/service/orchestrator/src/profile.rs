//! The quiet-machine PROFILE VERIFIER (MEASUREMENT-SERVICE.md section 7). It **only reads state** and
//! **refuses to run** when the profile is not met, printing the exact commands Pierce would run. It
//! never edits a setting (DECISIONS.md, 06 section 6.7): changing a system or security setting is the
//! Owner's, never the service's. On a mismatch the service refuses the session with a diagnostic
//! naming the failing item and the fix command.
//!
//! State is read through a `StateReader` so the policy is unit-tested with synthetic state and the
//! Windows reader (read-only `powercfg`/`Get-MpPreference` queries) is a thin adapter.

/// What the service reads, read-only. A None means "could not read" (unverifiable).
pub trait StateReader {
    /// GUID of the active power scheme, lowercase, or None.
    fn active_power_scheme(&self) -> Option<String>;
    /// The name of the active power scheme, or None.
    fn active_power_scheme_name(&self) -> Option<String>;
    /// AC value of SUB_PROCESSOR\CPMINCORES and CPMAXCORES for the active scheme (percent), or None.
    fn core_parking_min_max(&self) -> Option<(u32, u32)>;
    /// Defender exclusion paths, or None if unreadable (e.g. not elevated).
    fn defender_exclusion_paths(&self) -> Option<Vec<String>>;
}

/// The expected profile, pinned in the prereg before collection. Defaults follow section 7.
#[derive(Clone, Debug)]
pub struct ProfileSpec {
    /// Expected active-scheme GUID (filled in by Pierce after `powercfg /duplicatescheme`). None means
    /// "a dedicated MITHRIL-MEASURE plan must be active", checked by name until the GUID is pinned.
    pub expected_scheme_guid: Option<String>,
    pub expected_scheme_name: String,
    pub data_dir: String,
}

impl Default for ProfileSpec {
    fn default() -> Self {
        ProfileSpec {
            expected_scheme_guid: None,
            expected_scheme_name: "MITHRIL-MEASURE".to_string(),
            data_dir: "D:\\mithril-data".to_string(),
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct ProfileItem {
    pub name: String,
    pub ok: bool,
    pub observed: String,
    pub fix_command: String,
}

#[derive(Clone, Debug)]
pub struct ProfileReport {
    pub items: Vec<ProfileItem>,
}

impl ProfileReport {
    pub fn met(&self) -> bool {
        self.items.iter().all(|i| i.ok)
    }
    /// The service refuses to run when the profile is not met.
    pub fn refuses_to_run(&self) -> bool {
        !self.met()
    }
    /// A diagnostic naming every failing item and the command Pierce must run (never run by us).
    pub fn diagnostic(&self) -> String {
        let mut s = String::new();
        if self.met() {
            s.push_str("quiet-machine profile: MET. All items verified read-only.\n");
            return s;
        }
        s.push_str("quiet-machine profile: NOT MET -- the service refuses to run.\n");
        s.push_str("The service changes no system settings. Pierce runs the commands below (elevated where noted),\n");
        s.push_str("then re-runs `x4svc verify-profile`:\n\n");
        for it in self.items.iter().filter(|i| !i.ok) {
            s.push_str(&format!("  [FAIL] {}\n", it.name));
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
pub fn verify(spec: &ProfileSpec, reader: &dyn StateReader) -> ProfileReport {
    let mut items = Vec::new();

    // 7.1 power plan
    let name = reader.active_power_scheme_name();
    let guid = reader.active_power_scheme();
    let scheme_ok = match (&spec.expected_scheme_guid, &guid, &name) {
        (Some(want), Some(g), _) => g.eq_ignore_ascii_case(want),
        (None, _, Some(n)) => n.eq_ignore_ascii_case(&spec.expected_scheme_name),
        _ => false,
    };
    items.push(ProfileItem {
        name: "7.1 active power scheme is the dedicated measurement plan".into(),
        ok: scheme_ok,
        observed: format!("name={:?} guid={:?}", name, guid),
        fix_command: "powercfg /duplicatescheme 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c MITHRIL-MEASURE; \
                      powercfg /setactive MITHRIL-MEASURE   (elevated; record the printed GUID and pin it in the prereg)"
            .into(),
    });

    // 7.2 core parking off (CPMINCORES = CPMAXCORES = 100)
    let parking = reader.core_parking_min_max();
    let parking_ok = matches!(parking, Some((100, 100)));
    items.push(ProfileItem {
        name: "7.2 core parking disabled (CPMINCORES=CPMAXCORES=100)".into(),
        ok: parking_ok,
        observed: format!("{:?}", parking),
        fix_command: "powercfg /setacvalueindex MITHRIL-MEASURE SUB_PROCESSOR CPMINCORES 100; \
                      powercfg /setacvalueindex MITHRIL-MEASURE SUB_PROCESSOR CPMAXCORES 100; \
                      powercfg /setactive MITHRIL-MEASURE   (elevated)"
            .into(),
    });

    // 7.3 Defender exclusion of the data directory (recommended, not required; still reported)
    let excl = reader.defender_exclusion_paths();
    let excl_ok = match &excl {
        Some(paths) => paths.iter().any(|p| p.eq_ignore_ascii_case(&spec.data_dir)),
        None => false,
    };
    items.push(ProfileItem {
        name: "7.3 Defender real-time scan excludes the data directory (recommended)".into(),
        ok: excl_ok,
        observed: match &excl {
            Some(p) => format!("{:?}", p),
            None => "unreadable (not elevated?)".into(),
        },
        fix_command: format!("Add-MpPreference -ExclusionPath '{}'   (elevated; security trade-off, Owner's call)", spec.data_dir),
    });

    ProfileReport { items }
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

    #[test]
    fn balanced_plan_is_refused_with_commands() {
        let spec = ProfileSpec::default();
        let state = FakeState {
            name: Some("Balanced".into()),
            guid: Some("381b4222-f694-41f0-9685-ff5bb260df2e".into()),
            parking: Some((5, 100)),
            excl: None,
        };
        let r = verify(&spec, &state);
        assert!(r.refuses_to_run());
        let d = r.diagnostic();
        assert!(d.contains("NOT MET"));
        assert!(d.contains("duplicatescheme")); // prints the fix command
        assert!(d.contains("CPMINCORES"));
    }

    #[test]
    fn fully_configured_profile_is_met() {
        let spec = ProfileSpec::default();
        let state = FakeState {
            name: Some("MITHRIL-MEASURE".into()),
            guid: Some("abc".into()),
            parking: Some((100, 100)),
            excl: Some(vec!["D:\\mithril-data".into()]),
        };
        let r = verify(&spec, &state);
        assert!(r.met());
        assert!(!r.refuses_to_run());
    }

    #[test]
    fn guid_match_takes_precedence_when_pinned() {
        let mut spec = ProfileSpec::default();
        spec.expected_scheme_guid = Some("DEAD-BEEF".into());
        let state = FakeState {
            name: Some("Something".into()),
            guid: Some("dead-beef".into()),
            parking: Some((100, 100)),
            excl: Some(vec!["D:\\mithril-data".into()]),
        };
        let r = verify(&spec, &state);
        assert!(r.items[0].ok); // GUID matched case-insensitively despite the name differing
    }
}
