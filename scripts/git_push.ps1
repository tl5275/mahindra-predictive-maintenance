Write-Host "Adding files..."
git add .

$message = Read-Host "Enter commit message"

if ([string]::IsNullOrEmpty($message)) {
    $message = "update: $(Get-Date)"
}

git commit -m "$message"
git push origin main
