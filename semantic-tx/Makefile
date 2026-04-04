# it would be the path > ~/(...)/semantic-tx
ROOT_DIR:=$(shell pwd)

SRC_DIR:=${ROOT_DIR}/src
FRONTEND_DIR:=${SRC_DIR}/frontend
STT_LLM_SIR:=${SRC_DIR}/stt_llm
TESTS_DIR:=${SRC_DIR}/tests
TX_COMMS_DIR:=${SRC_DIR}/tx_comms

# ------------------- Executable commands -------------------

.PHONY: build-venv run-setup run-app clean

build-venv:
	./build-venv.sh

run-setup:
	./init_setup.sh

run-app:
	cd  ${SRC_DIR} && PYTHONPATH=${SRC_DIR} ${ROOT_DIR}/.venv/bin/streamlit run ${FRONTEND_DIR}/app.py

clean:
	@echo "[*] Cleaning the project of artifacts..." && echo "" && \
	cd ${FRONTEND_DIR} && rm -rf __pycache__ && \
	cd ${STT_LLM_SIR} && rm -rf __pycache__ && \
	cd ${TX_COMMS_DIR} && rm -rf __pycache__ && \
	sleep 3 && \
	echo "[CHECK] Artifacts cleaned up."
	@echo ""
# ------------------------  Help Menu ------------------------

help:
	@echo "=================================================="
	@echo "=               MAKEFILE TARGETS                 ="
	@echo "=================================================="
	@echo "= build-venv: runs the python command to create  ="
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
