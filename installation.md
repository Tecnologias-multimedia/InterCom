# Installation Guide

This guide will help you set up and run this Python project in your local environment. Make sure to follow the steps carefully to avoid installation issues.

## Prerequisites

Before you begin, ensure that you have the following items installed on your system:

- Python 3.x: Make sure you have Python 3.x installed. You can download it from [Python.org](https://www.python.org/downloads/).

## Installation Steps

Follow these steps to install and configure the project:

1. **Set the python environment**

   Open your terminal and follow these steps.

   ```bash
   mkdir environments
   cd environments
   git clone https://github.com/Tecnologias-multimedia/InterCom.git
   cd Intercom
   git checkout 20XX # Changing the XX by the year of the course, like for example 'git checkout 2023'
   sudo apt install python3.10-venv
   python3 -m venv ~/enviroments/intercom
   source ~/enviroments/intercom/bin/activate
   
2. **Install easily the dependencies/modules**


   ```bash
   pip install -r requirements.txt
   # If you are an ubuntu user, you need to run this command 'sudo apt install portaudio19-dev python3-pyaudio' without the quotes,
   # for downloading correctly pyaudio, a module needed for PortAudio.
   
3. **Run the first program**

   For example, you can run the minimal.py.

   ```bash
   cd src
   python3 minimal.py
   
   
