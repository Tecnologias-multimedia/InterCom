# Welcome!

InterCom is a low-latency full-duplex intercom(municator) designed for the transmission of media (audio and video) between networked users. 

## Implementation

InterCom is written in Python and uses the [`python-soundevice`](https://python-sounddevice.readthedocs.io/) package. InterCom implements the following steps:

1. Read raw data from the audio [ADC](https://en.wikipedia.org/wiki/Analog-to-digital_converter).
2. Encode the raw data.
3. Send the encoded data to the interlocutor.
4. Receive encoded data from the interlocutor.
5. Decode the encoded data.
6. Write the raw data to the audio [DAC](https://en.wikipedia.org/wiki/Digital-to-analog_converter).

The Steps 2 and 4 are CPU bound (the rest are IO bound). For this reason, Intercom runs two parallel tasks:

1. **CES (Capture Encode and Send)**, which samples, process and sends the media (currently only audio) towards an Internet end-point.
2. **RDP (Receive Decode and Play)**, that receives the media, decodes and plays it.

CES (Steps 1, 2 and 3) and RDP (Steps 4, 5, and 6) are run in two different processes, which share information about the data-flow control that CES must perform. A further multiprocessing decomposition could be performed in E (Encode) and D (Decode) steps.

## Configurations

### 1. One-to-one intercommunication

```
   Host A           Host B
+---------+      +---------+
|   CES   |----->|   RDP   |
|---------|      |---------|
|   RDP   |<-----|   CES   |
+---------+      +---------+
```

### 2. Many-to-many intercommunication

```
     Host A            Host B
  +---------+       +---------+
  |   CES   |------>|   RDP   |
  |---------|       |---------|
  |   RDP   |<------|   CES   |
  +---------+       +---------+
  +---------+       +---------+
+-|   CES   |    +->|   RDP   |
| |---------|    |  |---------|
| |   RDP   |<-+ |  |   CES   |-+
| +---------+  | |  +---------+ |
|       +------+ +-----+        |
|       |  +---------+ |        |
|       +->|   CES   | |        |
|          |---------| |        |
+--------->|   RDP   | |        |
           +---------+ |        |
           +---------+ |        |
           |   CES   |-+        |
           |---------|          |
           |   RDP   |<---------+
           +---------+
              Host C          
```
