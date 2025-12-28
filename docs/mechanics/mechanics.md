# Mechanics and Other Useful Info

## Building Degradation

The following was borrowed from [MoonSugarTravels degradation spreadsheet](https://docs.google.com/spreadsheets/d/1ELsfw4ii1hQFWDd-BL4JzwqHc-wGVXbJtvAeprv0pZ0)

### Efficiency Formula

```
η = 0.33 + 0.67 / (1 + e^((1789/25000) × (D - 100.87)))
```

Where:
- η = condition/efficiency (range: 0.33 to 1.0)
- D = days since last repair
- 100.87 = inflection point (note: may be 107.87 due to a game bug)

Efficiency timeline:
- Days 0-30: ~100% (negligible loss)
- Day 60: noticeable drop begins
- Day 90: falls below 80%
- Day 180: approaches floor of 33%

### Repair Cost Formula

```
RepairCost(material) = floor(BuildingCost(material) × D / 180)
```

- Applied independently to each construction material
- Includes environmental materials (SEA, INS, TSH, HSE, AEF, MGC) - these are required for every repair, not just initial construction
- At D=180, repair cost equals full building cost
- No difference between repair and demolish/rebuild

### Optimal Repair Interval

Simple buildings (single dominant material):
```
OptimalInterval = 180 / BuildingCost(material)
```

Examples:
- EXT (16 BSE): ~11.25 days
- RIG (12 BSE): ~15 days
- FRM (4 BBH + 4 BSE): ~45 days

Complex buildings require value-weighted analysis across all materials, optimizing for the point where daily profit minus amortized repair cost is maximized.

### Multi-Building Bases

- Game tracks each building's condition individually
- Production line efficiency = average of all buildings of that type
- Orders take same time regardless of which building slot executes them

## COGM (Cost of Goods Manufactured)

The following was borrowed from [Benten / Katoa Welcome Guide](https://docs.google.com/document/u/0/d/10qdF6wEpZshm-ErQmjyELfjcDpuXh4ZJjlB_1Wcibk4)

COGM = total cost to produce one unit of a material. Components:

1. Workforce consumables - DW, RAT, OVE (and luxuries) for your workers
2. Input materials - ingredients consumed by the recipe (none for extractors)
3. Building degradation - amortized repair costs

### Calculation

```
COGM = (daily consumable cost + daily input cost + daily degradation cost) / units produced per day
```

### Example: EXT producing GAL on Katoa

* 60 pioneers → 565.68 CIS/day consumables
* 116 CIS/day degradation
* 12.79 GAL/day output
* COGM = 53.29 CIS/unit

**Key insight:** Compare COGM to market price. If market < COGM, buy instead of produce.

### Ways to Lower COGM

* Increase production speed (experts, luxury consumables like COF)
* Reduce input/consumable costs (self-produce or find cheaper sources)

## RAT Recipes

Made in **Food Processor (FP)**, 6 hours, produces **10 RAT**

All RAT recipes require 3 ingredients (1 of each):

| Base Grain | Protein          | Supplement |
|------------|------------------|------------|
| GRN or MAI | ALG, BEA, or MUS | NUT or VEG |

12 valid combinations:

| #   | Inputs          |
|-----|-----------------|
| 1   | GRN + ALG + NUT |
| 2   | GRN + ALG + VEG |
| 3   | GRN + BEA + NUT |
| 4   | GRN + BEA + VEG |
| 5   | MAI + ALG + NUT |
| 6   | MAI + ALG + VEG |
| 7   | MAI + BEA + NUT |
| 8   | MAI + BEA + VEG |
| 9   | GRN + MUS + NUT |
| 10  | GRN + MUS + VEG |
| 11  | MAI + MUS + NUT |
| 12  | MAI + MUS + VEG |

