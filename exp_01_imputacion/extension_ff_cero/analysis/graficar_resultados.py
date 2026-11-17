"""Make a shareable scientific figure from the verified experiment results."""
from pathlib import Path
import csv
import json
import os

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/uba-imputacion-matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import numpy as np

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "outputs"
report = json.loads((OUT / "analisis_verificado.json").read_text())
assert report["status"] in {"verified", "aligned_existing_results"}
with (OUT / "metricas_por_semilla.csv").open() as f:
    rows = list(csv.DictReader(f))
methods = ["E0", "E4", "FF_ZERO", "FF_MEDIAN_MICA"]
labels = ["NaN nativos", "Forward fill", "Forward fill + cero", "FF + mediana (Mica)"]
summary = {r["method"]: r for r in report["summary"]}
rng = np.random.default_rng(20261114)
jitter = rng.uniform(-.14, .14, 30)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.spines.left": False, "axes.edgecolor": "#9b9b9b",
                     "text.color": "#222222", "axes.labelcolor": "#333333"})
fig, ax = plt.subplots(figsize=(10, 4.8))
fig.subplots_adjust(left=.245, right=.88, top=.75, bottom=.23)
fig.suptitle("Ganancia en octubre con la misma configuración", x=.03, y=.965,
             ha="left", fontsize=17, fontweight="bold")
fig.text(.03, .87, "Cada punto es una semilla; el rombo marca la media y la línea, ±1 desvío estándar.", fontsize=10.5)
fig.text(.895, .80, "Media", color="#444444", ha="center", fontsize=10)
for index, method in enumerate(methods):
    values = np.array([float(r["gain_at_n_fijo"]) / 1e6 for r in rows if r["method"] == method])
    assert len(values) == 30
    color = "#1d647d" if method == "FF_ZERO" else "#777e84"
    ax.scatter(values, index + jitter, color=color, alpha=.52, s=22, linewidths=0, zorder=2)
    mean, sd = summary[method]["gain_mean"] / 1e6, summary[method]["gain_sd"] / 1e6
    ax.errorbar(mean, index, xerr=sd, fmt="D", color=color, markersize=7,
                elinewidth=2, capsize=4, markeredgecolor="white", markeredgewidth=.8, zorder=3)
    ax.text(1.025, index, f"{mean:.2f}".replace(".", ","),
            transform=ax.get_yaxis_transform(), va="center", color="#222222", fontsize=11,
            fontweight="bold" if method == "FF_ZERO" else "normal")
ax.set_yticks(range(4), labels)
ax.set_ylim(3.5, -.5)
ax.tick_params(axis="y", length=0, pad=10)
ax.tick_params(axis="x", length=3, color="#999999")
for tick in ax.get_yticklabels():
    if tick.get_text() == "Forward fill + cero":
        tick.set_fontweight("bold")
ax.set_xlabel("Ganancia en millones de pesos", labelpad=10)
ax.xaxis.set_major_formatter(FuncFormatter(lambda value, position: f"{value:g}".replace(".", ",")))
ax.grid(axis="x", color="#e7e7e7", linewidth=.8)
ax.set_axisbelow(True)
fig.text(.03, .075, "Train: marzo–agosto de 2019 · Test: octubre de 2019 · 280 árboles · 4.323 contactos · 30 semillas comunes", fontsize=9.5)
fig.text(.03, .025, "E0/E4/FF_ZERO: corrida de Florencia. Mediana: resultados publicados de Mica. Un solo mes de test.", fontsize=9, color="#555555")
fig.savefig(OUT / "ganancia_por_metodo.png", dpi=180, facecolor="white")
fig.savefig(OUT / "ganancia_por_metodo.svg", facecolor="white")
print(OUT / "ganancia_por_metodo.png")
