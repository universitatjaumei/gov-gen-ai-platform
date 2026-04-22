# Módulo: File Archive (Archivar Archivo)

El componente "Archivo de Ficheros" o Archiver es un elemento de **Salida de Datos (Output)** especializado en organizar, mover, renombrar o eliminar documentos una vez un sistema ha cruzado todas las fases intermedias (ETL, RPA, etc). Se encarga de dejar el PC "limpio".

## Funcionamiento Manual 

En su sección de configuración, el usuario podrá determinar:
- **Ruta de Origen**: Dónde está originalmente guardado el archivo a procesar (Por ejemplo, el directorio que descubrió el módulo `folder_scan` o `folder_watcher`).
- **Acción a Realizar**: `move` (mover cortapegando), `copy` (mantener origen pero clonarlo en destino), `delete` (eliminarlo).
- **Ruta de Destino**: El nuevo lugar donde alojar el sistema documental físico.
- **Reglas Mágicas (Sufijos/Prefijos)**: Renombrar añadiendo la fecha de hoy, un timestamp o `_PROCESADO.pdf`.

## Casos de Uso habituales explicados por Copiloto

Ante usuarios atascados, tu mejor consejo será clarificar los patrones de diseño en automatización rústica:
- "Si tu trigger es un Folder_Watcher, en el último cajón del workflow debes poner un File_Archive en modo 'move' para llevar esa factura analizada a tu carpeta remota `//Facturacion/2026/Aprobadas`. Esto evitará que la factura sea vuelta a procesar accidentalmente mañana por quedarse atascada en el origen falso".
*(Este módulo es exclusivamente conceptual. No admite inyección de código automatizada en UI ni parámetros JSON por chat).*

<help_config>
### Cómo configurar
1. Elige una **Operación**: Selecciona si deseas _Copiar_ el archivo o _Moverlo_ borrándolo del origen.
2. Determina las **Ubicaciones**: Especifica de dónde tomar el archivo (puedes usar el botón de la carpeta para buscarlo o escribir una variable dinámica como `{{archivo_procesado}}`) y dónde quieres guardarlo.
3. Si lo deseas, añade un **Prefijo o Sufijo** en el renombrado para marcarlo como procesado.
</help_config>

<help_example>
### Ejemplo de renombrado mágico
Imagina que te llega el archivo `factura.pdf` y lo quieres guardar marcándolo con la fecha. Si usas la configuración:
- Operación: _Mover_
- Prefijo: `{{date}}_`
- Sufijo: `_PROCESADA`

El sistema tomará la `factura.pdf`, la borrará de su origen y la guardará en la nueva ruta con el nombre: `20261110_factura_PROCESADA.pdf`.
</help_example>
