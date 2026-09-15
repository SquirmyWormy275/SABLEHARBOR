import copy
import json
import unittest

from .shipment import SOURCE, validate


class ShipmentTest(unittest.TestCase):
    def test_valid_synthetic_qualification(self):
        self.assertEqual(validate(json.loads(SOURCE.read_text()))["checks"], 8)

    def test_changed_quantity_party_time_measurement_or_training_denied(self):
        source = json.loads(SOURCE.read_text())
        for mutate in [
            lambda d: d.update(carrier_id="ARU"),
            lambda d: d.update(available_on="2026-08-31"),
            lambda d: d["material"].update(contained_u3o8_lb="400"),
            lambda d: d["survey"].update(surface_max_msv_h="3"),
            lambda d: d["survey"].update(transport_index="0.0"),
            lambda d: d["survey"].update(max_wipe_activity_bq="9999"),
            lambda d: d["checks"].pop(),
            lambda d: d["training"][0].update(completed_on="2026-09-14"),
            lambda d: d["events"][1].update(event_at="2026-09-12T08:00:00-06:00"),
        ]:
            d = copy.deepcopy(source)
            mutate(d)
            with self.assertRaises(ValueError):
                validate(d)
