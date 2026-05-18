# esist-semantic-transmitter
Repository for the semantically encoded audio transmitter project. Proposal 9 from the Systems Engineering M.EEC course @ FEUP

## Contents

```
/esist-semantic-transmitter
├── docs                    # All the documentation related to presentations and diagrams for reports
└── front-end               # Midterm presentation code
```

## Setup

First, clone this repository to a directory of your choice:

```bash
git clone https://github.com/M1G039/esist-semantic-transmitter.git
```

All  of the code is written in Python so the creation of a virtual environment is necessary to install the required packages.
You can do that with the following command:

```bash
python3 -m venv venv
```

This will create a new venv called "venv" in your project directory.
Now you can install the required packages with

```bash
pip install -r requirements.txt
```

## Run

If everything is installed successfully you should be able to run the appplication with:

```bash
streamlit run app.py
```
