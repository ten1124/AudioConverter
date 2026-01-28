$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$outDir = Join-Path $root 'LICENSES'

New-Item -ItemType Directory -Path $outDir -Force | Out-Null

Invoke-WebRequest -Uri 'https://docs.python.org/3.12/license.html' -OutFile (Join-Path $outDir 'Python-PSF-License.html')
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/pyinstaller/pyinstaller/develop/COPYING.txt' -OutFile (Join-Path $outDir 'PyInstaller-COPYING.txt')
Invoke-WebRequest -Uri 'https://www.gnu.org/licenses/gpl-2.0.txt' -OutFile (Join-Path $outDir 'GPL-2.0.txt')
Invoke-WebRequest -Uri 'https://www.apache.org/licenses/LICENSE-2.0.txt' -OutFile (Join-Path $outDir 'Apache-2.0.txt')
Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/pmgagne/tkinterdnd2/master/LICENSE' -OutFile (Join-Path $outDir 'tkinterdnd2-LICENSE.txt')
Invoke-WebRequest -Uri 'https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt' -OutFile (Join-Path $outDir 'LGPL-2.1.txt')

Write-Host "Saved license texts to $outDir"
