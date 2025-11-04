import subprocess
import re
import pandas as pd


quant_steps = [64, 256, 512, 1024, 2048, 4096, 8192, 16384]
wavelets = ["db5"]
levels = [6]

results = []

for wavelet in wavelets:
    for lvl in levels:
        for q in quant_steps:
            print(f"\n>>> Ejecutando con wavelet={wavelet}, levels={lvl}, minimal_quantization_step={q}\n")

            cmd = [
                "python", "temporal_no_overlapped_DWT_coding.py",
                "--wavelet_name", wavelet,
                "--levels", str(lvl),
                "--minimal_quantization_step", str(q),
                "-t", "10",
                "--show_stats"
            ]

            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output = process.stdout

            rmse_match = re.search(r"Average\s+RMSE.*?=\s*\[([0-9eE\.\s\-]+)\]", output)
            snr_match = re.search(r"Average\s+SNR.*?=\s*\[([0-9eE\.\s\-]+)\]", output)

            if rmse_match and snr_match:
                rmse_vals = [float(x) for x in rmse_match.group(1).split()]
                snr_vals = [float(x) for x in snr_match.group(1).split()]

                results.append({
                    "Wavelet": wavelet,
                    "Levels": lvl,
                    "QuantStep": q,
                    "RMSE_L": rmse_vals[0],
                    "RMSE_R": rmse_vals[1],
                    "SNR_L": snr_vals[0],
                    "SNR_R": snr_vals[1]
                })
                print(f"✔ Resultados capturados: RMSE={rmse_vals}, SNR={snr_vals}")
            else:
                print("⚠ No se encontraron resultados para este valor de Q.")
                print("Salida completa del programa:\n")
                print(output)
                print("-" * 80)

# Crear DataFrame con los resultados
df = pd.DataFrame(results)
print("\n==================== RESULTADOS ====================")
print(df)

# Guardar resultados a CSV
df.to_csv("RD_DWT_results.csv", index=False)
print("\n📁 Resultados guardados en RD_DWT_results.csv")
