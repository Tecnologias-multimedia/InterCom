# InterCom

InterCom is a
low-[latency](https://en.wikipedia.org/wiki/Latency_(engineering))
[full-duplex](https://en.wikipedia.org/wiki/Duplex_(telecommunications)#FULL-DUPLEX)
intercom(municator) designed for the transmission of media between
networked users. It is implemented in
[Python](https://www.python.org/) and designed as a set of layers that
provide an incremental functionality.

## Current layers

### Audio

         Layer (class) name | Description                                                      | Provide by the module
    ------------------------+------------------------------------------------------------------+----------------------------------
                    Minimal | Full-duplex real-time transmission of chunks of audio over UDP   | minimal.py
                  Buffering | Network jitter hidding using a buffer of chunks                  | buffer.py
                DEFLATE_Raw | Compression of the chunks using DEFLATE                          | DEFLATE_raw.py
        DEFLATE_BytePlanes3 | Apply DEFLATE by planes of bytes                                 | DEFLATE_byteplanes3.py
              BR_Control_No | Increases compression ratios (and distortion) using quantization | BR_control_no.py
    BR_Control_Conservative | Network congestion control through the quantization step size    | BR_control_conservative.py
       Stereo_MST_Coding_32 | Exploiting inter-channel (spatial) correlation using the MST     | stereo_MST_coding_32.py
    Temporal_Overlapped_WPT | Exploiting intra-channel (temporal) correlation using the WPT    | temporal_overlapped_WPT_coding.py
                        ToH | Perceptial quantization considering the Threshold of Hearing     | ToH_coding.py 

### Video

         Layer (class) name | Description                                                      | Provide by the module
    ------------------------+------------------------------------------------------------------+----------------------------------
              Minimal_Video | Full-duplex real-time transmission of chunks of pixels over UDP  | minimal_video.py
 DEFLATE_Video_Conservative | Idem as BR_Control_Conservative byt applied to video data        | DEFLATE_video_conservative.py
          DEFLATE_Video_DCT | Exploit spatial correlation using the DCT (should inherit from   | DEFLATE_video_DCT.py
	                    |  DEFLATE_Video_Conservative)                                     |

## Future extensions

### Audio

1. **Frame interleaving and interpolation.**
2. **Chunk interpolation using neural networks.**

### Video

1. **Multiple description coding in the transform domain.**