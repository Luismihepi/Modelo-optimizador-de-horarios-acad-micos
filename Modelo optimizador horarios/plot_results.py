import os
import json
import csv
import math
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Rutas
BASE = os.path.dirname(__file__)
RESULTS_DIR = os.path.join(BASE, "resultados")
PLOTS_DIR = os.path.join(RESULTS_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)

TEACHER_LOAD_FILE = os.path.join(RESULTS_DIR, "teacher_load.json")
EVOL_FILE = os.path.join(RESULTS_DIR, "evolucion.csv")
DATOS_FILE = os.path.join(BASE, "datos_sistema.json")

# Cargar datos
with open(TEACHER_LOAD_FILE, "r", encoding="utf-8") as f:
    teacher_load = json.load(f)

with open(DATOS_FILE, "r", encoding="utf-8") as f:
    datos = json.load(f)

# Mapping id -> tipo_vinculacion
docentes_raw = datos.get("docentes", {})
id_to_tipo = {tid: d.get("tipo_vinculacion", "") for tid, d in docentes_raw.items()}

# Preparar arrays
names = []
hours = []
tipos = []
ids = []
for r in teacher_load:
    tid = r.get("teacher_id")
    names.append(r.get("teacher_name") or tid)
    hours.append(r.get("horas_asignadas", 0))
    tipos.append(id_to_tipo.get(tid, "catedra"))
    ids.append(tid)

# Colors por tipo
color_map = {
    "planta": "#2ca02c",
    "ocasional": "#1f77b4",
    "catedra": "#ff7f0e"
}
colors = [color_map.get(t, "#7f7f7f") for t in tipos]

# --- Gráfico 1: barras horas por docente (ordenadas) ---
order = np.argsort(hours)[::-1]
ordered_hours = [hours[i] for i in order]
ordered_names = [f"{ids[i]} - {names[i]}" for i in order]
ordered_colors = [colors[i] for i in order]

plt.figure(figsize=(12, 6))
plt.bar(range(len(ordered_hours)), ordered_hours, color=ordered_colors)
plt.xticks(range(len(ordered_names)), ordered_names, rotation=80, ha="right")
plt.ylabel("Horas asignadas")
plt.title("Horas asignadas por docente (ordenado)")
plt.tight_layout()
path1 = os.path.join(PLOTS_DIR, "teacher_hours_bar.png")
plt.savefig(path1, dpi=150)
plt.close()

# --- Gráfico 2: boxplot / distribución por tipo ---
by_type = defaultdict(list)
for t, h in zip(tipos, hours):
    by_type[t].append(h)

labels = []
data = []
for t in ["planta", "ocasional", "catedra"]:
    labels.append(t)
    data.append(by_type.get(t, []))

plt.figure(figsize=(8, 6))
plt.boxplot(data, labels=labels, showmeans=True)
plt.ylabel("Horas asignadas")
plt.title("Distribución de horas por tipo de vinculación")
plt.tight_layout()
path2 = os.path.join(PLOTS_DIR, "hours_by_type_boxplot.png")
plt.savefig(path2, dpi=150)
plt.close()

# --- Gráfico 3: evolución del GA (avg y max) ---
gens = []
avg = []
maxv = []
if os.path.exists(EVOL_FILE):
    with open(EVOL_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                gens.append(int(r.get('generacion', r.get('gen', 0))))
                avg.append(float(r.get('avg', 0)))
                maxv.append(float(r.get('max', 0)))
            except Exception:
                pass

if gens:
    plt.figure(figsize=(10, 5))
    plt.plot(gens, avg, label='avg')
    plt.plot(gens, maxv, label='max')
    plt.xlabel('Generación')
    plt.ylabel('Fitness')
    plt.title('Evolución del fitness (avg y max)')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    path3 = os.path.join(PLOTS_DIR, 'evolucion_avg_max.png')
    plt.savefig(path3, dpi=150)
    plt.close()
else:
    path3 = None

# --- Gráfico 4: pie de horas totales por tipo ---
sum_by_type = {t: sum(by_type.get(t, [])) for t in labels}
labels_present = [t for t in labels if sum_by_type.get(t, 0) > 0]
sizes = [sum_by_type[t] for t in labels_present]
colors_present = [color_map.get(t, '#7f7f7f') for t in labels_present]

plt.figure(figsize=(6, 6))
plt.pie(sizes, labels=labels_present, autopct='%1.1f%%', colors=colors_present)
plt.title('Proporción de horas totales por tipo de vinculación')
plt.tight_layout()
path4 = os.path.join(PLOTS_DIR, 'hours_share_by_type_pie.png')
plt.savefig(path4, dpi=150)
plt.close()

print('Gráficas generadas:')
print(' -', path1)
print(' -', path2)
if path3:
    print(' -', path3)
print(' -', path4)
print('\nResumen rápido:')
for tid, name, h, t in zip(ids, names, hours, tipos):
    print(f"{tid}\t{name}\t{h}h\t{t}")
