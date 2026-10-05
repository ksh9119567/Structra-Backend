<#
.SYNOPSIS
  Run the automated test-suite (Windows / PowerShell).

.EXAMPLE
  .\scripts\run_tests.ps1                        # whole suite
  .\scripts\run_tests.ps1 teams                  # one app
  .\scripts\run_tests.ps1 teams projects tasks   # several apps
  .\scripts\run_tests.ps1 projects -v 2          # anything else is passed to `manage.py test`
  .\scripts\run_tests.ps1 --failfast --parallel 4

.NOTES
  Apps: accounts organizations teams projects tasks governance comments sprints core
  ("core" = shared permissions, utils, activity logging, HTTP behaviour)

  Tests use config/settings_test.py automatically: in-memory SQLite, an in-memory
  fake Redis, eager Celery and captured e-mail - no Postgres / Redis / Docker needed.
  Set $env:TEST_DB = "postgres" to run against PostgreSQL instead (see docs/TESTING.md).
#>
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$TestArgs
)

# Note: no `$ErrorActionPreference = "Stop"` on purpose - Windows PowerShell 5.1 treats
# anything a native program writes to stderr (Django's test runner reports there) as an error.
Set-Location (Split-Path -Parent $PSScriptRoot)

if (Test-Path ".task_venv\Scripts\python.exe") {
    $py = ".task_venv\Scripts\python.exe"
} elseif (Test-Path ".task_venv/bin/python") {
    $py = ".task_venv/bin/python"
} else {
    $py = "python"
}

$apps = @("accounts", "comments", "governance", "organizations", "projects", "sprints", "tasks", "teams")
$labels = @()
$extra = @()
foreach ($arg in $TestArgs) {
    if ($apps -contains $arg) { $labels += "app.$arg" }
    elseif ($arg -eq "core") { $labels += "core" }
    else { $extra += $arg }
}

& $py manage.py test @labels @extra
exit $LASTEXITCODE
