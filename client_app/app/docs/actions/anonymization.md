# Módulo: Anonimizador y Masking

Este es un componente clasificado como **Procesador**, diseñado para detectar y ofuscar de forma irreversible Datos de Carácter Personal (DNI, nombres, pasaportes, cuentas) dentro de textos.

## Funcionamiento General
Aplica expresiones regulares avanzadas, validación estricta y algoritmos de anonimización asimétrica basados en la configuración seleccionada.

<help_config>
### Cómo configurar
1. **DNI/CIF/NIE**: Tildar si quieres que el sistema encuentre e invalide identificadores siguiendo la política seleccionada (AEPD, hashes, ocultar todo).
2. **Nombres Propios**: Permite ofuscar nombres manteniendo contextualmente su rol.
3. **Múltiples Reglas**: Puedes combinar todos los toggles para abarcar distintas sensibilidades PII.
</help_config>

<help_example>
### Ejemplo de Anonimización
Imagina que recibes esto: `Mi nombre es Juan Pérez y mi DNI es 12345678Z.`
Dependiendo de qué actives, el módulo emitirá algo seguro como:
`Mi nombre es J*** P**** y mi DNI es ***45678*.`

Ese string anonimizado será el único que se pase a la IA o se guarde en la BD, cumpliendo con la LOPD.
</help_example>
