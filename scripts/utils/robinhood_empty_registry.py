ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def _address(value):
    return str(value.address if hasattr(value, "address") else value)


def empty_registry_constructor_args(migration, hq):
    """Return the one approved constructor shape for empty RH registries.

    The RH deployer is also the initial UndyHq governor, and LocalGov rejects
    installing that same address as a duplicate local governor. Zero leaves
    the deployer authorized through UndyHq while requiring no later local-gov
    relinquishment transaction.
    """
    params = migration.blueprint.PARAMS
    zero_address = migration.blueprint.CONSTANTS.ZERO_ADDRESS
    if _address(zero_address).lower() != ZERO_ADDRESS.lower():
        raise RuntimeError("Robinhood ZERO_ADDRESS constant is invalid")
    return (
        hq,
        zero_address,
        params["UNDY_HQ_MIN_REG_TIMELOCK"],
        params["UNDY_HQ_MAX_REG_TIMELOCK"],
    )


def validate_empty_robinhood_registry(
    registry,
    hq,
    migration,
    *,
    name: str,
    registry_description: str,
):
    """Authenticate constructor state for an intentionally empty registry."""
    hq_address = _address(hq).lower()
    if _address(registry.getUndyHq()).lower() != hq_address:
        raise RuntimeError(f"Robinhood {name} is bound to the wrong UndyHq")
    if _address(registry.getUndyHqFromGov()).lower() != hq_address:
        raise RuntimeError(
            f"Robinhood {name} governance is bound to the wrong UndyHq"
        )

    if _address(registry.governance()).lower() != ZERO_ADDRESS.lower():
        raise RuntimeError(f"Robinhood {name} local governance is not zero")
    expected_governors = [_address(hq.governance()).lower()]
    actual_governors = [
        _address(governor).lower() for governor in registry.getGovernors()
    ]
    if actual_governors != expected_governors:
        raise RuntimeError(
            f"Robinhood {name} effective governors are {actual_governors!r}, "
            f"expected {expected_governors!r}"
        )
    if registry.numGovChanges() != 0 or registry.hasPendingGovChange():
        raise RuntimeError(f"Robinhood {name} has unexpected governance state")
    pending_gov = registry.pendingGov()
    if (
        _address(pending_gov.newGov).lower() != ZERO_ADDRESS.lower()
        or pending_gov.initiatedBlock != 0
        or pending_gov.confirmBlock != 0
    ):
        raise RuntimeError(f"Robinhood {name} has latent pending governance")

    params = migration.blueprint.PARAMS
    if (
        registry.govChangeTimeLock()
        != params["UNDY_HQ_MIN_GOV_TIMELOCK"]
        or registry.minGovChangeTimeLock()
        != params["UNDY_HQ_MIN_GOV_TIMELOCK"]
        or registry.maxGovChangeTimeLock()
        != params["UNDY_HQ_MAX_GOV_TIMELOCK"]
    ):
        raise RuntimeError(
            f"Robinhood {name} has unexpected governance timelocks"
        )
    if (
        registry.registryChangeTimeLock() != 0
        or registry.minRegistryTimeLock()
        != params["UNDY_HQ_MIN_REG_TIMELOCK"]
        or registry.maxRegistryTimeLock()
        != params["UNDY_HQ_MAX_REG_TIMELOCK"]
    ):
        raise RuntimeError(f"Robinhood {name} has unexpected registry timelocks")

    if registry.numAddrs() != 1 or registry.getNumAddrs() != 0:
        raise RuntimeError(f"Robinhood {name} registry is not empty")
    if registry.getRegistryDescription() != registry_description:
        raise RuntimeError(
            f"Robinhood {name} has unexpected registry description"
        )
    if registry.isPaused() is not False or registry.canMintUndy() is not False:
        raise RuntimeError(f"Robinhood {name} has unexpected department state")
