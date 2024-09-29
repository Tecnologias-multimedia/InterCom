# Installation Guide

This guide will help you set up and run this Python project in your local environment.

## Prerequisites

Before you begin, ensure that you have the following items installed on your system:

- Python 3.x: Make sure you have Python 3.x installed. You can download it from [Python.org](https://www.python.org/downloads/).

## Installation Steps

Follow these steps to install and configure the project:

1. **Set the python environment**

   Open your terminal and follow these steps.

   ```bash
   mkdir repos
   cd repos
   git clone https://github.com/Tecnologias-multimedia/InterCom.git
   cd
   mkdir envs
   cd envs
   python3 -m venv InterCom
   cd
   source ~/envs/InterCom/bin/activate
   ```
   
2. **Install easily the dependencies/modules**


   ```bash
   pip install -r requirements.txt
   # If you are an ubuntu user, you need to run this command 'sudo apt install portaudio19-dev python3-pyaudio' without the quotes,
   # for downloading correctly pyaudio, a module needed for PortAudio.
   
3. **Run**

   ```bash
   cd repos/src
   python minimal.py
   ```

