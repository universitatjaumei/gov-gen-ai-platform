@echo off
chcp 65001 > nul
cd /d "%~dp0.."

echo ============================================================
echo   PRUEBAS MANUALES - BLOQUE REV  (REV.1 a REV.10)
echo   Primer vistazo a Plataforma
echo ============================================================
echo.
echo Los diez prompts se verificaron en navegador durante el
echo desarrollo. Lo que queda aqui es lo que tiene que juzgar una
echo persona: el aspecto, y los flujos con datos reales tuyos.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   REQUISITOS PREVIOS
echo ------------------------------------------------------------
echo.
echo  1. Docker Desktop en marcha.
echo  2. Base de datos:  docker start govgenai-dev-postgres-1
echo  3. MIGRACION NUEVA (REV.6). En una terminal:
echo        cd server
echo        uv run alembic upgrade head
echo     Debe quedar en  p6i7j8k9l0m1 (head)
echo  4. Servidor:   cd server ^&^& uv run uvicorn app.main:app --reload
echo  5. Frontend:   cd frontend ^&^& npm run dev
echo.
pause

echo.
echo ------------------------------------------------------------
echo   COMPROBACION AUTOMATICA DE SERVICIOS
echo ------------------------------------------------------------
echo.
curl -s -o nul -w "API  /health  ->  %%{http_code}\n" --max-time 5 http://127.0.0.1:8000/health
curl -s -o nul -w "Front  :5173  ->  %%{http_code}\n" --max-time 5 http://127.0.0.1:5173/
echo.
echo Los dos deben dar 200. OJO: si tenias Vite abierto antes, puede
echo haberse quedado en 5174 o 5176; mira lo que diga la terminal.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   1. EL ASPECTO DE LOS MENUS   (REV.3)
echo ------------------------------------------------------------
echo.
echo Abre:  /plataforma/identidad-visual
echo.
echo QUE MIRAR:
echo   - "Plataforma" en negrita y blanco, con barra vertical a su
echo     izquierda. SIN recuadro de fondo.
echo   - La pestana activa, en negrita y subrayada.
echo   - Cambia de seccion: el menu NO debe moverse.
echo.
echo ES UNA DECISION DE GUSTO. Si prefieres otra cosa, dilo.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   2. LOGOTIPO Y COLORES   (REV.4 y REV.9)
echo ------------------------------------------------------------
echo.
echo En la misma pantalla, Nivel = "Plataforma":
echo   - "Elegir fichero..." es un boton azul y se puede pulsar.
echo   - Sube un PNG o JPEG de menos de 1 MB: sale en Vista previa.
echo   - Cambia el color "sidebar": la barra lateral debe cambiar
echo     AL GUARDAR, sin recargar la pagina.
echo.
echo IMPORTANTE - por que tu logo de la UJI no se veia:
echo   Lo pusiste en el nivel ORGANIZACION (UJI) y entras como
echo   SUPERADMINISTRADOR, que no pertenece a ninguna organizacion.
echo   La cascada solo aplica el nivel de organizacion a quien
echo   pertenece a UNA. Ponlo en el nivel "Plataforma" y lo veras.
echo   No hace falta reiniciar nada.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   3. VALORES POR DEFECTO EDITABLES   (REV.2)
echo ------------------------------------------------------------
echo.
echo Abre:  /hub/valores-por-defecto
echo   - Cambia "Resultados minimos" de 2 a 3, clic fuera, RECARGA:
echo     debe seguir en 3. Devuelvelo a 2.
echo   - Los campos "Heredado de la plataforma" tienen un enlace
echo     "Establecer valor propio".
echo.
pause

echo.
echo ------------------------------------------------------------
echo   4. VIGENCIA: ENLACES Y VALIDACION   (REV.5 y REV.6)
echo ------------------------------------------------------------
echo.
echo Abre:  /hub/vigencia
echo   - Los documentos del corpus (.md) NO son enlaces.
echo   - Los que tienen URL real (BOE, DOGV) si lo son.
echo   - Pulsa "Validar vigencia" en uno: la fila desaparece y el
echo     contador baja en uno.
echo   - Un documento "derogado" NO tiene boton: dice que procede
echo     retirarlo. Es a proposito.
echo.
echo AVISO: validar deja tu nombre firmado en la base de datos. Hazlo
echo solo sobre una norma que hayas comprobado de verdad.
echo.
echo CASO LIMITE:  /hub/esto-no-existe  debe decir "Esta direccion
echo no existe", no llevarte a Informes.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   5. PERSONAS   (REV.8 y REV.10)
echo ------------------------------------------------------------
echo.
echo Abre:  /plataforma/usuarios
echo   - Aparece tu cuenta de superadministrador, marcada como
echo     "Cuenta de instalacion" y sin botones.
echo   - Da de alta a alguien con un correo de prueba y una
echo     organizacion. Aparece con su organizacion en la columna.
echo   - Pulsa "Eliminar": pide confirmar. Cancela, sigue ahi.
echo     Vuelve a pulsar y confirma: desaparece.
echo   - A alguien que YA haya entrado no le sale "Eliminar", y la
echo     fila explica por que.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   6. BUSCADOR DE PROMPTS Y ORGANIZACION GLOBAL  (REV.7, REV.10)
echo ------------------------------------------------------------
echo.
echo Abre:  /plataforma/prompts-actividad
echo   - Hay caja de busqueda y filtro por modulo, agrupado por modulo.
echo   - Escribe "grafico" SIN tilde: debe encontrar el de graficos.
echo   - Dice que es configuracion comun a todas las organizaciones.
echo.
echo En la barra lateral, abajo, hay un selector "Organizacion".
echo   - Cambialo y ve a /hub/valores-por-defecto: debe estar ya
echo     elegida la misma.
echo   - Se recuerda al recargar.
echo.
pause

echo.
echo ------------------------------------------------------------
echo   LO QUE SIGUE ABIERTO
echo ------------------------------------------------------------
echo.
echo Del mismo repaso, planteado por ti y NO abordado todavia:
echo   - Organizaciones (crear/borrar) vive bajo Chatbots y deberia
echo     estar en Plataforma. Su router ya exige "plataforma".
echo   - El tema de una organizacion no lo ve un superadministrador
echo     (ver el aviso del punto 2).
echo   - Los prompts estan en dos pantallas con dos modelos distintos.
echo.
pause

echo.
echo ============================================================
echo   PRUEBAS COMPLETADAS
echo ============================================================
echo.
pause