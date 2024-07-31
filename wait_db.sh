#!bin/sh

until [ ! -n $(ss -tulpn | grep -E ":7678[[:space:]]" | grep -o "LISTEN") ]; do
    sleep 0.1;
done;