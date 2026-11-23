# Ders Ofisi başlatıcı: sunucu (gizli) + ofis uygulama penceresi + Claude Code
$kok = $PSScriptRoot
$port = 8765
$url = "http://127.0.0.1:$port/"

# Sunucu zaten açıksa ikinci kez başlatma
$acik = Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $acik) {
  python -c "import pymupdf" 2>$null
  if ($LASTEXITCODE -ne 0) { python -m pip install -q pymupdf }
  Start-Process python.exe -ArgumentList "-m", "ofis.sunucu" -WorkingDirectory $kok -WindowStyle Hidden
  for ($i = 0; $i -lt 40 -and -not (Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue); $i++) { Start-Sleep -Milliseconds 250 }
}

# Ofis: adres çubuğu olmayan uygulama penceresi
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"
if (Test-Path $chrome) { Start-Process $chrome -ArgumentList "--app=$url", "--window-size=1400,850" }
else { Start-Process msedge.exe -ArgumentList "--app=$url" }

# Claude Code: ofis klasöründe, ayrı terminal penceresinde
$claude = "$env:USERPROFILE\.local\bin\claude.exe"
if (Get-Command wt.exe -ErrorAction SilentlyContinue) { Start-Process wt.exe -ArgumentList "-d `"$kok`" --title `"Ders Ofisi - Claude`" `"$claude`"" } # tek metin: boşluklu başlık bölünmesin
else { Start-Process $claude -WorkingDirectory $kok }
