# it would be the path > /home/guilherme/Desktop/MEEC/2Sem/ESIST/semantic-tx
ROOT_DIR:=$(shell pwd)

SRC_DIR:=${ROOT_DIR}/src
FRONTEND_DIR:=${SRC_DIR}/frontend
STT_LLM_SIR:=${SRC_DIR}/stt_llm
TESTS_DIR:=${SRC_DIR}/tests
TX_COMMS_DIR:=${SRC_DIR}/tx_comms

# ------------------- Executable commands -------------------

.PHONY: build-venv run-setup run-app

build-venv:
	./build-venv.sh

run-setup:
	./init_setup.sh

run-app:
	cd  ${SRC_DIR} && PYTHONPATH=${SRC_DIR} ${ROOT_DIR}/.venv/bin/streamlit run ${FRONTEND_DIR}/app.py

# ------------------------  Help Menu ------------------------

help:
	@echo "=================================================="
	@echo "=               MAKEFILE TARGETS                 ="
	@echo "=================================================="
	@echo "= build-venv: runs the python command to create  ="
	@echo "=             the virtual environment            ="
	@echo "=                                                ="
	@echo "= enter-venv: runs the comand to activate/enter  ="
	@echo "=             the virtual environment            ="
	@echo "=                                                ="
	@echo "= deact-venv: runs the comand to deactivate the  ="
	@echo "=             virtual environment                ="
	@echo "=                                                ="
	@echo "= run-setup: runs installation of the            ="
	@echo "=            dependencies for the application    ="
	@echo "=                                                ="
	@echo "= run-app: executes the streamlit command to run ="
	@echo "=          the application                       ="
	@echo "=                                                ="
	@echo "=================================================="
