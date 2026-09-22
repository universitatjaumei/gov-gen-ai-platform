@echo off
chcp 65001 > nul
rem Se ejecuta desde la raiz del repositorio, este el .bat donde este.
cd /d "%~dp0.."
title Pruebas manuales - Validacion posterior al despliegue
echo.
echo ==========================================================
echo   VALIDACION POSTERIOR AL DESPLIEGUE
echo ==========================================================
echo.
echo POR QUE ESTE GUION EXISTE
echo.
echo   Hay cosas que solo se comportan distinto en el entorno
echo   desplegado: el dominio y su certificado, el almacenamiento de
echo   objetos, la identidad federada y el servicio bajo la
echo   configuracion real. En local todo eso esta simulado o apagado.
echo.
echo   La suite verde y el despliegue en verde no dicen nada de esto.
echo   Un despliegue puede salir en verde con una funcion apagada: paso
echo   con el login de Google, que salio a produccion sin dos variables
echo   porque nadie cruzaba lo que el despliegue escribe con lo que el
echo   contenedor recibe.
echo.
echo ANTES DE EMPEZAR - LEE ESTO
echo.
echo   Esto se ejecuta CONTRA PRODUCCION. Reglas:
echo     - Usa datos de prueba, nunca datos personales reales.
echo     - No borres nada. Si algo hay que retirar, anotalo y hazlo
echo       despues, a conciencia.
echo     - Lo que encuentres se convierte en issue. Ese es el criterio
echo       de cierre: recorrido hecho y anotado.
echo.
echo   Cambia la direccion si tu despliegue no es el de la UJI:
set SITIO=https://normativa.uji.es
echo     SITIO=%SITIO%
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 1 - Dominio y certificado
echo ----------------------------------------------------------
echo.
curl -s -o nul -w "   raiz:          %%{http_code}\n" %SITIO%/
curl -s -o nul -w "   salud del API: %%{http_code}\n" %SITIO%/api/v1/health
echo.
echo   Certificado (fijate en la fecha de caducidad):
curl -s -v %SITIO%/ 2>&1 | findstr /I "expire issuer subject:"
echo.
echo QUE DEBES VER: 200 en las dos, y un certificado vigente.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Cuanto queda para que caduque? Si no se renueva solo, esa
echo     fecha es una cuenta atras y tiene que estar en la agenda de
echo     alguien, no en este guion.
echo   - http:// redirige a https:// o sirve contenido en claro?
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 2 - El reparto de rutas bajo el mismo dominio
echo ----------------------------------------------------------
echo.
echo   El mismo dominio sirve el sitio publico y el panel. Comprueba
echo   que cada ruta la atiende quien debe.
echo.
curl -s -o nul -w "   sitio publico:  %%{http_code}\n" %SITIO%/
curl -s -o nul -w "   panel:          %%{http_code}\n" %SITIO%/hub
curl -s -o nul -w "   API sin sesion: %%{http_code}\n" %SITIO%/api/v1/hub/sites
echo.
echo QUE DEBES VER: sitio y panel 200, y la API 401 (pide sesion).
echo   Si la API devuelve 200 sin sesion, PARA: hay datos al aire.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 3 - Identidad federada, con una cuenta real
echo ----------------------------------------------------------
echo.
echo   Esto es lo que ningun agente puede verificar: hace falta una
echo   credencial institucional de verdad.
echo.
echo   Que proveedores dice el servidor que tiene encendidos:
curl -s %SITIO%/api/v1/auth/sso-providers
echo.
echo.
echo   1. Abre %SITIO% en una ventana privada.
echo   2. Entra con el proveedor que salga encendido arriba.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Entra, y vuelve a la aplicacion ya identificado?
echo   - Una cuenta de FUERA de la organizacion es rechazada? Pruebalo
echo     con una cuenta personal: es la comprobacion que impide que
echo     entre cualquiera.
echo   - El token no viaja en la barra de direcciones como parametro:
echo     debe ir detras de la almohadilla, que no queda en registros.
echo   - Despues de entrar: TIENES ACCESO A ALGUN MODULO? Identificarse
echo     no concede modulos. Si el menu sale vacio, no es un fallo del
echo     login.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 4 - Almacenamiento de objetos
echo ----------------------------------------------------------
echo.
echo   En local los ficheros van al disco; desplegado van al bucket. Es
echo   la diferencia que mas veces se escapa, porque el contenedor
echo   puede destruirse en cualquier momento y su disco con el.
echo.
echo   1. Sube un documento de prueba por la interfaz (ingesta, o un
echo      adjunto de informes).
echo   2. Comprueba que se puede descargar y que se ve entero.
echo   3. Pide que se reinicie el servicio, o espera a un despliegue.
echo   4. Vuelve a descargarlo.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Sigue estando despues del reinicio? Si desaparece, se escribio
echo     en el disco del contenedor y no en el almacenamiento.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 5 - La base de datos esta donde dice la cadena de Alembic
echo ----------------------------------------------------------
echo.
echo   Desde la maquina desplegada, dentro del contenedor:
echo.
echo        alembic current
echo        alembic check
echo.
echo QUE DEBES VER:
echo   - "current" coincide con la cabeza de la rama desplegada.
echo   - "check" no encuentra diferencias. Si las encuentra, hay un
echo     modelo sin su migracion, y el esquema lo define Alembic y solo
echo     Alembic.
echo.
pause
echo.
echo ----------------------------------------------------------
echo  PASO 6 - El servicio bajo configuracion real
echo ----------------------------------------------------------
echo.
echo   1. Haz una pregunta al asistente y cronometra la respuesta.
echo   2. Repitela. La segunda deberia ir mas rapida.
echo   3. Mira los registros del servicio mientras tanto.
echo.
echo LO QUE HAY QUE JUZGAR:
echo   - Tarda un tiempo razonable para quien lo va a usar?
echo   - En los registros aparece algun aviso repetido que en local no
echo     sale? Los que se repiten en cada peticion son los que importan.
echo   - Hay trazas con datos personales en los registros? No deberia
echo     haberlas, y es mas facil que pase en produccion que en local.
echo.
pause
echo.
echo ==========================================================
echo   VALIDACION COMPLETADA
echo ==========================================================
echo.
echo CRITERIO DE CIERRE: recorrido hecho y anotado, y cada hallazgo
echo convertido en su propia issue. Un hallazgo que solo vive en tu
echo memoria no lo arregla nadie.
echo.
pause
