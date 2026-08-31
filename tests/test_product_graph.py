from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import tomllib
import unittest

from product_graph import (
    Dependency,
    Domain,
    Epic,
    Product,
    ProductGraph,
    ProductGraphNotFound,
    ProductGraphValidationError,
    Wave,
)


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "docs" / "product" / "PRODUCT_GRAPH_BOOTSTRAP.toml"


def bootstrap_data() -> dict[str, object]:
    with BOOTSTRAP.open("rb") as handle:
        return tomllib.load(handle)


class ProductGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.graph = ProductGraph.load(BOOTSTRAP)

    def test_real_bootstrap_loads_as_read_only_snapshot(self) -> None:
        self.assertIsInstance(self.graph.product, Product)
        self.assertEqual("PRODUCT-AITOS", self.graph.product.id)
        self.assertEqual("AI Trading Operating System", self.graph.product.name)
        self.assertEqual(21, len(self.graph.domains()))
        self.assertTrue(all(isinstance(item, Domain) for item in self.graph.domains()))
        self.assertEqual(13, len(self.graph.waves()))
        self.assertTrue(all(isinstance(item, Wave) for item in self.graph.waves()))
        self.assertEqual(14, len(self.graph.epics()))
        self.assertTrue(all(isinstance(item, Epic) for item in self.graph.epics()))
        self.assertTrue(self.graph.is_read_only_snapshot)

    def test_get_by_id_and_explicit_not_found(self) -> None:
        self.assertEqual("Product OS", self.graph.get("W1").title)
        self.assertEqual(
            "Product Galaxy / Living Roadmap",
            self.graph.get("DOM-PRODUCT-GALAXY").title,
        )
        with self.assertRaises(ProductGraphNotFound):
            self.graph.get("MISSING")

    def test_status_filtering_uses_product_master_vocabulary(self) -> None:
        planned_ids = {item.id for item in self.graph.by_status("PLANNED")}
        self.assertIn("W1", planned_ids)
        self.assertIn("EPIC-W1-CANONICAL-PRODUCT-GRAPH", planned_ids)
        self.assertIn("DOM-PRODUCT-GALAXY", planned_ids)
        self.assertEqual((), self.graph.by_status("EIGHTY_PERCENT"))

    def test_dependency_lookup_exposes_both_directions(self) -> None:
        dependencies = self.graph.dependencies("W1")
        self.assertEqual(1, len(dependencies))
        self.assertIsInstance(dependencies[0], Dependency)
        self.assertEqual("W0", dependencies[0].depends_on)
        self.assertEqual("W1", self.graph.dependents("W0")[0].source_id)

    def test_locks_and_capital_authority_remain_fail_closed(self) -> None:
        locked_ids = {item.id for item in self.graph.locked()}
        for subject in ("PAPER", "LIMITED_LIVE", "LIVE"):
            lock = next(item for item in self.graph.locked() if getattr(item, "subject", None) == subject)
            with self.subTest(subject=subject):
                self.assertTrue(lock.locked)
                self.assertEqual("LOCKED", lock.status)
        self.assertIn("W7", locked_ids)
        self.assertIn("W12", locked_ids)
        self.assertIn("DOM-OPERATIONS-CENTER", locked_ids)
        self.assertFalse(self.graph.capital_authority)

    def test_current_and_next_waves_follow_status_and_readiness(self) -> None:
        self.assertEqual("W0", self.graph.current_wave().id)
        self.assertEqual("W1", self.graph.next_wave().id)

    def test_malformed_toml_and_shape_fail_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            malformed = Path(temp_dir) / "graph.toml"
            malformed.write_text("domains = [", encoding="utf-8")
            with self.assertRaisesRegex(ProductGraphValidationError, "cannot load Product Graph"):
                ProductGraph.load(malformed)

        data = bootstrap_data()
        data["domains"] = {"id": "NOT-A-LIST"}
        with self.assertRaisesRegex(ProductGraphValidationError, "E_COLLECTION_TYPE"):
            ProductGraph.load(data)

    def test_unresolved_dependencies_and_duplicate_ids_fail_validation(self) -> None:
        data = bootstrap_data()
        data["dependencies"][0]["depends_on"] = "MISSING"
        with self.assertRaisesRegex(ProductGraphValidationError, "E_DEPENDENCY_TARGET_MISSING"):
            ProductGraph.load(data)

        data = bootstrap_data()
        data["domains"][1]["id"] = data["domains"][0]["id"]
        with self.assertRaisesRegex(ProductGraphValidationError, "E_ID_DUPLICATE"):
            ProductGraph.load(data)

    def test_loading_and_queries_do_not_mutate_source_or_input(self) -> None:
        before = BOOTSTRAP.read_bytes()
        graph = ProductGraph.load(BOOTSTRAP)
        graph.by_status("LOCKED")
        graph.dependencies("W1")
        self.assertEqual(before, BOOTSTRAP.read_bytes())

        data = bootstrap_data()
        original = deepcopy(data)
        ProductGraph.load(data)
        self.assertEqual(original, data)


if __name__ == "__main__":
    unittest.main()
