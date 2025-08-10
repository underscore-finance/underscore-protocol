from scripts.utils.migration import Migration
from boa.contracts.abi.abi_contract import ABIContractFactory


def migrate(migration: Migration):
    hq = migration.get_address("UndyHq")
    migration.deploy(
        'RipeLego',
        hq,
        migration.blueprint.INTEGRATION_ADDYS["RIPE_HQ_V1"],
    )
