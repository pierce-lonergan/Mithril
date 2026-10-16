$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
Set-Location D:\mithril\tools\dl
foreach ($f in 'clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz','LLVM-23.1.3-Linux-X64.tar.xz','release-keys.asc','clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz.sig','LLVM-23.1.3-Linux-X64.tar.xz.sig','clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz.jsonl','LLVM-23.1.3-Linux-X64.tar.xz.jsonl') {
  $h = Get-FileHash -Algorithm SHA256 $f
  "SHA256 $($h.Hash.ToLower())  $f"
}
New-Item -ItemType Directory -Force D:\mithril\tools\gnupg-llvm | Out-Null
$gpg = 'C:\Program Files\Git\usr\bin\gpg.exe'
& $gpg --version | Select-Object -First 2
"--- import"
cmd /c "`"$gpg`" --batch --homedir D:/mithril/tools/gnupg-llvm --import release-keys.asc 2>&1"
"--- verify win"
cmd /c "`"$gpg`" --batch --homedir D:/mithril/tools/gnupg-llvm --verify clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz.sig clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz 2>&1"
"--- verify linux"
cmd /c "`"$gpg`" --batch --homedir D:/mithril/tools/gnupg-llvm --verify LLVM-23.1.3-Linux-X64.tar.xz.sig LLVM-23.1.3-Linux-X64.tar.xz 2>&1"
"--- gh attestation"
$env:GH_CONFIG_DIR = 'D:\mithril\tools\ghcfg'; $env:XDG_CACHE_HOME = 'D:\mithril\tools\ghcache'; $env:XDG_DATA_HOME='D:\mithril\tools\ghdata'; $env:XDG_STATE_HOME='D:\mithril\tools\ghstate'
gh --version | Select-Object -First 1
cmd /c "gh attestation verify --repo llvm/llvm-project clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz --bundle clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz.jsonl 2>&1"
"gh rc=$LASTEXITCODE"
cmd /c "gh attestation verify --repo llvm/llvm-project LLVM-23.1.3-Linux-X64.tar.xz --bundle LLVM-23.1.3-Linux-X64.tar.xz.jsonl 2>&1"
"gh rc=$LASTEXITCODE"

# --- attestation subjects (second pass, JSON output)
$env:GH_CONFIG_DIR = 'D:\mithril\tools\ghcfg'; $env:XDG_CACHE_HOME = 'D:\mithril\tools\ghcache'; $env:XDG_DATA_HOME='D:\mithril\tools\ghdata'; $env:XDG_STATE_HOME='D:\mithril\tools\ghstate'
foreach ($f in 'clang+llvm-23.1.3-x86_64-pc-windows-msvc.tar.xz','LLVM-23.1.3-Linux-X64.tar.xz') {
  cmd /c "gh attestation verify --repo llvm/llvm-project $f --bundle $f.jsonl --format json > D:\mithril\tools\dl\$f.attest.json 2> D:\mithril\tools\dl\$f.attest.err"
  "rc=$LASTEXITCODE $f"
  "stderr: " + (Get-Content "D:\mithril\tools\dl\$f.attest.err" -Raw)
  $j = Get-Content "D:\mithril\tools\dl\$f.attest.json" -Raw
  "json len: " + $j.Length
  if ($j.Length -gt 0) { $o = $j | ConvertFrom-Json; foreach ($e in $o) { "subject: " + ($e.verificationResult.statement.subject | ConvertTo-Json -Compress -Depth 5).Substring(0, [Math]::Min(600, ($e.verificationResult.statement.subject | ConvertTo-Json -Compress -Depth 5).Length)); "signerWorkflow: " + $e.verificationResult.signature.certificate.buildSignerURI; "sourceRepo: " + $e.verificationResult.signature.certificate.sourceRepositoryURI + " ref " + $e.verificationResult.signature.certificate.sourceRepositoryRef } }
}
Get-ChildItem -Recurse D:\mithril\tools\ghcfg, D:\mithril\tools\ghcache -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum | Select-Object Count,Sum | Out-String
Get-ChildItem "$env:LOCALAPPDATA\GitHub CLI","$env:APPDATA\GitHub CLI" -Recurse -ErrorAction SilentlyContinue | Select-Object FullName,Length,LastWriteTime | Out-String
