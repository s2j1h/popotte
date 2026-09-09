"""Normalisation des unités et arrondis d'achat."""

from app.units import canonical_unit, format_amount, parse_quantity, round_purchase


def test_alias_vers_unite_canonique():
    assert canonical_unit("Grammes") == "g"
    assert canonical_unit("KG") == "kg"
    assert canonical_unit("càs") == "c. à soupe"
    assert canonical_unit("cuillères à café") == "c. à café"
    assert canonical_unit("pièces") == "pièce"
    assert canonical_unit("") == ""


def test_unite_inconnue_est_conservee():
    assert canonical_unit("verre") == "verre"


def test_arrondi_achat():
    assert round_purchase(3.5, "pièce") == 4  # jamais 3,5 œufs
    assert round_purchase(4.0, "pièce") == 4
    assert round_purchase(212.5, "g") == 213
    assert round_purchase(1.201, "kg") == 1.21
    assert round_purchase(1.2, "c. à soupe") == 1.5


def test_saisie_quantite():
    assert parse_quantity("1,5") == 1.5
    assert parse_quantity("2") == 2
    assert parse_quantity("") is None
    assert parse_quantity("abc") is None


def test_affichage():
    assert format_amount(4, "pièce") == "4"
    assert format_amount(1.5, "kg") == "1,5 kg"
    assert format_amount(None, "") == "au goût"
