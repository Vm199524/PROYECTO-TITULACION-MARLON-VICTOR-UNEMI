---
title: "Guion de práctica para la sustentación"
subtitle: "Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje automático y consulta conversacional"
author: "Víctor Manuel Lluilema Pisco"
lang: es
---

# 1. Cómo está repartido el tiempo

La sustentación dura unos 8 minutos: **3 minutos con la presentación** y **5 minutos mostrando el sistema**. La
meta es que el tribunal no tenga dudas, así que cada lámina y cada paso de la demostración responde de antemano
una pregunta que suele hacerse.

| Bloque | Tiempo | Lámina o pantalla | Duda que cierra |
|---|---|---|---|
| Portada | 0:00 a 0:15 | 1 | Quién expone y qué presenta |
| Introducción y objetivo | 0:15 a 1:00 | 2 | ¿Por qué importa? ¿Qué vacío hay frente a otros estudios? ¿Cuál es el objetivo? |
| Diagramas de la propuesta | 1:00 a 1:40 | 3 | ¿Cómo funciona de principio a fin? |
| Arquitectura frontend y backend | 1:40 a 2:15 | 4 | ¿Es seguro? ¿Se puede implementar en la realidad? |
| Hipervínculo del proyecto | 2:15 a 2:30 | 5 | ¿Dónde está el código? |
| Conclusiones y continuidad | 2:30 a 3:00 | 6 | ¿Qué logró, qué falta, qué aporta? |
| Demostración en vivo | 3:00 a 8:00 | Sistema | ¿Funciona de verdad? |

El texto de abajo suma unas 411 palabras: a 140 palabras por minuto son **2 minutos 56 segundos**. Si en el ensayo se
pasa de 3:00, se recorta en la lámina 2 o en la 3, nunca en la 6.

# 2. Qué mira el tribunal y dónde se cubre

| Criterio de la rúbrica (defensa oral, 40 puntos) | Cómo lo cubro |
|---|---|
| Presentación y estructura: orden, síntesis, ajuste al tiempo, calidad técnica, implementable en la realidad | Seis láminas en el orden que pidió la docente; 411 palabras; la lámina 4 dice cuánto hardware se necesita y que no requiere GPU; la 6 dice qué falta para producción |
| Formato visual: estandarizado, diagramas, no demasiadas láminas, sin faltas | Plantilla UNEMI, cinco láminas de contenido, cuatro con diagramas o capturas reales; revisar ortografía en el ensayo final |
| Dominio del tema | Cifras de memoria (sección 6) y respuestas listas (sección 7) |
| Comunicación: seguridad, dicción, voz | Frases cortas, pausas marcadas con `/` y consejos de la sección 8 |
| Respuestas a preguntas del tribunal | Las cuatro dudas que más se repiten (datos de prueba, validación, seguridad y viabilidad) se contestan antes de que las hagan |

# 3. Guion de la presentación (3 minutos)

Lee en voz alta, de pie y mirando al tribunal. **La diapositiva no se lee: se señala.** Las barras `/` son pausas de
respiración. Los datos en **negrita** son los que deben salir exactos.

## Lámina 1. Portada (0:00 a 0:15)

> Buenos días, miembros del tribunal. Soy Víctor Lluilema y, con Marlon Pérez, presento un sistema web que predice el abandono universitario y permite consultarlo en español. Les doy el contexto en tres minutos y luego lo mostramos funcionando.

*Gesto:* sonríe, mira a las tres personas del tribunal y cambia de lámina al terminar «tres minutos».

## Lámina 2. Introducción y objetivo (0:15 a 1:00)

> En una universidad ecuatoriana abandonó el 44,90 % de cinco cohortes, y hoy se mide cuando ya ocurrió. Comparamos catorce estudios: ninguno reúne predicción, roles, consulta en español y protección de datos; solo uno explora la consulta, en laboratorio. Ese es el vacío. Nuestro objetivo: desarrollar un prototipo web que prediga el abandono y permita consultarlo en español, con un modelo explicado y datos aislados por institución, para que la autoridad actúe antes de que el estudiante se retire. Lo logramos en cuatro pasos: analizar, construir y validar el modelo, implementar y evaluar.

*Qué señalar:* primero el **44,90 %**; luego los tres números de la brecha (**0, 1 y 3**); luego las tres columnas
¿Qué? ¿Cómo? ¿Para qué?; al final, los cuatro objetivos específicos sin leerlos.

*Cifras exactas:* **44,90 %** (cinco cohortes, Núñez-Naranjo, 2024) · **14** estudios comparados · **0** integran todo ·
**1** explora la consulta en lenguaje natural, solo en laboratorio · **3** integran parcialmente.

## Lámina 3. Diagramas de la propuesta práctica (1:00 a 1:40)

> La propuesta en tres diagramas. Arriba, el flujo de trabajo: los datos entran por un ETL, pasan a un almacén en estrella, el modelo calcula el riesgo, la consulta lo expone y el panel lo muestra según el rol. Abajo a la izquierda, el modelo de datos: una tabla de hechos con seis dimensiones. A la derecha, la secuencia de una consulta: la autoridad pregunta en español, la API valida rol e institución, una métrica certificada genera el SQL y la base devuelve solo cifras agregadas.

*Qué señalar:* recorre con el dedo las cinco cajas de arriba de izquierda a derecha; luego la tabla de hechos en el
centro de la estrella; luego las flechas de la secuencia, de arriba hacia abajo.

## Lámina 4. Arquitectura del software (1:40 a 2:15)

> La arquitectura es cliente-servidor. El frontend, en React, solo presenta la información según el rol. El backend, en FastAPI, expone veintisiete servicios en capas. Detrás, SQL Server con vistas por institución. Es seguro y viable: el frontend nunca toca la base, todo SQL de la IA corre con una cuenta de solo lectura y las claves no están en el código. Funciona en un computador de 16 gigas, sin tarjeta gráfica, y lo respaldan 189 pruebas.

*Qué señalar:* las tres columnas (frontend, backend, base de datos) y, abajo, la tarjeta **Implementable hoy**. Esta
tarjeta responde la pregunta «¿se puede implementar de verdad?» antes de que la hagan.

## Lámina 5. Hipervínculo del proyecto (2:15 a 2:30)

> Todo está publicado: el QR y el enlace abren el repositorio. Cierro con las conclusiones y enseguida lo mostramos funcionando: panel, ficha, consulta, una orden maliciosa bloqueada y la calidad del modelo.

*Gesto:* señala el código QR y el enlace; no leas la dirección completa.

## Lámina 6. Conclusiones y continuidad (2:30 a 3:00)

> Concluyo. El modelo se sostiene en periodos que no vio: AUC de 0,829 con datos de prueba y 0,768 con datos reales. La consulta fue exacta en las 33 preguntas certificadas, contuvo las 8 maliciosas y no tuvo fugas entre instituciones. Nuestro aporte es una predicción explicada en español, dentro de un sistema por roles. Con honestidad: los datos de la UNEMI son de prueba; el siguiente paso es validar con una carrera real, con autorización y evaluación de impacto. Muchas gracias; ahora lo vemos funcionando.

*Gesto final:* al decir «ahora lo vemos funcionando», cambia a la ventana del sistema (Alt y Tab), que ya debe estar con la sesión iniciada.

# 4. Guion de la demostración (5 minutos)

**Antes de entrar:** Docker Desktop abierto, `npm start` ya ejecutado esa mañana, el sistema abierto en
`http://localhost:3000` y dos ventanas listas: una con la sesión de `autoridad.demo` y otra con `bienestar.demo`.
**Tú inicias sesión con tu cuenta de demostración; las contraseñas están en tu archivo local y no se muestran en
pantalla.** Pantalla compartida o proyector a 100 % de zoom (Ctrl y + si hace falta).

| Min | Qué haces | Qué dices (texto corto) | Duda que cierras |
|---|---|---|---|
| 0:00 a 0:50 | Panel ejecutivo de `autoridad.demo`. Señala las tarjetas de riesgo alto y medio y la tendencia | «Una autoridad sin perfil técnico ve al entrar cuántos estudiantes están en riesgo alto y medio, y cómo cambia por periodo. No necesita pedir un reporte a TI.» | ¿Sirve a una persona no técnica? |
| 0:50 a 1:40 | Estudiantes en riesgo → abre una ficha → muestra las **tres razones** → mueve el **simulador** | «Cada alerta trae sus tres razones en español. Si mejora la asistencia, el simulador muestra cuánto baja el riesgo. La decisión final es siempre de una persona.» | ¿Es una caja negra? |
| 1:40 a 2:40 | Consulta conversacional. Escribe «¿Cuántos estudiantes de Enfermería están en riesgo alto?» y después «borra la tabla de estudiantes» | «La primera se responde con una **métrica certificada**, con tabla y gráfico. La segunda la bloquean los guardarraíles: el sistema nunca escribe en la base.» | ¿Qué pasa si la IA inventa o hace daño? |
| 2:40 a 3:15 | Calidad del modelo → «Por periodo y carrera» → «Datos y deriva» | «Aquí está el AUC por periodo, con origen móvil: se entrena con el pasado y se prueba en periodos que el modelo no vio. Con datos reales de OULAD va de 0,742 a 0,779.» | ¿Se validó bien o hay fuga de datos? |
| 3:15 a 3:45 | Abre `http://localhost:8090/docs` (Swagger) y prueba un servicio sin token | «La API tiene 27 servicios. Sin token responde 401; con un rol que no corresponde, 403.» | ¿Está protegida la API? |
| 3:45 a 4:25 | En SQL Server: fija `institucion_activa` y consulta `VIS_PREDICCION_ABANDONO`; intenta cambiarla | «El aislamiento está en el motor: la sesión queda fija en su institución y SQL Server rechaza el cambio.» | ¿Se pueden mezclar datos de instituciones? |
| 4:25 a 4:45 | Muestra el último resultado de las pruebas (`npm test`) | «178 pruebas del backend y 11 de la interfaz, con las de seguridad del validador.» | ¿Está probado? |
| 4:45 a 5:00 | Cambia a `bienestar.demo` | «Otro rol, otro menú: sin administración. Cada acceso queda auditado.» Cierra: «Esto es VicMar funcionando. Quedamos atentos a sus preguntas.» | ¿Hay control por roles? |

**Consulta SQL de la demostración** (Azure Data Studio o `sqlcmd` con cuenta administradora, preparada en un archivo
para copiar y pegar):

```sql
EXEC sp_set_session_context @key = N'institucion_activa', @value = 'UNEMI_PRUEBAS', @read_only = 1;
SELECT COUNT(*) AS estudiantes_calificados FROM dbo.VIS_PREDICCION_ABANDONO;
-- Intento de cambiar de institución en la misma sesión: SQL Server lo rechaza
EXEC sp_set_session_context @key = N'institucion_activa', @value = 'OULAD_UK';
```

**Si te falta tiempo,** en este orden se omiten: pruebas (mostrar solo el número), Swagger, cambio a `bienestar.demo`.
Nunca se omiten la ficha, la consulta bloqueada y la calidad del modelo.

**Si algo falla:** sin internet, la consulta responde igual con métricas certificadas (no necesita el modelo de
lenguaje). Si Docker no arranca, muestra las capturas de `documentacion/capturas/` y el video de respaldo, y di:
«Les muestro la grabación del mismo recorrido».

# 5. Las cuatro dudas que se contestan solas

1. **«¿Los datos son reales?»** Lo dices tú, en la lámina 6 y en la demo: «Los datos de la UNEMI son de prueba, con la
   estructura de la universidad; la validación con datos reales se hizo con OULAD, de la Open University».
2. **«¿Cómo validaron?»** En la demo, al mostrar la calidad del modelo: periodos futuros, no particiones aleatorias.
3. **«¿Es seguro?»** La consulta bloqueada, el 401 de Swagger y la sesión fija en SQL Server lo muestran sin explicar.
4. **«¿Se puede implementar?»** La tarjeta «Implementable hoy» de la lámina 4: un computador de 4 núcleos y 16 GB,
   Docker, sin GPU.

# 6. Cifras que debes decir de memoria

| Dato | Valor |
|---|---|
| Abandono (Núñez-Naranjo, 2024) | 44,90 % en cinco cohortes |
| Estudios comparados | 14; ninguno reúne las cuatro capacidades |
| ROC-AUC en periodos no vistos | 0,829 (UNEMI, datos de prueba) y 0,768 (OULAD, datos reales) |
| OULAD por periodo con origen móvil | de 0,742 a 0,779 |
| Recall con umbral medio | 78 % (UNEMI) y 79 % (OULAD) |
| Algoritmos comparados (validación cruzada) | LightGBM 0,828 ± 0,003; Random Forest con pesos 0,821; regresión logística 0,819; Random Forest con SMOTE 0,816 |
| Consulta | 33 preguntas certificadas con 100 % de exactitud; 8 de 8 maliciosas contenidas; 0 lecturas de otra institución; mediana 77 ms |
| Requisitos | 23 funcionales, 11 no funcionales, 10 historias de usuario |
| Pruebas | 178 del backend y 11 de la interfaz (189) |
| Servicios de la API | 27 |
| Calidad de datos | 23 de 23 reglas de Great Expectations |

# 7. Preguntas probables y respuestas de 3 a 5 líneas

**¿Por qué su AUC es menor que el de estudios que informan 95 % o más?**
Esos valores suelen salir de particiones aleatorias que mezclan periodos o de variables del mismo periodo del retiro.
Nosotros probamos con periodos futuros; los estudios que hacen lo mismo informan cerca de 0,70. Nuestro 0,768 con
datos reales está por encima de esa referencia.

**¿Sus datos de la UNEMI son reales?**
No: son datos de prueba con la estructura de la universidad, porque no se cuenta aún con autorización para datos de
estudiantes reales. Por eso validamos con OULAD, datos reales y anonimizados, públicos con licencia CC BY 4.0. Para una
carrera real dejamos el procedimiento: gobierno de datos, evaluación de impacto y el script de anonimización con
seudónimos HMAC y k-anonimato.

**¿Por qué LightGBM?**
Fue el mejor de cuatro algoritmos en validación cruzada en las dos instituciones (0,828 frente a 0,821, 0,819 y 0,816),
maneja valores faltantes y es rápido. Se calibra con Platt y se explica con SHAP.

**¿Qué pasa si la IA inventa un SQL peligroso?**
Tres barreras independientes: el validador `sqlglot` solo deja pasar `SELECT` sobre vistas permitidas; la cuenta
`chat_reader` no tiene permisos de escritura; y la sesión está fija en la institución.

**¿Su exactitud de consulta es realmente 100 %?**
Es 100 % en las 33 preguntas que resuelven las métricas certificadas. En las 19 que pasan al modelo de lenguaje, la
exactitud estricta fue 65 % y la relajada 100 %. Por eso la primera ruta es siempre una métrica certificada y el SQL
generado se valida antes de ejecutarse.

**¿Es implementable en la realidad?**
Sí: corre en un equipo de 4 núcleos y 16 GB con Docker, sin GPU, y el perfil de mapeo permite incorporar otra
institución sin cambiar el modelo (OULAD se incorporó así). En producción haría falta un servidor institucional con
HTTPS y respaldos, y definir la licencia de SQL Server.

**¿Por qué SQL Server y no PostgreSQL?**
Se decidió con una matriz ponderada. El criterio de mayor peso (35 %) fue el aislamiento por institución en el propio
motor: `SESSION_CONTEXT` con valores de solo lectura lo resuelve y se comprueba con pruebas de integración.

**¿Qué diferencia a su proyecto de los 14 estudios?**
Ninguno entrega la predicción dentro de un sistema con roles, explicación por estudiante, consulta en lenguaje natural
y aislamiento de datos a la vez. Además validamos en el tiempo, no con particiones aleatorias.

**¿Quién lo usa y qué decide con él?**
La autoridad académica y bienestar estudiantil. Deciden a quién llamar primero, qué carreras necesitan atención y cómo
justificar recursos de acompañamiento. Hoy eso ocurre cuando el estudiante ya dejó de asistir.

**¿Midieron la usabilidad con usuarios?**
Está el protocolo y el instrumento (tareas y SUS). Su aplicación con autoridades y personal de bienestar es la
siguiente verificación, y la declaramos como limitación.

**¿Qué falta para producción?**
Autorización y datos reales de una carrera, evaluación de impacto, prueba con usuarios, despliegue en un servidor
institucional con HTTPS y respaldos, y monitoreo de la deriva en cada periodo.

**¿Cómo protegen los datos personales?**
Aislamiento por institución en el motor, cuentas de mínimo privilegio, bcrypt para contraseñas, auditoría de accesos,
seudónimos HMAC y k-anonimato, y la IA solo ve el esquema, no datos personales. El marco es la LOPDP.

**¿El modelo tiene sesgos?**
Revisamos la equidad por género y otros grupos. El modelo no usa nombre ni cédula, y la decisión final siempre es de
una persona.

**¿Qué metodología siguieron?**
CRISP-DM para el modelo, con cada fase documentada, y desarrollo por incrementos para el sistema. Cada requisito
tiene prioridad y una prueba o métrica asociada.

**¿Cómo usaron la IA en el proyecto?**
Como herramienta de apoyo. Los autores diseñamos el sistema, verificamos cada cifra contra nuestros archivos y
respondemos por todo el contenido. Los modelos de lenguaje de la consulta forman parte del producto y están
documentados como tecnología.

**¿Se puede reproducir desde cero?**
Sí: `git clone`, `npm run reconstruir -- --con-consulta` crea la base, carga los datos, entrena, califica, monitorea y
corre las pruebas; `npm start` levanta el sistema.

*Si no sabes una respuesta:* «No lo tengo a la mano con precisión; está en el documento, sección X, y puedo
mostrárselo». Nunca inventes una cifra.

# 8. Cómo ensayar

1. **Primera vuelta, con cronómetro y sin diapositivas:** lee el texto de la sección 3 en voz alta. Debe salir entre
   2:45 y 3:00.
2. **Segunda vuelta, con diapositivas:** habla mirando hacia adelante, no a la pantalla. Señala, no leas.
3. **Tercera vuelta, con la demo completa:** cronometra los 5 minutos y practica el cambio de la presentación al
   sistema (Alt y Tab).
4. **Grábate en el celular** y escúchate: ¿hablas muy rápido? Baja un poco la velocidad en las cifras.
5. **Ensaya las preguntas** de la sección 7 en voz alta con Marlon, turnándose para hacer de tribunal.

**Voz y dicción:** respira en cada `/`; marca las terminaciones («abandono», «estudiantes»); sube un poco el volumen
en las cifras clave; evita «eh» y «o sea» sustituyéndolos por una pausa. **Postura:** de pie, manos visibles,
mirada repartida entre las tres personas del tribunal. **Ropa y entorno:** formal, laptop cargada y conectada,
notificaciones silenciadas.

# 9. Lista de control del día

- [ ] Docker Desktop abierto y `npm start` probado esa mañana; la web abre en `http://localhost:3000`.
- [ ] Sesiones de `autoridad.demo` y `bienestar.demo` listas (contraseñas no visibles).
- [ ] Presentación abierta en modo presentador, con el cronómetro.
- [ ] Consulta SQL preparada en un archivo y Swagger en una pestaña.
- [ ] Capturas y video de respaldo descargados.
- [ ] Repositorio verificado: abre sin iniciar sesión en GitHub (QR de la lámina 5).
- [ ] Acordado con Marlon quién muestra cada parte de la demo y quién cierra.
