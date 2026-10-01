# Constantes de la periode test - calcul a la main

Calcul fait a la calculatrice, sans IA.

## Point de depart (deja valide, recopie-le)

TRAIN_END_MS = 1704067200000 (2024-01-01T00:00:00Z, premier open_time du test)

## Nombre de jours de 2024-01-01 (inclus) a 2026-09-01 (exclu)

2024 (bissextile) = 366 jours
2025 = 365 jours
2026, janvier a aout : 243
jan 31 + fev 28 + mars 31 + avril 30 + mai 31 + juin 30 + juil 31 + aout 31 = 243
jours = 974

## Constantes

jours x 86400000 = 84153600000
TEST_END_MS = 1704067200000 + (jours x 86400000) = 1788220800000
TEST_COUNT = jours x 6 = 5844