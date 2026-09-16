"""Tipos compartidos de la librería de grafos públicos.

**`PublicGraphProfile` se retiró en PLG.1**, y no se re-exporta: la regla del proyecto prohíbe los
shims de compatibilidad. El nombre de un perfil es una cadena validada contra el registro
(`registry.list_profiles()`), porque un perfil aportado por un paquete instalado no cabe en un
enum del núcleo. Los perfiles que el núcleo ofrece siguen siendo los mismos tres; lo que cambió es
quién decide la lista, que ahora es el registro y no este módulo.
"""
