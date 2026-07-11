"""Transaction-boundary gas benchmark for the user-wallet transfer flow.

Opt-in (slow, prints a report). MUST run standalone (it permanently mutates
shared session state — a guard skips it if other tests are collected):

    GAS_PROFILE=1 python3 -m pytest tests/gas_profiling/test_transfer_gas_profile.py -q -s

Methodology: boa/py-evm executes each contract call inside one rolling journal
context, so naive back-to-back calls leak transaction-warm state: repeat writes
get EIP-2200 dirty-write pricing (100 gas instead of 2,900+cold), and clearing
storage written earlier in the run earns same-transaction refunds (19,900/slot
instead of the cross-transaction 4,800/slot). Every measured scenario below is
therefore preceded by an explicit transaction boundary that:

  1. locks all prior storage as previous-transaction state (EIP-2200/3529
     originals reset),
  2. clears the EIP-2929 warm account/slot journal,
  3. clears transient storage,
  4. prewarms only what a real transaction warms: tx.origin, tx.to, and the
     precompile range.

Reported per scenario: gross execution gas of the top-level call, the RAW
refund counter (the receipt-like figure applies the EIP-3529 20% cap), modeled
intrinsic gas (21,000 + calldata bytes), and a receipt-like total approximating
a direct EOA transaction to the same entry point.

Scenario naming: plain scenarios run in the SAME BLOCK as setup (matching the
codex-2026-07-11 baseline; deposit points accrue zero and lastTxBlock/lastUpdate
rewrites are same-value). `_crossblock` scenarios advance one block first, so
period/points fields genuinely change value — closer to production steady state.

Isolation mechanics: `state.lock_changes()` flattens boa's snapshot journal, so
this module (a) is marked ignore_isolation, (b) runs forward-only (scenario
order matters — e.g. the agent's first manager action must stay first), and
(c) neutralizes leftover session-fixture anchor reverts on exit so the run
finishes with exit code 0. Never run it in the same session as other tests.
"""

import json
import os

import boa
import pytest

from config.BluePrint import TOKENS
from constants import EIGHTEEN_DECIMALS, MAX_UINT256, ZERO_ADDRESS
from conf_utils import set_live_cheque_settings

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("GAS_PROFILE"),
        reason="gas benchmark is opt-in: set GAS_PROFILE=1",
    ),
    pytest.mark.ignore_isolation,
]

# Prague warms 0x01-0x11 (incl. EIP-2537 BLS precompiles); none are hit by
# these paths, so warming the extended range is correctness, not a cost change
PRECOMPILES = [i.to_bytes(20, "big") for i in range(1, 0x12)]

# regression baselines (receipt-like gas) measured on
# cce97d56b62f58c0c3eeddb8fc551d1723bf0fc3 — see docs/gas-profiling/
BASELINES = {
    "owner_whitelist_first": 390_939,
    "owner_whitelist_repeat": 373_839,
    "owner_whitelist_repeat_crossblock": 385_307,
    "owner_payee_repeat_primary": 467_601,
    "owner_payee_repeat_primary_crossblock": 481_869,
    "agent_generic_whitelist_repeat": 416_554,
    "agent_generic_repeat_crossblock": 430_822,
    "cheque_owner_pay_existing": 602_758,
    "cheque_owner_create_steady": 606_717,
    "cheque_owner_pay_existing_steady": 468_790,
    "cheque_agent_atomic_create_and_pay": 691_384,
    "agent_batch_two_steady": 565_915,
    "billing_payee_pull_first": 470_708,
    "billing_payee_pull_repeat": 345_461,
}
TOLERANCE = 0.025
BATCH_SAVING_BASELINE = 284_293


def _canon(addr):
    return bytes.fromhex(str(addr)[2:])


def _tx_boundary(warm_addrs):
    state = boa.env.evm.vm.state
    state.lock_changes()
    journal = state._account_db._journal_accessed_state._journal
    journal._current_values = {}
    for checkpoint in journal._journal_data:
        journal._journal_data[checkpoint] = {}
    journal._clears_at.clear()
    journal._ignore_wrapped_db = False
    state.clear_transient_storage()
    for addr in PRECOMPILES:
        state.mark_address_warm(addr)
    for addr in warm_addrs:
        state.mark_address_warm(_canon(addr))


def _measure(label, contract, sender, call, report):
    _tx_boundary([sender, contract.address])
    result = call()
    comp = contract._computation
    gross = int(comp.get_gas_used())
    refund = int(comp.get_gas_refund())
    data = bytes(comp.msg.data)
    zeros = data.count(0)
    intrinsic = 21_000 + 4 * zeros + 16 * (len(data) - zeros)
    pre_refund = gross + intrinsic
    applied = min(refund, pre_refund // 5)
    report[label] = {
        "gross_execution": gross,
        "raw_refund_counter": refund,
        "refund_applied": applied,
        "intrinsic": intrinsic,
        "receipt_like": pre_refund - applied,
    }
    return result


def _batch_action(action, asset, recipient, amount):
    return (
        False, action, 0, asset, recipient, amount,
        ZERO_ADDRESS, 0, 0, 0, 0, 0, b"", b"", [], [],
    )


def test_transfer_gas_benchmark(
    request,
    fork,
    user_wallet,
    user_wallet_config,
    bob,
    alice,
    charlie,
    alpha_token,
    alpha_token_whale,
    mock_ripe,
    switchboard_alpha,
    migrator,
    paymaster,
    billing,
    cheque_book,
    starter_agent,
    starter_agent_sender,
    createPayeeSettings,
    createGlobalPayeeSettings,
    createChequeSettings,
):
    if len(request.session.items) != 1:
        pytest.skip("gas benchmark must be the only collected test (it breaks test isolation)")

    try:
        report = {}
        amount = 10 * EIGHTEEN_DECIMALS
        eth = TOKENS[fork]["ETH"]

        def fund_and_track(track_amount=1_000 * EIGHTEEN_DECIMALS):
            alpha_token.transfer(user_wallet.address, track_amount, sender=alpha_token_whale)
            user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)

        def whitelist(addr):
            user_wallet_config.addWhitelistAddrViaMigrator(addr, sender=migrator.address)

        # ---- setup (not measured) ----------------------------------------
        mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
        mock_ripe.setPrice(eth, 2_000 * EIGHTEEN_DECIMALS)
        fund_and_track()

        recipients = {
            name: boa.env.generate_address(f"gasbench_{name}")
            for name in [
                "prime", "wl", "wl_full", "agent_wl", "mgr_wl", "sep_wl", "batch_wl",
                "native_untracked", "native_fresh", "cheque_a", "cheque_b", "cheque_c",
            ]
        }
        for name in ["prime", "wl", "wl_full", "agent_wl", "mgr_wl", "sep_wl", "batch_wl", "native_untracked", "native_fresh"]:
            whitelist(recipients[name])

        # prime wallet-level state so "first" scenarios measure the recipient-side
        # first-use cost, not one-time wallet initialization (points structs etc.)
        user_wallet.transferFunds(recipients["prime"], alpha_token.address, EIGHTEEN_DECIMALS, sender=bob)

        # ---- owner -> whitelisted recipient --------------------------------
        _measure(
            "owner_whitelist_first", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["wl"], alpha_token.address, amount, sender=bob),
            report,
        )
        _measure(
            "owner_whitelist_repeat", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["wl"], alpha_token.address, amount, sender=bob),
            report,
        )
        _measure(
            "owner_whitelist_full_balance", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["wl_full"], alpha_token.address, MAX_UINT256, sender=bob),
            report,
        )
        fund_and_track()  # restore for later scenarios

        # ---- owner -> registered payee --------------------------------------
        payee_plain = boa.env.generate_address("gasbench_payee_plain")
        user_wallet_config.addPayee(payee_plain, createPayeeSettings(), sender=paymaster.address)
        _measure(
            "owner_payee_first_no_primary", user_wallet, bob,
            lambda: user_wallet.transferFunds(payee_plain, alpha_token.address, amount, sender=bob),
            report,
        )
        _measure(
            "owner_payee_repeat_no_primary", user_wallet, bob,
            lambda: user_wallet.transferFunds(payee_plain, alpha_token.address, amount, sender=bob),
            report,
        )

        payee_primary = boa.env.generate_address("gasbench_payee_primary")
        user_wallet_config.addPayee(
            payee_primary, createPayeeSettings(_primaryAsset=alpha_token.address), sender=paymaster.address
        )
        _measure(
            "owner_payee_first_primary", user_wallet, bob,
            lambda: user_wallet.transferFunds(payee_primary, alpha_token.address, amount, sender=bob),
            report,
        )
        _measure(
            "owner_payee_repeat_primary", user_wallet, bob,
            lambda: user_wallet.transferFunds(payee_primary, alpha_token.address, amount, sender=bob),
            report,
        )

        # ---- agent path (first manager action of the whole run) -------------
        def agent_transfer(recipient):
            return starter_agent_sender.transferFunds(
                starter_agent.address, user_wallet.address, recipient,
                alpha_token.address, amount, (b"", 0, 0), sender=charlie,
            )

        _measure(
            "agent_generic_whitelist_first", starter_agent_sender, charlie,
            lambda: agent_transfer(recipients["agent_wl"]), report,
        )
        _measure(
            "agent_generic_whitelist_repeat", starter_agent_sender, charlie,
            lambda: agent_transfer(recipients["agent_wl"]), report,
        )

        # manager data now initialized -> steady-state direct manager call.
        # NOTE: impersonates the wrapper contract as top-level sender; the
        # receipt-like figure models an EOA manager making the same call.
        _measure(
            "manager_direct_whitelist_steady", user_wallet, starter_agent.address,
            lambda: user_wallet.transferFunds(recipients["mgr_wl"], alpha_token.address, amount, sender=starter_agent.address),
            report,
        )

        # ---- batch vs separate (steady state) --------------------------------
        _measure(
            "agent_separate_steady_a", starter_agent_sender, charlie,
            lambda: agent_transfer(recipients["sep_wl"]), report,
        )
        _measure(
            "agent_separate_steady_b", starter_agent_sender, charlie,
            lambda: agent_transfer(recipients["sep_wl"]), report,
        )
        instructions = [
            _batch_action(1, alpha_token.address, recipients["batch_wl"], amount),
            _batch_action(1, alpha_token.address, recipients["batch_wl"], amount),
        ]
        _measure(
            "agent_batch_two_steady", starter_agent_sender, charlie,
            lambda: starter_agent_sender.performBatchActions(
                starter_agent.address, user_wallet.address, instructions, (b"", 0, 0), sender=charlie,
            ),
            report,
        )

        # ---- native ETH -------------------------------------------------------
        boa.env.set_balance(user_wallet.address, 100 * EIGHTEEN_DECIMALS)
        boa.env.set_balance(recipients["prime"], EIGHTEEN_DECIMALS)  # existing-balance recipient
        _measure(
            "owner_native_untracked_fresh_recipient", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["native_untracked"], eth, amount, sender=bob),
            report,
        )
        # the transfer above registered ETH -> tracked from here on
        _measure(
            "owner_native_tracked_fresh_recipient", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["native_fresh"], eth, amount, sender=bob),
            report,
        )
        _measure(
            "owner_native_tracked_existing_recipient", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["prime"], eth, amount, sender=bob),
            report,
        )

        # ---- cheque lifecycle: first-use, then steady -------------------------
        timelock = user_wallet_config.timeLock()
        cheque_settings = createChequeSettings(
            _instantUsdThreshold=100 * EIGHTEEN_DECIMALS,
            _expensiveDelayBlocks=max(timelock, cheque_book.MIN_EXPENSIVE_CHEQUE_DELAY()),
            _defaultExpiryBlocks=timelock,
            _canManagersCreateCheques=True,
            _canManagerPay=True,
            _canBePulled=False,
        )
        set_live_cheque_settings(cheque_book, user_wallet.address, *cheque_settings, sender=bob)

        def create_cheque(recipient):
            return cheque_book.createCheque(
                user_wallet.address, recipient, alpha_token.address,
                amount, 0, 0, True, False, sender=bob,
            )

        _measure("cheque_owner_create", cheque_book, bob, lambda: create_cheque(recipients["cheque_a"]), report)
        # pay in a later transaction: cross-tx refund pricing for the cheque clear
        _measure(
            "cheque_owner_pay_existing", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["cheque_a"], alpha_token.address, amount, True, False, sender=bob),
            report,
        )
        _measure(
            "cheque_agent_atomic_create_and_pay", starter_agent_sender, charlie,
            lambda: starter_agent_sender.createAndPayCheque(
                starter_agent.address, user_wallet.address, recipients["cheque_b"],
                alpha_token.address, amount, (b"", 0, 0), sender=charlie,
            ),
            report,
        )
        # steady lifecycle (cheque accounting already initialized) — the valid
        # comparator for the steady atomic figure above
        _measure("cheque_owner_create_steady", cheque_book, bob, lambda: create_cheque(recipients["cheque_c"]), report)
        _measure(
            "cheque_owner_pay_existing_steady", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["cheque_c"], alpha_token.address, amount, True, False, sender=bob),
            report,
        )

        # ---- cross-block repeats (one block advanced before each) -------------
        # points/lastTxBlock/lastUpdate fields genuinely change value here
        boa.env.time_travel(blocks=1)
        _measure(
            "owner_whitelist_repeat_crossblock", user_wallet, bob,
            lambda: user_wallet.transferFunds(recipients["wl"], alpha_token.address, amount, sender=bob),
            report,
        )
        boa.env.time_travel(blocks=1)
        _measure(
            "owner_payee_repeat_primary_crossblock", user_wallet, bob,
            lambda: user_wallet.transferFunds(payee_primary, alpha_token.address, amount, sender=bob),
            report,
        )
        boa.env.time_travel(blocks=1)
        _measure(
            "agent_generic_repeat_crossblock", starter_agent_sender, charlie,
            lambda: agent_transfer(recipients["agent_wl"]), report,
        )

        # ---- billing pulls (payee-initiated; skips the manager permission bundle)
        user_wallet_config.setGlobalPayeeSettings(
            createGlobalPayeeSettings(_canPull=True), sender=paymaster.address
        )
        user_wallet_config.addPayee(alice, createPayeeSettings(_canPull=True), sender=paymaster.address)
        _measure(
            "billing_payee_pull_first", billing, alice,
            lambda: billing.pullPaymentAsPayee(user_wallet.address, alpha_token.address, amount, sender=alice),
            report,
        )
        _measure(
            "billing_payee_pull_repeat", billing, alice,
            lambda: billing.pullPaymentAsPayee(user_wallet.address, alpha_token.address, amount, sender=alice),
            report,
        )

        print("GAS_BENCHMARK_JSON_START")
        print(json.dumps(report, indent=2))
        print("GAS_BENCHMARK_JSON_END")

        # regression gates
        for label, expected in BASELINES.items():
            actual = report[label]["receipt_like"]
            assert abs(actual - expected) <= expected * TOLERANCE, (
                f"{label}: receipt-like {actual:,} deviates >{TOLERANCE:.1%} from baseline {expected:,}"
            )
        # 10 nonzero cheque fields (canBePulled=False stays zero) + numActiveCheques 1->0, x 4,800 cross-tx
        assert report["cheque_owner_pay_existing"]["raw_refund_counter"] == 52_800
        assert report["cheque_owner_pay_existing_steady"]["raw_refund_counter"] == 52_800
        # atomic: the same 11 slots net-cleared within one tx, x 19,900; 20% cap binds
        atomic = report["cheque_agent_atomic_create_and_pay"]
        assert atomic["raw_refund_counter"] == 218_900
        assert atomic["refund_applied"] == 172_846
        batch_saving = (
            report["agent_separate_steady_a"]["receipt_like"]
            + report["agent_separate_steady_b"]["receipt_like"]
            - report["agent_batch_two_steady"]["receipt_like"]
        )
        assert abs(batch_saving - BATCH_SAVING_BASELINE) <= BATCH_SAVING_BASELINE * TOLERANCE
    finally:
        # lock_changes() flattened the snapshot journal, so session-fixture
        # anchor reverts can no longer work (and no longer matter — this run
        # is standalone and the process is about to exit). Neutralize them so
        # the benchmark exits cleanly instead of erroring in teardown.
        boa.env.evm.revert = lambda *args, **kwargs: None
