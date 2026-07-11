"""Transaction-boundary gas benchmark for the user-wallet transfer flow.

Opt-in (slow, prints a report): run with

    GAS_PROFILE=1 pytest tests/gas_profiling/test_transfer_gas_profile.py -q -s

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

Reported per scenario: gross execution gas of the top-level call, the raw
refund counter, modeled intrinsic gas (21,000 + calldata bytes), and a
receipt-like total (gross + intrinsic - refund capped at 20% per EIP-3529)
approximating a direct EOA transaction to the same entry point.

NOTE: this file intentionally does not use boa.env.anchor() — lock_changes()
flattens the snapshot journal, so state moves forward only. Scenario ordering
matters (e.g. the agent's first manager action must stay first). Run this file
standalone; session-teardown snapshot reverts may warn afterwards.
"""

import json
import os

import boa
import pytest

from config.BluePrint import TOKENS
from constants import EIGHTEEN_DECIMALS, MAX_UINT256, ZERO_ADDRESS
from conf_utils import set_live_cheque_settings

pytestmark = pytest.mark.skipif(
    not os.environ.get("GAS_PROFILE"),
    reason="gas benchmark is opt-in: set GAS_PROFILE=1",
)

PRECOMPILES = [i.to_bytes(20, "big") for i in range(1, 11)]


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
        "refund_counter": refund,
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
    fork,
    user_wallet,
    user_wallet_config,
    bob,
    charlie,
    alpha_token,
    alpha_token_whale,
    mock_ripe,
    switchboard_alpha,
    migrator,
    paymaster,
    cheque_book,
    starter_agent,
    starter_agent_sender,
    createPayeeSettings,
    createChequeSettings,
):
    report = {}
    amount = 10 * EIGHTEEN_DECIMALS
    eth = TOKENS[fork]["ETH"]

    def fund_and_track(track_amount=1_000 * EIGHTEEN_DECIMALS):
        alpha_token.transfer(user_wallet.address, track_amount, sender=alpha_token_whale)
        user_wallet_config.updateAssetData(0, alpha_token.address, False, sender=switchboard_alpha.address)

    def whitelist(addr):
        user_wallet_config.addWhitelistAddrViaMigrator(addr, sender=migrator.address)

    # ---- setup (not measured) --------------------------------------------
    mock_ripe.setPrice(alpha_token.address, EIGHTEEN_DECIMALS)
    mock_ripe.setPrice(eth, 2_000 * EIGHTEEN_DECIMALS)
    fund_and_track()

    recipients = {
        name: boa.env.generate_address(f"gasbench_{name}")
        for name in [
            "prime", "wl", "wl_full", "agent_wl", "mgr_wl", "sep_wl", "batch_wl",
            "native_untracked", "native_fresh", "cheque_a", "cheque_b",
        ]
    }
    for name in ["prime", "wl", "wl_full", "agent_wl", "mgr_wl", "sep_wl", "batch_wl", "native_untracked", "native_fresh"]:
        whitelist(recipients[name])

    # prime wallet-level state so "first" scenarios measure the recipient-side
    # first-use cost, not one-time wallet initialization (points structs etc.)
    user_wallet.transferFunds(recipients["prime"], alpha_token.address, EIGHTEEN_DECIMALS, sender=bob)

    # ---- owner -> whitelisted recipient ----------------------------------
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

    # ---- owner -> registered payee ---------------------------------------
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

    # ---- agent path (first manager action of the whole run) ---------------
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

    # manager data now initialized -> steady-state direct manager call
    _measure(
        "manager_direct_whitelist_steady", user_wallet, starter_agent.address,
        lambda: user_wallet.transferFunds(recipients["mgr_wl"], alpha_token.address, amount, sender=starter_agent.address),
        report,
    )

    # ---- batch vs separate (steady state) ---------------------------------
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

    # ---- cheque lifecycle --------------------------------------------------
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

    _measure(
        "cheque_owner_create", cheque_book, bob,
        lambda: cheque_book.createCheque(
            user_wallet.address, recipients["cheque_a"], alpha_token.address,
            amount, 0, 0, True, False, sender=bob,
        ),
        report,
    )
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

    print("GAS_BENCHMARK_JSON_START")
    print(json.dumps(report, indent=2))
    print("GAS_BENCHMARK_JSON_END")
