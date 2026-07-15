import boa.contracts.vyper.vyper_contract as _vc

# titanoboa 0.2.7 crashes while dumping certain HashMap storage layouts when it builds the contract
# repr used in a revert error message (StorageVar.get -> "'BoolT' object has no attribute 'key_type'").
# The revert itself is unaffected; use a lightweight repr in these tests so boa.reverts works normally.
_vc.VyperContract.__repr__ = lambda self: f"<{getattr(self, 'contract_name', 'VyperContract')} {self.address}>"
