#!/bin/bash


SERVER_SCRIPT="server.py"
CLIENT_SCRIPT="client.py"


NUM_CLIENTS=3  
USERNAMES=("Maahmoud" "Abdelrahman" "nour") 


echo "Starting chat server..."
gnome-terminal -- bash -c "python3 $SERVER_SCRIPT; exec bash"


sleep 2

# ---------------- Start Clients ----------------
for ((i=0;i<NUM_CLIENTS;i++)); do
    username=${USERNAMES[$i]}
    echo "Starting client: $username"
    gnome-terminal -- bash -c "python3 $CLIENT_SCRIPT $username; exec bash"
done
