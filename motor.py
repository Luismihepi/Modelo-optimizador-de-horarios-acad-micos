def repair_no_conflicts(individual):
    """Reparador duro: elimina solapamientos de docente y aula en el horario.
    Modifica el individuo in-place y retorna True si hizo cambios.
    """
    from collections import defaultdict
    changed = False
    # Mapas: (day, time) -> docente/aula
    slot_teacher = defaultdict(list)
    slot_room = defaultdict(list)
    for i, gene in enumerate(individual):
        slot_idx, room_idx, teacher_idx = gene
        s = SLOT_DEFINITIONS[slot_idx]
        key = (s['day_idx'], s['start'], s['end'])
        slot_teacher[key].append((i, teacher_idx))
        slot_room[key].append((i, room_idx))
    # Eliminar solapamientos de docente
    for key, lst in slot_teacher.items():
        docentes = defaultdict(list)
        for i, t in lst:
            docentes[t].append(i)
        for t, idxs in docentes.items():
            if len(idxs) > 1:
                # Mantener solo una asignación, reubicar las demás
                for idx in idxs[1:]:
                    block = BLOCKS[idx]
                    duration = block['duration']
                    candidates = SLOT_INDICES_BY_DURATION[duration]
                    found = False
                    for si in candidates:
                        if is_teacher_available(t, si) and all(gene[2] != t or gene[0] != si for gene in individual):
                            individual[idx] = (si, individual[idx][1], t)
                            changed = True
                            found = True
                            break
                    if not found:
                        # Si no hay slot alternativo, asignar otro docente disponible
                        for alt_t in range(len(DOCENTES)):
                            if (
                                alt_t != t
                                and is_teacher_available(alt_t, individual[idx][0])
                                and all(
                                    gene[2] != alt_t or gene[0] != individual[idx][0]
                                    for gene in individual
                                )
                            ):
                                individual[idx] = (individual[idx][0], individual[idx][1], alt_t)
                                changed = True
                                break
    # Eliminar solapamientos de aula
    for key, lst in slot_room.items():
        aulas = defaultdict(list)
        for i, r in lst:
            aulas[r].append(i)
        for r, idxs in aulas.items():
            if len(idxs) > 1:
                for idx in idxs[1:]:
                    block = BLOCKS[idx]
                    candidates = [
                        i for i, room in enumerate(AULAS)
                        if room_type_matches(room['type'], block['tipo_aula']) and room['capacity'] >= block['students']
                    ]
                    found = False
                    for alt_r in candidates:
                        if all(gene[1] != alt_r or gene[0] != individual[idx][0] for gene in individual):
                            individual[idx] = (individual[idx][0], alt_r, individual[idx][2])
                            changed = True
                            found = True
                            break
                    if not found and candidates:
                        individual[idx] = (individual[idx][0], candidates[0], individual[idx][2])
                        changed = True
    return changed

import os, json, math, random, csv, re, textwrap
from collections import defaultdict, OrderedDict
from copy import deepcopy
import unicodedata

import numpy as np  
from deap import base, creator, tools


DAY_ALIASES = {
    "lunes": "Lunes",
    "martes": "Martes",
    "miercoles": "Miércoles",
    "jueves": "Jueves",
    "viernes": "Viernes",
    "sabado": "Sábado",
}

DAY_RAW_FIXES = {
    "MiǸrcoles": "Miércoles",
    "MiÃ©rcoles": "Miércoles",
    "MiNrcoles": "Miércoles",
    "Sǭbado": "Sábado",
    "SÃ¡bado": "Sábado",
}

ROOM_TYPE_ALIASES = {
    "teorica": "teorica",
    "teórica": "teorica",
    "practica": "practica",
    "práctica": "practica",
    "laboratorio": "practica",
    "lab": "practica",
    "teorico-practica": "mixta",
    "teorico_practica": "mixta",
    "teoricopractica": "mixta",
    "mixta": "mixta",
    
}


def _strip_accents(value):
    if not isinstance(value, str):
        return value
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", value) if not unicodedata.combining(ch)
    )


def normalize_day_name(value):
    if not value:
        return value
    raw = value.strip()
    if raw in DAY_RAW_FIXES:
        return DAY_RAW_FIXES[raw]
    key = _strip_accents(raw).lower()
    return DAY_ALIASES.get(key, raw)


def normalize_room_type(value):
    if not value:
        return "teorica"
    key = (
        _strip_accents(value)
        .lower()
        .replace(" ", "")
        .replace("-", "_")
    )
    return ROOM_TYPE_ALIASES.get(key, "teorica")


def room_type_matches(room_type, block_type):
    rt = normalize_room_type(room_type)
    bt = normalize_room_type(block_type)
    if bt == "mixta":
        return rt in {"teorica", "practica"}
    if rt == "mixta":
        return bt in {"teorica", "practica"}
    return rt == bt


def normalize_specialty_label(value):
    if not value:
        return ""
    raw = _strip_accents(value).lower().strip()
    return raw

DATA_FILE = "datos_sistema.json"

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

DOCENTES_RAW = data["docentes"]
ASIGNATURAS_RAW = data["asignaturas"]
AULAS_RAW = data["aulas"]
CONFIG = data.get("configuracion", {})
HARD_LIMIT_FACTOR = CONFIG.get("hard_limit_factor", 1.0)  # factor para límite duro (1.0 = no exceder)
TARGET_HOURS_PLANTA = CONFIG.get("objetivo_horas_planta", 15)
TARGET_HOURS_OCASIONAL = CONFIG.get("objetivo_horas_ocasional", 23)

# ---------------------------
# Helpers de tiempo
# ---------------------------
def parse_hhmm(s):
    h, m = s.split(":")
    return int(h), int(m)

def time_to_float(hhmm):
    h, m = parse_hhmm(hhmm)
    return h + m/60.0

def rango_to_tuple(rango):
    """Convierte '07:00-22:00' -> (7.0, 22.0)"""
    a, b = rango.split("-")
    return time_to_float(a), time_to_float(b)

def slot_inside_ranges(start_h, end_h, rangos):
    """¿[start,end] está completamente dentro de algún rango?"""
    for r in rangos:
        rs, re = rango_to_tuple(r)
        if start_h >= rs and end_h <= re:
            return True
    return False

# ---------------------------
# Normalización estructuras
# ---------------------------
DOCENTES = []
doc_id_to_index = {}
for i, (did, d) in enumerate(DOCENTES_RAW.items()):
    raw_disp = d.get("disponibilidad", {})
    disponibilidad = {}
    for day, rangos in raw_disp.items():
        normalized_day = normalize_day_name(day)
        if not normalized_day:
            continue
        if isinstance(rangos, list):
            disponibilidad[normalized_day] = rangos
        elif isinstance(rangos, str):
            disponibilidad[normalized_day] = [rangos]
    if not disponibilidad:
        disponibilidad = raw_disp
    DOCENTES.append({
        "id": did,
        "name": d.get("nombre", did),
        "tipo_vinculacion": d.get("tipo_vinculacion", ""),
        "limite_horas": d.get("limite_horas_semanales", CONFIG.get("horas_maximas_planta", 16)),
        "especialidades": [normalize_specialty_label(s) for s in d.get("especialidades", []) if s],
        "disponibilidad": disponibilidad  # dict día -> ["07:00-22:00"]
    })
    doc_id_to_index[did] = i

AULAS = []
aula_id_to_index = {}
for i, (aid, a) in enumerate(AULAS_RAW.items()):
    room_type = normalize_room_type(a.get("tipo", a.get("type", "teorica")))
    AULAS.append({
        "id": aid,
        "capacity": a.get("capacidad", CONFIG.get("capacidad_maxima_grupo", 28)),
        "type": room_type,
        "raw": a
    })
    aula_id_to_index[aid] = i

ASIGNATURAS = []
for sid, s in ASIGNATURAS_RAW.items():
    subj_specialties = [normalize_specialty_label(x) for x in s.get("especialidades", []) if x]
    subj_name = s.get("name") or s.get("nombre", "")
    if not subj_specialties and subj_name:
        subj_specialties = [normalize_specialty_label(subj_name)]
    tipo_aula = normalize_room_type(s.get("tipo_aula", s.get("tipo_materia", "teorica")))
    ASIGNATURAS.append({
        "id": sid,
        "name": s.get("nombre", ""),
        "hours": s.get("horas_semanales", 2),
        "students": s.get("num_estudiantes", 0),
        "tipo_aula": tipo_aula,
        "possible_teachers": s.get("possible_teachers", []),
        "especialidades": subj_specialties
    })

CAPACIDAD_MAX_GRUPO = CONFIG.get("capacidad_maxima_grupo", 28)

DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]
SLOT_DEFINITIONS = []
for day_idx, day in enumerate(DAYS):
    for h in range(7, 21):  # 2h
        if h + 2 <= 22:
            SLOT_DEFINITIONS.append({
                "day_idx": day_idx, "day": day,
                "start": h, "end": h + 2, "duration": 2,
                "label": f"{h:02d}:00-{h+2:02d}:00"
            })
    for h in range(7, 20):  # 3h
        if h + 3 <= 22:
            SLOT_DEFINITIONS.append({
                "day_idx": day_idx, "day": day,
                "start": h, "end": h + 3, "duration": 3,
                "label": f"{h:02d}:00-{h+3:02d}:00"
            })

TOTAL_SLOTS = len(SLOT_DEFINITIONS)

SLOT_INDICES_BY_DURATION = {2: [], 3: []}
for idx, s in enumerate(SLOT_DEFINITIONS):
    SLOT_INDICES_BY_DURATION[s["duration"]].append(idx)

def slot_overlaps(s1_idx, s2_idx):
    s1 = SLOT_DEFINITIONS[s1_idx]
    s2 = SLOT_DEFINITIONS[s2_idx]
    if s1["day_idx"] != s2["day_idx"]:
        return False
    return not (s1["end"] <= s2["start"] or s2["end"] <= s1["start"])

def pretty_slot(slot_idx):
    s = SLOT_DEFINITIONS[slot_idx]
    return s["day"], s["label"], s["start"], s["end"], s["duration"]

def build_blocks(asignaturas):
    blocks = []
    for subj in asignaturas:
        sid = subj["id"]
        name = subj["name"]
        hours = subj["hours"]
        total_students = subj["students"]
        tipo_aula = subj["tipo_aula"]
        possible_teachers = subj.get("possible_teachers", []) or []
        subject_specialties = subj.get("especialidades", []) or [normalize_specialty_label(name)]

        n_groups = max(1, math.ceil(total_students / CAPACIDAD_MAX_GRUPO))
        base = total_students // n_groups
        remainder = total_students % n_groups
        group_sizes = [base + (1 if i < remainder else 0) for i in range(n_groups)]

        if hours == 2: pattern = [2]
        elif hours == 4: pattern = [2, 2]
        elif hours == 5: pattern = [2, 3]
        elif hours == 6: pattern = [3, 3] 
        else:
            remaining = hours
            pattern = []
            while remaining > 0:
                if remaining >= 3:
                    pattern.append(3); remaining -= 3
                else:
                    pattern.append(2); remaining -= 2

        for g in range(n_groups):
            block_room_types = []
            if tipo_aula == "mixta":
                for idx in range(len(pattern)):
                    block_room_types.append("teorica" if idx % 2 == 0 else "practica")
            else:
                block_room_types = [tipo_aula] * len(pattern)

            for dur in pattern:
                blocks.append({
                    "subj_id": sid,
                    "subj_name": name,
                    "group_id": g + 1,
                    "total_groups": n_groups,
                    "students": group_sizes[g],
                    "duration": dur,
                    "tipo_aula": block_room_types.pop(0),
                    "tipo_aula_original": tipo_aula,
                    "possible_teachers": list(possible_teachers),
                    "especialidades": list(subject_specialties)
                })
    return blocks

BLOCKS = build_blocks(ASIGNATURAS)
NUM_BLOCKS = len(BLOCKS)

def choose_room_for_block(block):
    candidates = [
        i
        for i, room in enumerate(AULAS)
        if room_type_matches(room["type"], block["tipo_aula"])
        and room["capacity"] >= block["students"]
    ]
    if not candidates:
        candidates = [i for i, room in enumerate(AULAS) if room["capacity"] >= block["students"]]
    if not candidates:
        candidates = list(range(len(AULAS)))
    return random.choice(candidates)

def choose_teacher_for_block(block, current_hours=None):
    """
    Elige un docente para un bloque considerando:
    1. Docentes listados como posibles
    2. Horas ya asignadas (balance de carga)
    3. Tipo de vinculación (prioridad a planta)
    4. Especialidades
    """
    if current_hours is None:
        current_hours = defaultdict(int)
    
    # Obtener candidatos iniciales
    candidates = [doc_id_to_index[t] for t in block.get("possible_teachers", []) if t in doc_id_to_index]
    if not candidates:
        candidates = list(range(len(DOCENTES)))
    
    # Ordenar candidatos por:
    # - Menor carga actual
    # - Prioridad a docentes de planta
    # - Coincidencia de especialidades
    def teacher_score(t_idx):
        teacher = DOCENTES[t_idx]
        hours = current_hours[t_idx]
        is_planta = teacher.get("tipo_vinculacion", "") == "planta"
        return (
            hours,  # menor es mejor
            0 if is_planta else 1,  # planta primero
            -len(set(teacher.get("especialidades", [])) & set(block.get("especialidades", [])))  # más coincidencias mejor
        )
    
    candidates.sort(key=teacher_score)
    return candidates[0] if candidates else 0

def is_teacher_available(teacher_idx, slot_idx):
    t = DOCENTES[teacher_idx]
    s = SLOT_DEFINITIONS[slot_idx]
    rangos = t.get("disponibilidad", {}).get(s["day"], [])
    if not rangos:
        return False  # sin rangos explícitos => no disponible
    return slot_inside_ranges(s["start"], s["end"], rangos)

def individual_generator():
    """
    Genera un individuo inicial respetando la disponibilidad y prefiriendo asignar el mismo docente a todos
    los bloques de una misma asignatura/grupo. También intenta colocar los bloques en días distintos.

    - assigned_days_map: registra los días ya utilizados por cada clave (subj_id, group_id) para evitar
      colocar dos bloques del mismo grupo en el mismo día.
    - group_teacher_map: asegura que todos los bloques de un grupo sean impartidos por el mismo docente si es posible.
    """
    ind = []
    assigned_days_map = defaultdict(set)
    group_teacher_map = {}
    current_hours = defaultdict(int)
    for block in BLOCKS:
        # elegir slots que cumplan con la duración
        cand_slots = SLOT_INDICES_BY_DURATION[block["duration"]]
        # filtrar slots con al menos un docente disponible
        viable_slots = [si for si in cand_slots if any(is_teacher_available(ti, si) for ti in range(len(DOCENTES)))]
        if not viable_slots:
            viable_slots = cand_slots[:]
        # evitar repetir días para el mismo grupo
        key = (block["subj_id"], block["group_id"])
        used_days = assigned_days_map[key]
        filtered_slots = [si for si in viable_slots if SLOT_DEFINITIONS[si]["day_idx"] not in used_days]
        candidate_slots = filtered_slots if filtered_slots else viable_slots
        slot_idx = random.choice(candidate_slots)
        # registrar día utilizado
        assigned_days_map[key].add(SLOT_DEFINITIONS[slot_idx]["day_idx"])
        # elegir sala válida
        room_idx = choose_room_for_block(block)
        # determinar docente para el grupo: preferir docentes con menor carga y disponible
        teacher_idx = None
        duration = block["duration"]
        # intentar reutilizar docente del mismo grupo si no provoca sobrecarga
        if key in group_teacher_map:
            prev_teacher = group_teacher_map[key]
            if is_teacher_available(prev_teacher, slot_idx) and current_hours[prev_teacher] + duration <= DOCENTES[prev_teacher]["limite_horas"] * 1.5:
                teacher_idx = prev_teacher

        if teacher_idx is None:
            possible = block.get("possible_teachers", []) or []
            possible_indices = [doc_id_to_index[t] for t in possible if t in doc_id_to_index]
            if not possible_indices:
                possible_indices = list(range(len(DOCENTES)))

            # separar candidatos disponibles en el slot
            avail = [ti for ti in possible_indices if is_teacher_available(ti, slot_idx)]
            candidates = avail if avail else possible_indices

            # filtrar candidatos que no excedan el límite duro (si es posible)
            feasible = [ti for ti in candidates if current_hours[ti] + duration <= DOCENTES[ti]["limite_horas"] * HARD_LIMIT_FACTOR]
            if feasible:
                candidates = feasible

            # ordenar por menor carga actual y prioridad a planta
            def cand_key(ti):
                """Priorizar docentes de planta/ocasional que aún no alcanzaron su objetivo.
                Orden: (under_target, current_hours, planta_priority),
                con under_target=0 cuando el docente está por debajo de su meta configurable.
                """
                tipo = DOCENTES[ti].get("tipo_vinculacion", "")
                ch = current_hours[ti]
                under_target = 1
                target = None
                if tipo == "planta":
                    target = TARGET_HOURS_PLANTA
                elif tipo == "ocasional":
                    target = TARGET_HOURS_OCASIONAL
                if target is not None and ch < target:
                    under_target = 0
                is_planta = 0 if tipo == "planta" else 1
                return (under_target, ch, is_planta)

            candidates.sort(key=cand_key)
            teacher_idx = candidates[0]
            # registrar la asignación para los siguientes bloques del mismo grupo (siempre que no sobrecargue)
            if current_hours[teacher_idx] + duration <= DOCENTES[teacher_idx]["limite_horas"] * 1.5:
                group_teacher_map[key] = teacher_idx

        # actualizar horas actuales
        current_hours[teacher_idx] += duration
        ind.append((slot_idx, room_idx, teacher_idx))
    return ind

# Penalizaciones y recompensas (ajustadas)
P_HARD_OVERLAP_TEACHER = 50000       # choque de docente en la misma franja
P_HARD_OVERLAP_ROOM = 50000          # choque de aula en la misma franja
P_HARD_ROOM_CAPACITY = 750          # asignar más estudiantes de los que admite el aula
P_HARD_ROOM_TYPE = 750              # tipo de aula incorrecto (teórica/lab)
P_HARD_TEACHER_HOURS = 500          # penalización base por exceder límite de horas semanales
P_HARD_TEACHER_AVAIL = 50000        # docente fuera de su disponibilidad
P_HARD_MULTI_SAME_DAY = 750         # bloques del mismo grupo asignados el mismo día
P_HARD_MULTI_TEACHER_GROUP = 50000   # penalización muy alta por usar distintos docentes en un mismo grupo
P_BONUS_SAME_TEACHER = 500          # bonificación por mismo docente
P_HARD_OVERLOAD = 30000              # penalización por sobrecarga extrema de docentes
P_HARD_UNBALANCED = 500            # penalización reducida por desbalance en la carga docente
P_SOFT_PREF_TEACHER = 300           # preferencia por docentes listados
P_SOFT_GAPS = 50                    # penalización por huecos entre clases (suave)
P_SOFT_PLANTA_BONUS = 20000          # recompensa aumentada por asignar a docentes de planta
P_UNDER_HOURS_PLANTA = 50000        # penalización extremadamente alta por horas insuficientes en planta
P_UNDER_HOURS_OCASIONAL = 50000     # penalización muy alta por horas insuficientes en ocasionales
P_SOFT_SPECIALTY_MATCH = 200        # recompensa por docente con especialidad adecuada

def evaluate_schedule(individual):
    score = 500000  # Puntuación base positiva aumentada aún más
    teacher_slots = defaultdict(list)
    room_slots = defaultdict(list)
    teacher_hours = defaultdict(int)
    subjgroup_days = defaultdict(list)
    subjgroup_teachers = defaultdict(set)

    for i, gene in enumerate(individual):
        slot_idx, room_idx, teacher_idx = gene
        block = BLOCKS[i]
        students = block["students"]
        duration = block["duration"]
        slot = SLOT_DEFINITIONS[slot_idx]
        room = AULAS[room_idx]
        teacher = DOCENTES[teacher_idx]

        teacher_slots[teacher_idx].append(slot_idx)
        room_slots[room_idx].append(slot_idx)
        teacher_hours[teacher_idx] += duration
        key = (block["subj_id"], block["group_id"])
        subjgroup_days[key].append(slot["day_idx"])
        subjgroup_teachers[key].add(teacher_idx)

        # Disponibilidad dura
        if not is_teacher_available(teacher_idx, slot_idx):
            score -= P_HARD_TEACHER_AVAIL

        # Capacidad y tipo de aula
        if room["capacity"] < students:
            score -= P_HARD_ROOM_CAPACITY
        if not room_type_matches(room["type"], block["tipo_aula"]):
            score -= P_HARD_ROOM_TYPE

        # Preferencia de docente listado
        if block.get("possible_teachers"):
            if teacher["id"] in block["possible_teachers"]:
                score += abs(P_SOFT_PREF_TEACHER)
            else:
                score -= abs(P_SOFT_PREF_TEACHER)

        # Recompensa por docente de planta
        if teacher.get("tipo_vinculacion", "") == "planta":
            score += P_SOFT_PLANTA_BONUS

        # Coincidencia con especialidades del bloque
        block_specs = block.get("especialidades", [])
        if block_specs:
            overlap = set(block_specs) & set(teacher.get("especialidades", []))
            if overlap:
                score += P_SOFT_SPECIALTY_MATCH * len(overlap)
            else:
                score -= P_SOFT_SPECIALTY_MATCH

    # Penalizar bloques en el mismo día para una misma asignatura/grupo
    for key, days in subjgroup_days.items():
        if len(days) > 1:
            repeats = len(days) - len(set(days))
            if repeats > 0:
                score -= repeats * P_HARD_MULTI_SAME_DAY

    # Penalizar uso de varios docentes y bonificar consistencia
    for key, teachers_set in subjgroup_teachers.items():
        if len(teachers_set) > 1:
            # Penalización exponencial por cada docente adicional
            repeats = len(teachers_set) - 1
            score -= (repeats * P_HARD_MULTI_TEACHER_GROUP) * (2 ** repeats)  # Penalización exponencial
        else:
            # Mayor bonificación por mantener el mismo docente
            score += P_BONUS_SAME_TEACHER * 2

    # Penalizar choques de docentes
    for t_idx, slots in teacher_slots.items():
        for a in range(len(slots)):
            for b in range(a + 1, len(slots)):
                if slot_overlaps(slots[a], slots[b]):
                    score -= P_HARD_OVERLAP_TEACHER
    # Penalizar choques de aulas
    for r_idx, slots in room_slots.items():
        for a in range(len(slots)):
            for b in range(a + 1, len(slots)):
                if slot_overlaps(slots[a], slots[b]):
                    score -= P_HARD_OVERLAP_ROOM

    # Manejo de horas por docente según tipo de vinculación
    total_horas = sum(teacher_hours.values())
    docentes_activos = len(teacher_hours)
    if docentes_activos > 0:
        # Promedio calculado entre docentes activos
        horas_promedio = total_horas / docentes_activos
        
        for t_idx, hours in teacher_hours.items():
            limite = DOCENTES[t_idx]["limite_horas"]
            tipo = DOCENTES[t_idx].get("tipo_vinculacion", "")
            
            # Manejo específico por tipo de vinculación
            if tipo == "planta":
                target = min(TARGET_HOURS_PLANTA, limite)
                bonus_upper = limite
                # Penalizar si no alcanza el objetivo configurado
                if hours < target:
                    score -= (target - hours) * P_UNDER_HOURS_PLANTA
                # Bonificación extra si alcanza el objetivo
                elif target <= hours <= bonus_upper:
                    score += P_SOFT_PLANTA_BONUS * 2
                # Penalizar exceso
                elif hours > limite:
                    score -= (hours - limite) * P_HARD_TEACHER_HOURS * 2
                    
            elif tipo == "ocasional":
                target = min(TARGET_HOURS_OCASIONAL, limite)
                bonus_upper = min(limite, target + 1)
                # Penalizar si no alcanza su objetivo
                if hours < target:
                    score -= (target - hours) * P_UNDER_HOURS_OCASIONAL
                # Bonificación si alcanza el rango ideal
                elif target <= hours <= bonus_upper:
                    score += P_SOFT_PLANTA_BONUS
                # Penalizar exceso
                elif hours > limite:
                    score -= (hours - limite) * P_HARD_TEACHER_HOURS * 1.5
                    
            else:  # cátedra
                # Solo penalizar excesos significativos
                if hours > limite:
                    score -= (hours - limite) * P_HARD_TEACHER_HOURS
            
            # Penalizaciones generales por sobrecarga
            if hours > limite * HARD_LIMIT_FACTOR:
                score -= P_HARD_OVERLOAD * (hours - limite * HARD_LIMIT_FACTOR)
            if hours > limite * 2:
                score -= P_HARD_OVERLOAD * (hours - limite * 2)
            
            # Penalización suavizada por desbalance
            desviacion = abs(hours - horas_promedio)
            if tipo != "catedra" and horas_promedio > 0 and desviacion > horas_promedio * 0.5:
                score -= (desviacion - horas_promedio * 0.5) * P_HARD_UNBALANCED
        
        # Penalizar si se usan muy pocos docentes de planta/ocasionales
        min_docentes_core = max(3, len([d for d in DOCENTES if d.get("tipo_vinculacion") in ["planta", "ocasional"]]) // 2)
        docentes_core_activos = len([t_idx for t_idx in teacher_hours.keys() if DOCENTES[t_idx].get("tipo_vinculacion") in ["planta", "ocasional"]])
        if docentes_core_activos < min_docentes_core:
            score -= (min_docentes_core - docentes_core_activos) * P_HARD_UNBALANCED * 2

    # Penalización suave por huecos entre clases
    for t_idx, slots in teacher_slots.items():
        slots_by_day = defaultdict(list)
        for si in slots:
            s = SLOT_DEFINITIONS[si]
            slots_by_day[s["day_idx"]].append((s["start"], s["end"]))
        for intervals in slots_by_day.values():
            intervals.sort()
            for j in range(len(intervals) - 1):
                gap = intervals[j + 1][0] - intervals[j][1]
                if gap > 0:
                    # penalizar huecos (restar)
                    score -= P_SOFT_GAPS * gap

    return (score,)

# DEAP
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)
toolbox = base.Toolbox()
toolbox.register("individual", tools.initIterate, creator.Individual, individual_generator)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)
def cx_uniform_events(ind1, ind2, indpb=0.5):
    for i in range(len(ind1)):
        if random.random() < indpb:
            ind1[i], ind2[i] = ind2[i], ind1[i]
    return ind1, ind2
def mut_schedule(individual, indpb=0.2):
    # calcular horas actuales por docente en el individuo antes de mutar
    teacher_hours_now = defaultdict(int)
    for j, gene in enumerate(individual):
        teacher_hours_now[gene[2]] += BLOCKS[j]["duration"]

    for i in range(len(individual)):
        if random.random() < indpb:
            slot, room, teacher = individual[i]
            choice = random.choice(["slot", "room", "teacher"])
            if choice == "slot":
                duration = BLOCKS[i]["duration"]
                candidates = SLOT_INDICES_BY_DURATION[duration]
                individual[i] = (random.choice(candidates), room, teacher)
            elif choice == "room":
                # reescoger sala válida
                new_room = choose_room_for_block(BLOCKS[i])
                individual[i] = (slot, new_room, teacher)
            else:
                # intentar mantener el mismo docente que otros bloques del grupo
                block = BLOCKS[i]
                key = (block["subj_id"], block["group_id"])
                current_teacher = None
                
                # buscar docente ya asignado a este grupo
                for j, gene in enumerate(individual):
                    if j != i and BLOCKS[j]["subj_id"] == block["subj_id"] and BLOCKS[j]["group_id"] == block["group_id"]:
                        current_teacher = gene[2]
                        if is_teacher_available(current_teacher, slot):
                            individual[i] = (slot, room, current_teacher)
                            break
                
                # si no se encontró un docente previo o no está disponible
                if current_teacher is None or not is_teacher_available(current_teacher, slot):
                    # construir lista de candidatos priorizando docentes listados y menor carga
                    teachers = list(range(len(DOCENTES)))
                    if block.get("possible_teachers"):
                        listed_teachers = [doc_id_to_index[t] for t in block["possible_teachers"] if t in doc_id_to_index]
                        # mantener orden: listados primero
                        teachers = listed_teachers + [t for t in teachers if t not in listed_teachers]

                    # filtrar por disponibilidad
                    avail = [ti for ti in teachers if is_teacher_available(ti, slot)]
                    candidates = avail if avail else teachers

                    # filtrar por límite duro si es posible
                    feasible = [ti for ti in candidates if teacher_hours_now.get(ti, 0) + BLOCKS[i]["duration"] <= DOCENTES[ti]["limite_horas"] * HARD_LIMIT_FACTOR]
                    if feasible:
                        candidates = feasible

                    # elegir por menor carga actual
                    def teacher_priority_key(ti):
                        tipo = DOCENTES[ti].get("tipo_vinculacion", "")
                        ch = teacher_hours_now.get(ti, 0)
                        under_target = 1
                        target = None
                        if tipo == "planta":
                            target = TARGET_HOURS_PLANTA
                        elif tipo == "ocasional":
                            target = TARGET_HOURS_OCASIONAL
                        if target is not None and ch < target:
                            under_target = 0
                        is_planta = 0 if tipo == "planta" else 1
                        return (under_target, ch, is_planta)

                    candidates.sort(key=teacher_priority_key)
                    new_t = candidates[0]
                    # actualizar carga estimada local
                    teacher_hours_now[new_t] += BLOCKS[i]["duration"]
                    individual[i] = (slot, room, new_t)
    return (individual,)
toolbox.register("mate", cx_uniform_events, indpb=0.5)
toolbox.register("mutate", mut_schedule, indpb=0.2)
toolbox.register("select", tools.selTournament, tournsize=3)
toolbox.register("evaluate", evaluate_schedule)

# Export
def crear_carpeta_resultados():
    os.makedirs("resultados", exist_ok=True); return "resultados"

def pretty_event_repr(gene, block):
    slot_idx, room_idx, teacher_idx = gene
    day, label, start, end, duration = pretty_slot(slot_idx)
    room = AULAS[room_idx]
    teacher = DOCENTES[teacher_idx]
    return {
        "subject_id": block["subj_id"],
        "subject": block["subj_name"],
        "group": f"{block['group_id']}/{block['total_groups']}",
        "students": block["students"],
        "day": day,
        "time": label,
        "start": start,
        "end": end,
        "duration": duration,
        "room": room["id"],
        "room_capacity": room["capacity"],
        "room_type": room["type"],
        "teacher_id": teacher["id"],
        "teacher_name": teacher["name"],
        "tipo_aula": block["tipo_aula"]
    }

def export_schedule(individual, filename_json="horario_final.json", filename_csv="horario_final.csv"):
    crear_carpeta_resultados()
    filepath_json = os.path.join("resultados", filename_json)
    filepath_csv = os.path.join("resultados", filename_csv)

    schedule = defaultdict(list)
    rows = []
    for i, gene in enumerate(individual):
        block = BLOCKS[i]
        rep = pretty_event_repr(gene, block)
        key = f"{rep['day']} - {rep['time']}"
        schedule[key].append(rep)
        rows.append(rep)

    with open(filepath_json, "w", encoding="utf-8") as f:
        json.dump(schedule, f, ensure_ascii=False, indent=2)

    csv_fields = ["subject_id","subject","group","students","day","time","start","end","duration","room","room_capacity","room_type","teacher_id","teacher_name","tipo_aula"]
    with open(filepath_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def save_teacher_load(individual, filename_csv="teacher_load.csv", filename_json="teacher_load.json"):
    """Exporta horas y estadísticas por docente para el `individual` dado."""
    crear_carpeta_resultados()
    path_csv = os.path.join("resultados", filename_csv)
    path_json = os.path.join("resultados", filename_json)

    teacher_hours = defaultdict(int)
    teacher_classes = defaultdict(int)
    teacher_intervals = defaultdict(lambda: defaultdict(list))  # teacher -> day_idx -> list of (s,e)

    for i, gene in enumerate(individual):
        slot_idx, room_idx, teacher_idx = gene
        duration = BLOCKS[i]["duration"]
        slot = SLOT_DEFINITIONS[slot_idx]
        teacher_hours[teacher_idx] += duration
        teacher_classes[teacher_idx] += 1
        teacher_intervals[teacher_idx][slot["day_idx"]].append((slot["start"], slot["end"]))

    rows = []
    for t_idx, t in enumerate(DOCENTES):
        hours = teacher_hours.get(t_idx, 0)
        nclasses = teacher_classes.get(t_idx, 0)
        # calcular avg gap por docente
        day_gaps = 0.0; day_counts = 0
        for intervals in teacher_intervals[t_idx].values():
            intervals.sort()
            for j in range(len(intervals)-1):
                gap = max(0, intervals[j+1][0] - intervals[j][1])
                day_gaps += gap; day_counts += 1
        avg_gap = (day_gaps / day_counts) if day_counts else 0.0
        rows.append({
            "teacher_id": t["id"],
            "teacher_name": t.get("name",""),
            "horas_asignadas": hours,
            "n_clases": nclasses,
            "avg_gap_horas": round(avg_gap,2)
        })

    # guardar CSV
    fieldnames = ["teacher_id","teacher_name","horas_asignadas","n_clases","avg_gap_horas"]
    with open(path_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # guardar JSON
    with open(path_json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

def plot_teacher_schedules(individual, output_dir=None):
    """
    Genera un gráfico por docente mostrando sus bloques asignados a lo largo de la semana.
    Guarda los PNG en resultados/plots/horarios_docentes (por defecto).
    """
    try:
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"No se generaron gráficos por docente (matplotlib no disponible: {exc}).")
        return

    crear_carpeta_resultados()
    plots_root = os.path.join("resultados", "plots")
    os.makedirs(plots_root, exist_ok=True)
    if output_dir is None:
        output_dir = os.path.join(plots_root, "horarios_docentes")
    os.makedirs(output_dir, exist_ok=True)

    day_info = sorted({(s["day_idx"], s["day"]) for s in SLOT_DEFINITIONS}, key=lambda x: x[0])
    y_positions = [d[0] for d in day_info]
    y_labels = [d[1] for d in day_info]
    if not day_info:
        print("No hay definición de días para graficar horarios por docente.")
        return

    min_hour = min(s["start"] for s in SLOT_DEFINITIONS)
    max_hour = max(s["end"] for s in SLOT_DEFINITIONS)

    subject_names = sorted({block["subj_name"] for block in BLOCKS})
    cmap = plt.cm.get_cmap("tab20")
    palette = list(getattr(cmap, "colors", [])) or [cmap(i) for i in range(cmap.N)]
    subject_colors = {}
    for idx, name in enumerate(subject_names):
        subject_colors[name] = palette[idx % len(palette)]

    teacher_events = defaultdict(list)
    for i, gene in enumerate(individual):
        slot_idx, _, teacher_idx = gene
        event = pretty_event_repr(gene, BLOCKS[i])
        slot = SLOT_DEFINITIONS[slot_idx]
        event["day_idx"] = slot["day_idx"]
        event["teacher_idx"] = teacher_idx
        teacher_events[event["teacher_id"]].append(event)

    def sanitize_filename(value):
        return re.sub(r"[^A-Za-z0-9_-]+", "_", (value or "docente"))[:80]

    generated = 0
    for teacher_id, events in teacher_events.items():
        if not events:
            continue
        teacher_name = events[0].get("teacher_name") or teacher_id
        fig_height = max(4.5, 2.0 + 0.8 * len(day_info))
        fig, ax = plt.subplots(figsize=(14, fig_height))

        sorted_events = sorted(events, key=lambda e: (e["day_idx"], e["start"]))
        for ev in sorted_events:
            y = ev["day_idx"]
            color = subject_colors.get(ev["subject"], "#1f77b4")
            ax.barh(
                y,
                width=ev["duration"],
                left=ev["start"],
                height=0.9,
                align="center",
                color=color,
                edgecolor="#333333",
                linewidth=0.5,
            )
            label = f"{ev['subject']} ({ev['group']})"
            label = textwrap.fill(label, width=28)
            ax.text(
                ev["start"] + ev["duration"] / 2,
                y,
                label,
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                clip_on=True,
            )

        ax.set_yticks(y_positions)
        ax.set_yticklabels(y_labels)
        ax.set_ylim(min(y_positions) - 0.5, max(y_positions) + 0.5)
        ax.set_xlim(min_hour, max_hour)
        ax.set_xticks(range(min_hour, max_hour + 1, 1))
        ax.set_xlabel("Hora")
        ax.set_ylabel("Día")
        teacher_label = f"{teacher_id} - {teacher_name}" if teacher_id else teacher_name
        ax.set_title(f"Horario de {teacher_label}")
        ax.grid(axis="x", linestyle="--", alpha=0.3)
        fig.tight_layout()

        filename = sanitize_filename(teacher_id or teacher_name) + "_schedule.png"
        fig.savefig(os.path.join(output_dir, filename), dpi=150)
        plt.close(fig)
        generated += 1

    if generated:
        print(f"Horarios de docentes exportados en '{output_dir}' ({generated} archivos).")
    else:
        print("No hubo asignaciones para graficar horarios por docente.")

def save_hof(hof):
    crear_carpeta_resultados()
    path = os.path.join("resultados", "hall_of_fame.json")
    hof_data = []
    for ind in hof:
        hof_data.append({
            "fitness": ind.fitness.values[0],
            "genes": ind,
            "readable": [pretty_event_repr(g, BLOCKS[i]) for i, g in enumerate(ind)]
        })
    with open(path, "w", encoding="utf-8") as f:
        json.dump(hof_data, f, ensure_ascii=False, indent=2)

def repair_individual_consistent_teachers(individual):
    """Reparador estricto: para cada (subj_id, group_id) fuerza la unificación del docente.
    - Si ya todos los bloques tienen el mismo docente, no hace nada.
    - Si hay varios, elige el docente más adecuado según estos criterios:
      1. Docente listado que esté disponible en todos los slots y no exceda límite
      2. Docente actual más frecuente que esté disponible en todos los slots
      3. Docente menos cargado que esté disponible en todos los slots
      4. Como último recurso, el docente menos cargado aunque no esté disponible
    Modifica el individuo in-place y lo retorna.
    """
    # índices por grupo
    group_indices = defaultdict(list)
    for i, gene in enumerate(individual):
        block = BLOCKS[i]
        key = (block["subj_id"], block["group_id"])
        group_indices[key].append(i)

    # carga estimada local
    teacher_hours = defaultdict(int)
    for i, gene in enumerate(individual):
        teacher_hours[gene[2]] += BLOCKS[i]["duration"]

    for key, indices in group_indices.items():
        teachers = [individual[i][2] for i in indices]
        if len(set(teachers)) <= 1:
            continue

        # preferir el docente más frecuente que sea disponible en todos los slots
        from collections import Counter
        cnt = Counter(teachers)
        selected = None
        for t_idx, _ in cnt.most_common():
            ok = True
            for i in indices:
                slot_idx = individual[i][0]
                if not is_teacher_available(t_idx, slot_idx):
                    ok = False; break
            if ok:
                selected = t_idx; break

        # si no hay candidato frecuente válido, buscar entre posibles del bloque
        if selected is None:
            first_block = BLOCKS[indices[0]]
            possible = first_block.get("possible_teachers", []) or []
            poss_idx = [doc_id_to_index[t] for t in possible if t in doc_id_to_index]
            candidates = poss_idx if poss_idx else list(range(len(DOCENTES)))
            
            # ordenar candidatos por prioridad
            def candidate_priority(ti):
                tipo = DOCENTES[ti].get("tipo_vinculacion", "")
                hours = teacher_hours.get(ti, 0)
                limite = DOCENTES[ti]["limite_horas"]
                # priorizar docentes que no excederán su límite
                would_exceed = hours + sum(BLOCKS[i]["duration"] for i in indices) > limite
                # prioridad a planta/ocasional que no excedan límite
                is_core = tipo in ["planta", "ocasional"]
                return (would_exceed, not is_core, hours)
            
            candidates.sort(key=candidate_priority)
            
            # buscar primero entre docentes que estén disponibles en todos los slots
            for ti in candidates:
                ok = True
                for i in indices:
                    if not is_teacher_available(ti, individual[i][0]):
                        ok = False; break
                if ok:
                    selected = ti; break

        # fallback: elegir el menos cargado entre candidatos
        if selected is None:
            candidates = poss_idx if poss_idx else list(range(len(DOCENTES)))
            candidates.sort(key=lambda ti: teacher_hours.get(ti, 0))
            selected = candidates[0]

        # aplicar la selección a todos los índices del grupo
        for i in indices:
            old = individual[i][2]
            if old != selected:
                teacher_hours[old] -= BLOCKS[i]["duration"]
                teacher_hours[selected] += BLOCKS[i]["duration"]
                individual[i] = (individual[i][0], individual[i][1], selected)

    return individual


def rebalance_overloaded_teachers(individual):
    """Intentar redistribuir bloques de docentes que exceden su `limite_horas` al menos posible.
    Modifica el individuo in-place y retorna True si se hicieron cambios.
    """
    changed = False
    # calcular horas por docente
    teacher_hours = defaultdict(int)
    assignments_by_teacher = defaultdict(list)
    for i, gene in enumerate(individual):
        slot_idx, room_idx, teacher_idx = gene
        dur = BLOCKS[i]["duration"]
        teacher_hours[teacher_idx] += dur
        assignments_by_teacher[teacher_idx].append(i)

    # lista de docentes sobrecargados ordenada por exceso descendente
    overloaded = []
    for t_idx, hours in teacher_hours.items():
        limite = DOCENTES[t_idx]["limite_horas"] * HARD_LIMIT_FACTOR
        if hours > limite:
            overloaded.append((t_idx, hours - limite))
    overloaded.sort(key=lambda x: x[1], reverse=True)

    for t_idx, excess in overloaded:
        # intentar liberar horas moviendo algunas asignaciones
        # ordenar las asignaciones por duración descendente para mover bloques grandes primero
        indices = sorted(assignments_by_teacher[t_idx], key=lambda ii: BLOCKS[ii]["duration"], reverse=True)
        for i in indices:
            slot_idx, room_idx, old_t = individual[i]
            dur = BLOCKS[i]["duration"]
            # buscar candidato receptor
            possible = BLOCKS[i].get("possible_teachers", []) or []
            candidates = [doc_id_to_index[x] for x in possible if x in doc_id_to_index]
            if not candidates:
                candidates = [ti for ti in range(len(DOCENTES)) if ti != t_idx]
            # filtrar por disponibilidad y por no exceder límite
            receivers = [ti for ti in candidates if is_teacher_available(ti, slot_idx) and (teacher_hours[ti] + dur) <= DOCENTES[ti]["limite_horas"] * HARD_LIMIT_FACTOR]
            # ordenar por menor carga
            receivers.sort(key=lambda ti: teacher_hours.get(ti, 0))
            if receivers:
                recv = receivers[0]
                # reasignar
                individual[i] = (slot_idx, room_idx, recv)
                teacher_hours[t_idx] -= dur
                teacher_hours[recv] += dur
                changed = True
                # si ya no está sobrecargado, romper
                limite = DOCENTES[t_idx]["limite_horas"] * HARD_LIMIT_FACTOR
                if teacher_hours[t_idx] <= limite:
                    break

    return changed


def promote_planta_hours(individual, min_hours=TARGET_HOURS_PLANTA):
    """Reasignar bloques desde docentes no planta hacia planta hasta alcanzar el mínimo requerido."""
    if min_hours <= 0:
        return False

    teacher_hours = defaultdict(int)
    assignments_by_teacher = defaultdict(list)
    for i, gene in enumerate(individual):
        slot_idx, room_idx, teacher_idx = gene
        dur = BLOCKS[i]["duration"]
        teacher_hours[teacher_idx] += dur
        assignments_by_teacher[teacher_idx].append(i)

    planta_indices = [ti for ti, doc in enumerate(DOCENTES) if doc.get("tipo_vinculacion") == "planta"]
    if not planta_indices:
        return False

    donors = [
        ti for ti in assignments_by_teacher.keys()
        if DOCENTES[ti].get("tipo_vinculacion") != "planta"
    ]
    if not donors:
        return False

    changed = False
    planta_indices.sort(key=lambda ti: teacher_hours.get(ti, 0))

    for t_idx in planta_indices:
        while teacher_hours.get(t_idx, 0) < min_hours:
            moved = False
            # siempre tomar al donante con mayor carga actual
            donor_candidates = sorted(donors, key=lambda ti: teacher_hours.get(ti, 0), reverse=True)
            for donor in donor_candidates:
                donor_assignments = assignments_by_teacher.get(donor, [])
                donor_assignments.sort(key=lambda ii: BLOCKS[ii]["duration"], reverse=True)
                for assign_idx in list(donor_assignments):
                    slot_idx, room_idx, _ = individual[assign_idx]
                    block = BLOCKS[assign_idx]
                    duration = block["duration"]
                    if block.get("possible_teachers"):
                        teacher_id = DOCENTES[t_idx]["id"]
                        if teacher_id not in block["possible_teachers"]:
                            continue
                    if not is_teacher_available(t_idx, slot_idx):
                        continue
                    limite = DOCENTES[t_idx]["limite_horas"] * HARD_LIMIT_FACTOR
                    if teacher_hours.get(t_idx, 0) + duration > limite:
                        continue

                    donor_tipo = DOCENTES[donor].get("tipo_vinculacion", "")
                    donor_target = 0
                    if donor_tipo == "planta":
                        donor_target = TARGET_HOURS_PLANTA
                    elif donor_tipo == "ocasional":
                        donor_target = TARGET_HOURS_OCASIONAL
                    if donor_target and teacher_hours.get(donor, 0) - duration < donor_target:
                        continue

                    individual[assign_idx] = (slot_idx, room_idx, t_idx)
                    assignments_by_teacher[donor].remove(assign_idx)
                    assignments_by_teacher[t_idx].append(assign_idx)
                    teacher_hours[t_idx] = teacher_hours.get(t_idx, 0) + duration
                    teacher_hours[donor] = teacher_hours.get(donor, 0) - duration
                    changed = True
                    moved = True
                    break
                if moved:
                    break
            if not moved:
                break

    return changed

def save_evolution_log(logbook):
    crear_carpeta_resultados()
    path = os.path.join("resultados", "evolucion.csv")
    gen = logbook.select("gen")
    avgs = logbook.select("avg")
    maxs = logbook.select("max")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["generacion","avg","max"])
        writer.writeheader()
        for g, a, m in zip(gen, avgs, maxs):
            writer.writerow({"generacion": g, "avg": a, "max": m})

def save_stats(best, logbook):
    crear_carpeta_resultados()
    path = os.path.join("resultados", "estadisticas.txt")
    total_classes = len(best)
    docentes_used = len(set(pretty_event_repr(g, BLOCKS[i])["teacher_id"] for i, g in enumerate(best)))
    aulas_used = len(set(pretty_event_repr(g, BLOCKS[i])["room"] for i, g in enumerate(best)))
    days_used = len(set(pretty_event_repr(g, BLOCKS[i])["day"] for i, g in enumerate(best)))

    # gaps promedio
    gaps_total = 0
    teachers = set(pretty_event_repr(g, BLOCKS[i])["teacher_id"] for i, g in enumerate(best))
    for tid in teachers:
        intervals = []
        for i, g in enumerate(best):
            rep = pretty_event_repr(g, BLOCKS[i])
            if rep["teacher_id"] == tid:
                intervals.append((rep["day"], rep["start"], rep["end"]))
        day_gaps = 0; counts = 0
        grouped = defaultdict(list)
        for d, s, e in intervals:
            grouped[d].append((s, e))
        for ints in grouped.values():
            ints.sort()
            for j in range(len(ints)-1):
                gap = max(0, ints[j+1][0] - ints[j][1])
                day_gaps += gap; counts += 1
        if counts:
            gaps_total += day_gaps / counts
    avg_gaps = gaps_total / max(1, len(teachers))

    with open(path, "w", encoding="utf-8") as f:
        f.write(f"Total clases programadas: {total_classes}\n")
        f.write(f"Docentes distintos asignados: {docentes_used}\n")
        f.write(f"Aulas distintas usadas: {aulas_used}\n")
        f.write(f"Días activos: {days_used}\n")
        f.write(f"Promedio huecos docentes (horas): {avg_gaps:.2f}\n")

class LogBookLite:
    def __init__(self):
        self._records = []
    def record(self, **kwargs):
        self._records.append(kwargs)
    def select(self, key):
        return [r[key] for r in self._records]

def run_ga(pop_size=1000, ngen=500, cxpb=0.8, mutpb=0.4, seed=42):
    random.seed(seed)
    os.makedirs("resultados", exist_ok=True)

    pop = toolbox.population(n=pop_size)
    hof = tools.HallOfFame(10)

    stats = tools.Statistics(lambda ind: ind.fitness.values[0])
    stats.register("avg", lambda fits: sum(fits)/len(fits))
    stats.register("min", min)
    stats.register("max", max)
    stats.register("std", lambda fits: np.std(fits) if len(fits)>1 else 0)

    # evaluar inicial
    fitnesses = list(map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    logbook = LogBookLite()

    for g in range(ngen):
        offspring = tools.selTournament(pop, len(pop), tournsize=3)
        offspring = list(map(toolbox.clone, offspring))

        # cruce
        for c1, c2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < cxpb:
                toolbox.mate(c1, c2)
                del c1.fitness.values; del c2.fitness.values

        # mutación
        for m in offspring:
            if random.random() < mutpb:
                toolbox.mutate(m); del m.fitness.values

        # Reparar consistencia docente por grupo (suavemente) en toda la descendencia
        for m in offspring:
            repair_individual_consistent_teachers(m)
        # Rebalancear sobrecargas tras reparación
        for m in offspring:
            rebalance_overloaded_teachers(m)
        # Promover horas mínimas para docentes de planta
        for m in offspring:
            promote_planta_hours(m)
        # Reparador duro de choques docente/aula
        for m in offspring:
            repair_no_conflicts(m)

        # reevaluar inválidos
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        fitvals = map(toolbox.evaluate, invalid)
        for ind, fit in zip(invalid, fitvals):
            ind.fitness.values = fit

        pop[:] = offspring
        hof.update(pop)

        rec = {
            "gen": g,
            "avg": stats.compile(pop)["avg"],
            "min": stats.compile(pop)["min"],
            "max": stats.compile(pop)["max"]
        }
        logbook.record(**rec)
        if g % 10 == 0 or g == ngen - 1:
            print(f"Gen {g:4d} | Max: {rec['max']:10.1f} | Avg: {rec['avg']:10.1f} | Min: {rec['min']:10.1f}")

    best = hof[0]
    export_schedule(best)
    # exportar carga por docente para el mejor individuo
    save_teacher_load(best)
    plot_teacher_schedules(best)
    save_hof(hof)
    save_evolution_log(logbook)
    save_stats(best, logbook)
    print("✅ Resultados guardados en 'resultados/'")
    return best, hof, logbook

if __name__ == "__main__":
    print("🚀 Iniciando DEAP GA con verificación de disponibilidad docente...")
    run_ga()
