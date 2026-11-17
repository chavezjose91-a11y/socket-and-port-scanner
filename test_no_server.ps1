# Test 7: run the client while no server is listening and show its exit code.
Write-Host '> py client.py "Is anyone there?"'
py client.py "Is anyone there?"
Write-Host "Exit code: $LASTEXITCODE"
