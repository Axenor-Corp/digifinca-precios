#!/usr/bin/env python3
"""Pruebas del extractor (sin red). Corren en CI ANTES de actualizar: si la
fuente cambia de redacción y el parser empieza a leer mal, esto lo caza antes
de publicar una cifra equivocada.

Los textos son fragmentos REALES de los boletines de Agronegocios/Asosubastas,
con las dos redacciones que usa el medio: "fue de $X" y "al pasar de $A a $B".
"""

import sys

from update_precios import parse_article

# Redacción A (boletín del 9 de julio de 2026): promedios directos + extremos
# en la entradilla — la trampa clásica es leer el "más caro" como promedio.
FIXTURE_A = '''<html><head><script type="application/ld+json">
{"datePublished":"2026-07-09T17:18:49-05:00"}</script></head><body>
<p>El precio m&aacute;s caro del kilo para los machos de ceba fue de $9.842, y
el m&aacute;s bajo alcanz&oacute; $8.250. El promedio para la franja de tiempo
analizada fue de $9.226</p>
<p>Asosubastas public&oacute; la informaci&oacute;n correspondiente a la segunda
semana de julio, con el precio de las diferentes categor&iacute;as de ganado.
Para este lapso, el valor promedio de los machos de ceba por kilogramo fue de
$9.226, mientras que el de las hembras de levante alcanz&oacute; $8.519.</p>
<p>En comparaci&oacute;n con la semana anterior, estos precios registraron una
disminuci&oacute;n. El valor del kilo de macho de ceba cay&oacute; $451,
mientras que el de las hembras de levante se redujo en $471.</p>
<p>Durante esta jornada, la categor&iacute;a que registr&oacute; el menor precio
por kilo fue la de hembras de levante, con un valor m&iacute;nimo de $7.819,
seguidas por las hembras de vientre, cuyo precio fue de $7.953. En el caso de
los machos, el menor precio correspondi&oacute; a los de levante, con un valor
de $8.161 por kilo.</p></body></html>'''

# Redacción B (boletín del 23 de julio de 2026): variaciones "de $A a $B",
# donde el valor vigente es SIEMPRE el segundo.
FIXTURE_B = '''<html><head><script type="application/ld+json">
{"datePublished":"2026-07-23T12:41:36-05:00"}</script></head><body>
<p>Asosubastas public&oacute; el bolet&iacute;n correspondiente a la semana 30
del a&ntilde;o, con el precio de las diferentes categor&iacute;as de ganado.
Para este lapso, el valor promedio de los machos de levante por kilogramo fue
de $9.517, el m&aacute;s alto, mientras que el de las hembras de vientre
alcanz&oacute; $8.561, el m&aacute;s bajo.</p>
<p>En comparaci&oacute;n con el bolet&iacute;n de la semana anterior, los machos
de levante registraron el mayor incremento en el precio promedio por kilogramo,
al pasar de $9.334 a $9.517, lo que representa un aumento de $183. Tambi&eacute;n
subieron las hembras de levante, cuyo precio promedio avanz&oacute; de $8.603 a
$8.700, con una variaci&oacute;n de $97 por kilo. En contraste, los machos de
ceba presentaron una leve disminuci&oacute;n en su precio promedio, al pasar de
$9.088 a $9.071, mientras que las hembras de vientre registraron la mayor
ca&iacute;da de la semana, con un descenso de $108 por kilogramo, al pasar de
$8.561 a $8.453.</p></body></html>'''

CASOS = [
    ("redacción A (9-jul-2026)", FIXTURE_A, "2026-07-09",
     {"machos de ceba": 9226, "hembras de levante": 8519},
     {"ceba_max": 9842, "ceba_min": 8250}),
    ("redacción B (23-jul-2026)", FIXTURE_B, "2026-07-23",
     {"machos de ceba": 9071, "hembras de levante": 8700,
      "machos de levante": 9517, "hembras de vientre": 8453},
     {}),
]


def main():
    fallos = 0
    for nombre, html, fecha, esperados, extras in CASOS:
        parsed = parse_article(html)
        if not parsed:
            print(f"FALLA {nombre}: el parser no reconoció el boletín")
            fallos += 1
            continue
        published, promedios, got_extras = parsed
        if published.date().isoformat() != fecha:
            print(f"FALLA {nombre}: fecha {published.date()} ≠ {fecha}")
            fallos += 1
        for clave, valor in esperados.items():
            if promedios.get(clave) != valor:
                print(f"FALLA {nombre}: {clave} = "
                      f"{promedios.get(clave)} ≠ {valor}")
                fallos += 1
        if got_extras != extras:
            print(f"FALLA {nombre}: extras {got_extras} ≠ {extras}")
            fallos += 1
        if not fallos:
            print(f"ok {nombre}: {promedios}")
    # Una nota que NO es el boletín semanal no debe parsearse jamás.
    if parse_article('<html><script>{"datePublished":"2026-07-24T10:00:00-05:00"}'
                     '</script><body><p>El precio del ganado subió en '
                     'Antioquia.</p></body></html>') is not None:
        print("FALLA: una nota sin Asosubastas fue aceptada como boletín")
        fallos += 1
    print("TODO OK" if not fallos else f"{fallos} FALLAS")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
