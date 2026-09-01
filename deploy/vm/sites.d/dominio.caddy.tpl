# Plantilla del sitio de un dominio con certificado PROPIO (D.8).
#
# La instala `scripts/vm_fetch_tls.sh` en /opt/govgenai/sites.d/<host>.caddy sustituyendo
# {{HOST}}, y **sólo después** de comprobar que el certificado y la clave están en disco: con un
# `tls` apuntando a ficheros que no existen, Caddy no arranca, y eso tumba también el nombre
# provisional que sirve a las páginas ya publicadas.
#
# ⚠️  ESTE CERTIFICADO NO SE RENUEVA SOLO.
#
# El del nombre provisional lo obtiene y renueva Caddy por ACME sin que nadie intervenga. Este
# lo emite la Universitat a través de HARICA/GÉANT y **caduca el 19 de marzo de 2027**; hay que
# pedir la renovación, cargarla en Secret Manager (`govgenai-tls-cert`, `govgenai-tls-key`) y
# reiniciar la pila. Una renovación olvidada deja el dominio con un certificado caducado, que en
# un navegador es indistinguible de un servicio caído.
#
# Renovar es: subir las dos versiones nuevas del secreto y `systemctl restart govgenai`. El
# guion baja siempre la versión `latest`, así que no hay que editar nada aquí.

{{HOST}} {
	# Cadena completa (hoja + intermedios) y clave, montadas en solo lectura desde
	# /opt/govgenai/tls. El orden del bundle importa y el que entregó desarrollo ya viene
	# bien: hoja primero.
	tls /etc/caddy/tls/fullchain.pem /etc/caddy/tls/privkey.pem

	import govgenai_rutas
}
