#!/usr/bin/env python3
"""
Output Vault Parameters Script for Underscore Protocol

Fetches and displays all vault-related configuration from Underscore Protocol
smart contracts on Base mainnet, formatted as markdown tables.

This script outputs to prod_vault_params.md and includes:
- All registered vaults (Earn and Leverage)
- VaultRegistry configuration (AddressRegistry + LocalGov modules)
- Per-vault configuration (VaultConfig, approved tokens)
- EarnVaultWallet storage (for standard Earn vaults)
- LevgVaultWallet storage (for Leverage vaults)

Usage:
    python scripts/params/vaults_params.py
"""

import os
import sys
import time

import boa

# Import shared utilities
from params_utils import (
    UNDY_HQ,
    RPC_DELAY,
    VAULT_REGISTRY_ID,
    ZERO_ADDRESS,
    get_token_name,
    format_address,
    format_percent,
    format_blocks_to_time,
    format_token_amount,
    format_token_amount_precise,
    print_table,
    setup_boa_etherscan,
    boa_fork_context,
    print_report_header,
    print_report_footer,
    output_to_file,
)

# ============================================================================
# Global state for loaded contracts and addresses
# ============================================================================


class VaultProtocolState:
    """Holds vault-related protocol contracts and addresses."""

    def __init__(self):
        self.hq = None
        self.vault_registry = None
        self.vault_registry_addr = None
        self.earn_vaults = {}  # name -> {address, contract, reg_id, decimals}
        self.levg_vaults = {}  # name -> {address, contract, reg_id, decimals}

    def get_known_addresses(self) -> dict:
        """Build a map of all known protocol addresses for name resolution."""
        known = {}

        # Add vaults
        for name, vault_info in self.earn_vaults.items():
            known[vault_info["address"].lower()] = name

        for name, vault_info in self.levg_vaults.items():
            known[vault_info["address"].lower()] = name

        # Add HQ and VaultRegistry
        known[UNDY_HQ.lower()] = "UndyHq"
        if self.vault_registry_addr:
            known[self.vault_registry_addr.lower()] = "VaultRegistry"

        return known


# Global protocol state
protocol = VaultProtocolState()


def _get_known_addresses():
    """Callback for address resolution."""
    return protocol.get_known_addresses()


# ============================================================================
# Dynamic Contract Loading Functions
# ============================================================================


def load_vaults_with_classification(vr):
    """Load all vaults from VaultRegistry and classify by type."""
    print("  Loading vaults from VaultRegistry...", file=sys.stderr)
    earn_vaults = {}
    levg_vaults = {}
    num_vaults = vr.numAddrs()

    for i in range(1, num_vaults):
        time.sleep(RPC_DELAY)
        addr = str(vr.getAddr(i))
        if addr != ZERO_ADDRESS:
            time.sleep(RPC_DELAY)
            vault = boa.from_etherscan(addr, name=f"Vault_{i}")
            name = vault.name()
            decimals = vault.decimals()

            # Check if leveraged vault
            time.sleep(RPC_DELAY)
            vault_config = vr.vaultConfigs(addr)
            is_leveraged = vault_config.isLeveragedVault

            symbol = vault.symbol()

            # Verify undyHq matches (from VaultErc20Token.vy)
            time.sleep(RPC_DELAY)
            vault_undy_hq = str(vault.undyHq())
            undy_hq_match = vault_undy_hq.lower() == UNDY_HQ.lower()
            if not undy_hq_match:
                print(f"    WARNING: {name} has mismatched UNDY_HQ: {vault_undy_hq}", file=sys.stderr)

            # Get total assets (max and low estimates)
            time.sleep(RPC_DELAY)
            total_assets_max = vault.getTotalAssets(True)
            time.sleep(RPC_DELAY)
            total_assets_low = vault.getTotalAssets(False)

            # Get total supply and share price
            time.sleep(RPC_DELAY)
            total_supply = vault.totalSupply()
            time.sleep(RPC_DELAY)
            # Share price: value of 1 share (10**decimals) in underlying terms
            share_price = vault.convertToAssets(10**decimals) if total_supply > 0 else 10**decimals

            vault_data = {
                "address": addr,
                "contract": vault,
                "reg_id": i,
                "decimals": decimals,
                "symbol": symbol,
                "name": name,
                "undy_hq": vault_undy_hq,
                "undy_hq_match": undy_hq_match,
                "total_assets_max": total_assets_max,
                "total_assets_low": total_assets_low,
                "total_supply": total_supply,
                "share_price": share_price,
            }

            if is_leveraged:
                levg_vaults[name] = vault_data
                print(f"    Found leverage vault: {name}", file=sys.stderr)
            else:
                earn_vaults[name] = vault_data
                print(f"    Found earn vault: {name}", file=sys.stderr)

    return earn_vaults, levg_vaults


def initialize_protocol():
    """Initialize vault-related protocol contracts from UNDY_HQ."""
    print("Loading contracts from Etherscan...", file=sys.stderr)

    # Load HQ first
    protocol.hq = boa.from_etherscan(UNDY_HQ, name="UndyHq")

    # Load VaultRegistry
    time.sleep(RPC_DELAY)
    protocol.vault_registry_addr = str(protocol.hq.getAddr(VAULT_REGISTRY_ID))
    time.sleep(RPC_DELAY)
    protocol.vault_registry = boa.from_etherscan(
        protocol.vault_registry_addr, name="VaultRegistry"
    )

    # Load and classify vaults
    protocol.earn_vaults, protocol.levg_vaults = load_vaults_with_classification(
        protocol.vault_registry
    )

    print("  All contracts loaded successfully.\n", file=sys.stderr)


# ============================================================================
# Data Fetching Functions
# ============================================================================


def print_vaults_summary():
    """Print summary table of all vaults."""
    print("\n" + "=" * 80)
    print("\n<a id=\"all-vaults-summary\"></a>")
    print("## All Vaults Summary")

    all_vaults = []

    # Add earn vaults
    for vault_name, vault_info in protocol.earn_vaults.items():
        hq_check = "Y" if vault_info["undy_hq_match"] else "N"
        decimals = vault_info["decimals"]
        total_max = format_token_amount(vault_info["total_assets_max"], decimals)
        total_low = format_token_amount(vault_info["total_assets_low"], decimals)
        all_vaults.append([
            vault_info["reg_id"],
            vault_name,
            "Earn",
            total_max,
            total_low,
            hq_check,
        ])

    # Add leverage vaults
    for vault_name, vault_info in protocol.levg_vaults.items():
        hq_check = "Y" if vault_info["undy_hq_match"] else "N"
        decimals = vault_info["decimals"]
        total_max = format_token_amount(vault_info["total_assets_max"], decimals)
        total_low = format_token_amount(vault_info["total_assets_low"], decimals)
        all_vaults.append([
            vault_info["reg_id"],
            vault_name,
            "Leverage",
            total_max,
            total_low,
            hq_check,
        ])

    # Sort by reg_id
    all_vaults.sort(key=lambda x: x[0])

    print("\n| ID | Name | Type | Total Assets (Max) | Total Assets (Low) | HQ |")
    print("| --- | --- | --- | --- | --- | --- |")
    for row in all_vaults:
        print(f"| {' | '.join(str(cell) for cell in row)} |")


def fetch_vault_registry_config():
    """Fetch and print VaultRegistry configuration (AddressRegistry + LocalGov)."""
    vr = protocol.vault_registry

    print("\n" + "=" * 80)
    print("\n<a id=\"vault-registry-config\"></a>")
    print("## VaultRegistry Configuration")
    print(f"Address: `{protocol.vault_registry_addr}`")

    # AddressRegistry settings
    print("\n<a id=\"registry-settings\"></a>")
    num_addrs = vr.numAddrs()
    time.sleep(RPC_DELAY)
    registry_timelock = vr.registryChangeTimeLock()

    rows = [
        ("numAddrs (vaults)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(registry_timelock)),
    ]
    print_table("Registry Settings (AddressRegistry Module)", ["Parameter", "Value"], rows)

    # LocalGov settings
    print("\n<a id=\"governance-settings\"></a>")
    time.sleep(RPC_DELAY)
    governance = str(vr.governance())
    time.sleep(RPC_DELAY)
    gov_timelock = vr.govChangeTimeLock()
    time.sleep(RPC_DELAY)
    pending_gov = vr.pendingGov()

    gov_rows = [
        ("governance", format_address(governance, _get_known_addresses)),
        ("govChangeTimeLock", format_blocks_to_time(gov_timelock)),
    ]

    # Check if there's a pending governance change
    pending_new_gov = str(pending_gov[0]) if pending_gov else ZERO_ADDRESS
    if pending_new_gov != ZERO_ADDRESS:
        gov_rows.append(("pendingGov.newGov", format_address(pending_new_gov, _get_known_addresses)))
        gov_rows.append(("pendingGov.initiatedBlock", pending_gov[1]))
        gov_rows.append(("pendingGov.confirmBlock", pending_gov[2]))
    else:
        gov_rows.append(("pendingGov", "None"))

    print_table("Governance Settings (LocalGov Module)", ["Parameter", "Value"], gov_rows)


def fetch_earn_vault_wallet_storage(vault, decimals, vault_info):
    """Fetch EarnVaultWallet-specific storage items."""
    time.sleep(RPC_DELAY)
    num_assets = vault.numAssets()
    time.sleep(RPC_DELAY)
    last_underlying = vault.lastUnderlyingBal()
    time.sleep(RPC_DELAY)
    pending_yield = vault.pendingYieldRealized()
    time.sleep(RPC_DELAY)
    claimable_fees = vault.getClaimablePerformanceFees()
    time.sleep(RPC_DELAY)
    num_managers = vault.numManagers()

    storage_rows = [
        ("totalSupply (shares)", format_token_amount_precise(vault_info["total_supply"], decimals)),
        ("totalAssets (max)", format_token_amount_precise(vault_info["total_assets_max"], decimals)),
        ("totalAssets (low)", format_token_amount_precise(vault_info["total_assets_low"], decimals)),
        ("sharePrice (1 share =)", format_token_amount_precise(vault_info["share_price"], decimals)),
        ("numAssets (yield positions)", num_assets - 1 if num_assets > 0 else 0),
        ("lastUnderlyingBal", format_token_amount_precise(last_underlying, decimals)),
        ("pendingYieldRealized", format_token_amount_precise(pending_yield, decimals)),
        ("claimablePerformanceFees", format_token_amount_precise(claimable_fees, decimals)),
        ("numManagers", num_managers - 1 if num_managers > 0 else 0),
    ]

    return storage_rows, num_assets, num_managers


def fetch_levg_vault_wallet_storage(vault, decimals, vault_info):
    """Fetch LevgVaultWallet-specific storage items."""
    time.sleep(RPC_DELAY)
    collateral_asset = vault.collateralAsset()
    time.sleep(RPC_DELAY)
    leverage_asset = vault.leverageAsset()
    time.sleep(RPC_DELAY)
    max_debt_ratio = vault.maxDebtRatio()
    time.sleep(RPC_DELAY)
    usdc_slippage = vault.usdcSlippageAllowed()
    time.sleep(RPC_DELAY)
    green_slippage = vault.greenSlippageAllowed()
    time.sleep(RPC_DELAY)
    levg_helper = str(vault.levgVaultHelper())
    time.sleep(RPC_DELAY)
    num_managers = vault.numManagers()

    storage_rows = [
        ("totalSupply (shares)", format_token_amount_precise(vault_info["total_supply"], decimals)),
        ("totalAssets (max)", format_token_amount_precise(vault_info["total_assets_max"], decimals)),
        ("totalAssets (low)", format_token_amount_precise(vault_info["total_assets_low"], decimals)),
        ("sharePrice (1 share =)", format_token_amount_precise(vault_info["share_price"], decimals)),
        ("collateralAsset.vaultToken", format_address(str(collateral_asset[0]), _get_known_addresses)),
        ("collateralAsset.ripeVaultId", collateral_asset[1]),
        ("leverageAsset.vaultToken", format_address(str(leverage_asset[0]), _get_known_addresses)),
        ("leverageAsset.ripeVaultId", leverage_asset[1]),
        ("maxDebtRatio", format_percent(max_debt_ratio)),
        ("usdcSlippageAllowed", format_percent(usdc_slippage)),
        ("greenSlippageAllowed", format_percent(green_slippage)),
        ("levgVaultHelper", format_address(levg_helper, _get_known_addresses)),
        ("numManagers", num_managers - 1 if num_managers > 0 else 0),
    ]

    return storage_rows, num_managers, levg_helper


def fetch_levg_vault_helper_config(levg_helper_addr: str):
    """Fetch and print LevgVaultHelper immutable configuration."""
    if levg_helper_addr == ZERO_ADDRESS:
        return

    try:
        time.sleep(RPC_DELAY)
        helper = boa.from_etherscan(levg_helper_addr, name="LevgVaultHelper")

        time.sleep(RPC_DELAY)
        ripe_registry = str(helper.RIPE_REGISTRY())
        time.sleep(RPC_DELAY)
        green_token = str(helper.GREEN_TOKEN())
        time.sleep(RPC_DELAY)
        savings_green = str(helper.SAVINGS_GREEN())
        time.sleep(RPC_DELAY)
        usdc = str(helper.USDC())

        helper_rows = [
            ("RIPE_REGISTRY", format_address(ripe_registry, _get_known_addresses)),
            ("GREEN_TOKEN", format_address(green_token, _get_known_addresses)),
            ("SAVINGS_GREEN", format_address(savings_green, _get_known_addresses)),
            ("USDC", format_address(usdc, _get_known_addresses)),
        ]
        print_table("LevgVaultHelper Configuration", ["Parameter", "Value"], helper_rows)
    except Exception as e:
        print(f"\n*Could not fetch LevgVaultHelper config: {e}*")


def print_vault_config(vault_name, vault_info, vr):
    """Print VaultConfig for a vault."""
    vault_addr = vault_info["address"]
    decimals = vault_info["decimals"]

    time.sleep(RPC_DELAY)
    vault_config = vr.vaultConfigs(vault_addr)
    time.sleep(RPC_DELAY)
    num_tokens = vr.numApprovedVaultTokens(vault_addr)

    max_deposit = vault_config.maxDepositAmount
    min_yield_withdraw = vault_config.minYieldWithdrawAmount
    config_rows = [
        ("canDeposit", vault_config.canDeposit),
        ("canWithdraw", vault_config.canWithdraw),
        ("maxDepositAmount", "Unlimited" if max_deposit == 0 else format_token_amount_precise(max_deposit, decimals)),
        ("isVaultOpsFrozen", vault_config.isVaultOpsFrozen),
        ("redemptionBuffer", format_percent(vault_config.redemptionBuffer)),
        ("minYieldWithdrawAmount", format_token_amount_precise(min_yield_withdraw, decimals)),
        ("performanceFee", format_percent(vault_config.performanceFee)),
        ("shouldAutoDeposit", vault_config.shouldAutoDeposit),
        ("defaultTargetVaultToken", format_address(str(vault_config.defaultTargetVaultToken), _get_known_addresses)),
        ("isLeveragedVault", vault_config.isLeveragedVault),
        ("shouldEnforceAllowlist", vault_config.shouldEnforceAllowlist),
    ]
    print_table("VaultConfig (from VaultRegistry)", ["Parameter", "Value"], config_rows)

    # Approved vault tokens
    if num_tokens > 0:
        print(f"\n**Approved Vault Tokens ({num_tokens}):**")
        print("| Index | Token |")
        print("| --- | --- |")
        for i in range(1, num_tokens + 1):
            time.sleep(RPC_DELAY)
            token_addr = vr.approvedVaultTokens(vault_addr, i)
            if str(token_addr) != ZERO_ADDRESS:
                print(f"| {i} | {format_address(str(token_addr), _get_known_addresses)} |")


def try_fetch_agent_ownership_data(mgr_addr: str) -> dict | None:
    """Try to fetch ownership data assuming manager is an EarnVaultAgent.

    Returns dict with ownership data if successful, None if not an agent contract.
    """
    try:
        time.sleep(RPC_DELAY)
        agent = boa.from_etherscan(mgr_addr, name=f"Agent_{mgr_addr[:8]}")

        # Try to call EarnVaultAgent-specific functions
        time.sleep(RPC_DELAY)
        group_id = agent.groupId()
        time.sleep(RPC_DELAY)
        owner = str(agent.owner())
        time.sleep(RPC_DELAY)
        ownership_timelock = agent.ownershipTimeLock()
        time.sleep(RPC_DELAY)
        min_timelock = agent.MIN_OWNERSHIP_TIMELOCK()
        time.sleep(RPC_DELAY)
        max_timelock = agent.MAX_OWNERSHIP_TIMELOCK()
        time.sleep(RPC_DELAY)
        pending_owner = agent.pendingOwner()

        return {
            "group_id": group_id,
            "owner": owner,
            "ownership_timelock": ownership_timelock,
            "min_timelock": min_timelock,
            "max_timelock": max_timelock,
            "pending_owner": pending_owner,
        }
    except Exception:
        # Not an EarnVaultAgent or failed to load
        return None


def print_managers(vault, num_managers):
    """Print managers for a vault, with ownership data if manager is an EarnVaultAgent."""
    if num_managers > 1:
        print(f"\n**Managers ({num_managers - 1}):**")

        for i in range(1, min(num_managers, 11)):  # Limit to 10 for output
            time.sleep(RPC_DELAY)
            mgr = vault.managers(i)
            mgr_addr = str(mgr)
            if mgr_addr != ZERO_ADDRESS:
                print(f"\n**Manager {i}:** `{mgr_addr}`")

                # Try to get EarnVaultAgent ownership data
                agent_data = try_fetch_agent_ownership_data(mgr_addr)
                if agent_data:
                    print(f"  - Type: EarnVaultAgent")
                    print(f"  - groupId: {agent_data['group_id']}")
                    print(f"  - owner: {format_address(agent_data['owner'], _get_known_addresses)}")
                    print(f"  - ownershipTimeLock: {format_blocks_to_time(agent_data['ownership_timelock'])}")
                    print(f"  - MIN/MAX_OWNERSHIP_TIMELOCK: {format_blocks_to_time(agent_data['min_timelock'])} / {format_blocks_to_time(agent_data['max_timelock'])}")

                    # Check for pending owner change
                    pending = agent_data["pending_owner"]
                    pending_new_owner = str(pending[0]) if pending else ZERO_ADDRESS
                    if pending_new_owner != ZERO_ADDRESS:
                        print(f"  - pendingOwner.newOwner: {format_address(pending_new_owner, _get_known_addresses)}")
                        print(f"  - pendingOwner.initiatedBlock: {pending[1]}")
                        print(f"  - pendingOwner.confirmBlock: {pending[2]}")
                    else:
                        print(f"  - pendingOwner: None")
                else:
                    print(f"  - Type: Unknown (not EarnVaultAgent)")


def print_yield_position_assets(vault, num_assets):
    """Print yield position assets for EarnVaultWallet."""
    if num_assets > 1:
        print(f"\n**Yield Position Assets ({num_assets - 1}):**")
        print("| Index | Vault Token | Lego ID |")
        print("| --- | --- | --- |")
        for i in range(1, num_assets):
            time.sleep(RPC_DELAY)
            asset_addr = str(vault.assets(i))
            if asset_addr != ZERO_ADDRESS:
                time.sleep(RPC_DELAY)
                lego_id = vault.vaultToLegoId(asset_addr)
                print(f"| {i} | {format_address(asset_addr, _get_known_addresses)} | {lego_id} |")


def print_table_of_contents():
    """Print a clickable table of contents."""
    print("""
## Table of Contents

1. [All Vaults Summary](#all-vaults-summary)
2. [VaultRegistry Configuration](#vault-registry-config)
   - [Registry Settings (AddressRegistry)](#registry-settings)
   - [Governance Settings (LocalGov)](#governance-settings)
3. [Earn Vaults](#earn-vaults)
4. [Leverage Vaults](#leverage-vaults)
""")


def fetch_earn_vaults():
    """Fetch and print all Earn vault configurations."""
    vr = protocol.vault_registry

    print("\n" + "=" * 80)
    print("\n<a id=\"earn-vaults\"></a>")
    print("## Earn Vaults")

    if not protocol.earn_vaults:
        print("\n*No Earn vaults registered.*")
        return

    for vault_name, vault_info in protocol.earn_vaults.items():
        time.sleep(RPC_DELAY * 2)  # Extra pause between vaults
        vault = vault_info["contract"]
        decimals = vault_info["decimals"]

        print(f"\n### {vault_name}")
        print(f"Address: `{vault_info['address']}`")
        print(f"Symbol: `{vault_info['symbol']}` | Decimals: {vault_info['decimals']}")
        undy_hq_status = "Verified" if vault_info['undy_hq_match'] else f"MISMATCH: `{vault_info['undy_hq']}`"
        print(f"UNDY_HQ: {undy_hq_status}")

        # VaultConfig
        print_vault_config(vault_name, vault_info, vr)

        # EarnVaultWallet Storage
        storage_rows, num_assets, num_managers = fetch_earn_vault_wallet_storage(vault, decimals, vault_info)
        print_table("EarnVaultWallet Storage", ["Parameter", "Value"], storage_rows)

        # Yield Position Assets
        print_yield_position_assets(vault, num_assets)

        # Managers
        print_managers(vault, num_managers)


def fetch_leverage_vaults():
    """Fetch and print all Leverage vault configurations."""
    vr = protocol.vault_registry

    print("\n" + "=" * 80)
    print("\n<a id=\"leverage-vaults\"></a>")
    print("## Leverage Vaults")

    if not protocol.levg_vaults:
        print("\n*No Leverage vaults registered.*")
        return

    for vault_name, vault_info in protocol.levg_vaults.items():
        time.sleep(RPC_DELAY * 2)  # Extra pause between vaults
        vault = vault_info["contract"]
        decimals = vault_info["decimals"]

        print(f"\n### {vault_name}")
        print(f"Address: `{vault_info['address']}`")
        print(f"Symbol: `{vault_info['symbol']}` | Decimals: {vault_info['decimals']}")
        undy_hq_status = "Verified" if vault_info['undy_hq_match'] else f"MISMATCH: `{vault_info['undy_hq']}`"
        print(f"UNDY_HQ: {undy_hq_status}")

        # VaultConfig
        print_vault_config(vault_name, vault_info, vr)

        # LevgVaultWallet Storage
        storage_rows, num_managers, levg_helper = fetch_levg_vault_wallet_storage(vault, decimals, vault_info)
        print_table("LevgVaultWallet Storage", ["Parameter", "Value"], storage_rows)

        # LevgVaultHelper Configuration
        fetch_levg_vault_helper_config(levg_helper)

        # Managers
        print_managers(vault, num_managers)


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point."""
    # Output file path (same directory as this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "vaults_params_output.md")

    # Progress messages go to stderr so user sees them
    print("Connecting to Base mainnet via Alchemy...", file=sys.stderr)

    # Set etherscan API for contract loading
    setup_boa_etherscan()

    # Fork at latest block
    with boa_fork_context() as block_number:
        print(f"Connected. Block: {block_number}\n", file=sys.stderr)

        # Initialize vault-related protocol contracts
        initialize_protocol()

        print(f"Writing output to {output_file}...", file=sys.stderr)

        # Write report to file
        with output_to_file(output_file):
            # Header
            print_report_header("Underscore Vault Parameters", block_number)

            # Table of Contents
            print_table_of_contents()

            # All Vaults Summary
            print_vaults_summary()

            # VaultRegistry Configuration
            fetch_vault_registry_config()

            # Earn Vaults
            fetch_earn_vaults()

            # Leverage Vaults
            fetch_leverage_vaults()

            # Footer
            print_report_footer(block_number)

        print(f"Done! Output saved to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
