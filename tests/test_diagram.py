import unittest

import matplotlib
matplotlib.use("Agg")

from exergyflow import Diagram, DiagramConfig, RouteSegment


class DiagramTests(unittest.TestCase):
    def test_custom_flow_label(self):
        d = Diagram()
        d.add_process("P1")
        d.add_process("P2")
        d.add_flow("F1", 5, label="Q_in", source="P1", target="P2")
        fig, ax = d.draw()
        try:
            texts = [t.get_text() for t in ax.texts]
            self.assertIn("Q_in = 5", texts)
        finally:
            fig.clf()

    def test_negative_flow_rejected(self):
        d = Diagram()
        d.add_process("A")
        d.add_process("B")
        d.add_flow("F", -1, source="A", target="B")
        with self.assertRaises(ValueError):
            d.draw()

    def test_zero_flow_allowed(self):
        d = Diagram()
        d.add_process("A")
        d.add_process("B")
        d.add_flow("F", 0, source="A", target="B")
        fig, ax = d.draw()
        try:
            self.assertIsNotNone(fig)
            self.assertIsNotNone(ax)
        finally:
            fig.clf()

    def test_route_direction_validation(self):
        d = Diagram()
        d.add_process("A", direction="right")
        d.add_process("B", direction="right")
        bad_route = [RouteSegment(kind="rect", length=1.0, direction="left")]
        d.add_flow("F", 1, source="A", target="B", route=bad_route)
        with self.assertRaises(ValueError):
            d.draw()

    def test_flow_label_unit_formatting(self):
        cfg = DiagramConfig(flow_value_format=".1f", flow_value_unit="kW")
        d = Diagram(config=cfg)
        d.add_process("P1")
        d.add_process("P2")
        d.add_flow("F1", 5, source="P1", target="P2")
        fig, ax = d.draw()
        try:
            texts = [t.get_text() for t in ax.texts]
            self.assertIn("F1 = 5.0 kW", texts)
        finally:
            fig.clf()

    def test_process_label_rotation(self):
        d = Diagram()
        d.add_process("P1", label_rotation=30)
        d.add_process("P2")
        d.add_flow("F1", 1, source="P1", target="P2")
        fig, ax = d.draw()
        try:
            rot = None
            for t in ax.texts:
                if t.get_text() == "P1":
                    rot = t.get_rotation()
                    break
            self.assertIsNotNone(rot)
            self.assertAlmostEqual(rot, 30.0)
        finally:
            fig.clf()

    def test_value_only_excludes_units(self):
        cfg = DiagramConfig(flow_value_format=".1f", flow_value_unit="kW", flow_label_mode="value_only")
        d = Diagram(config=cfg)
        d.add_process("P1")
        d.add_process("P2")
        d.add_flow("F1", 5, source="P1", target="P2")
        fig, ax = d.draw()
        try:
            texts = [t.get_text() for t in ax.texts]
            self.assertIn("5.0", texts)
            self.assertNotIn("5.0 kW", texts)
        finally:
            fig.clf()


if __name__ == "__main__":
    unittest.main()
