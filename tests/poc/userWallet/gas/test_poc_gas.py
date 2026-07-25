"""Standalone User Wallet v3 PoC gas and modeled-fee evidence.

This module deliberately owns one forward-only test. Each measured Boa call is
preceded by the repository's transaction-boundary reset: prior storage is
locked as previous-transaction state, access journals and transient storage are
cleared, and only tx.origin, tx.to, and Prague precompiles are prewarmed.
"""

import hashlib
import json
import os
import rlp
import subprocess
from importlib.metadata import version as package_version
from pathlib import Path

import boa
import pytest
from eth.vm.forks.prague import PragueVM
from eth_utils import keccak
from vyper import __version__ as vyper_version
from web3 import Web3

from config.BluePrint import TOKENS, WHALES
from conf_env import FORKS
from conftest import V3_COMPILER_REPORT, deploy_v3
from constants import EIGHTEEN_DECIMALS
from test_mpp import attach_payment
from test_x402 import (
    DOMAIN_SEPARATOR,
    PINNED_BASE_FEE,
    PINNED_BLOCK,
    PINNED_BLOCK_HASH,
    PINNED_TIMESTAMP,
    TRANSFER_TYPEHASH,
    USDC_ABI,
    USDC_ADDRESS,
)


pytestmark = [
    pytest.mark.fork("always"),
    pytest.mark.skipif(
        os.environ.get("GAS_PROFILE") != "1",
        reason="gas benchmark is opt-in: set GAS_PROFILE=1",
    ),
    pytest.mark.ignore_isolation,
]

PRECOMPILES = [i.to_bytes(20, "big") for i in range(1, 0x12)]
REPO_ROOT = Path(__file__).resolve().parents[4]
THRESHOLD_PATH = Path(__file__).with_name("thresholds.json")
GAS_ORACLE = "0x420000000000000000000000000000000000000F"
ZERO = "0x0000000000000000000000000000000000000000"
EXPECTED_CALIBRATION = {
    "clear_initialized_slot_gross": 5_102,
    "clear_initialized_slot_raw_refund": 4_800,
    "zero_to_nonzero_clean_write_gross": 22_217,
    "zero_to_nonzero_clean_write_raw_refund": 0,
    "initialWarmSet": "tx.origin, tx.to, fork-valid Prague precompiles only",
    "initialStorageWarm": False,
}
SERIALIZED_Y_PARITY = 1
SERIALIZED_R = int.from_bytes(keccak(text="wallet-v3-gas-signature-r"), "big")
SERIALIZED_S = int.from_bytes(keccak(text="wallet-v3-gas-signature-s"), "big")
PINNED_PREFLIGHT_L1_FEE = 1_233_604_915

ORACLE_ABI = json.dumps(
    [
        {
            "type": "function",
            "name": "getL1Fee",
            "stateMutability": "view",
            "inputs": [{"type": "bytes"}],
            "outputs": [{"type": "uint256"}],
        },
        {
            "type": "function",
            "name": "getOperatorFee",
            "stateMutability": "view",
            "inputs": [{"type": "uint256"}],
            "outputs": [{"type": "uint256"}],
        },
    ]
)


def _canon(address):
    return bytes.fromhex(str(address)[2:])


def _tx_boundary(warm_addresses):
    state = boa.env.evm.vm.state
    state.lock_changes()
    journal = state._account_db._journal_accessed_state._journal
    journal._current_values = {}
    for checkpoint in journal._journal_data:
        journal._journal_data[checkpoint] = {}
    journal._clears_at.clear()
    journal._ignore_wrapped_db = False
    state.clear_transient_storage()
    for address in PRECOMPILES:
        state.mark_address_warm(address)
    for address in warm_addresses:
        state.mark_address_warm(_canon(address))


def _tx_metrics(gross, refund, calldata):
    zero_bytes = calldata.count(0)
    nonzero_bytes = len(calldata) - zero_bytes
    tokens = zero_bytes + 4 * nonzero_bytes
    standard_intrinsic = 21_000 + 4 * tokens
    pre_refund = gross + standard_intrinsic
    applied_refund = min(refund, pre_refund // 5)
    standard_total = pre_refund - applied_refund
    eip7623_floor = 21_000 + 10 * tokens
    return {
        "calldata_bytes": len(calldata),
        "zero_calldata_bytes": zero_bytes,
        "nonzero_calldata_bytes": nonzero_bytes,
        "calldata_tokens": tokens,
        "standard_intrinsic": standard_intrinsic,
        "pre_refund_gas": pre_refund,
        "raw_refund_counter": refund,
        "applied_refund": applied_refund,
        "standard_total": standard_total,
        "eip7623_floor": eip7623_floor,
        "eip7623_floor_bound": eip7623_floor > standard_total,
        "minimum_executable_gas_limit": max(pre_refund, eip7623_floor),
        "tx_equivalent": max(standard_total, eip7623_floor),
    }


def _measure(
    scenario,
    role,
    contract,
    sender,
    call,
    report,
    *,
    token=ZERO,
    amount=0,
    state_description,
    semantic_check,
):
    _tx_boundary([sender, contract.address])
    result = call()
    computation = contract._computation
    execution_success = bool(computation.is_success)
    gross = int(computation.get_gas_used())
    refund = int(computation.get_gas_refund())
    calldata = bytes(computation.msg.data)
    semantic_success = bool(semantic_check())
    assert execution_success
    assert semantic_success
    entry = {
        "scenario": scenario,
        "role": role,
        "executionMode": (
            "boa-pyevm-overlay"
            if report["profile"] == "base"
            else "boa-pyevm-local"
        ),
        "receipt": "not-applicable",
        "execution_success": execution_success,
        "semantic_success": semantic_success,
        "caller": str(sender),
        "entry_contract": str(contract.address),
        "token": str(token),
        "amount": amount,
        "initialized_state": state_description,
        "gross_execution": gross,
        "raw_calldata": "0x" + calldata.hex(),
        "calldata_hash": "0x" + keccak(calldata).hex(),
    }
    entry.update(_tx_metrics(gross, refund, calldata))
    report["results"][scenario] = entry
    return result


def _serialize_type2(entry, base_fee):
    to_bytes = bytes.fromhex(entry["entry_contract"][2:])
    calldata = bytes.fromhex(entry["raw_calldata"][2:])
    payload = [
        8453,
        0,
        0,
        base_fee,
        entry["minimum_executable_gas_limit"],
        to_bytes,
        0,
        calldata,
        [],
        SERIALIZED_Y_PARITY,
        SERIALIZED_R,
        SERIALIZED_S,
    ]
    serialized = b"\x02" + rlp.encode(payload)
    decoded = rlp.decode(serialized[1:])
    assert int.from_bytes(decoded[4], "big") == entry["minimum_executable_gas_limit"]
    assert decoded[9] == b"\x01"
    assert len(decoded[10]) == 32 and int.from_bytes(decoded[10], "big") != 0
    assert len(decoded[11]) == 32 and int.from_bytes(decoded[11], "big") != 0
    return serialized


def _add_base_fee_evidence(report, base_fee):
    oracle = boa.loads_abi(ORACLE_ABI, name="BaseGasPriceOracle").at(GAS_ORACLE)
    assert oracle.getOperatorFee(190_000) == 0
    for entry in report["results"].values():
        serialized = _serialize_type2(entry, base_fee)
        modeled_l1_fee = oracle.getL1Fee(serialized)
        operator_fee = oracle.getOperatorFee(entry["tx_equivalent"])
        l2_fee = entry["tx_equivalent"] * base_fee
        entry.update(
            {
                "chain_id": 8453,
                "executionMode": "boa-pyevm-overlay",
                "receipt": "not-applicable",
                "serialized_transaction": "0x" + serialized.hex(),
                "serialized_transaction_hash": "0x" + keccak(serialized).hex(),
                "effective_l2_gas_price": base_fee,
                "modeled_l2_fee": l2_fee,
                "modeled_l1_fee": modeled_l1_fee,
                "operator_fee": operator_fee,
                "modeled_sponsored_fee": l2_fee + modeled_l1_fee + operator_fee,
                "serialized_signature": {
                    "yParity": SERIALIZED_Y_PARITY,
                    "r": hex(SERIALIZED_R),
                    "s": hex(SERIALIZED_S),
                },
            }
        )


def _base_preflight():
    overlay_chain_id = int(boa.env.evm.patch.chain_id)
    overlay_timestamp = int(boa.env.evm.patch.timestamp)
    assert overlay_chain_id == 8453
    assert overlay_timestamp == PINNED_TIMESTAMP
    assert FORKS["base"]["block"] == PINNED_BLOCK
    configured_usdc = Web3.to_checksum_address(TOKENS["base"]["USDC"])
    canonical_usdc = Web3.to_checksum_address(USDC_ADDRESS)
    assert configured_usdc == canonical_usdc
    upstream = Web3(Web3.HTTPProvider(FORKS["base"]["rpc_url"]))
    block = upstream.eth.get_block(PINNED_BLOCK)
    observed_block_hash = "0x" + bytes(block.hash).hex()
    observed_timestamp = int(block.timestamp)
    observed_base_fee = int(block.baseFeePerGas)
    assert observed_block_hash == PINNED_BLOCK_HASH
    assert observed_timestamp == PINNED_TIMESTAMP
    assert observed_base_fee == PINNED_BASE_FEE

    usdc = boa.loads_abi(USDC_ABI, name="GasPreflightBaseUSDC").at(USDC_ADDRESS)
    observed_usdc_address = Web3.to_checksum_address(str(usdc.address))
    observed_usdc_name = usdc.name()
    observed_usdc_version = usdc.version()
    observed_domain_separator = bytes(usdc.DOMAIN_SEPARATOR())
    observed_transfer_typehash = bytes(
        usdc.TRANSFER_WITH_AUTHORIZATION_TYPEHASH()
    )
    assert observed_usdc_address == canonical_usdc
    assert observed_usdc_name == "USD Coin"
    assert observed_usdc_version == "2"
    assert observed_domain_separator == DOMAIN_SEPARATOR
    assert observed_transfer_typehash == TRANSFER_TYPEHASH
    oracle_code = boa.env.get_code(GAS_ORACLE)
    assert oracle_code != b""
    oracle = boa.loads_abi(ORACLE_ABI, name="BasePreflightGasPriceOracle").at(
        GAS_ORACLE
    )
    observed_oracle_address = Web3.to_checksum_address(str(oracle.address))
    assert observed_oracle_address == Web3.to_checksum_address(GAS_ORACLE)
    operator_fee = int(oracle.getOperatorFee(190_000))
    assert operator_fee == 0
    probe_entry = {
        "entry_contract": USDC_ADDRESS,
        "raw_calldata": "0x",
        "minimum_executable_gas_limit": 21_000,
    }
    probe_transaction = _serialize_type2(probe_entry, PINNED_BASE_FEE)
    probe_l1_fee = int(oracle.getL1Fee(probe_transaction))
    assert probe_l1_fee == PINNED_PREFLIGHT_L1_FEE, (
        "unexpected pinned Base oracle probe fee: "
        f"{probe_l1_fee} != {PINNED_PREFLIGHT_L1_FEE}"
    )
    return {
        "chainId": overlay_chain_id,
        "block": int(block.number),
        "blockHash": observed_block_hash,
        "timestamp": observed_timestamp,
        "overlayTimestamp": overlay_timestamp,
        "upstreamBaseFeePerGas": observed_base_fee,
        "canonicalUSDC": observed_usdc_address,
        "configuredUSDC": configured_usdc,
        "usdcName": observed_usdc_name,
        "usdcVersion": observed_usdc_version,
        "usdcDomainSeparator": "0x" + observed_domain_separator.hex(),
        "usdcTransferWithAuthorizationTypehash": (
            "0x" + observed_transfer_typehash.hex()
        ),
        "gasPriceOracle": observed_oracle_address,
        "gasPriceOracleCodeHash": "0x" + keccak(oracle_code).hex(),
        "operatorFeeAt190000": operator_fee,
        "l1FeeProbeAt21000": probe_l1_fee,
        "l1FeeProbeTransactionHash": "0x" + keccak(probe_transaction).hex(),
    }


def _git_metadata():
    commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=REPO_ROOT,
    )
    tracked_diff = subprocess.check_output(
        ["git", "diff", "--binary", "HEAD", "--"],
        cwd=REPO_ROOT,
    )
    state_digest = hashlib.sha256()
    state_digest.update(b"git-status\0")
    state_digest.update(status)
    state_digest.update(b"git-diff-head\0")
    state_digest.update(tracked_diff)
    for record in status.split(b"\0"):
        if not record.startswith(b"?? "):
            continue
        relative = record[3:].decode()
        candidate = REPO_ROOT / relative
        if candidate.is_file():
            state_digest.update(b"untracked-file\0")
            state_digest.update(relative.encode())
            state_digest.update(b"\0")
            state_digest.update(candidate.read_bytes())
    return commit, bool(status), state_digest.hexdigest()


def _evidence_paths(fork):
    configured = os.environ.get("WALLET_V3_GAS_OUTPUT")
    if not configured:
        pytest.fail("WALLET_V3_GAS_OUTPUT must name an absolute /tmp evidence path")
    configured_path = Path(configured)
    if not configured_path.is_absolute():
        pytest.fail("WALLET_V3_GAS_OUTPUT must be absolute")
    output_path = configured_path.resolve()
    tmp_root = Path("/tmp").resolve()
    if tmp_root != output_path.parent and tmp_root not in output_path.parents:
        pytest.fail("WALLET_V3_GAS_OUTPUT must resolve beneath /tmp")
    expected_suffix = f"-{fork}.json"
    if not output_path.name.endswith(expected_suffix):
        pytest.fail(
            f"{fork} evidence path must end with {expected_suffix}: {output_path}"
        )
    local_path = None
    path_evidence = {
        "requestedOutput": str(configured_path),
        "resolvedOutput": str(output_path),
    }
    if fork == "base":
        local_name = configured_path.name[: -len(expected_suffix)] + "-local.json"
        requested_local_path = configured_path.with_name(local_name)
        local_path = requested_local_path.resolve()
        if local_path == output_path:
            pytest.fail("Base and local gas evidence paths must be distinct")
        path_evidence.update(
            {
                "requestedLocalEvidence": str(requested_local_path),
                "resolvedLocalEvidence": str(local_path),
            }
        )
    return output_path, local_path, path_evidence


def _settings(contract):
    settings = contract.compiler_data.settings
    optimize = settings.optimize.name.lower() if settings.optimize is not None else None
    return {
        "optimizer": optimize,
        "evmVersion": settings.evm_version,
    }


def test_poc_gas(
    request,
    fork,
    hatchery,
    user_wallet_template,
    user_wallet_config_template,
    bob,
    recipient,
    alpha_token,
    alpha_token_whale,
    mock_ripe,
    mission_control,
    switchboard_alpha,
    migrator,
):
    if os.environ.get("PYTEST_XDIST_WORKER") or getattr(
        request.config.option,
        "numprocesses",
        None,
    ) not in (None, 0, "0"):
        pytest.fail("wallet-v3 gas evidence must not run under xdist")
    if len(request.session.items) != 1:
        pytest.fail("wallet-v3 gas module must be the only collected test")
    output_path, local_report_path, path_evidence = _evidence_paths(fork)

    assert type(boa.env.evm.vm) is PragueVM
    observed_versions = {
        "vyper": vyper_version,
        "titanoboa": package_version("titanoboa"),
        "py-evm": package_version("py-evm"),
    }
    assert observed_versions == {
        "vyper": "0.4.3",
        "titanoboa": "0.2.7",
        "py-evm": "0.12.1b1",
    }
    base_preflight = _base_preflight() if fork == "base" else None
    commit, dirty, worktree_state = _git_metadata()
    report = {
        "schemaVersion": 1,
        "profile": fork,
        "sourceCommit": commit,
        "dirty": dirty,
        "worktreeStateSha256": worktree_state,
        "evidenceClassification": "diagnostic-dirty-tree" if dirty else "final-clean-commit",
        "evidencePaths": path_evidence,
        "versions": {
            **observed_versions,
            "v3Compiler": V3_COMPILER_REPORT,
            "executionVM": type(boa.env.evm.vm).__name__,
        },
        "results": {},
    }
    if base_preflight is not None:
        report["fork"] = base_preflight

    try:
        # Boa's Base account prefetch can replace locally deployed blueprint
        # code with the upstream empty account at the same address. Restore the
        # exact existing v2 fixture bytecode into the py-evm overlay before the
        # existing session fixture asks Hatchery to EXTCODECOPY it.
        creation_config = mission_control.getUserWalletCreationConfig(
            switchboard_alpha.address
        )
        for configured, blueprint in (
            (creation_config.walletTemplate, user_wallet_template),
            (creation_config.configTemplate, user_wallet_config_template),
        ):
            if fork == "base" and boa.env.get_code(configured) == b"":
                boa.env.set_code(configured, blueprint.bytecode)
            assert boa.env.get_code(configured) == blueprint.bytecode

        user_wallet = request.getfixturevalue("user_wallet")
        user_wallet_config = request.getfixturevalue("user_wallet_config")

        # Transaction-boundary calibration.
        boundary = deploy_v3("contracts/poc/userWallet/mocks/MockGasBoundary.vy")
        boundary.setValue(1, sender=bob)
        _tx_boundary([bob, boundary.address])
        state = boa.env.evm.vm.state
        assert state.is_address_warm(_canon(bob))
        assert state.is_address_warm(_canon(boundary.address))
        assert not state.is_address_warm(_canon(boa.env.generate_address("cold-calibration")))
        assert not state.is_storage_warm(_canon(boundary.address), 0)
        boundary.clearValue(sender=bob)
        clear_gross = int(boundary._computation.get_gas_used())
        clear_refund = int(boundary._computation.get_gas_refund())
        assert clear_refund == 4_800
        _tx_boundary([bob, boundary.address])
        boundary.setValue(1, sender=bob)
        clean_write_gross = int(boundary._computation.get_gas_used())
        clean_write_refund = int(boundary._computation.get_gas_refund())
        assert clean_write_refund == 0
        calibration = {
            "clear_initialized_slot_gross": clear_gross,
            "clear_initialized_slot_raw_refund": clear_refund,
            "zero_to_nonzero_clean_write_gross": clean_write_gross,
            "zero_to_nonzero_clean_write_raw_refund": clean_write_refund,
            "initialWarmSet": "tx.origin, tx.to, fork-valid Prague precompiles only",
            "initialStorageWarm": False,
        }
        assert calibration == EXPECTED_CALIBRATION
        report["transactionBoundaryCalibration"] = calibration
        if fork == "base":
            if not local_report_path.is_file():
                pytest.fail(
                    "run the matching local gas profile first; expected evidence at "
                    f"{local_report_path}"
                )
            local_report_bytes = local_report_path.read_bytes()
            local_report_sha256 = hashlib.sha256(local_report_bytes).hexdigest()
            local_report = json.loads(local_report_bytes)
            assert local_report["profile"] == "local", (
                f"expected local profile in {local_report_path}"
            )
            assert local_report["sourceCommit"] == commit, (
                "local and Base evidence source commits differ"
            )
            assert local_report["dirty"] == dirty, (
                "local and Base evidence dirty states differ"
            )
            assert local_report["worktreeStateSha256"] == worktree_state, (
                "local and Base evidence worktree states differ"
            )
            assert local_report["transactionBoundaryCalibration"] == calibration, (
                "local and Base independently pinned calibration values differ"
            )
            report["localBaseCalibrationMatch"] = {
                "matched": True,
                "localEvidence": str(local_report_path),
                "localEvidenceContentSha256": local_report_sha256,
                "sourceCommit": commit,
                "dirty": dirty,
                "worktreeStateSha256": worktree_state,
                "comparisonScope": (
                    "exact local artifact identity and workflow linkage; each "
                    "profile independently asserts the pinned calibration values"
                ),
            }

        # Paired v2/v3 initialized, independent, cross-block transfer.
        amount = 10 * EIGHTEEN_DECIMALS
        transfer_recipient = boa.env.generate_address("wallet_v3_gas_recipient")
        mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
        alpha_token.transfer(
            user_wallet.address,
            1_000 * EIGHTEEN_DECIMALS,
            sender=alpha_token_whale,
        )
        user_wallet_config.updateAssetData(
            0,
            alpha_token.address,
            False,
            sender=switchboard_alpha.address,
        )
        user_wallet_config.addWhitelistAddrViaMigrator(
            transfer_recipient,
            sender=migrator.address,
        )
        user_wallet.transferFunds(
            transfer_recipient,
            alpha_token.address,
            amount,
            sender=bob,
        )

        wallet_v3 = deploy_v3("contracts/poc/userWallet/UserWalletV3.vy", bob)
        config_v3 = deploy_v3(
            "contracts/poc/userWallet/UserWalletConfigV3.vy",
            wallet_v3.address,
            [],
            [transfer_recipient],
            [(alpha_token.address, 1_000 * EIGHTEEN_DECIMALS, 1_000 * EIGHTEEN_DECIMALS)],
            [],
        )
        wallet_v3.replaceConfig(config_v3.address, sender=bob)
        alpha_token.transfer(
            wallet_v3.address,
            1_000 * EIGHTEEN_DECIMALS,
            sender=alpha_token_whale,
        )
        wallet_v3.transferFunds(
            transfer_recipient,
            alpha_token.address,
            amount,
            sender=bob,
        )

        boa.env.time_travel(blocks=1)
        v2_recipient_before = alpha_token.balanceOf(transfer_recipient)
        _measure(
            "v2.transfer.repeat",
            "gate-comparator" if fork == "base" else "diagnostic-comparator",
            user_wallet,
            bob,
            lambda: user_wallet.transferFunds(
                transfer_recipient,
                alpha_token.address,
                amount,
                sender=bob,
            ),
            report,
            token=alpha_token.address,
            amount=amount,
            state_description="v2 initialized owner-to-whitelist repeat; independent transaction; next block",
            semantic_check=lambda: alpha_token.balanceOf(transfer_recipient)
            == v2_recipient_before + amount,
        )
        boa.env.time_travel(blocks=1)
        v3_recipient_before = alpha_token.balanceOf(transfer_recipient)
        _measure(
            "v3.transfer.repeat",
            "gate" if fork == "base" else "diagnostic",
            wallet_v3,
            bob,
            lambda: wallet_v3.transferFunds(
                transfer_recipient,
                alpha_token.address,
                amount,
                sender=bob,
            ),
            report,
            token=alpha_token.address,
            amount=amount,
            state_description="v3 initialized owner-to-allowed-recipient repeat; independent transaction; next block",
            semantic_check=lambda: alpha_token.balanceOf(transfer_recipient)
            == v3_recipient_before + amount,
        )
        report["versions"]["v2Compiler"] = _settings(user_wallet)
        report["versions"]["v3ObservedCompiler"] = _settings(wallet_v3)

        if fork == "local":
            # Empty session and minimal yield versus direct mock protocol.
            token = deploy_v3(
                "contracts/poc/userWallet/mocks/MockReentrantToken.vy",
                "Gas Token",
                "GAS",
                18,
            )
            yield_wallet = deploy_v3("contracts/poc/userWallet/UserWalletV3.vy", bob)
            yield_config = deploy_v3(
                "contracts/poc/userWallet/UserWalletConfigV3.vy",
                yield_wallet.address,
                [],
                [transfer_recipient],
                [(token.address, 10**24, 10**24)],
                [(1, 10**24), (255, 0)],
            )
            yield_wallet.replaceConfig(yield_config.address, sender=bob)
            lego = deploy_v3("contracts/poc/userWallet/mocks/MockYieldLego.vy")
            vault = deploy_v3("contracts/poc/userWallet/mocks/MockVault.vy", token.address)
            extender = deploy_v3(
                "contracts/poc/userWallet/extenders/YieldExtender.vy",
                lego.address,
            )
            yield_selector = bytes(
                extender.deposit.prepare_calldata(
                    yield_wallet.address,
                    vault.address,
                    token.address,
                    1,
                )[:4]
            )
            yield_wallet.attachExtender(
                (
                    keccak(text="gas-yield"),
                    1,
                    extender.address,
                    lego.address,
                    ZERO,
                    ZERO,
                    [(yield_selector, 1, 1, 1)],
                    [],
                ),
                sender=bob,
            )
            benchmark = deploy_v3(
                "contracts/poc/userWallet/mocks/MockBenchmarkExtender.vy"
            )
            empty_selector = bytes(
                benchmark.emptySession.prepare_calldata(yield_wallet.address)[:4]
            )
            yield_wallet.attachExtender(
                (
                    keccak(text="gas-empty"),
                    1,
                    benchmark.address,
                    ZERO,
                    ZERO,
                    ZERO,
                    [(empty_selector, 255, 2, 3)],
                    [],
                ),
                sender=bob,
            )
            token.mint(yield_wallet.address, 1_000)
            token.mint(bob, 1_000)
            _measure(
                "v3.session.empty",
                "review",
                yield_wallet,
                bob,
                lambda: yield_wallet.execute(
                    benchmark.emptySession.prepare_calldata(yield_wallet.address),
                    sender=bob,
                ),
                report,
                state_description="measurement-only NONE-consumer empty routed session",
                semantic_check=lambda: (
                    yield_wallet.phase() == 0
                    and token.balanceOf(yield_wallet.address) == 1_000
                    and token.allowance(yield_wallet.address, benchmark.address) == 0
                ),
            )
            token.approve(vault.address, 10, sender=bob)
            _measure(
                "control.yield.protocol_direct",
                "review-control",
                vault,
                bob,
                lambda: vault.deposit(10, bob, sender=bob),
                report,
                token=token.address,
                amount=10,
                state_description="direct initialized mock-vault deposit with prior exact approval",
                semantic_check=lambda: vault.balanceOf(bob) == 10,
            )
            _measure(
                "v3.session.yield_minimal",
                "review",
                yield_wallet,
                bob,
                lambda: yield_wallet.execute(
                    extender.deposit.prepare_calldata(
                        yield_wallet.address,
                        vault.address,
                        token.address,
                        10,
                    ),
                    sender=bob,
                ),
                report,
                token=token.address,
                amount=10,
                state_description="minimal routed yield deposit; exact wallet and protocol approvals",
                semantic_check=lambda: (
                    vault.balanceOf(yield_wallet.address) == 10
                    and token.allowance(yield_wallet.address, lego.address) == 0
                    and yield_wallet.phase() == 0
                ),
            )

            # Representative MPP lifecycle.
            mpp_wallet = deploy_v3("contracts/poc/userWallet/UserWalletV3.vy", bob)
            helper = deploy_v3("contracts/poc/userWallet/rails/X402Helper.vy", token.address)
            payment = deploy_v3(
                "contracts/poc/userWallet/extenders/PaymentExtender.vy",
                helper.address,
            )
            operator = boa.env.generate_address("gas_mpp_operator")
            mpp_config = deploy_v3(
                "contracts/poc/userWallet/UserWalletConfigV3.vy",
                mpp_wallet.address,
                [],
                [transfer_recipient],
                [(token.address, 10**24, 10**24)],
                [(20, 10**24), (21, 10**24)],
            )
            mpp_wallet.replaceConfig(mpp_config.address, sender=bob)
            attach_payment(mpp_wallet, payment, helper, bob)
            token.mint(mpp_wallet.address, 1_000)
            commitment_id = keccak(text="gas-mpp")
            _measure(
                "v3.mpp.authorize",
                "review",
                mpp_wallet,
                bob,
                lambda: mpp_wallet.execute(
                    payment.authorizeReservedTransfer.prepare_calldata(
                        mpp_wallet.address,
                        commitment_id,
                        token.address,
                        100,
                        transfer_recipient,
                        operator,
                    ),
                    sender=bob,
                ),
                report,
                token=token.address,
                amount=100,
                state_description="new representative reserved-transfer commitment",
                semantic_check=lambda: (
                    mpp_wallet.commitment(commitment_id).state == 1
                    and mpp_wallet.commitment(commitment_id).remainingAmount == 100
                    and mpp_wallet.reserved(token.address) == 100
                ),
            )
            _measure(
                "v3.mpp.partial_settle",
                "review",
                mpp_wallet,
                operator,
                lambda: mpp_wallet.settleReservedTransfer(
                    commitment_id,
                    30,
                    sender=operator,
                ),
                report,
                token=token.address,
                amount=30,
                state_description="live commitment with 100 reserved; first partial settlement",
                semantic_check=lambda: (
                    mpp_wallet.commitment(commitment_id).state == 1
                    and mpp_wallet.commitment(commitment_id).remainingAmount == 70
                    and mpp_wallet.reserved(token.address) == 70
                    and token.balanceOf(transfer_recipient) == 30
                ),
            )
            _measure(
                "v3.mpp.refund",
                "review",
                mpp_wallet,
                bob,
                lambda: mpp_wallet.refundReservedTransfer(
                    commitment_id,
                    sender=bob,
                ),
                report,
                token=token.address,
                amount=70,
                state_description="live commitment with 70 remaining after partial settlement",
                semantic_check=lambda: (
                    mpp_wallet.commitment(commitment_id).state == 5
                    and mpp_wallet.commitment(commitment_id).remainingAmount == 0
                    and mpp_wallet.reserved(token.address) == 0
                ),
            )
        else:
            # Base-USDC external exact authorization and permissionless sync.
            usdc = boa.loads_abi(USDC_ABI, name="GasBaseUSDC").at(
                TOKENS["base"]["USDC"]
            )
            x_wallet = deploy_v3("contracts/poc/userWallet/UserWalletV3.vy", bob)
            helper = deploy_v3(
                "contracts/poc/userWallet/rails/X402Helper.vy",
                TOKENS["base"]["USDC"],
            )
            payment = deploy_v3(
                "contracts/poc/userWallet/extenders/PaymentExtender.vy",
                helper.address,
            )
            x_config = deploy_v3(
                "contracts/poc/userWallet/UserWalletConfigV3.vy",
                x_wallet.address,
                [],
                [transfer_recipient],
                [(TOKENS["base"]["USDC"], 10**12, 10**12)],
                [(20, 10**12), (21, 10**12)],
            )
            x_wallet.replaceConfig(x_config.address, sender=bob)
            attach_payment(x_wallet, payment, helper, bob)
            usdc.transfer(
                x_wallet.address,
                1_000_000,
                sender=WHALES["base"]["USDC"],
            )
            now = boa.env.evm.patch.timestamp
            commitment_id = keccak(text="gas-x402")
            nonce = keccak(text="gas-x402-nonce")
            _measure(
                "v3.x402.authorize",
                "review",
                x_wallet,
                bob,
                lambda: x_wallet.execute(
                    payment.authorizeExternalExact.prepare_calldata(
                        x_wallet.address,
                        commitment_id,
                        TOKENS["base"]["USDC"],
                        100_000,
                        transfer_recipient,
                        now - 1,
                        now + 3_600,
                        nonce,
                    ),
                    sender=bob,
                ),
                report,
                token=TOKENS["base"]["USDC"],
                amount=100_000,
                state_description="new exact Base-USDC EIP-3009 commitment",
                semantic_check=lambda: (
                    x_wallet.commitment(commitment_id).state == 1
                    and x_wallet.commitment(commitment_id).remainingAmount == 100_000
                    and x_wallet.reserved(TOKENS["base"]["USDC"]) == 100_000
                ),
            )
            usdc.transferWithAuthorization(
                x_wallet.address,
                transfer_recipient,
                100_000,
                now - 1,
                now + 3_600,
                nonce,
                b"gas-evidence",
                sender=transfer_recipient,
            )
            _measure(
                "v3.x402.sync",
                "review",
                x_wallet,
                transfer_recipient,
                lambda: x_wallet.syncExternalPull(
                    commitment_id,
                    sender=transfer_recipient,
                ),
                report,
                token=TOKENS["base"]["USDC"],
                amount=100_000,
                state_description="used external authorization with conservative reservation pending sync",
                semantic_check=lambda: (
                    x_wallet.commitment(commitment_id).state == 2
                    and x_wallet.commitment(commitment_id).remainingAmount == 0
                    and x_wallet.reserved(TOKENS["base"]["USDC"]) == 0
                ),
            )
            _add_base_fee_evidence(report, PINNED_BASE_FEE)

        v2 = report["results"]["v2.transfer.repeat"]["tx_equivalent"]
        v3 = report["results"]["v3.transfer.repeat"]["tx_equivalent"]
        report["pairedTransfer"] = {
            "absoluteDelta": v3 - v2,
            "percentageDelta": (v3 - v2) / v2 * 100,
            "featureParityNote": (
                "Same owner caller, already-allowed recipient, token, amount, "
                "initialized independent transaction, and next-block repeat; "
                "lean v3 intentionally omits v2 production policy work."
            ),
        }
        if fork == "local":
            direct_yield = report["results"][
                "control.yield.protocol_direct"
            ]["tx_equivalent"]
            routed_yield = report["results"][
                "v3.session.yield_minimal"
            ]["tx_equivalent"]
            report["yieldComparison"] = {
                "absoluteDelta": routed_yield - direct_yield,
                "percentageDelta": (
                    (routed_yield - direct_yield) / direct_yield * 100
                ),
                "control": "control.yield.protocol_direct",
                "candidate": "v3.session.yield_minimal",
            }
        report["coreRuntimeBytes"] = len(wallet_v3.compiler_data.bytecode_runtime)

        if fork == "base":
            threshold = json.loads(THRESHOLD_PATH.read_text())
            assert threshold == {
                "schemaVersion": 1,
                "scenario": "v3.transfer.repeat",
                "profile": "base",
                "metric": "tx_equivalent",
                "max": 190000,
            }
            assert v3 < threshold["max"]
            assert v3 < v2

        output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print("WALLET_V3_POC_GAS_JSON_START")
        print(json.dumps(report, indent=2, sort_keys=True))
        print("WALLET_V3_POC_GAS_JSON_END")
    finally:
        boa.env.evm.revert = lambda *args, **kwargs: None
