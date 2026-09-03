@echo off
chcp 65001 > nul
cd /d "%~dp0.."
title Pruebas manuales - Bloque USR (contrasena local para las personas)

echo ==========================================================================
echo  BLOQUE USR - contrasena local para las personas, hasta que llegue el SSO
echo ==========================================================================
echo.
echo  Lo que el agente YA verifico en navegador (no hace falta repetirlo):
echo.
echo   - Alta de una persona con rol Usuario y organizacion UJI.
echo   - Fijarle la contrasena desde la pantalla de Personas, con su
echo     confirmacion y sin volver a mostrar el valor.
echo   - Entrada de esa persona con su contrasena.
echo   - Conversacion con un asistente de su organizacion, con citas.
echo   - Los limites: no ve el panel de plataforma, no abre un asistente de
echo     otra organizacion (403), no fija contrasenas (403), y desactivada
echo     no entra (401).
echo   - Dos administradores sobre la MISMA organizacion, los dos viendo los
echo     mismos cuatro asistentes de la UJI y ninguno el de otra.
echo   - Cambiar la propia contrasena de punta a punta: la vieja deja de
echo     servir y la nueva sirve.
echo   - USR.9: la pantalla de Personas desde un administrador de
echo     organizacion: ve solo a la gente de la UJI y ninguna de las cuentas
echo     de superadministracion, sin formulario de alta y sin desactivar, y
echo     con "Fijar contrasena" en cada fila.
echo   - USR.10: quien tiene un modulo y pide otro se queda en la direccion
echo     que pidio, con el aviso correcto; quien no tiene ninguno sigue
echo     yendo a la pantalla de "sin acceso".
echo   - USR.8: el asistente agentico de Gerencia responde y AHORA registra
echo     la interaccion (de 0 pasa a 1) y cierra el flujo con su evento.
echo.
echo  Aqui queda SOLO lo que una persona tiene que decidir o hacer con datos
echo  reales.
echo.
pause

echo.
echo ==========================================================================
echo  1. DAR DE ALTA A LOS PROBADORES DE VERDAD
echo ==========================================================================
echo.
echo  Requisitos previos:
echo    - Docker Desktop en marcha.
echo    - El servidor y el panel levantados (arranque.bat, opcion 1).
echo.
echo  En https://normativa.uji.es/panel/ (o en local, http://localhost:5173):
echo.
echo   1. Entra como superadministrador.
echo   2. Personas (en el menu de la izquierda; desde USR.9 ya no cuelga de
echo      Plataforma, tiene su propio modulo).
echo   3. Para cada probador de Gerencia:
echo        - Correo institucional real.
echo        - Rol: Informador si va a anotar respuestas; Usuario si solo
echo          consulta; Administrador si va a administrar la organizacion.
echo        - Organizacion: Universitat Jaume I.
echo        - Dar de alta, y despues "Fijar contrasena" con UNA DISTINTA POR
echo          PERSONA. Ese es el punto del bloque: la atribucion por persona.
echo   4. Comunicale a cada uno su contrasena por un canal seguro. La pantalla
echo      no la vuelve a mostrar, a proposito.
echo   5. Diles que entren y usen "Cambiar mi contrasena" (menu de su cuenta,
echo      abajo a la izquierda). Desde ese momento el secreto es solo suyo.
echo.
echo   6. A quien lleve rol Administrador, concedele ademas el modulo
echo      "Personas de la organizacion" en Plataforma ^> Modulos. Sin el no ve
echo      la pantalla, y con el vera SOLO a la gente de sus organizaciones y
echo      podra fijarles la contrasena, pero no dar de alta ni cambiar roles.
echo      A quien ya tenia el modulo Plataforma se lo dio la migracion.
echo.
echo  DECISION TUYA: que rol lleva cada uno. El agente no puede inventarlo.
echo.
pause

echo.
echo ==========================================================================
echo  2. CONCEDER MODULOS - si no, entran y no ven nada
echo ==========================================================================
echo.
echo  Una persona recien dada de alta NO tiene ningun modulo, asi que al entrar
echo  ve "Todavia no tienes acceso a ningun modulo". No esta roto: es el fallo
echo  seguro.
echo.
echo   1. Plataforma ^> Modulos.
echo   2. Concede a cada probador lo que necesite: chatbots, informes o
echo      curacion.
echo   3. Que vuelva a entrar y compruebe que ve su seccion.
echo.
echo  Si un probador solo va a conversar con el asistente publico, no necesita
echo  ningun modulo ni entrar al panel.
echo.
pause

echo.
echo ==========================================================================
echo  3. RETIRAR LAS SEIS CUENTAS ELEVADAS
echo ==========================================================================
echo.
echo  En produccion hay SIETE superadministradores: la tuya y los seis
echo  probadores creados el 2026-09-01 con una contrasena compartida. Mientras
echo  duren, seis personas pueden cambiar proveedores de modelo, borrar
echo  asistentes y fijar contrasenas.
echo.
echo   1. Da de alta a esas seis personas como Personas, con su rol real
echo      (paso 1 de este guion).
echo   2. Comprueba que cada una entra con SU contrasena.
echo   3. Solo entonces, retira sus SuperAdminAccount.
echo.
echo  El paso 3 se hace desde el servidor: esas filas viven en otra tabla y la
echo  pantalla de Personas las ensena en solo lectura. Pidelo cuando los seis
echo  hayan entrado con su cuenta nueva.
echo.
pause

echo.
echo ==========================================================================
echo  4. COMPROBACION RAPIDA DE QUE LA VIA NUEVA RESPONDE
echo ==========================================================================
echo.
echo  Un 401 aqui es lo CORRECTO: significa que la ruta existe y rechaza una
echo  credencial inventada. Un 404 significaria que el login local esta
echo  apagado (LOCAL_USER_LOGIN_ENABLED=false).
echo.
curl -s -o nul -w "     %%{http_code}  POST /api/v1/auth/user/login (se espera 401)\n" -X POST "http://localhost:8000/api/v1/auth/user/login" -H "Content-Type: application/json" -d "{\"email\":\"nadie@example.invalid\",\"password\":\"una-contrasena-inventada\"}"
echo.
echo  Si da 000, el servidor no esta levantado.
echo.
pause

echo.
echo ==========================================================================
echo  5. Y CUANDO LLEGUE EL SSO
echo ==========================================================================
echo.
echo  Este bloque es provisional por definicion. El dia que el IdP de la UJI
echo  este configurado, lo primero es apagar el login local:
echo.
echo      LOCAL_USER_LOGIN_ENABLED=false
echo.
echo  Con eso la ruta responde 404 y la tercera puerta del formulario deja de
echo  existir. Sin ese interruptor, "hasta que llegue el SSO" se convierte en
echo  "para siempre".
echo.
pause

echo.
echo PRUEBAS COMPLETADAS
echo.
pause
