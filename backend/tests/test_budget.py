import pytest
from pydantic import ValidationError

from app.services.budget import BudgetLineIn, compute_totals


def unit(id, qty, price):
    return {"id": id, "kind": "unit", "quantity": qty, "unit_price": price, "total": None, "refs": []}


def lump(id, total):
    return {"id": id, "kind": "lump_sum", "quantity": None, "unit_price": None, "total": total, "refs": []}


def pct(id, percent, refs):
    return {"id": id, "kind": "percentage", "quantity": percent, "unit_price": None, "total": None, "refs": refs}


# Adele's example (Excel): tasks 1-9, then Sicurezza 1% and Gestione amministrativa 4%.
EXAMPLE = [
    unit(1, 8, 199.6),        # Project Management
    unit(2, 30, 161.29),      # Progettazione e sviluppo web
    unit(3, 0, 161.29),       # Messa in esercizio
    unit(4, 101, 137.55),     # Assistenza
    unit(5, 20, 350),         # Trasferte
    unit(6, 108, 50),         # Hosting
    unit(7, 0.25, 4838.7),    # Gestione sistemistica
    unit(8, 20, 137.55),      # Contenuti - immagini
    unit(9, 25, 137.55),      # Contenuti - schede
    lump(10, 0),              # Traduzioni (a cottimo)
    pct(11, 1, [1, 2, 3, 4, 5, 6, 7, 8, 9]),     # Sicurezza
    pct(12, 4, [1, 2, 3, 4, 7, 8, 9]),           # Gestione amministrativa
]


def test_example_from_excel():
    totals = compute_totals(EXAMPLE)
    assert totals[1] == 1596.8 and totals[4] == 13892.55 and totals[7] == 1209.675
    assert totals[10] == 0
    assert totals[11] == 401.2748
    assert round(totals[12], 3) == 1109.099


def test_percentage_of_a_percentage_row():
    totals = compute_totals([lump(1, 1000), pct(2, 10, [1]), pct(3, 50, [1, 2])])
    assert totals[2] == 100 and totals[3] == 550


def test_cycle_and_missing_reference_give_no_total():
    totals = compute_totals([pct(1, 10, [2]), pct(2, 10, [1]), pct(3, 10, [99])])
    assert totals == {1: None, 2: None, 3: None}


@pytest.mark.parametrize("data", [
    {"kind": "unit", "task": "A", "quantity": 1},                       # missing price
    {"kind": "lump_sum", "task": "A"},                                  # missing total
    {"kind": "percentage", "task": "A", "quantity": 4},                 # no tasks selected
    {"kind": "unit", "task": "", "quantity": 1, "unit_price": 1},       # empty task
])
def test_required_fields_per_kind(data):
    with pytest.raises(ValidationError):
        BudgetLineIn(**data)
