$env:IUSTUS_E2E_SQLITE='true'
$env:IUSTUS_E2E_ASSOCIATION='true'
$env:IDENTITY_MFA_REQUIRED='false'
$env:PLAYWRIGHT_CHANNEL='chrome'
$env:IUSTUS_TEST_API_PORT='8011'
$env:IUSTUS_TEST_WEB_PORT='3011'
$env:IUSTUS_PROXY_SECRET='synthetic-association-e2e-proxy'
$env:DJANGO_API_ORIGIN='http://127.0.0.1:8011'
$env:IUSTUS_PUBLIC_ORIGIN='http://localhost:3011'
$env:DJANGO_SECRET_KEY='synthetic-e2e-django-key-only'
$env:IDENTITY_ENCRYPTION_KEY='MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='
$env:PAGBANK_ENVIRONMENT='sandbox'
& backend/.venv/Scripts/python.exe tests/e2e/fixture.py prepare
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Push-Location frontend
try { & node.exe node_modules/@playwright/test/cli.js test --config=playwright.association.config.ts; $result = $LASTEXITCODE }
finally { Pop-Location }
exit $result
