# Ders Ofisi başlatıcı: sunucu (gizli) + ofis uygulama penceresi + Claude Code
$kok = $PSScriptRoot
$port = 8765
$url = "http://127.0.0.1:$port/"

# Sunucu zaten açıksa ikinci kez başlatma
$acik = Test-NetConnection 127.0.0.1 -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
if (-not $acik) {
  if (Test-Path "$kok\ofis\sunucu.py") { $arg = "-m", "ofis.sunucu" }
  else { $arg = "-m", "http.server", "$port", "--bind", "127.0.0.1", "-d", "web" } # shortcut: Task 7 sunucusu gelene kadar önizleme
  Start-Process python.exe -ArgumentList $arg -WorkingDirectory $kok -WindowStyle Hidden
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
