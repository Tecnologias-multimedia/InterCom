# Welcome to the RTIC Project

RTIC (Real Time InterCom) is a low-latency full-duplex intercommunicator designed for the transmission of audio (and in the future, video) between networked users.

# (Current and Future) modules

RTIC consist of three modules:

1. The **Sender**, which captures, process and send the media (audio y vídeo) to an Internet end-point.
2. The **Receiver**, that receives the media, process and plays it.
3. The **Mixer**, that receives a collection of streams, mix them, and sends the mixed media to a collection of end-points.

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
