#!/bin/bash

SERVER_SCRIPT="server.py"
CLIENT_SCRIPT="client.py"

NUM_CLIENTS=3
USERNAMES=("Maahmoud" "Abdelrahman" "nour")

echo -e "\033[0;32mStarting chat server...\033[0m"
kitty -- bash -c "python3 $SERVER_SCRIPT; exec bash" &
sleep 2

# Start Clients
echo -e "\033[0;32mStarting clients...\033[0m"
for ((i=0; i<NUM_CLIENTS; i++)); do
    username="${USERNAMES[$i]}"
    echo -e "\033[0;36mStarting client: $username\033[0m"
    kitty -- bash -c "python3 $CLIENT_SCRIPT $username; exec bash" &
    sleep 0.5
done

echo -e "\n\033[0;32mAll clients started!\033[0m"
echo -e "\033[0;33mServer and $NUM_CLIENTS clients are running in separate windows.\033[0m"