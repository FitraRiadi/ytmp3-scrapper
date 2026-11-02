# Jalankan backend Django (8137) + frontend Vite (5233) sekaligus.
$root = $PSScriptRoot

Write-Host "Menjalankan backend  -> http://127.0.0.1:8137" -ForegroundColor Magenta
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\backend'; py manage.py runserver 127.0.0.1:8137 --noreload"
)

Start-Sleep -Seconds 2

Write-Host "Menjalankan frontend -> http://localhost:5233" -ForegroundColor Magenta
Start-Process powershell -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location '$root\frontend'; pnpm dev"
)

Write-Host ""
Write-Host "Buka http://localhost:5233 (dev) atau http://127.0.0.1:8137 (setelah pnpm build)." -ForegroundColor Green
