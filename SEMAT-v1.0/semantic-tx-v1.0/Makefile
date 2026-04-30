# it would be the path > ~/(...)/semantic-tx
ROOT_DIR:=$(shell pwd)

SRC_DIR:=${ROOT_DIR}/src
FRONTEND_DIR:=${SRC_DIR}/frontend
AI_SOUND_DIR:=${SRC_DIR}/ai_sound
TESTS_DIR:=${SRC_DIR}/tests
TX_COMMS_DIR:=${SRC_DIR}/tx_comms

# ------------------- Executable commands -------------------

.PHONY:	build-venv	run-setup	run-broker	dockps	run-app 	clean

build-venv:
	@echo "[*] Building the python virtual environment..." && \
	echo  && \
	sleep 2 && \
	python3 -m venv .venv && \
	echo "[CHECK] Virtual Environment built."

run-setup:
	./init_setup.sh

run-broker:
	./run-nw-emulator.sh

dockps:
	@out=$$(mktemp); \
	(sudo docker ps -a) 2>$$out || status=$$?; \
	if [ -n "$$status" ]; then \
		if grep -Ei "permission denied|operation not permitted|are you root|permission error" $$out >/dev/null 2>&1; then \
			printf "Error: command failed due to permissions. If docker needs root permissions run: sudo usermod -aG docker <username>\n" >&2; \
		else \
			printf "Error: command failed (exit %s).\n" "$$status" >&2; \
		fi; \
		rm -f $$out; \
		exit $$status; \
	else \
		rm -f $$out; \
	fi; \
	printf "To run an interactive shell on the receiver/subscriber run the command:\n\nsudo docker exec -it <CONTAINER_ID> /usr/bin/bash \n" \
	@echo "Run `make subscribe` for more information"

subscribe:
	@echo "Once inside the container shell to subscribe to a topic and receive the messages run the command:" \
	echo \
	echo "mosquitto_sub -h <hostname/hostname_IP> -f "TOPIC" " \
	echo \
	echo "Example"


run-app:
	cd  ${SRC_DIR} && PYTHONPATH=${SRC_DIR} ${ROOT_DIR}/.venv/bin/streamlit run ${FRONTEND_DIR}/app.py

clean:
	@echo "[*] Cleaning the project of artifacts..." && echo "" && \
	rm -rf .venv && \
	echo "Cleaning frontend diretory..." && \
	cd ${FRONTEND_DIR} && rm -rf __pycache__ && \
	sleep 1 && \
	echo "Cleaning ai_sound diretory..." && \
	cd ${AI_SOUND_DIR} && rm -rf __pycache__ && \
	sleep 1 && \
	echo "Cleaning tx_comms diretory..." && \
	cd ${TX_COMMS_DIR} && rm -rf __pycache__ && \
	echo "Cleaning src diretory..." && \
	cd ${SRC_DIR} && rm -rf *.pt && \
	sleep 1 && \
	echo && \
	echo "[CHECK] Artifacts cleaned up."
	@echo ""
# ------------------------  Help Menu ------------------------

help:
	@echo "=================================================="
	@echo "=               MAKEFILE TARGETS                 ="
	@echo "=================================================="
	@echo "= build-venv: runs the python command to CREATE  ="
	@echo "=             the virtual environment            ="
	@echo "=                                                ="
	@echo "= run-setup: runs installation of the            ="
	@echo "=            dependencies for the application    ="
	@echo "=                                                ="
	@echo "= run-app: executes the streamlit command to run ="
	@echo "=          the application                       ="
	@echo "=                                                ="
	@echo "= clean: clean the artifacts from running the    ="
	@echo "=        application                             ="
	@echo "=================================================="
