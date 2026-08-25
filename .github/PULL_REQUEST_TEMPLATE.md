<!--
Gracias por contribuir. Esta plantilla es corta a propósito: la primera pregunta es la que
decide si el cambio entra en el principal, y las demás son las que ya exige AGENTS.md.
-->

## ¿Por qué esto es generalizable?

<!--
**La pregunta central de la gobernanza de este proyecto.** El principal sirve a varias
administraciones —con atención particular a las entidades locales—, no a una. Lo específico de
una institución se queda en su fork; al principal sube lo que otra organización querría.

De `CONTRIBUTING.md`: si la respuesta a «¿otra administración querría este cambio?» es «le daría
igual», es material de fork. Si es «lo necesita pero al revés», lo que sube es la **opción de
configuración**, no la decisión.

Ejemplos de lo que sí sube: un módulo o capacidad que cualquiera pueda activar; el arreglo de un
defecto real, con su test; hacer parametrizable algo que estaba fijo; accesibilidad, i18n,
rendimiento, seguridad.
-->

## Qué problema resuelve

<!-- Para cualquier organización, no sólo para la que envía el cambio. -->

## Cómo se ha comprobado

<!--
TDD es obligatorio: no hay PR sin tests. Di qué tests pasan y, si el cambio toca la interfaz,
qué se ha verificado en el navegador y con qué evidencia (URL, texto encontrado, consola).
-->

## Repaso antes de pedir revisión

- [ ] **Tests**: el test se escribió antes que el código y la suite pasa.
- [ ] **Commits firmados** (`git commit -s`). El DCO lo comprueba CI, y la firma tiene que
      coincidir con el autor del commit.
- [ ] **Nada específico de una institución**: ni configuración, ni integraciones internas, ni
      corpus, ni datos reales, ni credenciales.
- [ ] **Sin secretos en el diff** (claves, DSN, contraseñas, volcados).
- [ ] **Frontera edge/cloud** respetada si toca `server/`: sin `relationship()` entre las dos
      bases ORM, sin que un módulo edge importe de uno cloud, y el router nuevo etiquetado
      (`Deploy: cloud|edge|shared`) y registrado donde toca.
- [ ] **Contract-First** si toca la API: contrato regenerado y cliente al día; nada de `fetch`
      crudo ni tipos escritos a mano en el frontend.
- [ ] **i18n** si toca la interfaz: sin cadenas incrustadas, y las tres lenguas (`ca`/`es`/`en`).
- [ ] **Legacy retirado** si esto migra algo: sin código muerto ni imports sin usar.
