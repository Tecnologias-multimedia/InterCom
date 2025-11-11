import matplotlib.pyplot as plt

# Datos Code 16
RMSE_16 = [0.017656, 0.059742, 0.143267, 0.295782, 0.663760, 1.402722, 2.370920, 2.374480]
SNR_16 = [96.295147, 69.885396, 56.596801, 40.491646, 21.784894, 11.393311, 0.000538, 0.0]
Kbps_16 = [96.85, 41.65, 36.916667, 30.6, 27.8, 26.05, 25.3, 25.316667]

# Datos Code 32
RMSE_32 = [0.017662, 0.058179, 0.146738, 0.297739, 0.666798, 1.409698, 2.349830, 2.393351]
SNR_32 = [95.961539, 70.945373, 56.001244, 40.607287, 21.804457, 11.151392, 0.088059, 0.0]
Kbps_32 = [110.9, 53.866667, 40.2, 30.6, 28.683333, 29.183333, 25.885246, 25.266667]

# Función para graficar
def plot_metric_vs_kbps(Kbps, Metric, ylabel, title, filename):
    plt.figure(figsize=(10,6))
    plt.plot(Kbps, Metric, marker='o', linestyle='-', color='b')
    plt.xlabel('Kbps')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True)
    plt.savefig(filename, bbox_inches='tight')
    plt.close()

# Graficas Code 16
plot_metric_vs_kbps(Kbps_16, RMSE_16, 'RMSE', 'Code 16: RMSE vs Kbps', 'code16_rmse.png')
plot_metric_vs_kbps(Kbps_16, SNR_16, 'SNR', 'Code 16: SNR vs Kbps', 'code16_snr.png')

# Graficas Code 32
plot_metric_vs_kbps(Kbps_32, RMSE_32, 'RMSE', 'Code 32: RMSE vs Kbps', 'code32_rmse.png')
plot_metric_vs_kbps(Kbps_32, SNR_32, 'SNR', 'Code 32: SNR vs Kbps', 'code32_snr.png')
