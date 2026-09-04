from scripts.utils.migration import Migration
from scripts.utils.registry_preconditions import (
    deploy_and_register,
    install_hq_materialization_dependency,
    materialize_contract_runtime,
)

SWITCHBOARD_RUNTIME_CODEHASH = (
    "0x5bd296fff97b5babcb198a82cf9f932f86852ffa432265c98c2479e1672c8e8e"
)
SWITCHBOARD_ALPHA_RUNTIME_CODEHASH = (
    "0x65240af6dd13315bd53c11ac6ac46338353aae43b1eb79d7b51410f7fe3bcade"
)
SWITCHBOARD_BRAVO_RUNTIME_CODEHASH = (
    "0x366e90ac90765e6c2ebc602b988fe0dcba307b6e568b893c82d5b183e52d6001"
)


def _validate_switchboard(switchboard, hq, migration):
    if str(switchboard.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError("Robinhood Switchboard is bound to the wrong UndyHq")
    if str(switchboard.governance()) != migration.blueprint.CONSTANTS.ZERO_ADDRESS:
        raise RuntimeError("Robinhood Switchboard has unexpected local governance")
    if switchboard.getRegistryDescription() != "Switchboard.vy":
        raise RuntimeError(
            "Robinhood Switchboard has an unexpected registry identity"
        )
    if switchboard.numAddrs() < 1 or switchboard.numAddrs() > 3:
        raise RuntimeError("Robinhood Switchboard has unexpected child state")
    if switchboard.registryChangeTimeLock() != 0:
        raise RuntimeError(
            "Robinhood Switchboard registry timelock is already active"
        )
    if (
        switchboard.govChangeTimeLock() != hq.minGovChangeTimeLock()
        or switchboard.numGovChanges() != 0
        or switchboard.hasPendingGovChange()
    ):
        raise RuntimeError("Robinhood Switchboard has unexpected governance state")
    if switchboard.isPaused() or switchboard.canMintUndy():
        raise RuntimeError(
            "Robinhood Switchboard has unexpected department flags"
        )
    if (
        switchboard.minRegistryTimeLock()
        != migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"]
        or switchboard.maxRegistryTimeLock()
        != migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"]
    ):
        raise RuntimeError(
            "Robinhood Switchboard has unexpected registry timelocks"
        )


def _validate_switchboard_module(module, hq, migration, name):
    if str(module.getUndyHq()).lower() != str(hq.address).lower():
        raise RuntimeError(f"Robinhood {name} is bound to the wrong UndyHq")
    if str(module.governance()) != migration.blueprint.CONSTANTS.ZERO_ADDRESS:
        raise RuntimeError(f"Robinhood {name} has unexpected local governance")
    if (
        module.govChangeTimeLock() != hq.minGovChangeTimeLock()
        or module.numGovChanges() != 0
        or module.hasPendingGovChange()
    ):
        raise RuntimeError(f"Robinhood {name} has unexpected governance state")
    if (
        module.minActionTimeLock()
        != migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"]
        or module.maxActionTimeLock()
        != migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"]
        or module.actionTimeLock() != 0
    ):
        raise RuntimeError(f"Robinhood {name} has unexpected action timelocks")
    pending_action = module.pendingActions(1)
    if (
        module.actionId() != 1
        or module.expiration()
        != migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"]
        or pending_action.initiatedBlock != 0
        or pending_action.confirmBlock != 0
        or pending_action.expiration != 0
    ):
        raise RuntimeError(f"Robinhood {name} has latent pending actions")


def migrate(migration: Migration):
    migration.log.h2("Switchboard")
    hq = migration.get_contract("UndyHq")
    registry_args = (
        hq,
        # HQ governance can govern LocalGov children directly. A matching
        # local governor is forbidden by LocalGov.__init__.
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["UNDY_HQ_MIN_REG_TIMELOCK"],
        migration.blueprint.PARAMS["UNDY_HQ_MAX_REG_TIMELOCK"],
    )
    switchboard = deploy_and_register(
        migration,
        hq,
        name="Switchboard",
        args=registry_args,
        description="Switchboard",
        expected_id=4,
        expected_prefix=(
            ("Ledger", migration.get_address("Ledger")),
            ("MissionControl", migration.get_address("MissionControl")),
            ("LegoBook", migration.get_address("LegoBook")),
        ),
        context="before Robinhood Switchboard deployment",
        validate=lambda contract: _validate_switchboard(
            contract,
            hq,
            migration,
        ),
        expected_runtime_codehash=SWITCHBOARD_RUNTIME_CODEHASH,
        runtime_builder=lambda: materialize_contract_runtime(
            migration,
            "Switchboard",
            registry_args,
            prepare=lambda: install_hq_materialization_dependency(
                hq,
                migration,
            ),
        ),
    )

    module_args = (
        hq,
        migration.blueprint.CONSTANTS.ZERO_ADDRESS,
        migration.blueprint.PARAMS["GEN_MIN_CONFIG_TIMELOCK"],
        migration.blueprint.PARAMS["GEN_MAX_CONFIG_TIMELOCK"],
    )
    switchboard_alpha = deploy_and_register(
        migration,
        switchboard,
        name="SwitchboardAlpha",
        args=module_args,
        description="SwitchboardAlpha",
        expected_id=1,
        expected_prefix=(),
        context="before Robinhood SwitchboardAlpha deployment",
        validate=lambda module: _validate_switchboard_module(
            module,
            hq,
            migration,
            "SwitchboardAlpha",
        ),
        expected_runtime_codehash=SWITCHBOARD_ALPHA_RUNTIME_CODEHASH,
        runtime_builder=lambda: materialize_contract_runtime(
            migration,
            "SwitchboardAlpha",
            module_args,
            prepare=lambda: install_hq_materialization_dependency(
                hq,
                migration,
            ),
        ),
        maximum_next_id=3,
    )

    deploy_and_register(
        migration,
        switchboard,
        name="SwitchboardBravo",
        args=module_args,
        description="SwitchboardBravo",
        expected_id=2,
        expected_prefix=(("SwitchboardAlpha", switchboard_alpha.address),),
        context="before Robinhood SwitchboardBravo deployment",
        validate=lambda module: _validate_switchboard_module(
            module,
            hq,
            migration,
            "SwitchboardBravo",
        ),
        expected_runtime_codehash=SWITCHBOARD_BRAVO_RUNTIME_CODEHASH,
        runtime_builder=lambda: materialize_contract_runtime(
            migration,
            "SwitchboardBravo",
            module_args,
            prepare=lambda: install_hq_materialization_dependency(
                hq,
                migration,
            ),
        ),
    )
