# scan_tests.ps1 - Runs one port-scanner test case, with a timestamped header.
#
# Usage: .\scan_tests.ps1 <case number 1-6>
#   1  Common ports on localhost
#   2  Custom port range on localhost
#   3  Selected ports on scanme.nmap.org (slow and gentle on purpose)
#   4  Invalid port numbers and options
#   5  Unreachable and unauthorized hosts
#   6  Performance with different port ranges
#
# Only localhost and scanme.nmap.org are scanned.

param([Parameter(Mandatory)][ValidateRange(1, 6)][int]$Case)

function Run([string]$title, [string[]]$scanArgs) {
    Write-Host ""
    Write-Host "--- $title" -ForegroundColor Cyan
    Write-Host "> py port_scanner.py $($scanArgs -join ' ')" -ForegroundColor Yellow
    py port_scanner.py @scanArgs
    Write-Host "Exit code: $LASTEXITCODE"
}

$names = @{
    1 = 'Common ports on localhost'
    2 = 'Custom port range on localhost'
    3 = 'Selected ports on scanme.nmap.org'
    4 = 'Error handling: invalid port numbers and options'
    5 = 'Error handling: unreachable and unauthorized hosts'
    6 = 'Performance with different port ranges'
}
Write-Host "=== Test case $Case`: $($names[$Case]) ===" -ForegroundColor Green
Write-Host "Run at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

switch ($Case) {
    1 {
        # A 2.5 s timeout lets Windows report closed ports as "closed".
        Run 'FTP, SSH, HTTP, HTTPS plus Windows RPC/SMB' @('127.0.0.1', '-p', '21,22,80,443,135,445', '-t', '2.5', '--show-closed')
    }
    2 {
        Run 'Ports 130-145 on localhost' @('127.0.0.1', '-p', '130-145', '-t', '2.5', '--show-closed')
    }
    3 {
        # 2 workers and 1 s between attempts: a light, polite scan.
        Run 'Well-known ports on scanme.nmap.org' @('scanme.nmap.org', '-p', '21,22,23,25,80,443,9929,31337', '-t', '3', '-w', '2', '-d', '1', '--show-closed')
    }
    4 {
        Run 'Port 0 (below range)'         @('-p', '0')
        Run 'Port 70000 (above range)'     @('-p', '70000')
        Run 'Not a number'                 @('-p', 'abc')
        Run 'Backwards range'              @('-p', '100-50')
        Run 'Timeout of zero'              @('-p', '80', '-t', '0')
        Run 'Negative delay'               @('-p', '80', '-d', '-1')
    }
    5 {
        Run 'Host name that does not exist'  @('no-such-host.invalid', '-p', '80')
        Run 'Host that is not authorized'    @('example.com', '-p', '80')
    }
    6 {
        Run '100 ports'   @('127.0.0.1', '-p', '1-100')
        Run '500 ports'   @('127.0.0.1', '-p', '1-500')
        Run '1000 ports'  @('127.0.0.1', '-p', '1-1000')
        Run '2000 ports'  @('127.0.0.1', '-p', '1-2000')
        Run '1000 ports, no delay (-d 0)'  @('127.0.0.1', '-p', '1-1000', '-d', '0')
        Run '500 ports, only 10 workers'   @('127.0.0.1', '-p', '1-500', '-w', '10')
    }
}
Write-Host ""
Write-Host "Finished at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
