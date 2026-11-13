"""A model gateway in memory: the fake call and the fixed catalog, one family as the real factories make (ADR 0109)."""

from dataclasses import dataclass, field

from tests.fakes.model_call import FakeModelCallAdapter
from tests.fakes.model_catalog import InMemoryModelCatalogAdapter


@dataclass
class FakeModelGatewayAdapter:
    """Realises the model gateway port with the call and the catalog the test gives."""

    catalog: InMemoryModelCatalogAdapter
    call: FakeModelCallAdapter = field(default_factory=FakeModelCallAdapter)

    def model_call(self) -> FakeModelCallAdapter:
        return self.call

    def model_catalog(self) -> InMemoryModelCatalogAdapter:
        return self.catalog
