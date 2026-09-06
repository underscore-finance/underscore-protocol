import json
import os
import shutil
from unittest.mock import patch

import boa
import pytest
import rlp
from boa.util.abi import Address
from eth_utils import keccak, to_canonical_address, to_checksum_address

from scripts.utils.deploy_args import DeployArgs
from scripts.utils.migration import Migration
from scripts.utils.migration_helpers import load_vyper_files
from scripts.utils.migration_runner import MigrationError, MigrationRunner
from scripts.utils.mock_account import MockAccount
from scripts.utils.nonce_alignment import align_account_nonce, get_account_nonce


DEPLOYER = "0x14051A647C2B647363739ccfD4B008AfEeb8FD8e"
EXPECTED_UNDY_HQ = "0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9"
TARGET_UNDY_HQ_NONCE = 5
ROBINHOOD_REHEARSAL_BLOCK = 54_618_507
ROBINHOOD_REHEARSAL_BLOCK_HASH = (
    "0x7742bcaf84a046d8d608820599d3585395cc6c7874e3ca4f4775ae950ed9f911"
)


pytestmark = pytest.mark.fork("robinhood")


# The repo's two global autouse fixtures build the full local protocol. This
# module owns its fork lifecycle and intentionally exercises only the RH core
# migration, so override those unrelated setup fixtures here.
@pytest.fixture(scope="session")
def undy_hq():
    return None


@pytest.fixture(scope="session")
def wallet_backpack():
    return None


def _predict_create_address(deployer: str, nonce: int) -> str:
    encoded = rlp.encode([to_canonical_address(deployer), nonce])
    return to_checksum_address(keccak(encoded)[-20:])


def _expected_core_addresses():
    return {
        "UserWallet": _predict_create_address(DEPLOYER, 0),
        "UserWalletConfig": _predict_create_address(DEPLOYER, 1),
        "AgentWrapper": _predict_create_address(DEPLOYER, 2),
        "DefaultsRobinhood": _predict_create_address(DEPLOYER, 3),
        "UndyHq": EXPECTED_UNDY_HQ,
    }


def _deploy_args(rpc_url: str, *, ignore_logs: bool = True) -> DeployArgs:
    return DeployArgs(
        MockAccount(DEPLOYER),
        "robinhood-mainnet",
        ignore_logs=ignore_logs,
        blueprint="robinhood",
        rpc=rpc_url,
    )


def _empty_migration(tmp_path, rpc_url: str) -> Migration:
    history_path = tmp_path / "nonce-alignment-history"
    return Migration(
        _deploy_args(rpc_url),
        files={},
        timestamp="nonce-alignment",
        previous_timestamp=None,
        history_path=str(history_path),
    )


def _run_core_migration(
    tmp_path,
    rpc_url: str,
    *,
    ignore_logs: bool = True,
    end_timestamp: str = "0000",
):
    history_path = tmp_path / "robinhood-core-history"
    return _run_migration_range(
        history_path,
        rpc_url,
        start_timestamp="0000",
        end_timestamp=end_timestamp,
        ignore_logs=ignore_logs,
    )


def _run_migration_range(
    history_path,
    rpc_url: str,
    *,
    start_timestamp: str,
    end_timestamp: str,
    ignore_logs: bool = True,
):
    runner = MigrationRunner(
        "migrations/robinhood-mainnet/v1",
        str(history_path),
        load_vyper_files(),
    )
    runner.run(
        _deploy_args(rpc_url, ignore_logs=ignore_logs),
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp,
    )
    with open(history_path / "current-manifest.json") as manifest_file:
        contracts = json.load(manifest_file)["contracts"]
    return {
        name: deployment["address"] for name, deployment in contracts.items()
    }


def _materialize_exact_prefix(fork_env, rpc_url: str, tmp_path, prefix_nonce: int):
    expected = _expected_core_addresses()
    contracts = {}

    if prefix_nonce >= 1:
        contracts["UserWallet"] = boa.load_partial(
            "contracts/core/userWallet/UserWallet.vy"
        ).deploy_as_blueprint()
        assert str(contracts["UserWallet"].address) == expected["UserWallet"]
    if prefix_nonce >= 2:
        contracts["UserWalletConfig"] = boa.load_partial(
            "contracts/core/userWallet/UserWalletConfig.vy"
        ).deploy_as_blueprint()
        assert (
            str(contracts["UserWalletConfig"].address)
            == expected["UserWalletConfig"]
        )
    if prefix_nonce >= 3:
        contracts["AgentWrapper"] = boa.load_partial(
            "contracts/core/agent/AgentWrapper.vy"
        ).deploy_as_blueprint()
        assert str(contracts["AgentWrapper"].address) == expected["AgentWrapper"]
    if prefix_nonce >= 4:
        contracts["DefaultsRobinhood"] = boa.load(
            "contracts/config/DefaultsRobinhood.vy",
            contracts["UserWallet"],
            contracts["UserWalletConfig"],
        )
        assert (
            str(contracts["DefaultsRobinhood"].address)
            == expected["DefaultsRobinhood"]
        )
    if prefix_nonce >= 5:
        padding_migration = _empty_migration(
            tmp_path / "prefix-padding",
            rpc_url,
        )
        assert align_account_nonce(padding_migration, 5) == 5
    if prefix_nonce >= 6:
        params = _deploy_args(rpc_url).blueprint.PARAMS
        contracts["UndyHq"] = boa.load(
            "contracts/registries/UndyHq.vy",
            DEPLOYER,
            params["UNDY_HQ_MIN_GOV_TIMELOCK"],
            params["UNDY_HQ_MAX_GOV_TIMELOCK"],
            params["UNDY_HQ_MIN_REG_TIMELOCK"],
            params["UNDY_HQ_MAX_REG_TIMELOCK"],
        )
        assert str(contracts["UndyHq"].address) == expected["UndyHq"]

    assert get_account_nonce(DEPLOYER) == prefix_nonce
    return contracts


@pytest.fixture(scope="module")
def robinhood_fork():
    rpc_url = os.environ.get("ROBINHOOD_MAINNET_RPC_URL")
    if not rpc_url:
        pytest.skip("ROBINHOOD_MAINNET_RPC_URL is not configured")

    with boa.fork(
        rpc_url,
        block_identifier=ROBINHOOD_REHEARSAL_BLOCK,
        allow_dirty=True,
    ) as fork_env:
        fork_env.eoa = Address(DEPLOYER)
        fork_env.set_balance(DEPLOYER, 10 * 10**18)

        # Pin the rehearsal to a known predeployment block so it remains
        # reproducible after RH goes live. Production uses separate latest and
        # pending nonce/code preflights immediately before broadcasting.
        block_info = fork_env.evm.vm.state._account_db._block_info
        assert fork_env.evm.patch.block_number == ROBINHOOD_REHEARSAL_BLOCK
        assert int(block_info["number"], 16) == ROBINHOOD_REHEARSAL_BLOCK
        assert block_info["hash"].lower() == ROBINHOOD_REHEARSAL_BLOCK_HASH
        assert get_account_nonce(DEPLOYER) == 0
        assert fork_env.get_code(DEPLOYER) == b""
        assert fork_env.get_code(EXPECTED_UNDY_HQ) == b""
        yield fork_env, rpc_url


def test_nonce_alignment_pads_from_zero(robinhood_fork, tmp_path):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        starting_balance = fork_env.get_balance(DEPLOYER)
        migration = _empty_migration(tmp_path, rpc_url)

        assert align_account_nonce(migration, TARGET_UNDY_HQ_NONCE) == 5
        assert get_account_nonce(DEPLOYER) == 5
        assert fork_env.get_balance(DEPLOYER) == starting_balance


def test_nonce_alignment_aborts_after_target_nonce(robinhood_fork, tmp_path):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        for expected_nonce in range(6):
            assert get_account_nonce(DEPLOYER) == expected_nonce
            fork_env.deploy(sender=DEPLOYER, bytecode=b"\x00")

        migration = _empty_migration(tmp_path, rpc_url)
        with pytest.raises(
            RuntimeError,
            match=(
                "deployer nonce 6 exceeds required nonce 5; "
                "the target CREATE address is permanently unreachable"
            ),
        ):
            align_account_nonce(migration, TARGET_UNDY_HQ_NONCE)

        assert get_account_nonce(DEPLOYER) == 6


def test_robinhood_core_migration_aborts_before_deploying_if_nonce_is_too_high(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        padding_migration = _empty_migration(tmp_path, rpc_url)
        assert align_account_nonce(padding_migration, 7) == 7

        runner = MigrationRunner(
            "migrations/robinhood-mainnet/v1",
            str(tmp_path / "over-nonce-core-history"),
            load_vyper_files(),
        )
        with pytest.raises(MigrationError) as exc_info:
            runner.run(
                _deploy_args(rpc_url),
                start_timestamp="0000",
                end_timestamp="0000",
            )

        assert str(exc_info.value.__cause__) == (
            "deployer nonce 7 has passed nonce 5 and UndyHq is absent at "
            f"{EXPECTED_UNDY_HQ}; the target is unreachable"
        )
        assert get_account_nonce(DEPLOYER) == 7
        assert fork_env.get_code(EXPECTED_UNDY_HQ) == b""


def test_robinhood_core_migration_rejects_wrong_chain_before_nonce_use(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        fork_env.evm.patch.chain_id = 8_453

        # The runner's chain guard intentionally executes before loading a
        # migration, so this boundary is a direct RuntimeError rather than a
        # migration-body failure wrapped in MigrationError.
        with pytest.raises(RuntimeError) as exc_info:
            _run_core_migration(tmp_path, rpc_url)

        assert str(exc_info.value) == "wrong chain id: expected 4663, got 8453"
        assert get_account_nonce(DEPLOYER) == 0
        for address in _expected_core_addresses().values():
            assert fork_env.get_code(address) == b""


def test_robinhood_core_migration_deploys_undy_hq_at_base_address(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        deployed_addresses = _run_core_migration(tmp_path, rpc_url)
        expected_addresses = _expected_core_addresses()

        assert deployed_addresses == expected_addresses
        assert (
            _predict_create_address(DEPLOYER, TARGET_UNDY_HQ_NONCE)
            == EXPECTED_UNDY_HQ
        )
        assert fork_env.get_code(_predict_create_address(DEPLOYER, 4)) == b""
        for deployed_address in expected_addresses.values():
            assert fork_env.get_code(deployed_address) != b""
        assert get_account_nonce(DEPLOYER) == 6

        defaults = boa.load_partial("contracts/config/DefaultsRobinhood.vy").at(
            expected_addresses["DefaultsRobinhood"]
        )
        wallet_defaults = defaults.userWalletConfig()
        assert str(wallet_defaults.walletTemplate) == expected_addresses["UserWallet"]
        assert str(wallet_defaults.configTemplate) == expected_addresses["UserWalletConfig"]

        undy_hq = boa.load_partial("contracts/registries/UndyHq.vy").at(
            EXPECTED_UNDY_HQ
        )
        assert str(undy_hq.governance()).lower() == DEPLOYER.lower()
        assert undy_hq.minGovChangeTimeLock() == 7_200
        assert undy_hq.maxGovChangeTimeLock() == 216_000
        assert undy_hq.minRegistryTimeLock() == 600
        assert undy_hq.maxRegistryTimeLock() == 216_000


def test_robinhood_core_registries_deploy_end_to_end(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        deployed_addresses = _run_core_migration(
            tmp_path,
            rpc_url,
            end_timestamp="0004",
        )
        # These post-HQ addresses are deterministic only inside Boa's fork
        # environment. In-process contract calls do not consume the deployer
        # nonce there, while every registration stage/confirm is a real
        # nonce-consuming transaction on a live NetworkEnv. Base proves the
        # difference: its committed manifest has MissionControl at deployer
        # nonce 9 (0x910F...), whereas this fork assigns that same address to
        # Switchboard. Only the nonce-5 UndyHq address is an intentional
        # production parity guarantee; keep this assertion to detect changes
        # to the fork migration graph, not as a Robinhood production map.
        expected_fork_addresses = {
            **_expected_core_addresses(),
            "Ledger": "0x9e97A2e527890E690c7FA978696A88EFA868c5D0",
            "MissionControl": "0x5Ae89bfd4B835c8D9BabEabd9789eD7221c96CEe",
            "LegoBook": "0x39021456aDe8283fb1baA85fB82A1991Bf9d6620",
            "Switchboard": "0x910FE9484540fa21B092eE04a478A30A6B342006",
            "SwitchboardAlpha": "0x135B15CCAe0329846802bBa529d2f74f4A62A0dF",
            "SwitchboardBravo": "0x78d4eA139ed53579EeB0e9aE56C910Ef828b5262",
        }
        assert deployed_addresses == expected_fork_addresses

        hq = boa.load_partial("contracts/registries/UndyHq.vy").at(
            EXPECTED_UNDY_HQ
        )
        assert hq.numAddrs() == 5
        assert [str(hq.getAddr(reg_id)) for reg_id in range(1, 5)] == [
            deployed_addresses[name]
            for name in ("Ledger", "MissionControl", "LegoBook", "Switchboard")
        ]

        lego_book = boa.load_partial("contracts/registries/LegoBook.vy").at(
            deployed_addresses["LegoBook"]
        )
        assert lego_book.numAddrs() == 1

        switchboard = boa.load_partial("contracts/registries/Switchboard.vy").at(
            deployed_addresses["Switchboard"]
        )
        assert switchboard.numAddrs() == 3
        assert [str(switchboard.getAddr(reg_id)) for reg_id in range(1, 3)] == [
            deployed_addresses[name]
            for name in (
                "SwitchboardAlpha",
                "SwitchboardBravo",
            )
        ]


def test_robinhood_empty_registries_keep_appraiser_non_earn_path_operational(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        deployed = _run_core_migration(
            tmp_path,
            rpc_url,
            end_timestamp="0011",
        )
        hq = boa.load_partial("contracts/registries/UndyHq.vy").at(
            EXPECTED_UNDY_HQ
        )
        vault_registry = boa.load_partial(
            "contracts/registries/VaultRegistry.vy"
        ).at(deployed["VaultRegistry"])
        helpers = boa.load_partial("contracts/registries/Helpers.vy").at(
            deployed["Helpers"]
        )

        assert hq.numAddrs() == 12
        assert str(hq.getAddr(10)) == deployed["VaultRegistry"]
        assert str(hq.getAddr(11)) == deployed["Helpers"]
        for registry in (vault_registry, helpers):
            assert str(registry.governance()) == (
                "0x0000000000000000000000000000000000000000"
            )
            assert [str(governor) for governor in registry.getGovernors()] == [
                DEPLOYER
            ]
            assert registry.numAddrs() == 1
            assert registry.getNumAddrs() == 0

        assert "LegoTools" not in deployed
        assert "LevgVaultTools" not in deployed
        ripe_token = _deploy_args(rpc_url).blueprint.TOKENS["RIPE"]
        assert vault_registry.isBasicEarnVault(ripe_token) is False
        assert helpers.isHelpersAddr(DEPLOYER) is False

        appraiser = boa.load_partial("contracts/core/Appraiser.vy").at(
            deployed["Appraiser"]
        )
        assert appraiser.updatePriceAndGetUsdValue(
            ripe_token,
            10**18,
            sender=deployed["Ledger"],
        ) == 0
        usd_value, is_yield_asset = (
            appraiser.updatePriceAndGetUsdValueAndIsYieldAsset(
                ripe_token,
                10**18,
                sender=deployed["Ledger"],
            )
        )
        # RIPE intentionally has no Robinhood price at launch. The important
        # property is that the ordinary non-earn path reaches the empty ID-10
        # registry and returns fail-closed instead of reverting on address(0).
        assert usd_value == 0
        assert is_yield_asset is False


def test_switchboard_migration_resumes_every_registry_boundary(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        base_history = tmp_path / "through-lego-book"
        _run_migration_range(
            base_history,
            rpc_url,
            start_timestamp="0000",
            end_timestamp="0003",
        )

        for interruption_call in range(1, 7):
            case_history = tmp_path / f"switchboard-interrupt-{interruption_call}"
            shutil.copytree(base_history, case_history)

            with fork_env.anchor():
                execute_calls = 0
                original_execute = Migration.execute

                def execute_then_interrupt(self, transaction, *args, **kwargs):
                    nonlocal execute_calls
                    result = original_execute(self, transaction, *args, **kwargs)
                    execute_calls += 1
                    if execute_calls == interruption_call:
                        raise RuntimeError(
                            f"simulated interruption after call {interruption_call}"
                        )
                    return result

                with patch.object(Migration, "execute", execute_then_interrupt):
                    with pytest.raises(MigrationError) as exc_info:
                        _run_migration_range(
                            case_history,
                            rpc_url,
                            start_timestamp="0004",
                            end_timestamp="0004",
                        )

                assert str(exc_info.value.__cause__) == (
                    f"simulated interruption after call {interruption_call}"
                )
                assert execute_calls == interruption_call

                deployed = _run_migration_range(
                    case_history,
                    rpc_url,
                    start_timestamp="0004",
                    end_timestamp="0004",
                )
                # These remain the deterministic Boa-fork addresses described
                # in test_robinhood_core_registries_deploy_end_to_end, not live
                # Robinhood CREATE predictions.
                assert deployed["Switchboard"] == (
                    "0x910FE9484540fa21B092eE04a478A30A6B342006"
                )
                assert deployed["SwitchboardAlpha"] == (
                    "0x135B15CCAe0329846802bBa529d2f74f4A62A0dF"
                )
                assert deployed["SwitchboardBravo"] == (
                    "0x78d4eA139ed53579EeB0e9aE56C910Ef828b5262"
                )

                hq = boa.load_partial("contracts/registries/UndyHq.vy").at(
                    EXPECTED_UNDY_HQ
                )
                assert str(hq.getAddr(4)) == deployed["Switchboard"]
                switchboard = boa.load_partial(
                    "contracts/registries/Switchboard.vy"
                ).at(deployed["Switchboard"])
                assert switchboard.numAddrs() == 3
                assert str(switchboard.getAddr(1)) == deployed["SwitchboardAlpha"]
                assert str(switchboard.getAddr(2)) == deployed["SwitchboardBravo"]


@pytest.mark.parametrize("prefix_nonce", range(1, 7))
def test_robinhood_core_migration_resumes_each_authenticated_prefix(
    robinhood_fork,
    tmp_path,
    prefix_nonce,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        _materialize_exact_prefix(
            fork_env,
            rpc_url,
            tmp_path,
            prefix_nonce,
        )
        nonce_before_resume = get_account_nonce(DEPLOYER)

        deployed_addresses = _run_core_migration(tmp_path, rpc_url)

        assert deployed_addresses == _expected_core_addresses()
        assert nonce_before_resume == prefix_nonce
        assert get_account_nonce(DEPLOYER) == 6
        assert fork_env.get_code(EXPECTED_UNDY_HQ) != b""


@pytest.mark.parametrize(
    ("prefix_nonce", "corrupted_artifact"),
    [(1, "UserWallet"), (4, "DefaultsRobinhood")],
)
def test_robinhood_core_migration_rejects_corrupted_prefix_before_sending(
    robinhood_fork,
    tmp_path,
    prefix_nonce,
    corrupted_artifact,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        _materialize_exact_prefix(
            fork_env,
            rpc_url,
            tmp_path,
            prefix_nonce,
        )
        corrupted_address = _expected_core_addresses()[corrupted_artifact]
        fork_env.set_code(corrupted_address, b"\x60\x00")

        with pytest.raises(MigrationError) as exc_info:
            _run_core_migration(tmp_path, rpc_url)

        assert str(exc_info.value.__cause__) == (
            f"Robinhood core prefix at nonce {prefix_nonce} cannot be "
            "authenticated; no transaction was sent and the nonce-5 UndyHq "
            "address may still be reachable only after manual reconciliation"
        )
        assert corrupted_artifact in str(exc_info.value.__cause__.__cause__)
        assert get_account_nonce(DEPLOYER) == prefix_nonce


def test_robinhood_core_migration_rejects_nonce_six_without_undy_hq(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        _materialize_exact_prefix(fork_env, rpc_url, tmp_path, 5)
        consumed_hq_nonce = _empty_migration(
            tmp_path / "consumed-hq-nonce",
            rpc_url,
        )
        assert align_account_nonce(consumed_hq_nonce, 6) == 6
        assert fork_env.get_code(EXPECTED_UNDY_HQ) == b""

        with pytest.raises(MigrationError) as exc_info:
            _run_core_migration(tmp_path, rpc_url)

        assert str(exc_info.value.__cause__) == (
            "deployer nonce 6 has consumed the nonce-5 CREATE but UndyHq is "
            f"absent at {EXPECTED_UNDY_HQ}; the target is unreachable"
        )
        assert get_account_nonce(DEPLOYER) == 6


def test_robinhood_core_migration_rejects_nonzero_target_account_nonce(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        fork_env.evm.vm.state.set_nonce(
            Address(EXPECTED_UNDY_HQ).canonical_address,
            1,
        )
        assert fork_env.get_code(EXPECTED_UNDY_HQ) == b""

        with pytest.raises(MigrationError) as exc_info:
            _run_core_migration(tmp_path, rpc_url)

        assert str(exc_info.value.__cause__) == (
            "Robinhood core prefix at nonce 0 cannot be authenticated; no "
            "transaction was sent and the nonce-5 UndyHq address may still be "
            "reachable only after manual reconciliation"
        )
        assert str(exc_info.value.__cause__.__cause__) == (
            f"UndyHq address {EXPECTED_UNDY_HQ} is not a pristine CREATE target: "
            "latest nonce 1, pending nonce 1"
        )
        assert get_account_nonce(DEPLOYER) == 0


def test_robinhood_core_migration_discards_stale_positional_replay_log(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        _materialize_exact_prefix(fork_env, rpc_url, tmp_path, 2)
        history_path = tmp_path / "robinhood-core-history"
        history_path.mkdir(parents=True)
        with open(history_path / "0000-log.json", "w") as log_file:
            json.dump({"transactions": ["stale-fork-transaction"] * 8}, log_file)

        deployed_addresses = _run_core_migration(
            tmp_path,
            rpc_url,
            ignore_logs=False,
        )

        assert deployed_addresses == _expected_core_addresses()
        assert get_account_nonce(DEPLOYER) == 6


def test_robinhood_completed_state_rejects_wrong_hq_constructor_storage(
    robinhood_fork,
    tmp_path,
):
    fork_env, rpc_url = robinhood_fork

    with fork_env.anchor():
        _materialize_exact_prefix(fork_env, rpc_url, tmp_path, 5)
        params = _deploy_args(rpc_url).blueprint.PARAMS
        wrong_governance = "0x0000000000000000000000000000000000000002"
        undy_hq = boa.load(
            "contracts/registries/UndyHq.vy",
            wrong_governance,
            params["UNDY_HQ_MIN_GOV_TIMELOCK"],
            params["UNDY_HQ_MAX_GOV_TIMELOCK"],
            params["UNDY_HQ_MIN_REG_TIMELOCK"],
            params["UNDY_HQ_MAX_REG_TIMELOCK"],
        )
        assert str(undy_hq.address) == EXPECTED_UNDY_HQ
        assert get_account_nonce(DEPLOYER) == 6

        with pytest.raises(MigrationError) as exc_info:
            _run_core_migration(tmp_path, rpc_url)

        assert str(exc_info.value.__cause__) == (
            "cannot authenticate completed UndyHq: governance is "
            f"'{wrong_governance}', expected '{DEPLOYER.lower()}'"
        )
        assert get_account_nonce(DEPLOYER) == 6
