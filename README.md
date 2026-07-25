# Precios de referencia — DigiFinca

Catálogo público de precios del kilo de ganado en pie (COP) que la app
DigiFinca consulta por internet. La app lo lee de:

```
https://raw.githubusercontent.com/Axenor-Corp/digifinca-precios/main/precios.json
```

## Se actualiza SOLO — nadie tiene que tocar nada

Un robot (GitHub Actions, `.github/workflows/actualizar-precios.yml`) corre
**todos los días a las 6:00 a. m. hora de Colombia**:

1. Busca el boletín semanal de **Asosubastas** publicado en Agronegocios.co
   (el mismo que difunde Fedegán).
2. Extrae el precio promedio por categoría (macho de ceba, hembra de levante,
   macho de levante, hembra de vientre).
3. Reescribe `precios.json` **solo si el boletín es más nuevo** que el vigente,
   y hace commit.
4. Los teléfonos con internet lo toman solos: la app consulta al abrir, al
   volver del fondo y al abrir "Precio y objetivo".

El boletín sale un día variable de la semana; por eso se revisa a diario y se
publica únicamente cuando hay novedad. También se puede lanzar a mano desde la
pestaña **Actions → Actualizar precios → Run workflow**.

## Por qué no puede publicar una cifra equivocada

- **Pruebas antes de correr**: `test_update_precios.py` valida el extractor
  contra las dos redacciones reales del medio. Si la fuente cambia de estilo y
  el extractor empieza a leer mal, el robot **falla y no publica**.
- **Rango**: se descarta cualquier promedio fuera de $5.000–$20.000 por kilo.
- **Salto brusco**: si una categoría variara más de 25 % contra el catálogo
  vigente, no se publica y queda la alerta en el log (el precio semanal se
  mueve unos pocos puntos).
- **Nunca retrocede**: un boletín con fecha más vieja que el vigente se ignora,
  tanto aquí como en la app.
- **Categorías obligatorias**: sin macho de ceba y hembra de levante no se
  publica nada.
- Si la fuente está caída, no pasa nada: queda el catálogo anterior y la app
  avisa al ganadero cuando la referencia pasa de 6 semanas.

## Revisar que esté vivo

**Actions** en este repo muestra la corrida de cada día (verde = revisó;
"Sin cambios que publicar" es lo normal casi todos los días). El historial de
commits de `precios.json` es el registro de precios publicados.

Una corrida en **rojo** significa que el robot encontró algo raro y prefirió no
publicar (la fuente cambió de redacción, o una cifra saltaría más de 25 %). El
log dice cuál fue y con qué artículo; se corrige el extractor o se edita el
precio a mano.

GitHub **desactiva los workflows programados** de un repo sin actividad durante
60 días y avisa por correo; si pasa, basta con entrar a Actions y darle
"Enable workflow".

## Editar a mano (excepcional)

Se puede editar `precios.json` directamente en GitHub; el robot respeta el
archivo y solo lo pisa cuando encuentra un boletín **más nuevo** que la `fecha`
que quedó escrita.

Formato: el `Codable` de `PriceReference` en el repo de la app iOS
(`DigiFinca/Services/PriceReference.swift`). Al publicar una versión nueva de
la app, copiar este JSON al catálogo empacado (`PriceReference.bundled`) para
que un teléfono sin internet estrene la referencia más reciente.
