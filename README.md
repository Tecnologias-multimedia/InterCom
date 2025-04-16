# InterCom

InterCom is a low-[latency](https://en.wikipedia.org/wiki/Latency_(engineering)) [full-duplex](https://en.wikipedia.org/wiki/Duplex_(telecommunications)#FULL-DUPLEX) intercom(municator) designed for the transmission of media (at this moment, only [audio](https://en.wikipedia.org/wiki/Digital_audio)) between networked users. It is implemented in [Python](https://www.python.org/) and designed as a set of layers that provide an incremental functionality, following a multilevel (one-to-one) [inheritance](https://en.wikipedia.org/wiki/Inheritance_(object-oriented_programming)) model.

## Install (if Python is already installed)

   pip install -r requirements.txt

### Python install

#### Linux

Python is already installed in Linux.

#### Visual Studio Code (all platforms)

See [Getting Started with Python in VS Code](https://code.visualstudio.com/docs/python/python-tutorial#_install-a-python-interpreter).

### Jupyter-lab install

Required only to run the notebooks, not the InterCom.

#### Linux (better in a [virtual Python environment](https://docs.python.org/3/library/venv.html))

     pip install jupyterlab

#### Visual Studio Code (all platforms)

See [Jupyter Notebooks in VS Code](https://code.visualstudio.com/docs/datascience/jupyter-notebooks).

## Implementation details

                      Minimal --> Minimal__verbose
                         |                  |
                         v                  v
                    Buffering --> Buffering__verbose
                         |                  |
                         v                  v
                     DEFLATE_Row --> DEFLATE_Row__verbose
                         |                  |
                         v                  v
             DEFLATE_BytePlanes3 --> DEFLATE_BytePlanes3__verbose
                         |                  |
                         v                  v
                   BR_Control_No --> BR_Control_No__verbose
                         |                  |
                         v                  v
         BR_Control_Conservative --> BR_Control_Conservative__verbose
                         |                  |
                         v                  v
                Stereo_Coding_32 --> Stereo_Coding_32__verbose
                         |                  |
                         v                  v
      Temporal_No_Overlapped_DWT --> Temporal_No_Overlapped_DWT__verbose
                         |                  |
                         v                  v
         Temporal_Overlapped_DWT --> Temporal_Overlapped_DWT__verbose
                         |                  |
                         v                  v
                      Dyadic_ToH --> Dyadic_ToH__verbose
                         |                  |
                         v                  v
                   Linear_ToH_NO --> Linear_ToH_NO__verbose
