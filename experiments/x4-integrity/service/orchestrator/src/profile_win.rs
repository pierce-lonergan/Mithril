//! Windows adapter for the profile verifier (`StateReader`) and the fingerprint reader: read-only
//! `powercfg`, registry and CIM queries. It runs query commands only; it never sets a value
//! (MEASUREMENT-SERVICE.md section 7).

#![cfg(windows)]

use crate::profile::{Fingerprint, StateReader};
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
        Some(after.trim().split_whitespace().next()?.to_lowercase())
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
        // CPMINCORES and CPMAXCORES are hidden settings: `powercfg /query` omits them, so the round-3
        // reader always saw None (found 2026-10-23 [M]); `/qh` with the setting alias prints them.
        let guid = self.active_power_scheme()?;
        let get = |alias: &str| -> Option<u32> {
            let out = run("powercfg", &["/qh", &guid, "SUB_PROCESSOR", alias])?;
            let idx = out.find(alias)?;
            let rest = &out[idx..];
            let ac = rest.find("Current AC Power Setting Index:")?;
            let hex = rest[ac..].lines().next()?.split(':').nth(1)?.trim().to_string();
            match hex.strip_prefix("0x") {
                Some(h) => u32::from_str_radix(h, 16).ok(),
                None => hex.parse().ok(),
            }
        };
        match (get("CPMINCORES"), get("CPMAXCORES")) {
            (Some(a), Some(b)) => Some((a, b)),
            _ => None,
        }
    }
    fn defender_exclusion_paths(&self) -> Option<Vec<String>> {
        // Without elevation Get-MpPreference reports a placeholder or nothing; an empty or failed read
        // is "unreadable" (None), never "no exclusions".
        let out = run("powershell", &["-NoProfile", "-Command", "(Get-MpPreference).ExclusionPath -join \"`n\""])?;
        let v: Vec<String> = out.lines().map(|s| s.trim().to_string()).filter(|s| !s.is_empty()).collect();
        if v.is_empty() || v.iter().any(|s| s.starts_with("N/A")) {
            None
        } else {
            Some(v)
        }
    }
}

/// One read-only PowerShell query printing `key=value` lines for the section 5.2 identity fields.
const FP_QUERY: &str = r#"
$ErrorActionPreference = 'SilentlyContinue'
$p = Get-CimInstance Win32_Processor | Select-Object -First 1
"cpu.model=$($p.Name.Trim())"
"cpu.logical_processors=$($p.NumberOfLogicalProcessors)"
$u = (Get-ItemProperty 'HKLM:\HARDWARE\DESCRIPTION\System\CentralProcessor\0').'Update Revision'
if ($u) { "cpu.microcode=" + (($u | ForEach-Object { $_.ToString('x2') }) -join '') }
$b = Get-CimInstance Win32_BIOS
"bios.version=$($b.SMBIOSBIOSVersion) $($b.ReleaseDate.ToString('yyyy-MM-dd'))"
$bb = Get-CimInstance Win32_BaseBoard
"board.product=$($bb.Manufacturer) $($bb.Product)"
$m = Get-CimInstance Win32_PhysicalMemory
"mem.configured_speed_mts=" + (($m | ForEach-Object { $_.ConfiguredClockSpeed }) -join ',')
"mem.modules=" + (($m | ForEach-Object { "$($_.PartNumber.Trim())/$($_.Capacity)" }) -join ',')
$cv = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
"os.build=$($cv.CurrentBuildNumber).$($cv.UBR)"
"disk.models_firmware=" + ((Get-PhysicalDisk | Sort-Object DeviceId | ForEach-Object { "$($_.FriendlyName)/$($_.FirmwareVersion)/$($_.BusType)" }) -join ',')
"#;

/// Read the identity fields (read-only). `job_affinity`, `priority_class` and the env-block hash are
/// the orchestrator's own values for this session. PBO/Curve-Optimizer state and FCLK have no
/// read-only source wired here and stay "unavailable" (listed in IMPLEMENTATION.md).
pub fn read_fingerprint(job_affinity: u64, priority_class: u32, env_sha256_hex: &str) -> Fingerprint {
    let mut fp = Fingerprint::default();
    if let Some(out) = run("powershell", &["-NoProfile", "-NonInteractive", "-Command", FP_QUERY]) {
        for line in out.lines() {
            if let Some((k, v)) = line.split_once('=') {
                fp.set(k.trim(), v);
            }
        }
    }
    if let Some(g) = WinState.active_power_scheme() {
        fp.set("power.scheme_guid", &g);
    }
    fp.set("job.affinity_mask", &format!("{:#x}", job_affinity));
    fp.set("job.priority_class", &format!("{:#x}", priority_class));
    fp.set("env.block_sha256", env_sha256_hex);
    fp
}
