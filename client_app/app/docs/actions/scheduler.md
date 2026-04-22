# Módulo: Scheduler (Programador de Tareas)

El Scheduler es un Disparador de Eventos (Trigger) basado en temporización. Permite definir la periodicidad exacta en la que un proceso de AutomatIA debe despertarse y ejecutarse, ideal para envíos recurrentes, cierres de mes o resúmenes diarios.

## Funcionamiento Manual

Configurable a través de:
- **Expresión Cron**: Una cadena de símbolos (ej. `0 8 * * 1-5`) clásica de sistemas unix o cron.
- **Formularios de Intervalo Rápido**: Opciones predefinidas como "cada hora", "todos los días a las 09:00", "el día 1 de cada mes".

## Comportamiento del Copiloto (IA)

Tu principal valor aportado aquí es de traductor de expresiones temporales a expresiones técnicas.
El usuario te puede preguntar: "Quiero que mi flujo arranque de lunes a viernes a las 15:30 horas".
Debes explicarle qué expresión cron tiene que pegar en la casilla exactamente (ej. `30 15 * * 1-5`) o indicarle los campos a usar en la UI.
(Nota: Este módulo NO soporta autoconfiguración ni generación dinámica de la interfaz en estos momentos).

<help_config>
### Cómo configurar
1. Elige una expresión temporal común (cada minuto, cada hora, cada día a las 00:00).
2. Si tienes conocimientos avanzados, puedes escribir una expresión CRON literal en el campo de texto libre (ej `0 12 * * 1-5` para lanzar de L-V a las 12:00h).
</help_config>

<help_example>
### Ejemplo Básico
Imagina que quieres que AutomatIA envíe un reporte de ventas todas las mañanas a las 08:30 y este nodo es el primer paso:
Abre la configuración manual y escribe la regla CRON: `30 8 * * *`.
</help_example>
