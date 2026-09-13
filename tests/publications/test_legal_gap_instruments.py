"""Adversarial checks against truncated clauses and incorrectly normalized source text."""
import importlib.util
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / 'tools/legal_gaps/validate.py'
spec = importlib.util.spec_from_file_location('legal_gap_validate', MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_clause_omission_is_detectable():
    blocks = module.source_blocks('# Agreement\n\nPayment is due only after acceptance.\n\nNo lien attaches to customer equipment.\n')
    truncated = module.norm('Agreement Payment is due only after acceptance.')
    assert blocks[0] in truncated
    assert blocks[1] in truncated
    assert blocks[2] not in truncated


def test_link_and_emphasis_do_not_erase_words():
    blocks = module.source_blocks('Retain **all** [source records](records.md), including `native` files.')
    assert blocks == [module.norm('Retain all source records, including native files.')]


def test_html_furniture_cannot_supply_missing_clause():
    parser = module.HTML()
    parser.feed('<aside>No lien attaches.</aside><article><p>Payment terms.</p></article>')
    assert module.norm('No lien attaches') not in module.norm(''.join(parser.text))


def test_table_cells_are_individually_preserved():
    blocks = module.source_blocks('| Holder | USD |\n|---|---:|\n| Nora | 100000 |\n| Seth | 80000 |')
    assert module.norm('100000') in blocks
    assert module.norm('80000') in blocks


def test_normalization_does_not_hide_wrong_amount():
    assert module.norm('$3,000,000') != module.norm('$300,000')


def test_published_package_is_complete():
    assert module.validate() == 0
