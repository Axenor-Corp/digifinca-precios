# Precios de referencia — DigiFinca

Catálogo público de precios del kilo de ganado en pie (COP) que la app
DigiFinca consulta por internet. La app lo lee de:

```
https://raw.githubusercontent.com/Axenor-Corp/digifinca-precios/main/precios.json
```

## Actualizar (cada semana, ~2 minutos)

1. Cifra nueva de la semana: [Fedegán — precios](https://www.fedegan.org.co/estadisticas/precios),
   [CONtexto Ganadero](https://www.contextoganadero.com) o
   [Agronegocios](https://www.agronegocios.co) publican el promedio semanal de
   las subastas (Asosubastas): macho de ceba y hembra de levante, COP/kg en pie.
2. Editar `precios.json` acá en GitHub (botón del lápiz): cambiar `copPorKg`,
   `minCop`/`maxCop`, el texto de `semana` y la `fecha` — fin de la semana de
   referencia, formato `AAAA-MM-DDT12:00:00Z`. Commit directo a `main`.
3. Listo: los teléfonos con internet toman el precio nuevo solos (la app
   consulta al abrir, al volver del fondo y al abrir "Precio y objetivo").

## Reglas que la app impone (a prueba de errores)

- Un catálogo con `fecha` más VIEJA que el vigente se ignora — no se puede
  retroceder la referencia por equivocación.
- JSON inválido, `entradas` vacías o respuestas de más de 100 KB se ignoran.
- Solo poner categorías con PROMEDIO real publicado (no un mínimo como si
  fuera promedio).

Formato exacto: el `Codable` de `PriceReference` en el repo de la app iOS
(`DigiFinca/Services/PriceReference.swift`). Al publicar una versión nueva de
la app, copiar este JSON al catálogo empacado (`PriceReference.bundled`).
