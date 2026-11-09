param([Parameter(Mandatory=$true)][string]$Exe,[Parameter(Mandatory=$true)][string]$Out)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
Add-Type -AssemblyName System.Drawing
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$icon=[System.Drawing.Icon]::ExtractAssociatedIcon($Exe)
if(-not $icon) { throw 'Official Notepad++ executable has no extractable icon' }
try {
  $stream=[IO.File]::Create((Join-Path $Out 'appicon.ico'))
  try { $icon.Save($stream) } finally { $stream.Dispose() }
  $base=$icon.ToBitmap()
  try {
    foreach($size in @(16,32)) {
      $bmp=[System.Drawing.Bitmap]::new($base,$size,$size)
      try { $bmp.Save((Join-Path $Out "appicon_$size.png"),[System.Drawing.Imaging.ImageFormat]::Png) }
      finally { $bmp.Dispose() }
    }
  } finally { $base.Dispose() }
} finally { $icon.Dispose() }
