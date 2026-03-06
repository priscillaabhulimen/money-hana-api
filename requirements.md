# SETUP PROJECT


### 1. Install Python
- [ ] Go to the [Python Downloads](https://www.python.org/downloads/) page
- [ ] Download and install your preferred version of Python
- [ ] Test by running:

      python --version
- [ ] Install VSCode Python Extension by **Microsoft**


### 2. Setup virtual environment
- [ ] In your working project directory, run:

      python3 -m venv <name-of-virtual-environment>
- [ ] Open View > Command Palette > Python: Select Interpreter
- [ ] Select the virtual environment you just created, or
    - Enter the path to your python instance in your project's virtual environment with: 
    `./<name-of-virtual-environment>/bin/python`
- [ ] Set terminal to refer to virtual environment by running

      source <name-of-virtual-environment>/bin/activate


### Install dependencies
- [ ] Confirm that your terminal is running in the virtual environment
- [ ] Run the command:
      
      pip install fastapi[all]
- [ ] To see a list of installed packages, run:

      pip freeze