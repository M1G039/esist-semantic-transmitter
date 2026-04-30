#!/usr/bin/bash

echo "Buiding and running the docker containers..."
echo
echo "	Container team10-rx - emulates the 2nd device"
echo "	Container mqtt-broker - emulates the broker - if IP is 'docker0' on 172.17.0.1"
echo
sleep 2
sudo docker-compose build
sudo docker-compose up &
sleep 1
echo "To check if the containers are running run the command:"
echo
echo "	make dockps"
