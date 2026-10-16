$ErrorActionPreference = 'Continue'
Set-Location D:\mithril\tools\dl
foreach ($f in 'cmake-4.4.3-linux-x86_64.tar.gz','cmake-4.4.3-SHA-256.txt','cmake-4.4.3-SHA-256.txt.asc','cmake-signing-key-CBA23971357C2E6590D9EFD3EC8FEF3A7BFB4EDA.asc') { $h = Get-FileHash -Algorithm SHA256 $f; "SHA256 $($h.Hash.ToLower())  $f" }
(Select-String -Path cmake-4.4.3-SHA-256.txt -Pattern 'linux-x86_64.tar.gz').Line
$gpg = 'C:\Program Files\Git\usr\bin\gpg.exe'
cmd /c "`"$gpg`" --batch --no-autostart --homedir D:/mithril/tools/gnupg-cmake --verify cmake-4.4.3-SHA-256.txt.asc cmake-4.4.3-SHA-256.txt 2>&1"
