//! Windows adapter for the profile verifier's `StateReader`: read-only `powercfg` / `Get-MpPreference`
//! queries. It runs query commands only; it never sets a value (MEASUREMENT-SERVICE.md section 7).

#![cfg(windows)]

use crate::profile::StateReader;
use std::process::Command;

pub struct WinState;

fn run(cmd: &str, args: &[&str]) -> Option<String> {
    let out = Command::new(cmd).args(args).output().ok()?;
    if out.status.success() || !out.stdout.is_empty() {
        Some(String::from_utf8_lossy(&out.stdout).to_string())
    } else {
        None
    }
}

impl WinState {
    fn active_scheme_line(&self) -> Option<String> {
        run("powercfg", &["/getactivescheme"])
    }
}

impl StateReader for WinState {
    fn active_power_scheme(&self) -> Option<String> {
        // "Power Scheme GUID: <guid>  (<name>)"
        let line = self.active_scheme_line()?;
        let after = line.split("GUID:").nth(1)?;
        let guid = after.trim().split_whitespace().next()?.to_string();
        Some(guid.to_lowercase())
    }
    fn active_power_scheme_name(&self) -> Option<String> {
        let line = self.active_scheme_line()?;
        let open = line.find('(')?;
        let close = line.rfind(')')?;
        if close > open + 1 {
            Some(line[open + 1..close].trim().to_string())
        } else {
            None
        }
    }
    fn core_parking_min_max(&self) -> Option<(u32, u32)> {
        // query the active scheme's SUB_PROCESSOR settings; parse the AC index of CPMINCORES/CPMAXCORES
        let guid = self.active_power_scheme()?;
        let out = run("powercfg", &["/query", &guid, "SUB_PROCESSOR"])?;
        let get = |needle: &str| -> Option<u32> {
            // find the GUID Alias line, then the next "Current AC Power Setting Index: 0x...."
            let idx = out.find(needle)?;
            let rest = &out[idx..];
            let ac = rest.find("Current AC Power Setting Index:")?;
            let hex = rest[ac..].lines().next()?.split(':').nth(1)?.trim().to_string();
            let v = if let Some(h) = hex.strip_prefix("0x") {
                u32::from_str_radix(h, 16).ok()?
            } else {
                hex.parse().ok()?
            };
            Some(v)
        };
        match (get("CPMINCORES"), get("CPMAXCORES")) {
            (Some(a), Some(b)) => Some((a, b)),
            _ => None,
        }
    }
    fn defender_exclusion_paths(&self) -> Option<Vec<String>> {
        let out = run(
            "powershell",
            &["-NoProfile", "-Command", "(Get-MpPreference).ExclusionPath -join \"`n\""],
        )?;
        let v: Vec<String> = out.lines().map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
        if v.is_empty() {
            // could be genuinely empty or unreadable; treat empty as "readable, none set"
            Some(v)
        } else {
            Some(v)
        }
    }
}
