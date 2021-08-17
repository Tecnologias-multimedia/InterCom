# Runme

You can run a `module` using `python3 module.py`. However, it is [a good
idea](https://towardsdatascience.com/why-you-should-use-a-virtual-environment-for-every-python-project-c17dab3b0fd0)
to use a new Python
[environment](https://docs.python.org/3/library/venv.html)
specifically for this project and run the modules inside.

1. Create an new environment (example -- replace this path by one of
   your convenience --):

		mkdir /home/vruiz/python_environments
		python3 -m venv /home/vruiz/python_environments/intercom

2. Activate the environment:

		source /home/vruiz/python_environments/intercom/bin/activate
		
3. To deactivate the environment:

		deactivate
		
## Remember

To install the dependencies (example for `sounddevice`):

	pip3 install sounddevice
	
To stop (killing it) an Unix process, press at the same time <CTRL> and <c>.
