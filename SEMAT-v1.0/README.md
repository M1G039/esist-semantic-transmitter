# SEMAT - SEMantic Audio Transmitter
Repository for the semantically encoded audio transmitter project. Proposal 9 from the Systems Engineering M.EEC course @ FEUP

---
## Setup - for stremlit app only

```bash
py -3 -m pip install -r requirements.txt
```

## Run

```bash
py -3 -m streamlit run app.py
```
---

## Setup execution steps - fully integrated project

- From the `src` directory:
  - **1)** Run the command `make build-env`
  - **2)** Run the command `make run-setup`
    - **2.1)** This will install the necessary depencies and pull the `SemantiCodec` model
    - **2.2)** At this point we could also run the docker containers to demo the projectÇ
      - **2.2.1)** The `docker-compose.yaml` instantiates 2 containers:
        - Container 1, named `mqtt-broker` - emulates the physical broker
        - Container 2, named `team10-rx` - emulates a 2nd device working as the receiver/subscriber to get out messages
  - **3)** Once the depencies are installed, the model pulled and the containers are up and running we can:
    - **3.2)** Run the docker network with the command `make run-broker` which runs the script `run-nw-emulator.sh`, starting the containers.
    - **3.1)** Run the application with the `make run-app` - this will pop the app up on the browser running in `http://localhost:8501`
    - **3.3)** In order to see the published messages on the `team10-rx` we need to enter and interactive shell on the container and for that we can run the commands:

    ```bash
        sudo docker ps -a   # this will show the field CONTAINER_ID
        sudo docker exec -it <CONTAINER_ID> sh
    ```
    - **3.3)** Inside the shell we must subscribe to the topic. For that we can run:

    ```bash
        mosquitto_sub -h <BROKER_IP> -f "TOPIC" # in the code provided BROKER_IP=172.17.0.1 (docker0 if IP) and TOPIC="team9/messages"
    ```
    Encode some audio and send it.. The token should appeat in the `team10-rx` shell encoded in base64.
