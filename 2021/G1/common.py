import sounddevice as sd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.axes as ax
import math
import matplotlib
from scipy import signal
from ipywidgets import interact, interactive, fixed, interact_manual
import ipywidgets as widgets

from br_control import Quantization

def plot(x, *args, xlabel='', ylabel='', title='', ylim=None):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.set_title(title)
    ax.grid()
    ax.xaxis.set_label_text(xlabel)
    ax.yaxis.set_label_text(ylabel)
    if ylim:
        ax.set_ylim([-ylim, ylim])
    ax.plot(x, *args)
    plt.show(block=False)


def average_energy(x):
    return np.sum(x.astype(np.double)*x.astype(np.double))/len(x)

def RMSE(x, y):
    error_signal = x - y
    return math.sqrt(average_energy(error_signal))

def entropy_in_bits_per_symbol(sequence_of_symbols):
    value, counts = np.unique(sequence_of_symbols, return_counts = True)
    probs = counts / len(sequence_of_symbols)
    n_classes = np.count_nonzero(probs)

    if n_classes <= 1:
        return 0

    entropy = 0.
    for i in probs:
        entropy -= i * math.log(i, 2)

    return entropy

def RD_curve(x):
    points = []
    for q_step in range(1, 32768, 32):
        k, y = q_deq(x, q_step)
        rate = entropy_in_bits_per_symbol(k)
        distortion = RMSE(x, y)
        points.append((rate, distortion))
    return points
    
def q_deq(x, quantization_step):
    quantization = Quantization()
    k = quantization.quantize(x, quantization_step)
    y = quantization.dequantize(k, quantization_step)
    return k, y