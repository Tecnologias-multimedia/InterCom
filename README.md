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

## Configturations

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
   Host A           Host B
+---------+      +---------+
|   CES   |----->|   RDP   |
|---------|      |---------|
|   RDP   |<-----|   CES   |
+---------+      +---------+
+---------+      +---------+
|   CES   |      |   RDP   |
|---------|      |---------|
|   RDP   |      |   CES   |
+---------+      +---------+

           Host C
        +---------+
        |   CES   |
        |---------|
        |   RDP   |
        +---------+
```



The local Receiver share with the local Sender the amount of data that the remote Receiver task has received from the local sender. A picture helps:

```
   Host A            Host B
+----------+      +----------+
|  Sender  |----->| Receiver |
|----------|      |----------|
| Receiver |<----+|  Sender  |
+----------+      +----------+
instance of        instance of
    RTic               RToc
```


# (Current and Future) modules

RTIC consist of three modules:

1. The **Sender**, which captures, process and send the media (audio and vídeo) to an Internet end-point.
2. The **Receiver**, that receives the media, de-process and plays it.
3. The **Mixer**, that receives a collection of streams, mix them, and sends the mixed media to a collection of end-points.

Sender receives from the (local) Receiver

# Configurations

## 1. Half-duplex one-to-one

```
  Host A           Host B
+--------+      +----------+
| Sender |----->| Receiver |
+--------+      +----------+
"captures"        "plays"
```

### Use

#### 1. Host A == Host B (Wire mode)

```
terminal 1> python3 sender.py 
terminal 2> python3 receiver.py
```
#### 2. Host A != Host B

```
host A> python3 sender.py
host B> python3 receiver.py
```

## 2. Full-duplex one-to-one

```
   Host A         Host B
 +--------+    +----------+
 | Sender |--->| Receiver |
 +--------+    +----------+
"captures"        "plays"
+----------+    +--------+
| Receiver |<---| Sender |
+----------+    +--------+
  "plays"       "captures"  
```

### Use

```
to be described
```

## 3. Half-duplex one-to-many (radio/TV mode)

```
  Host A          Host B          Host C
+--------+      +-------+      +----------+
| Sender |----->| Mixer |----->| Receiver |
+--------+      +-------+-+    +----------+
"captures"     "averages" |      "plays"
                          |       Host D
                          |    +----------+
                          +---->| Receiver |
                               +----------+
                                 "plays"  
```

### Use

```
to be described
```

## 4. Half-duplex many-to-many (multisource radio/TV mode)

```
  Host A          Host B          Host C
+--------+      +-------+      +----------+
| Sender |----->| Mixer |----->| Receiver |
+--------+  +-->+-------+-+    +----------+
"captures"  |  "averages" |      "plays"
  Host E    |             |       Host D
+--------+  |             |    +----------+
| Sender |--+             +---->| Receiver |
+--------+                     +----------+
"captures"                       "plays"  
```
### Use

```
to be described
```

## 5. Full-duplex many-to-many (conference mode):

```
to be drawn
```

### Use

```
to be described
```
