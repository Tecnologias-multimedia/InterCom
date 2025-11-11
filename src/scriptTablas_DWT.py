import subprocess
import re
import pandas as pd
import sys

# Parámetros de prueba
wavelets = ["db5"]
levels = [3, 5, 7]
quant_steps = [64, 256, 512, 1024, 2048, 4096, 8192, 16384]
results = []

for wavelet in wavelets:
    for lvl in levels:
        for q in quant_steps:
            print(f"\n>>> Ejecutando con wavelet={wavelet}, levels={lvl}, minimal_quantization_step={q}\n")

            # Comando a ejecutar
            cmd = [
                sys.executable, "temporal_no_overlapped_DWT_coding.py",
                "--wavelet_name", wavelet,
                "--levels", str(lvl),
                "--minimal_quantization_step", str(q),
                "-t", "10",
                "--show_stats"
            ]

            # Ejecutar proceso y capturar salida
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output = process.stdout

            # Buscar RMSE, SNR y kbps
            rmse_match = re.search(r"Average\s+RMSE.*?=\s*\[([0-9eE\.\s\-]+)\]", output)
            snr_match = re.search(r"Average\s+SNR.*?=\s*\[([0-9eE\.\s\-]+)\]", output)
            kbps_match = re.search(r"Payload sent average\s*=\s*([\d\.]+)\s*kilo bits per second", output, re.IGNORECASE)
            kbps = float(kbps_match.group(1)) if kbps_match else None

            if rmse_match and snr_match:
                rmse_vals = [float(x) for x in rmse_match.group(1).split()]
                snr_vals = [float(x) for x in snr_match.group(1).split()]

                # Calcular medias
                rmse_mean = sum(rmse_vals) / len(rmse_vals)
                snr_mean = sum(snr_vals) / len(snr_vals)

                results.append({
                    "Wavelet": wavelet,
                    "Levels": lvl,
                    "QuantStep": q,
                    "RMSE_Mean": rmse_mean,
                    "SNR_Mean": snr_mean,
                    "Bitrate_kbps": kbps
                })

                print(f"✔ Resultados: Wavelet={wavelet}, Levels={lvl}, Q={q}, RMSE_Mean={rmse_mean:.4f}, SNR_Mean={snr_mean:.2f}, Bitrate={kbps if kbps else 'N/A'} kbps")
            else:
                print("⚠ No se encontraron resultados para este valor de Q.")
                print(output)
                print("-" * 80)

# Crear DataFrame con resultados
df = pd.DataFrame(results)
df = df.sort_values(["Levels", "QuantStep"], ascending=[True, True])
print("\n==================== RESULTADOS ====================")
print(df)

# Guardar resultados a CSV
df.to_csv("RD_DWT_results.csv", index=False)
print("\n📁 Resultados guardados en RD_DWT_results.csv")
