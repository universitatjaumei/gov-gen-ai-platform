# Política de seguridad

Esta plataforma la despliegan administraciones públicas y trata datos de ciudadanos. Un fallo de
seguridad aquí no es una incidencia de producto: puede ser una brecha de datos personales con
obligaciones de notificación. Por eso este documento existe y por eso pide que los fallos se
comuniquen **en privado primero**.

## Cómo comunicar un fallo

**La vía preferida es el aviso privado de GitHub**, en la pestaña *Security* del repositorio:

👉 **[Report a vulnerability](https://github.com/universitatjaumei/teclab-govgenai/security/advisories/new)**

Es privado entre quien avisa y quien mantiene, queda asociado al repositorio en vez de a un buzón,
y desemboca en el aviso público que hay que publicar al corregirlo. Que no dependa de una persona
concreta es justamente lo que se busca: un correo se pierde cuando alguien cambia de puesto.

Si prefieres el correo, o el aviso de GitHub no te sirve, escribe a **fabra@uji.es** con el asunto
`[SEGURIDAD]`. Si quieres cifrar, dilo en un primer mensaje sin detalles y se acuerda la vía.

**No abras un issue público** para un fallo explotable. Un issue es visible para cualquiera,
incluidos los despliegues que todavía no han actualizado, y convierte el aviso en instrucciones.

Ayuda mucho incluir:

- Qué versión o *commit* estás mirando, y si es un despliegue propio o el código sin modificar.
- Qué permite hacer el fallo: leer datos de otra organización, saltarse una guarda, ejecutar
  código, elevar privilegios.
- Los pasos mínimos para reproducirlo. Si hace falta una petición concreta, pégala **sin
  credenciales reales**.
- El impacto que le ves, aunque sea aproximado.

## Qué puedes esperar

- **Acuse de recibo en 5 días laborables.** Si no llega, insiste: puede haberse perdido.
- Una primera valoración —si se reproduce y qué alcance tiene— en **15 días naturales**.
- Te mantendremos al tanto mientras se trabaja, y te diremos cuándo está corregido.

Esto es un proyecto de investigación con un equipo pequeño, así que estos plazos son un
compromiso de **respuesta**, no de resolución: un fallo complejo puede tardar más, y en ese caso
lo que se compromete es contártelo.

## Divulgación

Se sigue divulgación coordinada:

1. Se acuerda contigo una fecha de publicación, normalmente **90 días** desde el aviso o antes si
   ya hay corrección disponible.
2. Se publica el arreglo y, con él, un **aviso de seguridad** en la pestaña *Security* del
   repositorio, que describa el fallo y a partir de qué versión está corregido — porque **quien
   despliega necesita saber si le afecta**, y sin esa nota no puede decidir si actualizar corre
   prisa. Publicado ahí, además, llega a quien tenga un *fork* aunque no siga el proyecto.
3. Se te acredita por nombre si quieres. Dilo, y con qué nombre.

Si el fallo ya está siendo explotado o es público, se acelera todo y se avisa cuanto antes.

## Qué entra y qué no

**Entra**: cualquier cosa que permita acceder a datos de otra organización, saltarse la
autenticación o la frontera de módulos, ejecutar código en el servidor o en el sandbox, obtener
credenciales o *tokens*, o dejar el servicio inoperativo con poco esfuerzo.

**No entra**: fallos de un despliegue mal configurado que el código no causa (por ejemplo, una
instancia publicada sin HTTPS o con `ENVIRONMENT` mal puesto), resultados de un escáner
automático sin impacto demostrado, y ausencia de cabeceras que no afecten a este producto. Si
tienes dudas de si algo cuenta, escribe igualmente: preferimos descartarlo entre los dos.

## Si el despliegue es tuyo

La AGPL no traslada responsabilidad de operación: **quien despliega es responsable de su
instancia**. Dos cosas que el código no puede hacer por ti y que conviene repasar:

- **Los secretos**. `JWT_SECRET_KEY`, la credencial de base de datos y las claves de los
  proveedores de modelo se leen del entorno; la aplicación se niega a arrancar en producción con
  valores de ejemplo, pero no puede impedir que se filtren por otra vía.
- **Las actualizaciones**. Un arreglo publicado aquí no llega a tu instancia hasta que la
  actualizas, y si mantienes un fork, hasta que lo sincronizas.

El detalle de las garantías que el sistema sí implementa —aislamiento entre organizaciones,
sandbox de scripts, anonimización, trazabilidad— está en `docs/MARCO_GOBERNANZA_IA.md` y
`docs/MULTITENENCIA.md`.
