# Méthodologie fiscale

🌐 [Deutsch](../de/tax-methodology.md) · [English](../en/tax-methodology.md) · **Français** · [Español](../es/tax-methodology.md)

> **Ni conseil fiscal ni conseil juridique.** Cette page décrit la manière dont le XMR-Ledger calcule et s'appuie
> sur la doctrine de l'administration fiscale **allemande** (état 11/2026). Elle ne remplace pas l'examen de votre
> situation individuelle ; d'autres pays appliquent d'autres règles. La [version allemande](../de/tax-methodology.md)
> fait foi.

L'outil fournit des chiffres et des justificatifs ; la qualification du cas individuel incombe au contribuable.
La base est la doctrine administrative exposée dans la circulaire du ministère fédéral allemand des Finances
(BMF-Schreiben) du 6 mars 2025 (IV C 1 - S 2256/00042/064/043, « Einzelfragen zur ertragsteuerrechtlichen
Behandlung bestimmter Kryptowerte », qui remplace la circulaire du 10 mai 2022 ; création de blocs : n° 35 et
suivants).

## Entrées (revenus)

- Les revenus issus de la création de blocs sont – selon les circonstances – des revenus industriels et
  commerciaux (§ 15 EStG) ou d'autres revenus de prestations (§ 22 n° 3 EStG) ; cela vaut aussi pour les
  crypto-actifs reçus de pools de minage.
- Évaluation au **cours du marché au moment de la réception** (de manière simplifiée : à l'inscription dans le
  portefeuille).
- Mise en œuvre : moment = heure du bloc de la transaction coinbase ; cours = cours CoinGecko à 5 minutes le plus
  proche (écart max. 15 min), sinon cours du jour à 00:00 UTC, sinon saisie manuelle. La source est enregistrée
  pour chaque entrée.
- Montant en EUR arrondi au centime par entrée, puis additionné.
- Seules les entrées coinbase comptent ; les autres entrées (p. ex. la monnaie rendue de vos propres transferts)
  sont listées mais pas comptées comme revenus.

## Dépenses : électricité (Werbungskosten / Betriebsausgaben)

- **Surconsommation** mesurée par appareil × **temps de minage** enregistré automatiquement × **prix de
  l'électricité**.
- Mesure : `powermetrics` charge − repos, +10 % de pertes de l'alimentation, arrondi vers le haut pour la RAM ;
  la date et la méthode figurent dans `config.toml` (`note`) et dans le rapport (feuille **Geräte**, appareils).
- Les watts et le tarif sont figés à chaque enregistrement ; les modifications ultérieures n'ont d'effet que pour
  l'avenir.
- Facultatif : surconsommation du NAS (`nas_extra_watts`) – actuellement 0, le NAS fonctionnant de toute façon.
- Non pris en compte : l'amortissement du matériel existant (les ordinateurs sont aussi utilisés à titre privé).

## Seuil d'exonération du § 22 n° 3 EStG

Le rapport vérifie si le résultat (revenus − électricité) est **inférieur à 256 €**. Ce seuil (Freigrenze, et non
un abattement : une fois atteint, la totalité est imposable) s'applique à l'ensemble des revenus de prestations
de l'année. Les pertes ne sont imputables que sur des revenus relevant du § 22 n° 3 (§ 22 n° 3, phrases 3 et 4
EStG, § 10d applicable par analogie). L'intention de réaliser un bénéfice doit être appréciée séparément en cas
de résultat durablement négatif.

## Cession (§ 23, al. 1, phrase 1, n° 2 EStG)

- Chaque paiement constitue une **acquisition** ; coût d'acquisition = valeur à la réception.
- Ordre de sortie **FIFO** par portefeuille (le portefeuille de minage).
- **Délai de détention d'un an :** « exonéré à partir du » (steuerfrei ab) = le jour suivant l'expiration d'un an
  à compter de la réception (§§ 187, al. 1, 188, al. 2 BGB ; 29/02 → 01/03).
- L'échange contre d'autres crypto-actifs et le paiement en XMR sont aussi des cessions ; produit = valeur en EUR
  de ce qui est reçu.
- Un transfert vers votre propre portefeuille n'est pas une cession ; les lots (coût d'acquisition, date) figurent
  dans le rapport afin de pouvoir être reportés dans le portefeuille de destination.
- Seuil d'exonération de **1 000 €** (§ 23, al. 3, phrase 5 EStG) pour l'ensemble des opérations de cession
  privées de l'année.

## Justificatifs

- Rapport annuel Excel (avec la version du ledger qui l'a produit), CSV des entrées.
- Export du portefeuille : `export_transfers in output=…` dans `monero-wallet-cli`.
- Preuve P2Pool : mini.p2pool.observer (saisir l'adresse).
- Justification de l'origine des fonds pour les banques et plateformes : adresse de minage, paiements, coûts
  d'électricité.

## Réglementation

À partir du **10 juillet 2027** (règlement européen anti-blanchiment, règlement (UE) 2024/1624, art. 79), les
prestataires de services sur crypto-actifs réglementés dans l'UE ne pourront plus tenir de comptes en
« privacy coins » comme Monero. La détention dans votre propre portefeuille et le minage restent autorisés ; une
conversion en euros ne serait alors possible qu'en deux étapes (XMR → BTC de manière décentralisée, puis
plateforme réglementée).

## Autres pays

Le ledger n'applique pour l'instant que les règles allemandes. Des profils fiscaux pour d'autres pays (délais de
détention, seuils, méthodes de calcul du coût d'acquisition) figurent dans la [feuille de route](../../ROADMAP.md)
– les contributions de personnes qui connaissent les règles de leur pays sont les bienvenues.
