$ErrorActionPreference = 'Continue'
$env:CUDA_VISIBLE_DEVICES = '-1'
$dl = 'D:\mithril\tools\dl'
Set-Location $dl
$base = 'https://github.com/Kitware/CMake/releases/download/v4.4.3'
foreach ($f in 'cmake-4.4.3-linux-x86_64.tar.gz','cmake-4.4.3-SHA-256.txt','cmake-4.4.3-SHA-256.txt.asc') { curl.exe -sS -L --fail --retry 3 -o $f "$base/$f"; "dl $f rc=$LASTEXITCODE" }
curl.exe -sS -L --fail --retry 3 -o cmake-signing-key-CBA23971357C2E6590D9EFD3EC8FEF3A7BFB4EDA.asc "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xcba23971357c2e6590d9efd3ec8fef3a7bfb4eda"; "key rc=$LASTEXITCODE"
foreach ($f in 'cmake-4.4.3-linux-x86_64.tar.gz','cmake-4.4.3-SHA-256.txt','cmake-4.4.3-SHA-256.txt.asc','cmake-signing-key-CBA23971357C2E6590D9EFD3EC8FEF3A7BFB4EDA.asc') { $h = Get-FileHash -Algorithm SHA256 $f; "SHA256 $($h.Hash.ToLower())  $f" }
Select-String -Path cmake-4.4.3-SHA-256.txt -Pattern 'linux-x86_64.tar.gz'
New-Item -ItemType Directory -Force D:\mithril\tools\gnupg-cmake | Out-Null
$gpg = 'C:\Program Files\Git\usr\bin\gpg.exe'
cmd /c "`"$gpg`" --batch --no-autostart --homedir D:/mithril/tools/gnupg-cmake --import cmake-signing-key-CBA23971357C2E6590D9EFD3EC8FEF3A7BFB4EDA.asc 2>&1"
cmd /c "`"$gpg`" --batch --no-autostart --homedir D:/mithril/tools/gnupg-cmake --verify cmake-4.4.3-SHA-256.txt.asc cmake-4.4.3-SHA-256.txt 2>&1"
