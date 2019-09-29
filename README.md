# intercom

A low-latency full-duplex intercom. Two or more intercom users will be
able (the project is still unfinished) to communicate (audio and
video) in real-time (with a minimal latency) using a _room_ defined in
a public server. All communications are Peer-to-Peer (P2P).

<!-- ## Platform

The software is written in Python 3, and therefore, you should be able
to run it in any machine where a Python 3 interpreter is available.

## Intercom without data-flow control.

```
Task 1. Receiver

1. Forever:
1.1. Receive a packet.
1.2. Decompress the packet, generating a quality layer.
1.3. Store the layer in a buffer.

Task 2. Player

1. Get the first chunk from the buffer.
2. Forever:
2.1. Play the chunk.
2.2. Get the next chunk from the buffer.

Task 3. SamplerAndSender

1. Forever:
1.1. Sample a chunk.
1.2. Generate the sequence of compressed packets, one for each quality layer.
1.3. Send the sequence of packets.
```
-->

## Resources

* [PyWavelet](https://pywavelets.readthedocs.io).
* [Public chat room for intercom at Gitter](https://gitter.im/Tecnologias-multimedia/intercom).
* [Public chat room for Tecnologías Multimedia at Gitter](https://gitter.im/Tecnologias-multimedia/community).
<!-- * [Slack channel](https://tec-multimedia-ual.slack.com/messages/intercom_2018/). -->
