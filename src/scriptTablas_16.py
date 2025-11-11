import subprocess
import re
import pandas as pd

# Lista de valores que quieres probar
quant_steps = [64, 256, 512, 1024, 2048, 4096, 8192, 16384]

results = []

for q in quant_steps:
    print(f"\n>>> Ejecutando con minimal_quantization_step = {q}\n")

    cmd = [
        "./stereo_MST_coding_16.py",
        "--minimal_quantization_step", str(q),
        "-t", "60",
        "--show_stats"
    ]
    process = subprocess.run(cmd, capture_output=True, text=True)
    output = process.stdout

    # RMSE y SNR
    rmse_match = re.search(r"Average RMSE .*=\s*\[([^\]]+)\]", output)
    snr_match = re.search(r"Average SNR .*=\s*\[([^\]]+)\]", output)

    # Kbps: Payload sent average
    kbps_match = re.search(r"Payload sent average\s*=\s*([\d\.]+)\s*kilo bits per second", output, re.IGNORECASE)

    if rmse_match and snr_match and kbps_match:
        rmse_vals = [float(x.strip()) for x in rmse_match.group(1).split()]
        snr_vals = [float(x.strip()) for x in snr_match.group(1).split()]
        
        rmse_avg = sum(rmse_vals)/len(rmse_vals)
        snr_avg = sum(snr_vals)/len(snr_vals)
        
        kbps = float(kbps_match.group(1))

        results.append({
            "QuantStep": q,
            "RMSE_avg": rmse_avg,
            "SNR_avg": snr_avg,
            "Kbps": kbps
        })
        print(f"✔ Resultados: RMSE_avg={rmse_avg:.6f}, SNR_avg={snr_avg:.2f}, Kbps={kbps:.2f}")
    else:
        print("⚠ No se encontraron todos los resultados para este valor de Q.")

# Crear tabla y mostrar
df = pd.DataFrame(results)
print("\n==================== RESULTADOS ====================")
print(df)

# Guardar a CSV
df.to_csv("RD_MST_results.csv", index=False)
print("\n📁 Resultados guardados en RD_MST_results.csv")
