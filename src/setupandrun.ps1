# PowerShell script to setup and run the chat server and clients

$SERVER_SCRIPT = "server.py"
$CLIENT_SCRIPT = "client.py"

$NUM_CLIENTS = 3
$USERNAMES = @("Maahmoud", "Abdelrahman", "nour")

Write-Host "Starting chat server..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python $SERVER_SCRIPT"

Start-Sleep -Seconds 2

# Start Clients
Write-Host "Starting clients..." -ForegroundColor Green
for ($i = 0; $i -lt $NUM_CLIENTS; $i++) {
    $username = $USERNAMES[$i]
    Write-Host "Starting client: $username" -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; python $CLIENT_SCRIPT $username"
    Start-Sleep -Milliseconds 500
}

Write-Host "`nAll clients started!" -ForegroundColor Green
Write-Host "Server and $NUM_CLIENTS clients are running in separate windows." -ForegroundColor Yellow

