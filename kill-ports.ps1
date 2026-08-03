# kill-ports.ps1
# Called by all-start.bat / all-stop.bat to safely kill only our services on given ports.
param(
    [int[]]$Ports = @(5000, 8080, 5173),
    [string[]]$SafeProcessNames = @('python', 'java', 'node')
)

$results = @()

foreach ($port in $Ports) {
    $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) {
        continue
    }

    foreach ($conn in $listeners) {
        $pid = $conn.OwningProcess
        $proc = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if (-not $proc) {
            continue
        }

        # Strip .exe suffix so matching is reliable
        $procName = $proc.ProcessName -replace '\.exe$', '' -replace '\.cmd$', '' -replace '\.bat$', ''
        $label = "[$port] PID=$pid proc=$procName"

        if ($SafeProcessNames -contains $procName) {
            Write-Host "  [!] $label -> killing ..."
            Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            $results += "killed $label"
        } else {
            Write-Host "  [skip] $label (not our service, keeping it)"
            $results += "skipped $label"
        }
    }
}

if ($results.Count -eq 0) {
    Write-Host "  (no listeners found on ports $Ports)"
}
