# La licencia de este proyecto, explicada en español

> **Documento informativo, sin valor jurídico.** El único texto vinculante es el de
> [`LICENSE`](../LICENSE), en inglés: la **GNU Affero General Public License, versión 3 o
> posterior** (`AGPL-3.0-or-later`).
>
> La Free Software Foundation **no aprueba traducciones** de sus licencias, y por buenas razones:
> una traducción no revisada puede alterar el significado de una obligación sin que nadie lo note,
> y a partir de ahí hay dos textos que dicen cosas distintas. Por eso este documento no traduce la
> licencia: la **explica**, remitiendo a los parágrafos del original para que cualquier duda se
> resuelva ahí y no aquí. Si algo de lo que sigue contradijera a `LICENSE`, vale `LICENSE`.

Está escrito pensando en quien tiene que decidir si su administración puede usar, desplegar o
modificar esta plataforma, y en quien tiene que redactar o valorar un pliego.

---

## En una frase

Puedes usar, estudiar, modificar y redistribuir este programa libremente; a cambio, si distribuyes
tu versión **o la ofreces como servicio en red**, tienes que ofrecer su código fuente en los mismos
términos.

---

## Qué puedes hacer

- **Usar el programa para cualquier fin**, sin pedir permiso, sin pagar y sin límite de usuarios,
  instancias o territorio.
- **Estudiar el código** y comprobar qué hace realmente. En actuación administrativa asistida por
  IA, esto no es un lujo: es la condición para poder explicar una resolución.
- **Modificarlo** para adaptarlo a tu organización.
- **Redistribuirlo**, con o sin modificaciones, en los términos del apartado siguiente.
- **Cobrar** por copias, soporte, despliegue, formación o mantenimiento. La licencia no exige que
  el programa sea gratuito: exige que sea libre. Lo que no puedes es cobrar por el permiso, ni
  cobrar aparte por entregar el código fuente al que ya tiene derecho quien recibe el programa.
- **Ejercer los derechos que la licencia otorga sin que se te puedan revocar** mientras la cumplas.
  Y si incumples y lo corriges, el §8 prevé cómo se recuperan.

## Qué te obliga

| Cuándo | Qué debes hacer | Dónde lo dice |
|---|---|---|
| **Distribuyes el código fuente**, modificado o no | Entregarlo bajo AGPL-3.0, conservando avisos de copyright, de licencia y de ausencia de garantía, y señalando de forma destacada que lo modificaste y en qué fecha | §4 y §5 |
| **Distribuyes el programa en forma no-fuente** (imagen de contenedor, binario, paquete) | Acompañarlo del *Corresponding Source* completo, o de una oferta escrita válida para obtenerlo, por una de las vías del §6 | §6 |
| **Ofreces por red una versión modificada** a usuarios que interactúan con ella | Ofrecer a **esos usuarios** acceso al *Corresponding Source* de **esa versión**, gratuitamente y por medios de red, de forma destacada | **§13** |
| **Aportas código** | Concedes con ello una licencia de patente no exclusiva sobre tus contribuciones, a todo el que reciba el programa | §11 |
| **Siempre** | No imponer restricciones adicionales sobre los derechos que la licencia concede: ni cláusulas contractuales, ni medidas técnicas, ni condiciones de uso | §7 y §10 |

**«*Corresponding Source*» no es «el repositorio».** Es el fuente que hace falta para generar,
instalar y ejecutar **exactamente esa versión**: el código, los ficheros de definición de interfaz,
los guiones que controlan la compilación y la instalación. Un enlace al proyecto principal no
cumple el §13 si lo que tú ejecutas es otra cosa.

## Qué NO te obliga

Conviene decirlo porque es la confusión más frecuente y la que paraliza decisiones.

- **No te obliga a contribuir al proyecto principal.** Ningún copyleft lo hace, ni la AGPL ni la
  GPL. Tu obligación es frente a **quienes reciben o usan tu versión**, no frente a nosotros. Que
  lo generalizable suba por *pull request* es una **convención de gobernanza** de este proyecto
  (está en el `README`), no una cláusula de la licencia.
- **No te obliga a publicar al mundo.** Si tu instancia la usa solo tu personal, tus usuarios son
  tu personal: a ellos les corresponde el fuente, no a la ciudadanía en general.
- **No te obliga a nada si modificas y no despliegas ni distribuyes.** Las modificaciones privadas
  que no se distribuyen ni se ofrecen por red no activan ninguna obligación (§2).
- **No te obliga a nada distinto si despliegas el programa tal cual, sin modificarlo.** El §13 se
  activa sobre la versión *modificada*. Enlazar el fuente sigue siendo lo razonable, pero no es
  exigible por esa vía.
- **No convierte en AGPL todo lo que tengas en el mismo servidor.** El copyleft alcanza a la obra
  derivada, no a programas independientes que simplemente coexistan o se comuniquen por protocolos
  estándar. Dónde está exactamente esa frontera es una cuestión técnica y jurídica que conviene
  analizar caso por caso.
- **No cede tu copyright.** Ni la licencia ni el `DCO` que exigimos en las contribuciones. Firmar
  `Signed-off-by` certifica que tienes derecho a aportar ese código; no transfiere su titularidad.

## El §13, que es la razón de que sea AGPL y no GPL

La GPL se activa cuando **entregas** el programa. Si nunca lo entregas —si solo lo *sirves* por
web— la GPL no obliga a nada. Para software de administración pública servido por navegador, esa
laguna se lo come todo: una modificación puede prestarse a la ciudadanía indefinidamente sin
devolver nada.

El §13 la cierra: **quien ofrece por red una versión modificada debe ofrecer su fuente a quien la
usa**. Tres consecuencias prácticas para cualquier despliegue de esta plataforma:

1. **La obligación es de quien despliega**, no del proyecto principal. Aparece en la interfaz de
   *tu* instancia, no en el `README` de aquí.
2. **El enlace apunta al fuente de tu versión**, en el commit desplegado. Por eso debe ser
   **configuración** (`SOURCE_URL` o equivalente) y no una URL fija en el código: una URL fija al
   principal haría que cualquier despliegue modificado incumpliera.
3. **Tiene que verse donde están los usuarios**, y eso incluye el **widget público embebido** en
   una web institucional. La ciudadanía que conversa con el chatbot también «interactúa
   remotamente» en el sentido del §13. Es el caso que se olvida.

Y una compatibilidad que a veces sorprende: el propio §13 permite **combinar** una obra AGPLv3 con
código GPLv3, cada parte bajo su licencia. AGPL y GPLv3 no son mundos incomunicados.

## «o posterior»

Este proyecto se distribuye como `AGPL-3.0-or-later`. Significa que puedes cumplir con la versión 3
o con cualquier versión posterior que publique la FSF, a tu elección (§14). Es una decisión
deliberada: evita que el proyecto quede atado a un texto de 2007 si la FSF corrige algo que el
tiempo revele mal resuelto.

## Sin garantía

Los §15 y §16 excluyen toda garantía y limitan la responsabilidad **en la medida en que lo permita
la ley aplicable**. Esa última coletilla importa en España: hay límites legales a la exclusión de
responsabilidad que una licencia no puede saltarse. Si tu organización necesita garantías
contractuales, la vía es un contrato de soporte con un proveedor —cosa que la licencia permite
expresamente—, no una lectura optimista del §15.

## Qué significa para una compra pública

- **Adquirir el programa no requiere licitación**: no hay precio ni contrato de licencia. Lo que se
  licita, si hace falta, son **servicios** —despliegue, adaptación, soporte, formación, corpus—, y
  esos se contratan con normalidad.
- **Los desarrollos que encargues nacen AGPL.** Conviene decirlo en el pliego, junto con la
  exigencia de que el adjudicatario **entregue el fuente** de lo que produzca y no imponga
  restricciones adicionales. Es lo que impide que una mejora pagada con fondos públicos quede
  cerrada en el proveedor que la hizo.
- **Reutilización entre administraciones**: encaja con el régimen de reutilización y transferencia
  de tecnología entre administraciones del **art. 157 de la Ley 40/2015** y con la publicación en
  directorios de aplicaciones reutilizables.
- **Interoperabilidad de licencias**: la **EUPL v1.2** reconoce la AGPLv3 entre las licencias
  compatibles de su apéndice, lo que facilita la combinación con obras publicadas bajo EUPL,
  habitual en el sector público europeo.
- **Soberanía**: el modo *edge* y la portabilidad por configuración (almacenamiento, base de datos,
  proveedor de modelos) son requisitos de arquitectura del proyecto, no extras. Un pliego puede
  exigirlos y comprobarlos.

## Titularidad

Copyright © 2026 **Universitat Jaume I de Castelló**. Desarrollado en el grupo de investigación
**INNOVAP** — Derecho Público e Innovación. Autor: **Modesto Fabra** — `fabra@uji.es`.

La titularidad corresponde a la UJI, que es la persona jurídica; INNOVAP consta como procedencia
porque explica la vocación multiorganización del proyecto. El detalle está en el `README`.

## Dónde mirar

| Para | Documento |
|---|---|
| El texto vinculante | [`LICENSE`](../LICENSE) (inglés) |
| El original en la web de la FSF | <https://www.gnu.org/licenses/agpl-3.0.html> |
| Preguntas frecuentes de la FSF sobre GPL/AGPL | <https://www.gnu.org/licenses/gpl-faq.html> |
| Por qué AGPL, gobernanza y forks | `README.md` |
| Cómo contribuir y el DCO | `CONTRIBUTING.md` y `DCO` |
