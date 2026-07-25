#!/usr/bin/env python3
"""Actualiza precios.json con el último boletín semanal de Asosubastas.

Corre a diario en GitHub Actions (sin dependencias: solo stdlib). Descubre el
artículo semanal de precios en Agronegocios.co (grupo La República, que publica
el boletín de Asosubastas difundido por Fedegán), extrae los promedios por
categoría y reescribe precios.json SOLO si el boletín es más nuevo que el
vigente. Ante cualquier duda (página caída, redacción rara, cifras absurdas)
no toca nada: la app tolera un catálogo viejo y lo dice, pero nunca debe
recibir una cifra inventada.
"""

import json
import re
import sys
import unicodedata
import urllib.request
from datetime import datetime, timezone

MERCADOS_URL = "https://www.agronegocios.co/mercados"
RSS_URL = "https://www.agronegocios.co/rss"
UA = {"User-Agent": "Mozilla/5.0 (DigiFinca precios bot)"}

# Categorías del boletín → nombre como lo muestra la app.
CATEGORIAS = [
    ("machos de ceba", "Macho de ceba (gordo)"),
    ("hembras de levante", "Hembra de levante"),
    ("machos de levante", "Macho de levante"),
    ("hembras de vientre", "Hembra de vientre"),
]

# Un promedio fuera de este rango es un error de extracción, no un precio.
MIN_COP, MAX_COP = 5_000, 20_000
# Salto máximo aceptable contra el catálogo vigente: el precio semanal se mueve
# unos pocos puntos; un salto mayor es casi seguro un error de lectura, así que
# el bot NO publica y deja el aviso en el log para revisarlo a mano.
MAX_SALTO = 0.25
# El boletín es SEMANAL: si pasan 3 semanas sin uno nuevo, la fuente cambió y
# hay que revisar — el robot lo grita en vez de dejar los precios congelados.
DIAS_ALERTA = 21

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                timeout=30) as r:
        return r.read().decode("utf-8", errors="ignore")


def plain_text(html):
    text = re.sub(r"<[^>]+>", " ", html)
    text = (text.replace("&aacute;", "á").replace("&eacute;", "é")
                .replace("&iacute;", "í").replace("&oacute;", "ó")
                .replace("&uacute;", "ú").replace("&ntilde;", "ñ")
                .replace("&amp;", "&").replace("&quot;", '"')
                .replace("&#36;", "$").replace("&nbsp;", " "))
    return re.sub(r"\s+", " ", text)


def sin_tildes(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def cop(s):
    """'$9.517' / '9.517,50' → 9517 (formato es-CO: punto = miles)."""
    return int(s.replace(".", "").split(",")[0])


def discover_article_urls():
    """URLs candidatas del boletín, la más NUEVA primero (el id Arc crece)."""
    urls = {}
    for source in (MERCADOS_URL, RSS_URL):
        try:
            html = fetch(source)
        except Exception as e:
            print(f"aviso: no se pudo leer {source}: {e}")
            continue
        for m in re.finditer(
                r"(?:https://www\.agronegocios\.co)?(/mercados/[a-z0-9-]*"
                r"precio-del-ganado[a-z0-9-]*-(\d+))", html):
            urls[int(m.group(2))] = "https://www.agronegocios.co" + m.group(1)
    return [urls[k] for k in sorted(urls, reverse=True)]


def parse_article(html):
    """(fecha_publicacion, {clave_categoria: promedio}, extras) o None."""
    m = re.search(r'"datePublished":"([^"]+)"', html)
    if not m:
        return None
    published = datetime.fromisoformat(m.group(1)).astimezone(timezone.utc)

    text = sin_tildes(plain_text(html))
    if "asosubastas" not in text:
        return None  # otro tipo de nota de precios: no es el boletín semanal

    claves = [c for c, _ in CATEGORIAS]
    promedios = {}
    for clave, _ in CATEGORIAS:
        otras = [c for c in claves if c != clave]
        mejor = None  # (prioridad, valor); prioridad 1 gana sobre 2
        for hit in re.finditer(re.escape(clave), text):
            ventana = text[hit.end():hit.end() + 200]
            # Si JUSTO ANTES de la categoría se habla de un extremo ("el precio
            # más caro ... para los machos de ceba fue de $X"), esa cifra es un
            # máximo/mínimo, no el promedio: saltar esta mención.
            prefijo = text[max(0, hit.start() - 45):hit.start()]
            if any(p in prefijo for p in ("mas caro", "mas bajo",
                                          "minimo", "maximo")):
                continue

            def limpio(hasta):
                """La ventana hasta el match no menciona OTRA categoría (si la
                menciona, la cifra es de esa otra categoría, no de esta)."""
                tramo = ventana[:hasta]
                return not any(o in tramo for o in otras)

            # Prioridad 1: "al pasar de $A a $B" / "avanzó de $A a $B" —
            # el valor VIGENTE es B (el A es la semana anterior).
            m = re.search(r"(?:pasar|avanzo|paso|cayo|bajo|subio) de "
                          r"\$\s?[\d.,]+ a \$\s?([\d.,]+)", ventana)
            if m and limpio(m.start()):
                mejor = (1, cop(m.group(1)))
                break
            # Prioridad 2: "fue de $X" / "alcanzó $X" / "se registró en $X" /
            # "se ubicó en $X" — sin cruzar a otra categoría ni a la frase de
            # "la semana anterior" (evita capturar el valor viejo).
            m = re.search(r"(?:fue de|alcanzo|se registro en|se ubico en|"
                          r"con un valor(?: promedio)? de)\s?\$\s?([\d.,]+)",
                          ventana)
            if m and limpio(m.start()) \
                    and "semana anterior" not in ventana[:m.start()] \
                    and (mejor is None or mejor[0] > 2):
                mejor = (2, cop(m.group(1)))
                # seguir buscando: una mención posterior podría dar prioridad 1
        if mejor:
            promedios[clave] = mejor[1]
    # Rango observado del macho de ceba (si el artículo lo trae en el lede).
    extras = {}
    m = re.search(r"mas caro del kilo para los machos de ceba fue de "
                  r"\$\s?([\d.,]+),? y el mas bajo alcanzo \$\s?([\d.,]+)", text)
    if m:
        extras["ceba_max"] = cop(m.group(1))
        extras["ceba_min"] = cop(m.group(2))
    return published, promedios, extras


def alerta_si_esta_viejo(fecha_vigente):
    """Falla (rojo en Actions + correo) si el catálogo lleva demasiado sin
    renovarse: significa que la fuente cambió y el robot dejó de encontrar
    boletines. Sin esto, los precios se congelarían EN SILENCIO."""
    dias = (datetime.now(timezone.utc) - fecha_vigente).days
    if dias > DIAS_ALERTA:
        print(f"ALERTA: el catálogo lleva {dias} días sin renovarse "
              f"(último boletín {fecha_vigente.date()}). Revisar si la fuente "
              f"cambió de formato o de dirección.")
        return 1
    print(f"catálogo al día ({dias} días desde el último boletín)")
    return 0


def main():
    with open("precios.json", encoding="utf-8") as f:
        vigente = json.load(f)
    fecha_vigente = datetime.fromisoformat(
        vigente["fecha"].replace("Z", "+00:00"))

    for url in discover_article_urls()[:5]:
        try:
            parsed = parse_article(fetch(url))
        except Exception as e:
            print(f"aviso: fallo leyendo {url}: {e}")
            continue
        if not parsed:
            continue
        published, promedios, extras = parsed
        # Validación dura: cifras en rango y las dos categorías principales.
        promedios = {k: v for k, v in promedios.items()
                     if MIN_COP <= v <= MAX_COP}
        if ("machos de ceba" not in promedios
                or "hembras de levante" not in promedios):
            print(f"aviso: {url} sin las categorías principales; se ignora")
            continue
        if published <= fecha_vigente:
            print(f"sin cambios: el boletín de {published.date()} no es más "
                  f"nuevo que el vigente ({fecha_vigente.date()})")
            return alerta_si_esta_viejo(fecha_vigente)
        # Salto absurdo contra el catálogo vigente ⇒ casi seguro un error de
        # lectura (la fuente cambió de redacción): NO publicar, avisar.
        previos = {e["categoria"]: e["copPorKg"] for e in vigente["entradas"]}
        for clave, nombre in CATEGORIAS:
            antes, ahora = previos.get(nombre), promedios.get(clave)
            if antes and ahora and abs(ahora - antes) / antes > MAX_SALTO:
                print(f"ALERTA: {nombre} saltaría de ${antes} a ${ahora} "
                      f"(>{int(MAX_SALTO * 100)}%). No se publica; revisar "
                      f"{url}")
                return 1
        entradas = []
        for clave, nombre in CATEGORIAS:
            if clave not in promedios:
                continue
            e = {"categoria": nombre, "copPorKg": promedios[clave],
                 "minCop": None, "maxCop": None}
            if clave == "machos de ceba" and "ceba_min" in extras:
                if extras["ceba_min"] <= e["copPorKg"] <= extras["ceba_max"]:
                    e["minCop"] = extras["ceba_min"]
                    e["maxCop"] = extras["ceba_max"]
            entradas.append(e)
        d = published.date()
        nuevo = {
            "pais": "CO",
            "paisNombre": "Colombia",
            "fuente": "Subastas ganaderas (Fedegán/Asosubastas)",
            "semana": f"boletín del {d.day} de {MESES[d.month - 1]} de {d.year}",
            "fecha": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "entradas": entradas,
        }
        with open("precios.json", "w", encoding="utf-8") as f:
            json.dump(nuevo, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"ACTUALIZADO al boletín del {d}: "
              + ", ".join(f"{e['categoria']} ${e['copPorKg']}" for e in entradas))
        return
    print("sin cambios: ningún boletín nuevo utilizable")
    return alerta_si_esta_viejo(fecha_vigente)


if __name__ == "__main__":
    sys.exit(main())
