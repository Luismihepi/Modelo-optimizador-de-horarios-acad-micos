Optimización Inteligente de Horarios Académicos (Ingeniería de Sistemas, Unipamplona)
Descripción General
La planificación de horarios académicos en el programa de Ingeniería de Sistemas de la Universidad de Pamplona es un proceso complejo que debe considerar múltiples restricciones (disponibilidad de docentes, aulas, asignaturas, etc.) y evitar conflictos en la asignación de clases. Tradicionalmente, este proceso se realiza de forma manual o con herramientas básicas, lo cual puede generar ineficiencias y errores en la programación.
Este proyecto propone el desarrollo de un sistema de optimización inteligente de horarios académicos utilizando algoritmos genéticos, con el propósito de automatizar la generación de horarios óptimos, minimizando los conflictos (solapamientos) y mejorando la distribución de los recursos académicos. Para lograrlo, se diseñó un modelo computacional en Python empleando la librería DEAP (Distributed Evolutionary Algorithms in Python), que permite implementar un algoritmo genético capaz de producir horarios factibles de alta calidad respetando las restricciones del programa. En resumen, la solución busca optimizar la planificación académica, reduciendo el tiempo y esfuerzo dedicados a construir horarios, a la vez que mejora la calidad de la asignación (clases sin choques, aulas adecuadas, cargas equilibradas). Esto sienta las bases para futuras aplicaciones de inteligencia artificial en educación, mostrando cómo técnicas evolutivas pueden mejorar la gestión académica institucional.
Características Principales del Modelo
•	Algoritmo Genético Personalizado: El núcleo del sistema es un algoritmo genético (GA) desarrollado con DEAP, configurado para maximizar una función de fitness que combina factibilidad y calidad del horario. Cada posible horario (individuo) se representa como un cromosoma: una lista de genes, donde cada gen es una tupla que codifica una asignación de clase (por ejemplo, (slot, aula, docente) para un bloque de curso).
•	Restricciones Duras y Blandas: El modelo considera restricciones duras (inviolables) y blandas (deseables). Entre las restricciones duras se incluyen: que ningún docente tenga dos clases a la misma hora, que un aula no sea asignada a más de una clase simultáneamente, que la capacidad y tipo de aula sean adecuados para el curso, y que a cada asignatura se le programe exactamente el número de horas semanales requeridas. Las restricciones blandas abarcan criterios como minimizar los huecos (periodos libres) en el horario de cada profesor y balancear la distribución de clases de cada grupo a lo largo de la semana (evitando cargas muy desequilibradas entre días). El algoritmo penaliza fuertemente las violaciones a restricciones duras y aplica penalizaciones moderadas o bonificaciones para fomentar el cumplimiento de las blandas, buscando un horario óptimo en ambos aspectos.
•	Inicialización y Población: La generación inicial de horarios es aleatoria pero guiada por reglas básicas. Por ejemplo, se asigna a cada clase un docente válido aleatorio, un día y franja horaria al azar, y un aula aleatoria con capacidad suficiente, evitando solo conflictos directos obvios (como no repetir exactamente el mismo docente y aula en la misma franja). Esta población inicial ofrece diversidad de soluciones candidatas que luego serán evolucionadas por el GA.
•	Operadores Genéticos y Reparación: Se implementaron operadores genéticos adaptados al problema de horarios. La selección de padres es por torneo (tamaño 3) para favorecer los individuos con mejor fitness. El cruce (crossover) es uniforme por posición: intercambia genes (clases) entre dos horarios con cierta probabilidad, generando nuevos individuos mezcla de ambos horarios. La mutación altera un gen (clase) escogiendo aleatoriamente un nuevo horario (slot) y/o un nuevo docente o aula compatibles para esa clase, introduciendo variaciones adicionales. Después de cada generación, el modelo aplica operadores de reparación para asegurar factibilidad y mejorar la calidad de las soluciones. Estos reparadores corrigen, por ejemplo, solapamientos residuales de última hora, unifican un mismo docente para todos los bloques de una asignatura/grupo (si por cruce quedaron divididos) y redistribuyen clases desde docentes sobrecargados hacia otros con disponibilidad, priorizando también que los profesores de planta alcancen su carga objetivo mínima. Gracias a estos mecanismos, incluso si cruce o mutación generan un horario sub-óptimo, el sistema lo ajusta para mantener soluciones válidas y diversificadas en cada generación.
•	Criterio de Parada y Mejores Soluciones: El algoritmo evoluciona la población por un número fijo de generaciones (configurable, típicamente del orden de 100 a 400 iteraciones según pruebas). Al finalizar, se conserva el mejor individuo encontrado (Hall of Fame) y se detiene el proceso. El mejor horario resultante es aquel con mayor fitness, es decir, el que cumple todas las restricciones duras y obtiene la puntuación más alta considerando las preferencias (huecos mínimos, equilibrio, etc.). El sistema registra también los mejores individuos de cada generación y las estadísticas de evolución.
•	Salidas y Reportes Automáticos: Al terminar la optimización, el sistema genera automáticamente múltiples reportes con los resultados. Estos incluyen: el horario final optimizado en formato CSV (y JSON) con el detalle de todas las clases programadas; un resumen de carga docente (CSV/JSON) indicando cuántas horas y clases tiene asignadas cada profesor en el horario final; un registro de la evolución del fitness por generación en CSV (con valores mínimo, promedio y máximo de cada generación) para analizar la convergencia; un archivo JSON con el Hall of Fame de los mejores horarios encontrados; y un informe de estadísticas globales (por ejemplo, total de clases programadas, número de docentes y aulas utilizados, porcentaje de uso de recursos, promedio de huecos, etc.). Estas salidas permiten validar y visualizar fácilmente la solución generada.
Requisitos del Sistema e Instalación
Requisitos del sistema: Para ejecutar este proyecto se requiere Python 3 (se probó con versiones recientes de Python 3.x) y la instalación de la librería DEAP (versión 2.0.0 o superior). DEAP es fundamental, ya que proporciona las clases y métodos para implementar el algoritmo evolutivo de manera eficiente. Adicionalmente, se utilizan algunas bibliotecas estándar de Python: por ejemplo, NumPy para cálculos auxiliares y generación aleatoria eficiente, así como módulos integrados como random, itertools, collections, y las bibliotecas estándar csv y json para manejo de datos y persistencia de resultados. Es recomendable también contar con un entorno virtual de Python para aislar las dependencias.
Instrucciones de instalación:
1.	Clonar o descargar el repositorio del proyecto en su máquina local. El proyecto consta principalmente de código Python y archivos de datos de configuración.
2.	Instalar las dependencias requeridas. Si utiliza pip, puede instalar DEAP y otras librerías necesarias ejecutando:

 	pip install deap numpy
 	(Puede instalar otras dependencias si se especifican en un archivo requirements.txt o documentación adicional. En general, DEAP es la dependencia principal no estándar.)
Con Python y las bibliotecas instaladas, estará listo para ejecutar el modelo.
Estructura del Proyecto
La estructura principal de archivos y directorios del proyecto es la siguiente:
├── datos_sistema.json        <- Archivo de **entrada** con los datos del sistema (docentes, asignaturas, aulas, etc.)[7].
├── motor.py                  <- Script **principal** que implementa el algoritmo genético: carga datos, configura DEAP, evalúa fitness, ejecuta cruce/mutación y genera la solución[8].
├── plots_results.py          <- Script opcional para generar visualizaciones (gráficas de la evolución del fitness, etc.) a partir de los archivos de resultados.
├── resultados/               <- Carpeta que se llena con los **archivos de salida** generados tras la ejecución:
│   ├── horario_final.csv          <- Horario optimizado final en formato CSV (cada fila es una clase asignada).
│   ├── horario_final.json         <- Horario final en formato JSON estructurado (misma información que el CSV).
│   ├── teacher_load.csv           <- Resumen de carga horaria por docente (horas asignadas, número de clases, huecos promedio).
│   ├── teacher_load.json          <- Versión JSON de la carga por docente.
│   ├── evolucion.csv              <- Registro de la evolución del algoritmo por generación (fitness promedio y máximo en cada generación).
│   ├── hof.json                   <- Hall of Fame con los mejores horarios encontrados (incluye genes/fitness de top 10 individuos).
│   └── estadisticas.txt           <- Indicadores globales del horario final (número total de clases, docentes y aulas utilizados, distribución de horarios, etc.).
└── README.md                 <- Documentación del proyecto (este archivo README).
Archivo de datos datos_sistema.json: Este JSON contiene la información necesaria para construir el horario. Incluye típicamente listas de docentes (con sus identificadores, nombre, especialidad, disponibilidad horaria y límite de horas semanales), aulas (con identificador, capacidad, tipo de aula – teórica, práctica o mixta), y asignaturas (con código, nombre, número de horas semanales, número de estudiantes, tipo de aula requerida, grupo o grupos existentes, profesores posibles/asignables, etc.), además de una sección de configuración general de parámetros (por ejemplo, meta de horas para profesores de planta, cantidad de generaciones a ejecutar, penalizaciones/pesos para las restricciones blandas, etc.). Este archivo debe ser editado o generado previamente con los datos reales del semestre a programar antes de ejecutar el algoritmo.
Script principal motor.py: Es el corazón del sistema. Al ejecutarlo, este módulo realiza las siguientes tareas principales:
•	Lee y carga los datos desde datos_sistema.json, normalizando la información (por ejemplo, convirtiendo etiquetas de días a índices, unificando formatos de disponibilidad, etc.).
•	Construye las estructuras internas de representación (slots de horario disponibles, bloques de clases a programar por asignatura, etc.).
•	Configura el algoritmo genético usando DEAP: define cómo se representa el individuo (cromosoma), la función de fitness que calcula la puntuación de cada horario, y registra los operadores genéticos (selección, cruce, mutación) y reparadores.
•	Genera la población inicial de horarios aleatorios y luego entra en el bucle evolutivo, iterando generación tras generación. En cada generación, evalúa todos los individuos (horarios) calculando su fitness, selecciona los mejores para reproducirse, aplica cruce y mutación para producir nuevos horarios, repara si es necesario y forma la siguiente generación.
•	Lleva un registro de estadísticas de cada generación (fitness promedio, mejor fitness, etc.) en un logbook interno.
•	Tras completar el número de generaciones estipulado, identifica el mejor individuo (horario óptimo) obtenido y procede a exportar los resultados en los archivos mencionados (horario_final, teacher_load, etc.). Esta exportación se realiza mediante funciones internas, e.g., export_schedule() para el CSV del horario, save_teacher_load() para la carga docente, save_hof() para el hall of fame, save_evolution_log() para la evolución, entre otras.
Script plots_results.py: Este componente (opcional) toma los datos producidos en resultados/ (por ejemplo, evolucion.csv) y genera visualizaciones gráficas. Por ejemplo, puede crear una gráfica de línea del fitness a lo largo de las generaciones (mostrando cómo el fitness promedio y máximo fueron mejorando), o gráficos de barras de la carga horaria por docente, etc. Esto es útil para analizar de forma visual el comportamiento del algoritmo genético y la solución obtenida. Se usa después de haber corrido motor.py.
Instrucciones de Uso
A continuación se describen los pasos para utilizar el optimizador de horarios una vez instalado el entorno:
1.	Preparar los datos de entrada: Edite o genere el archivo datos_sistema.json con la información actualizada de docentes, asignaturas y aulas. Asegúrese de incluir todos los campos necesarios. Por ejemplo, cada docente debe tener su disponibilidad horaria (días/horas en que puede dictar clase), número máximo de horas semanales, especialidad, etc.; las asignaturas deben indicar cuántas horas semanales requieren, a qué grupo(s) pertenecen, qué tipo de aula necesitan (teórica/práctica) y qué docentes son elegibles para dictarlas; las aulas deben listar su capacidad y tipo. Este paso es crucial, pues la calidad de la solución dependerá de la fidelidad de estos datos a la realidad institucional.
2.	Ejecutar el algoritmo genético: Desde una terminal o consola ubicada en el directorio del proyecto, ejecute el script principal con Python:

 	python motor.py
 	Esto iniciará la carga de datos y la ejecución del algoritmo genético. Dependiendo de los parámetros configurados (tamaño de población, número de generaciones, etc.), el proceso podría tardar desde unos segundos hasta varios minutos. Durante la ejecución, el programa puede imprimir en pantalla información sobre el progreso (por ejemplo, la generación actual y el mejor fitness encontrado hasta ese punto).
3.	Monitorear la ejecución (opcional): Mientras el GA corre, puede observar en la consola los mensajes o logs (si fueron habilitados) para ver si el algoritmo está convergiendo. No obstante, el resultado final solo se obtendrá al completar todas las generaciones o alcanzar un criterio de parada definido.
4.	Verificar los resultados exportados: Una vez finalizado el proceso, el programa indicará que ha exportado los resultados. Puede entonces revisar el directorio resultados/ donde encontrará los archivos CSV/JSON generados. En particular, abra resultados/horario_final.csv para examinar el horario propuesto. Cada fila de este CSV representa una clase programada en el horario óptimo. Asimismo, puede revisar teacher_load.csv para ver un resumen de cuántas horas se asignó a cada docente y cuántos huecos quedaron en su agenda. El archivo estadisticas.txt brindará un panorama general del uso de recursos (por ejemplo, cuántas aulas diferentes se usaron, cuántos docentes quedaron sin carga, etc.).
5.	Visualizar métricas (opcional): Para analizar el desempeño del algoritmo, ejecute el script de gráficos:

 	python plots_results.py
 	Este script leerá, por ejemplo, el archivo resultados/evolucion.csv y generará una gráfica de la evolución del fitness generacional (en formato de imagen o ventana interactiva). Podrá ver cómo partió el fitness promedio de la población inicial y cómo fue mejorando hasta la última generación. También puede generar otras visualizaciones, según lo implementado, como histogramas de distribución de cargas docentes, etc.
6.	Ajustar parámetros y re-ejecutar (iterativo): Si el resultado obtenido no es satisfactorio o desea experimentar con diferentes condiciones, puede ajustar los parámetros del algoritmo genético y volver a correr el modelo. Por ejemplo, puede cambiar el tamaño de población, el número de generaciones, o los pesos de penalización de ciertas restricciones (ya sea editando el JSON de configuración si existe, o modificando constantes en el código). Tras cada ajuste, vuelva a ejecutar motor.py para generar un nuevo horario. En la carpeta de resultados, podría optar por renombrar los archivos anteriores o moverlos, para que no se sobreescriban, si desea comparar diferentes corridas.
7.	Interpretar y utilizar el horario generado: Finalmente, con el horario óptimo en mano (en CSV o JSON), puede presentarlo en el formato requerido para la coordinación académica (por ejemplo, convertirlo a una tabla de horarios por semestre, o ingresarlo a un sistema institucional si corresponde). Los beneficios esperados son que este horario ya cumple todas las restricciones definidas y optimiza la experiencia académica (sin choques, con mínimas horas libres perdidas, uso adecuado de aulas, etc.), por lo que debería reducir la necesidad de ajustes manuales posteriores.
Nota: Es importante siempre verificar manualmente el horario sugerido, al menos en sus primeras ejecuciones, para asegurar que todos los datos de entrada eran correctos y que el resultado es coherente. Ante cualquier inconsistencia, se recomienda revisar los datos de entrada o la configuración de penalizaciones, ya que el modelo busca optimizar según lo que se le proporciona.
Ejemplo de Entrada/Salida
A continuación se ilustra un ejemplo simplificado de cómo se representan los datos de entrada y qué tipo de salida produce el sistema.
Ejemplo de formato de entrada (datos_sistema.json):
{
  "docentes": [
    {
      "id": "PROF01",
      "nombre": "Dr. Juan Pérez",
      "especialidades": ["bases_de_datos", "ingenieria_software"],
      "limite_horas_semanales": 16,
      "disponibilidad": {
        "lunes": ["08:00-10:00", "10:00-12:00", "14:00-16:00"],
        "martes": ["08:00-10:00", "10:00-12:00"],
        "...": ["..."] 
      }
    },
    // ... otros docentes ...
  ],
  "aulas": [
    { "id": "A-101", "capacidad": 40, "tipo": "teorica" },
    { "id": "LAB-202", "capacidad": 25, "tipo": "practica" }
    // ... otras aulas ...
  ],
  "asignaturas": [
    {
      "id": "IS301",
      "nombre": "Bases de Datos",
      "horas_semanales": 4,
      "estudiantes": 35,
      "tipo_aula": "teorica",
      "grupo": "301",
      "docentes_posibles": ["PROF01", "PROF02"]
    },
    {
      "id": "IS302L",
      "nombre": "Laboratorio de Bases de Datos",
      "horas_semanales": 2,
      "estudiantes": 35,
      "tipo_aula": "practica",
      "grupo": "301",
      "docentes_posibles": ["PROF01", "PROF03"]
    }
    // ... otras asignaturas ...
  ],
  "config": {
    "TARGET_HOURS_PLANTA": 12,
    "TARGET_HOURS_OCASIONAL": 6,
    "GENERACIONES": 200,
    "POBLACION": 100,
    "PESO_HUECOS": 1,
    "PESO_BALANCE": 1,
    "PESO_CHOQUE": 1000
    // ... otros parámetros de penalización/peso ...
  }
}
En el ejemplo anterior, el docente Dr. Juan Pérez (PROF01) está disponible ciertos bloques los lunes y martes, hay dos aulas (un salón teórico y un laboratorio), y se muestran dos asignaturas: una teórica de 4 horas semanales y su respectivo laboratorio de 2 horas semanales, ambas para el mismo grupo 301. La configuración indica algunos parámetros como la carga objetivo de profesores de planta y ocasionales, número de generaciones, tamaño de población y pesos de penalización para criterios (estos parámetros afectarían la optimización, p. ej., PESO_CHOQUE muy alto penaliza fuertemente cualquier choque de horarios). En un caso real, este JSON contendría todos los docentes, aulas y asignaturas del semestre a programar.
Ejemplo de salida (resultados/horario_final.csv):
Asignatura,Grupo,Estudiantes,Día,Franja Horaria,Aula (capacidad,tipo),Docente,Modalidad
Bases de Datos,301,35,Lunes,08:00-10:00,A-101 (40,teorica),Dr. Juan Pérez,Teórica
Laboratorio de Bases de Datos,301,35,Lunes,10:00-12:00,LAB-202 (25,practica),Dr. Juan Pérez,Práctica
... (resto de asignaciones del horario óptimo) ...
Cada fila en el CSV de salida representa una clase asignada en el horario. En este ejemplo ficticio, la asignatura "Bases de Datos" del grupo 301 (35 estudiantes) fue programada el Lunes de 08:00 a 10:00 en el aula A-101 (capacidad 40, tipo teórica) con el Dr. Juan Pérez como docente, y la sesión práctica ("Laboratorio de Bases de Datos") quedó a continuación, el mismo Lunes de 10:00 a 12:00 en el LAB-202 (laboratorio de capacidad 25). Obsérvese que el algoritmo logró asignar el mismo docente para la materia teórica y su laboratorio consecutivo, evitando cambiar de profesor entre teoría y práctica, lo cual suele ser deseable. Además, no hay conflicto de aulas ni docentes en esas franjas, y probablemente el resto del archivo listará las demás clases de otros cursos distribuidas en la semana. Este horario final cumple las restricciones duras (por construcción) y ha intentado minimizar los huecos: en el ejemplo, el profesor Juan Pérez tiene sus 4 horas seguidas el lunes, sin espacios intermedios vacíos, lo que es ideal.
El archivo teacher_load.csv correspondiente mostraría, por ejemplo, que el Dr. Juan Pérez tiene 6 horas asignadas en total (4h de teoría + 2h de laboratorio) y quizás 0 horas de hueco promedio (ya que sus clases quedaron contiguas ese día). Mientras tanto, estadisticas.txt podría indicar que se programaron todas las clases requeridas, que se usaron 2 aulas diferentes, X docentes en total, Y días de la semana efectivos, etc., dependiendo de la totalidad de los datos.
Estos ejemplos ilustran cómo los datos de entrada se traducen en un horario final. Por supuesto, en un escenario real con decenas de asignaturas y docentes, el algoritmo ubicará cada clase en algún día y franja disponible, respetando las disponibilidades y tratando de agrupar inteligentemente las clases para reducir tiempos muertos.
Resultados Esperados y Métricas de Validación
El objetivo fundamental del modelo es obtener un horario factible (que respete todas las restricciones duras) y de alta calidad (óptimo en cuanto a las preferencias blandas). En términos cualitativos, se espera un horario sin solapamientos — es decir, ningún docente ni aula ocupados en más de una clase a la misma hora, y cada asignatura recibiendo todas sus horas requeridas —, con huecos mínimos en las agendas de los profesores, y una carga docente equilibrada a lo largo de la semana. La pregunta de investigación que motivó este proyecto planteaba precisamente si un algoritmo genético podía lograr horarios “libres de solapamientos, con huecos mínimos y carga docente equilibrada” para el programa de Ingeniería de Sistemas.
Para comprobar que estos objetivos se cumplen, el sistema realiza una validación cuantitativa mediante varias métricas registradas en los resultados:
•	Factibilidad: Número de choques de horario de docente o aula (debe ser 0 en la solución final) y violaciones de capacidad o tipo de aula (también 0 si el horario es válido). Asimismo, se verifica el cumplimiento de la carga horaria de cada asignatura (todas las materias deben aparecer con el número exacto de clases que necesitan). Estas condiciones garantizan que el horario es implementable sin conflictos.
•	Calidad: Promedio de horas de hueco por docente (se busca que sea lo más bajo posible, idealmente cercano a 0 horas perdidas), así como la varianza en la distribución de clases por día para cada grupo o docente (indicador de equilibrio: se prefiere que ningún grupo tenga, por ejemplo, todas sus clases concentradas en un solo día ni demasiados días completamente libres). Otra medida de calidad es el grado de cumplimiento de las preferencias, como la utilización de profesores de planta hasta alcanzar su meta de horas (se registra el porcentaje de docentes de planta que lograron al menos TARGET_HOURS_PLANTA) y la coincidencia de especialidad (qué proporción de clases fue asignada a un profesor cuya especialidad coincide con la materia, lo cual se bonifica en la función fitness).
•	Evolución del algoritmo: Se monitorea la curva de fitness a lo largo de las generaciones. En el archivo evolucion.csv se almacenan, para cada generación, el valor máximo y promedio de fitness en la población. Un incremento constante del fitness promedio y la convergencia del fitness máximo indican que el algoritmo está mejorando la solución gradualmente y acercándose a un óptimo. Idealmente, hacia las últimas generaciones la curva se estabiliza, mostrando que añadir más generaciones no produce mejoras significativas (criterio de parada adecuado). Estas métricas permiten ajustar hiperparámetros si, por ejemplo, se observa estancamiento prematuro (pudiendo incrementar la probabilidad de mutación o el número de generaciones en corridas posteriores).
•	Uso de recursos: En las estadísticas finales se reporta el número de docentes, aulas y días efectivamente utilizados en el horario. Un buen resultado tiende a utilizar los recursos de manera eficiente; por ejemplo, si hay disponibilidad de aulas o docentes que nunca se utilizan, podría indicar restricciones demasiado rígidas o potencial de asignar más clases en paralelo. Asimismo, se incluyen contadores como el total de clases programadas (que debe coincidir con la suma de horas semanales de todas las asignaturas), el número de días de la semana ocupados con clases, etc., para dar una visión global del horario generado.
En pruebas realizadas con datos reales del programa, el modelo logró cero conflictos de profesor y aula (factibilidad plena) y redujo al mínimo los huecos por docente. Por ejemplo, en un experimento se obtuvo un promedio de ~0.02 horas de hueco por docente, prácticamente nulo, lo que implica que la mayoría de profesores no tenían espacios libres entre sus clases en un mismo día. También se observó que ninguna asignatura quedó incompleta en horas, y que la carga semanal de clases para cada grupo estuvo repartida en varios días, evitando concentraciones excesivas. El fitness del mejor horario alcanzó un valor alto y la diferencia entre el fitness máximo y el promedio se redujo en las últimas generaciones, señal de que la población entera convergió hacia soluciones de calidad similar.
En cuanto a las métricas de carga docente, el reporte teacher_load.csv confirmó que los profesores de planta alcanzaron o se acercaron a su carga objetivo (por ejemplo, un profesor de planta con objetivo 12h se le asignaron 12 horas de clase), mientras que la carga de docentes ocasionales se mantuvo dentro de sus límites. Adicionalmente, todas las clases que requerían laboratorio efectivamente fueron programadas en aulas de tipo laboratorio, y las clases teóricas en salones normales, respetando los requisitos de cada asignatura.
En resumen, el sistema proporciona un horario que cumple todas las restricciones y optimiza criterios académicos importantes. Esto se refleja en métricas cuantitativas (0 conflictos, huecos ≈ 0, cargas balanceadas) y en la inspección manual del horario final, que muestra una distribución racional y justa de las clases. Cualquier desviación o resultado no deseado puede ser detectado a través de las métricas e informes generados, lo que da confianza sobre la validez de la solución y permite refinar aún más el modelo si fuera necesario.
Créditos
Autor: Luis Miguel Hernández Piñeres – Desarrollador del modelo y autor del trabajo de grado en el Programa de Ingeniería de Sistemas, Universidad de Pamplona.
Tutor Académico: Dra. Luz Marina Santos Jaimes – Docente investigadora, Universidad de Pamplona, quien orientó y supervisó el proyecto.
Institución: Universidad de Pamplona – Facultad de Ingenierías y Arquitectura, Programa de Ingeniería de Sistemas. Este proyecto se desarrolló como trabajo de grado para optar al título de Ingeniero de Sistemas, año 2025.
Agradecimientos especiales a la Universidad de Pamplona y al cuerpo docente del programa, cuyo apoyo y datos suministrados hicieron posible la realización de este proyecto.
Licencia
Este proyecto se distribuye bajo la Licencia MIT, lo que permite su uso, modificación y distribución libre, siempre que se conserve la atribución al autor original. Para más detalles, consulte el archivo LICENSE incluido en el repositorio.
(Nota: Si se utiliza este código o se derivan trabajos a partir de él, se solicita citar al autor y la institución original. Aunque es un proyecto académico, la licencia abierta busca fomentar su utilización y mejora por la comunidad interesada en la optimización de horarios y aplicaciones de algoritmos genéticos en educación.)
