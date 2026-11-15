param(
  [Parameter(Mandatory=$true)][string]$SourceDir,
  [Parameter(Mandatory=$true)][string]$FtpUrl,
  [Parameter(Mandatory=$true)][string]$User,
  [Parameter(Mandatory=$true)][string]$Pass,
  [string]$CheckUrl = ""
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path $SourceDir)) { throw "No existe la carpeta de origen: $SourceDir" }

$root  = (Resolve-Path $SourceDir).Path.TrimEnd('\')
$base  = $FtpUrl.TrimEnd('/')
$count = 0
foreach ($f in Get-ChildItem -Path $root -Recurse -File) {
  $rel = $f.FullName.Substring($root.Length + 1).Replace('\','/')
  & curl.exe --silent --show-error --fail --ftp-create-dirs -u "${User}:${Pass}" -T $f.FullName "$base/$rel"
  if ($LASTEXITCODE -ne 0) { throw "Fallo la subida de $rel" }
  Write-Host "Subido: $rel"
  $count++
}
Write-Host "Archivos subidos por FTP: $count"

if ($CheckUrl -ne "") {
  $r = Invoke-WebRequest -Uri $CheckUrl -UseBasicParsing -TimeoutSec 15
  if ($r.StatusCode -ne 200) { throw "El sitio no respondio 200: $CheckUrl" }
  Write-Host "Sitio verificado ($($r.StatusCode)): $CheckUrl"
}