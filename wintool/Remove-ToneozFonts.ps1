<#
Remove-PrefixedFonts.ps1
Removes fonts whose *registry display name* starts with prefixes, and ALSO
removes any font files whose *internal family name* starts with prefixes
(works even if filename is random like "text.ttf").

Run in elevated Windows PowerShell 5.1.
#>

$Prefixes = @(
  "ArcSnow",
  "Quicksand"
)

$RegPaths = @(
  "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
  "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows NT\CurrentVersion\Fonts",
  "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
)

$FontDirs = @(
  (Join-Path $env:WINDIR "Fonts"),
  (Join-Path $env:LOCALAPPDATA "Microsoft\Windows\Fonts")
) | Where-Object { Test-Path $_ }

function Grant-DeleteRights {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (Test-Path $Path) {
    & takeown.exe /F "$Path" /A | Out-Null
    & icacls.exe "$Path" /grant Administrators:F /T /C | Out-Null
  }
}

function Starts-WithAnyPrefix {
  param([Parameter(Mandatory=$true)][string]$Text, [Parameter(Mandatory=$true)][string[]]$PrefixList)
  foreach ($p in $PrefixList) {
    if ($Text.StartsWith($p, [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
  }
  return $false
}

function Get-FontLeafFromRegValue {
  param([Parameter(Mandatory=$true)][string]$Value)

  if ([string]::IsNullOrWhiteSpace($Value)) { return $null }
  $v = $Value.Trim()

  $paren = $v.IndexOf(" (")
  if ($paren -ge 0) { $v = $v.Substring(0, $paren).Trim() }

  $comma = $v.IndexOf(",")
  if ($comma -ge 0) { $v = $v.Substring(0, $comma).Trim() }

  try {
    $leaf = Split-Path $v -Leaf
    if (-not [string]::IsNullOrWhiteSpace($leaf)) { return $leaf }
  } catch { }

  return $null
}

Write-Host "1) Searching registry (HKLM + HKCU) for display-name prefixes: $($Prefixes -join ', ') ..." -ForegroundColor Cyan

$Matches = @()

foreach ($rp in $RegPaths) {
  if (-not (Test-Path $rp)) { continue }

  $props = Get-ItemProperty -Path $rp
  foreach ($p in $props.PSObject.Properties) {
    if ($p.Name -in "PSPath","PSParentPath","PSChildName","PSDrive","PSProvider") { continue }

    $displayName = [string]$p.Name
    $regValue    = [string]$p.Value

    if (Starts-WithAnyPrefix -Text $displayName -PrefixList $Prefixes) {
      $leaf = Get-FontLeafFromRegValue -Value $regValue
      $Matches += [PSCustomObject]@{
        RegistryPath = $rp
        DisplayName  = $displayName
        RegValue     = $regValue
        LeafFile     = $leaf
      }
    }
  }
}

if ($Matches.Count -gt 0) {
  Write-Host "Found $($Matches.Count) matching registry entries:" -ForegroundColor Green
  $Matches | Format-Table -AutoSize

  foreach ($m in $Matches) {
    try {
      Write-Host "Removing registry entry: $($m.DisplayName) from $($m.RegistryPath)" -ForegroundColor Cyan
      Remove-ItemProperty -Path $m.RegistryPath -Name $m.DisplayName -ErrorAction Stop
    } catch {
      Write-Warning "Failed removing registry entry '$($m.DisplayName)': $($_.Exception.Message)"
    }
  }
} else {
  Write-Host "No matching fonts found by DISPLAY NAME in registry (this is common for per-user or oddly-named entries)." -ForegroundColor Yellow
}

Write-Host "`n2) Scanning font files by INTERNAL family name (this catches random filenames like text.ttf) ..." -ForegroundColor Cyan

Add-Type -AssemblyName System.Drawing

$FilesToDelete = New-Object System.Collections.Generic.List[string]

foreach ($dir in $FontDirs) {
  Write-Host "Scanning: $dir" -ForegroundColor DarkCyan

  Get-ChildItem -Path $dir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -match '^\.(ttf|otf|ttc)$' } |
    ForEach-Object {
      $path = $_.FullName
      $isMatch = $false

      $pfc = New-Object System.Drawing.Text.PrivateFontCollection
      try {
        $pfc.AddFontFile($path)
        foreach ($fam in $pfc.Families) {
          if (Starts-WithAnyPrefix -Text $fam.Name -PrefixList $Prefixes) {
            $isMatch = $true
            break
          }
        }
      } catch {
        # ignore fonts System.Drawing can't parse
      } finally {
        $pfc.Dispose()
      }

      if ($isMatch) {
        $FilesToDelete.Add($path) | Out-Null
      }
    }
}

# Also include registry-resolved leaf filenames (if any)
foreach ($m in $Matches) {
  if (-not [string]::IsNullOrWhiteSpace($m.LeafFile)) {
    foreach ($dir in $FontDirs) {
      $candidate = Join-Path $dir $m.LeafFile
      if (Test-Path $candidate) {
        if (-not $FilesToDelete.Contains($candidate)) {
          $FilesToDelete.Add($candidate) | Out-Null
        }
      }
    }
  }
}

$UniqueFiles = $FilesToDelete | Sort-Object -Unique

if ($UniqueFiles.Count -eq 0) {
  Write-Host "No matching font files found by internal family name." -ForegroundColor Yellow
} else {
  Write-Host "Deleting $($UniqueFiles.Count) matching font file(s) ..." -ForegroundColor Green
  foreach ($full in $UniqueFiles) {
    try {
      Write-Host "Deleting: $full" -ForegroundColor Cyan
      Grant-DeleteRights -Path $full
      Remove-Item -Path $full -Force -ErrorAction Stop
    } catch {
      Write-Warning "Failed deleting '$full': $($_.Exception.Message)"
    }
  }
}

Write-Host "`nDone. SIGN OUT / RESTART to fully unload fonts from running apps." -ForegroundColor Magenta