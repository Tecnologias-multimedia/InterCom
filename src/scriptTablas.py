import subprocess
import re
import pandas as pd

# Lista de valores que quieres probar
quant_steps = [64, 256 ,512 ,1024, 2048, 4096, 8192, 16384]

results = []

for q in quant_steps:
    print(f"\n>>> Ejecutando con minimal_quantization_step = {q}\n")

    # Ejecuta el comando y captura la salida completa
    cmd = [
        "./stereo_MST_coding_16.py",
        "--minimal_quantization_step", str(q),
        "-t", "60",
        "--show_stats"
    ]
    process = subprocess.run(cmd, capture_output=True, text=True)
    output = process.stdout

    # Busca las líneas de RMSE y SNR usando regex
    rmse_match = re.search(r"Average RMSE .*=\s*\[([^\]]+)\]", output)
    snr_match = re.search(r"Average SNR .*=\s*\[([^\]]+)\]", output)

    if rmse_match and snr_match:
        # Extrae y convierte los valores a float
        rmse_vals = [float(x.strip()) for x in rmse_match.group(1).split()]
        snr_vals = [float(x.strip()) for x in snr_match.group(1).split()]

        results.append({
            "QuantStep": q,
            "RMSE_L": rmse_vals[0],
            "RMSE_R": rmse_vals[1],
            "SNR_L": snr_vals[0],
            "SNR_R": snr_vals[1]
        })
        print(f"✔ Resultados capturados: RMSE={rmse_vals}, SNR={snr_vals}")
    else:
        print("⚠ No se encontraron resultados para este valor de Q.")

# Crear tabla y mostrar
df = pd.DataFrame(results)
print("\n==================== RESULTADOS ====================")
print(df)

# Guardar a CSV para tus curvas RD
df.to_csv("RD_MST_results.csv", index=False)
print("\n📁 Resultados guardados en RD_MST_results.csv")
