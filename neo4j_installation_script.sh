#!bin/sh

wget -O - https://debian.neo4j.com/neotechnology.gpg.key | gpg --dearmor -o /etc/apt/keyrings/neotechnology.gpg | apt-key add -
echo 'deb [signed-by=/etc/apt/keyrings/neotechnology.gpg] https://debian.neo4j.com stable latest' | tee -a /etc/apt/sources.list.d/neo4j.list
apt-get update

apt-get install neo4j=1:5.18.0
