//! The explicit, minimal environment block every harness child gets (MEASUREMENT-SERVICE.md section 3
//! step 0; review R2-8). It is built from a pinned, sorted list and is byte-identical for both arms and
//! for every run: the per-run scratch directory has a fixed path (`<scratch_root>\run`), wiped before and
//! deleted after each run, so TEMP/TMP do not vary. Its SHA-256 (over the UTF-16LE bytes, terminators
//! included) goes into the run record and the fingerprint (section 5.2).

use crate::sha256;

#[derive(Clone, Debug)]
pub struct EnvBlock {
    /// Sorted (case-insensitively) KEY=VALUE pairs.
    pub pairs: Vec<(String, String)>,
    /// `K=V\0K=V\0\0` in UTF-16 (CREATE_UNICODE_ENVIRONMENT).
    pub utf16: Vec<u16>,
    pub sha256_hex: String,
}

/// Build the block. `system_root` is pinned (Winsock and the loader need it); `scratch_dir` is the
/// fixed per-run directory; `pinned` are the record's pinned variables (e.g. HEARTH_THREADS).
pub fn build(system_root: &str, scratch_dir: &str, pinned: &[(String, String)]) -> Result<EnvBlock, String> {
    let mut pairs: Vec<(String, String)> = vec![
        ("SystemRoot".into(), system_root.into()),
        ("TEMP".into(), scratch_dir.into()),
        ("TMP".into(), scratch_dir.into()),
    ];
    for (k, v) in pinned {
        if k.is_empty() || k.contains('=') || k.contains('\0') || v.contains('\0') {
            return Err(format!("invalid environment entry {:?}", k));
        }
        if pairs.iter().any(|(e, _)| e.eq_ignore_ascii_case(k)) {
            return Err(format!("duplicate environment key {:?}", k));
        }
        pairs.push((k.clone(), v.clone()));
    }
    pairs.sort_by(|a, b| a.0.to_uppercase().cmp(&b.0.to_uppercase()));
    let mut utf16: Vec<u16> = Vec::new();
    for (k, v) in &pairs {
        utf16.extend(format!("{}={}", k, v).encode_utf16());
        utf16.push(0);
    }
    utf16.push(0);
    let bytes: Vec<u8> = utf16.iter().flat_map(|w| w.to_le_bytes()).collect();
    let sha256_hex = sha256::hex(&sha256::digest(&bytes));
    Ok(EnvBlock { pairs, utf16, sha256_hex })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn block_is_sorted_terminated_and_stable() {
        let a = build("C:\\Windows", "D:\\s\\run", &[("HEARTH_THREADS".into(), "1".into())]).unwrap();
        let keys: Vec<&str> = a.pairs.iter().map(|p| p.0.as_str()).collect();
        assert_eq!(keys, vec!["HEARTH_THREADS", "SystemRoot", "TEMP", "TMP"]);
        assert_eq!(&a.utf16[a.utf16.len() - 2..], &[0, 0]);
        let b = build("C:\\Windows", "D:\\s\\run", &[("HEARTH_THREADS".into(), "1".into())]).unwrap();
        assert_eq!(a.sha256_hex, b.sha256_hex);
        let c = build("C:\\Windows", "D:\\s\\run", &[("HEARTH_THREADS".into(), "2".into())]).unwrap();
        assert_ne!(a.sha256_hex, c.sha256_hex);
        assert!(build("C:\\Windows", "x", &[("TEMP".into(), "y".into())]).is_err());
        assert!(build("C:\\Windows", "x", &[("A=B".into(), "y".into())]).is_err());
    }
}
