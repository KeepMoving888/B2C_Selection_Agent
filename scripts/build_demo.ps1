# Build frontend - generates both single-file HTML (for ZIP) and normal build (for deployment)

Write-Host "=== Step 1: Build single-file HTML for ZIP demo ===" -ForegroundColor Cyan
Set-Location $PSScriptRoot\..\web
$env:SINGLE_FILE = 'true'
npm run build

Write-Host "=== Packaging single-file demo zip ===" -ForegroundColor Cyan
Set-Location $PSScriptRoot\..
if (Test-Path web\b2c-selection-agent-demo.zip) {
    Remove-Item web\b2c-selection-agent-demo.zip
}
Compress-Archive -Path web\dist\* -DestinationPath web\b2c-selection-agent-demo.zip -Force
Write-Host "  -> web\b2c-selection-agent-demo.zip (single file HTML)" -ForegroundColor Green

Write-Host ""
Write-Host "=== Step 2: Build normal version for deployment ===" -ForegroundColor Cyan
Set-Location $PSScriptRoot\..\web
$env:SINGLE_FILE = 'false'
npm run build

Write-Host "=== Done! ===" -ForegroundColor Green
Write-Host "ZIP for upload:  web\b2c-selection-agent-demo.zip"
Write-Host "Normal build:    web\dist\ (for GitHub Pages / Cloudflare Pages)"
