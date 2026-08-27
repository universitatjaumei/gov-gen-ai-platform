"""HIB.S — el juez tiene que ver la parte del artículo que importa, no las primeras dos páginas.

**El defecto que esto corrige, medido el 2026-08-27.** La comprobación de fundamento rechazó dos
respuestas de Normativa, y las dos eran correctas. ORI-16 decía «la quota de l'assegurança escolar
és d'1,12 euros» y el juez dictaminó que el extracto citado no lo sostenía. Comprobado despues:

- la frase «La cuota es de 1,12 euros» **sí** está en el documento, en el caracter 21.915;
- el padre que la contiene mide **21.324 caracteres**;
- el juez recibía los **primeros 8.000**.

El juez dijo la verdad sobre lo que se le dio, y lo que se le dio estaba recortado. Un prefijo
ciego de un artículo largo no es el artículo: es su principio, que casi nunca contiene el dato.

**Y la trampa de arreglarlo mal.** El atajo obvio —si el término no aparece en el extracto, no hay
fundamento y no se gasta llamada— es peligroso en un corpus bilingüe: la respuesta sigue la lengua
de la pregunta y la norma puede estar en la otra, así que «seis años» no aparece donde dice «sis
anys». Cuando no se localiza nada, la comprobación **no rechaza**: degrada a «no se pudo decidir».
Un rechazo sólo puede ocurrir si el juez vio la parte relevante.
"""
from server.app.modules.agents_hub.agent.grounding_check import ventana_relevante


ARTICULO = (
    "##### Articulo 1. Matricula\n"
    "La matricula es el acto administrativo por el cual se formaliza un contrato.\n"
    + "Relleno intermedio que no dice nada del dato buscado. " * 400
    + "\nEl estudiantado que no haya hecho los 28 anos antes del 1 de octubre. "
    "La cuota es de 1,12 euros, que se abona cuando se formaliza la matricula.\n"
    + "Mas relleno posterior. " * 200
)


class TestLaVentanaAlcanzaElDato:

    def test_should_find_a_figure_beyond_the_first_eight_thousand_characters(self):
        """El caso exacto de ORI-16: el dato esta pasado el caracter 8.000."""
        assert len(ARTICULO) > 8000
        assert ARTICULO.find("1,12") > 8000

        texto, localizado = ventana_relevante(
            "La quota de l'assegurança escolar es d'1,12 euros", ARTICULO
        )
        assert localizado is True
        assert "1,12" in texto

    def test_should_keep_the_heading_so_the_judge_knows_which_article_it_is(self):
        """Sin el encabezado el juez ve un parrafo sin dueno y no puede valorar si el articulo
        citado es el que corresponde: perderia justo el eje que el ambito equivocado rompe."""
        texto, _ = ventana_relevante("cuota de 1,12 euros", ARTICULO)
        assert "Articulo 1. Matricula" in texto

    def test_should_be_much_shorter_than_the_whole_excerpt(self):
        """La ventana existe para que el juez lea poco y lo pertinente. Si devolviera el
        articulo entero, el coste por afirmacion se iria con los padres de 32.000 caracteres."""
        texto, _ = ventana_relevante("cuota de 1,12 euros", ARTICULO)
        assert len(texto) < len(ARTICULO) / 2

    def test_should_return_the_whole_excerpt_when_it_is_short(self):
        corto = "##### Article 4\nCal superar un minim del 20% dels credits matriculats."
        texto, localizado = ventana_relevante("hay que superar el 20% de los creditos", corto)
        assert texto == corto
        assert localizado is True


class TestCuandoNoSeLocalizaNada:

    def test_should_report_that_nothing_was_located_instead_of_denying_support(self):
        """El corpus es bilingue y la respuesta sigue la lengua de la pregunta: «seis anos» no
        aparece donde la norma dice «sis anys». Devolver «no localizado» es lo que impide que un
        desencuentro de lengua se convierta en un rechazo."""
        texto, localizado = ventana_relevante(
            "El mandato dura seis anos", "##### Article 9\nLa durada del mandat es de sis anys."
        )
        assert localizado is False
        assert texto

    def test_should_still_give_the_judge_something_to_read(self):
        texto, localizado = ventana_relevante("dato inexistente 99999", ARTICULO)
        assert localizado is False
        assert texto.startswith("##### Articulo 1. Matricula")

    def test_should_not_treat_common_words_as_distinctive(self):
        """Si «para», «este» o «tiene» contaran como terminos distintivos, cualquier afirmacion
        se localizaria en cualquier articulo y la ventana caeria en el primer parrafo — que es
        el mismo prefijo ciego que esto viene a arreglar."""
        texto, localizado = ventana_relevante(
            "Para esto se tiene que hacer con los que sean", ARTICULO
        )
        assert localizado is False
