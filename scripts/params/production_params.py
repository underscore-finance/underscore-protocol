#!/usr/bin/env python3
"""
Output Production Parameters Script for Underscore Protocol

Fetches and displays all current production configuration from Underscore Protocol
smart contracts on Base mainnet, formatted as markdown tables.

This script only requires the UNDY_HQ address - all other contract addresses
are dynamically derived from the on-chain registries.

Usage:
    python scripts/params/production_params.py
"""

import os
import sys
import time

import boa

# Import shared utilities
from params_utils import (
    UNDY_HQ,
    RPC_URL,
    RPC_DELAY,
    HUNDRED_PERCENT,
    LEDGER_ID,
    MISSION_CONTROL_ID,
    LEGO_BOOK_ID,
    SWITCHBOARD_ID,
    HATCHERY_ID,
    LOOT_DISTRIBUTOR_ID,
    APPRAISER_ID,
    WALLET_BACKPACK_ID,
    BILLING_ID,
    VAULT_REGISTRY_ID,
    ZERO_ADDRESS,
    get_token_name,
    format_address,
    format_percent,
    format_blocks_to_time,
    format_token_amount,
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


class ProtocolState:
    """Holds all dynamically loaded protocol contracts and addresses."""

    def __init__(self):
        self.hq = None
        self.core_contracts = {}
        self.core_addresses = {}
        self.wallet_backpack_components = {}
        self.vaults = {}
        self.legos = {}
        self.switchboard_configs = {}
        self.templates = {}

    def get_known_addresses(self) -> dict:
        """Build a map of all known protocol addresses for name resolution."""
        known = {}

        # Add core addresses
        for name, addr in self.core_addresses.items():
            known[addr.lower()] = name

        # Add wallet backpack components
        for name, addr in self.wallet_backpack_components.items():
            known[addr.lower()] = name

        # Add vaults
        for name, vault_info in self.vaults.items():
            known[vault_info["address"].lower()] = name

        # Add legos
        for lego_id, lego_info in self.legos.items():
            known[lego_info["address"].lower()] = lego_info.get("description", f"Lego_{lego_id}")

        # Add switchboard configs
        for config_id, config_info in self.switchboard_configs.items():
            known[config_info["address"].lower()] = config_info.get("description", f"Config_{config_id}")

        # Add templates
        for name, addr in self.templates.items():
            if addr:
                known[addr.lower()] = name

        # Add HQ
        known[UNDY_HQ.lower()] = "UndyHq"

        return known


# Global protocol state
protocol = ProtocolState()


def _get_known_addresses():
    """Callback for address resolution."""
    return protocol.get_known_addresses()


# ============================================================================
# Dynamic Contract Loading Functions
# ============================================================================


def load_core_contracts(hq):
    """Load all core contracts from UndyHq registry."""
    print("  Loading core contracts from UndyHq...", file=sys.stderr)

    # Get addresses first
    addresses = {
        "Ledger": str(hq.getAddr(LEDGER_ID)),
        "MissionControl": str(hq.getAddr(MISSION_CONTROL_ID)),
        "LegoBook": str(hq.getAddr(LEGO_BOOK_ID)),
        "Switchboard": str(hq.getAddr(SWITCHBOARD_ID)),
        "Hatchery": str(hq.getAddr(HATCHERY_ID)),
        "LootDistributor": str(hq.getAddr(LOOT_DISTRIBUTOR_ID)),
        "Appraiser": str(hq.getAddr(APPRAISER_ID)),
        "WalletBackpack": str(hq.getAddr(WALLET_BACKPACK_ID)),
        "Billing": str(hq.getAddr(BILLING_ID)),
        "VaultRegistry": str(hq.getAddr(VAULT_REGISTRY_ID)),
    }

    # Load contracts from Etherscan
    contracts = {}
    for name, addr in addresses.items():
        time.sleep(RPC_DELAY)
        if addr != ZERO_ADDRESS:
            contracts[name] = boa.from_etherscan(addr, name=name)
        else:
            contracts[name] = None

    return contracts, addresses


def load_wallet_backpack_components(wb):
    """Load wallet backpack component addresses from WalletBackpack registry."""
    print("  Loading WalletBackpack components...", file=sys.stderr)
    return {
        "Kernel": str(wb.kernel()),
        "Sentinel": str(wb.sentinel()),
        "HighCommand": str(wb.highCommand()),
        "Paymaster": str(wb.paymaster()),
        "ChequeBook": str(wb.chequeBook()),
        "Migrator": str(wb.migrator()),
    }


def load_templates_and_agent(mc):
    """Load templates and agent wrapper from MissionControl."""
    print("  Loading templates and agent from MissionControl...", file=sys.stderr)
    user_wallet_config = mc.userWalletConfig()
    agent_config = mc.agentConfig()

    return {
        "UserWalletTemplate": str(user_wallet_config.walletTemplate),
        "UserWalletConfigTemplate": str(user_wallet_config.configTemplate),
        "AgentWrapper": str(agent_config.startingAgent),
    }


def load_earn_vaults(vr):
    """Load all earn vaults from VaultRegistry."""
    print("  Loading earn vaults from VaultRegistry...", file=sys.stderr)
    vaults = {}
    num_vaults = vr.numAddrs()

    for i in range(1, num_vaults):
        time.sleep(RPC_DELAY)
        addr = str(vr.getAddr(i))
        if addr != ZERO_ADDRESS:
            vault = boa.from_etherscan(addr, name=f"EarnVault_{i}")
            name = vault.name()
            vaults[name] = {"address": addr, "contract": vault, "reg_id": i}

    return vaults


def load_legos(lb):
    """Load all legos from LegoBook registry."""
    print("  Loading legos from LegoBook...", file=sys.stderr)
    legos = {}
    num_legos = lb.numAddrs()

    for i in range(1, num_legos):
        time.sleep(RPC_DELAY)
        addr = str(lb.getAddr(i))
        if addr != ZERO_ADDRESS:
            addr_info = lb.addrInfo(i)
            legos[i] = {"address": addr, "description": addr_info.description}

    return legos


def load_switchboard_configs(sb):
    """Load all switchboard config contracts."""
    print("  Loading switchboard configs from Switchboard...", file=sys.stderr)
    configs = {}
    num_configs = sb.numAddrs()

    for i in range(1, num_configs):
        time.sleep(RPC_DELAY)
        addr = str(sb.getAddr(i))
        if addr != ZERO_ADDRESS:
            addr_info = sb.addrInfo(i)
            configs[i] = {"address": addr, "description": addr_info.description}

    return configs


def initialize_protocol():
    """Initialize all protocol contracts and addresses from UNDY_HQ."""
    print("Loading contracts from Etherscan...", file=sys.stderr)

    # Load HQ first
    protocol.hq = boa.from_etherscan(UNDY_HQ, name="UndyHq")

    # Load core contracts
    protocol.core_contracts, protocol.core_addresses = load_core_contracts(protocol.hq)

    # Load wallet backpack components
    if protocol.core_contracts.get("WalletBackpack"):
        protocol.wallet_backpack_components = load_wallet_backpack_components(
            protocol.core_contracts["WalletBackpack"]
        )

    # Load templates and agent from MissionControl
    if protocol.core_contracts.get("MissionControl"):
        protocol.templates = load_templates_and_agent(protocol.core_contracts["MissionControl"])

    # Load vaults
    if protocol.core_contracts.get("VaultRegistry"):
        protocol.vaults = load_earn_vaults(protocol.core_contracts["VaultRegistry"])

    # Load legos
    if protocol.core_contracts.get("LegoBook"):
        protocol.legos = load_legos(protocol.core_contracts["LegoBook"])

    # Load switchboard configs
    if protocol.core_contracts.get("Switchboard"):
        protocol.switchboard_configs = load_switchboard_configs(protocol.core_contracts["Switchboard"])

    print("  All contracts loaded successfully.\n", file=sys.stderr)


# ============================================================================
# Data Fetching Functions
# ============================================================================


def try_identify_sender_type(sender_addr: str) -> str:
    """Identify if sender is AgentSenderGeneric or AgentSenderSpecial.

    AgentSenderSpecial has RIPE_GREEN_TOKEN immutable.
    AgentSenderGeneric does not.
    """
    try:
        time.sleep(RPC_DELAY)
        sender = boa.from_etherscan(sender_addr, name=f"Sender_{sender_addr[:8]}")
        # Try to call RIPE_GREEN_TOKEN - only exists on AgentSenderSpecial
        time.sleep(RPC_DELAY)
        sender.RIPE_GREEN_TOKEN()
        return "AgentSenderSpecial"
    except Exception:
        # Either failed to load or doesn't have RIPE_GREEN_TOKEN
        try:
            # Check if it has owner() which both Generic and Special have via Ownership module
            time.sleep(RPC_DELAY)
            sender = boa.from_etherscan(sender_addr, name=f"Sender_{sender_addr[:8]}")
            sender.owner()
            return "AgentSenderGeneric"
        except Exception:
            return "Unknown"


def fetch_agent_wrapper_senders(agent_wrapper_addr: str):
    """Fetch and print senders registered in AgentWrapper."""
    if agent_wrapper_addr == ZERO_ADDRESS:
        return

    try:
        time.sleep(RPC_DELAY)
        agent_wrapper = boa.from_etherscan(agent_wrapper_addr, name="AgentWrapper")
        time.sleep(RPC_DELAY)
        num_senders = agent_wrapper.numSenders()

        if num_senders > 1:
            print(f"\n**Registered Senders ({num_senders - 1}):**")
            print("| Index | Address | Type |")
            print("| --- | --- | --- |")
            for i in range(1, num_senders):
                time.sleep(RPC_DELAY)
                sender_addr = str(agent_wrapper.senders(i))
                if sender_addr != ZERO_ADDRESS:
                    sender_type = try_identify_sender_type(sender_addr)
                    print(f"| {i} | `{sender_addr}` | {sender_type} |")
        else:
            print("\n*No senders registered in AgentWrapper.*")
    except Exception as e:
        print(f"\n*Could not fetch AgentWrapper senders: {e}*")


def print_executive_summary():
    """Print an executive summary with key protocol metrics."""
    print("\n<a id=\"executive-summary\"></a>")
    print("## Executive Summary\n")

    ledger = protocol.core_contracts.get("Ledger")
    lego_book = protocol.core_contracts.get("LegoBook")

    num_wallets = ledger.numUserWallets() if ledger else 0
    num_legos = lego_book.numAddrs() if lego_book else 0
    num_vaults = len(protocol.vaults)

    rows = [
        ("Total User Wallets", num_wallets - 1 if num_wallets > 0 else 0),
        ("Registered Legos", num_legos - 1 if num_legos > 0 else 0),
        ("Earn Vaults", num_vaults),
    ]

    print("| Metric | Value |")
    print("| --- | --- |")
    for row in rows:
        print(f"| **{row[0]}** | {row[1]} |")


def print_table_of_contents():
    """Print a clickable table of contents."""
    print("""
## Table of Contents

1. [Executive Summary](#executive-summary)
2. **Registries**
   - [UndyHq Configuration](#undy-hq)
   - [UNDY Token State](#undy-token)
   - [Switchboard Registry](#switchboard-registry) (includes all config contracts)
3. **Core Protocol**
   - [Department Pause States](#department-pause-states)
   - [WalletBackpack Components](#wallet-backpack)
   - [MissionControl Configuration](#mission-control)
     - [User Wallet Config](#user-wallet-config)
     - [Per-Asset Configs](#per-asset-configs)
     - [Agent Config](#agent-config)
     - [Manager Config](#manager-config)
     - [Payee Config](#payee-config)
     - [Cheque Config](#cheque-config)
     - [RIPE Rewards Config](#ripe-rewards-config)
     - [Security Signers](#security-signers)
     - [Creator Whitelist](#creator-whitelist)
   - [LootDistributor Config](#loot-distributor)
   - [Ledger Statistics](#ledger)
     - [Vault Token Registry](#vault-token-registry)
     - [Backpack Items](#backpack-items)

> **Note:** Contract addresses: `deployments_output.md`
> **Note:** Vault configuration: `vaults_params_output.md`
> **Note:** Lego configuration: `lego_params_output.md`
""")


def fetch_undy_hq_data():
    """Fetch and print UndyHq configuration data."""
    hq = protocol.hq

    print("\n" + "=" * 80)
    print("\n<a id=\"undy-hq\"></a>")
    print("# UndyHq - Main Registry & Governance")
    print(f"Address: {UNDY_HQ}")

    num_addrs = hq.numAddrs()
    rows = [
        ("undyToken", format_address(str(hq.undyToken()), _get_known_addresses)),
        ("mintEnabled", hq.mintEnabled()),
        ("numAddrs (departments)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(hq.registryChangeTimeLock())),
    ]

    print_table("Registry Config (AddressRegistry Module)", ["Parameter", "Value"], rows)

    # LocalGov settings
    time.sleep(RPC_DELAY)
    governance = str(hq.governance())
    time.sleep(RPC_DELAY)
    gov_timelock = hq.govChangeTimeLock()
    time.sleep(RPC_DELAY)
    pending_gov = hq.pendingGov()

    gov_rows = [
        ("governance", format_address(governance, _get_known_addresses)),
        ("govChangeTimeLock", format_blocks_to_time(gov_timelock)),
    ]

    pending_new_gov = str(pending_gov[0]) if pending_gov else ZERO_ADDRESS
    if pending_new_gov != ZERO_ADDRESS:
        gov_rows.append(("pendingGov.newGov", format_address(pending_new_gov, _get_known_addresses)))
        gov_rows.append(("pendingGov.initiatedBlock", pending_gov[1]))
        gov_rows.append(("pendingGov.confirmBlock", pending_gov[2]))
    else:
        gov_rows.append(("pendingGov", "None"))

    print_table("Governance Settings (LocalGov Module)", ["Parameter", "Value"], gov_rows)

    # List registered departments
    if num_addrs > 1:
        print("\n### Registered Departments")
        headers = ["ID", "Description", "Address", "Can Mint UNDY", "Can Set Blacklist"]
        dept_rows = []
        for i in range(1, num_addrs):
            time.sleep(RPC_DELAY)
            addr_info = hq.addrInfo(i)
            contract_addr = str(addr_info.addr)
            if contract_addr == ZERO_ADDRESS:
                continue

            hq_config = hq.hqConfig(i)
            dept_rows.append([
                i,
                addr_info.description,
                format_address(contract_addr, _get_known_addresses),
                "Yes" if hq_config.canMintUndy else "No",
                "Yes" if hq_config.canSetTokenBlacklist else "No",
            ])

        if dept_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in dept_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")

        # Check for pending HQ config changes
        pending_changes = []
        for i in range(1, num_addrs):
            time.sleep(RPC_DELAY)
            if hq.hasPendingHqConfigChange(i):
                time.sleep(RPC_DELAY)
                pending = hq.pendingHqConfig(i)
                addr_info = hq.addrInfo(i)
                pending_changes.append({
                    "reg_id": i,
                    "description": addr_info.description,
                    "new_config": pending[0],  # HqConfig struct
                    "initiated_block": pending[1],
                    "confirm_block": pending[2],
                })

        if pending_changes:
            print("\n### Pending HQ Config Changes")
            for change in pending_changes:
                new_cfg = change["new_config"]
                print(f"\n**Department {change['reg_id']} ({change['description']}):**")
                print(f"  - New canMintUndy: {'Yes' if new_cfg.canMintUndy else 'No'}")
                print(f"  - New canSetTokenBlacklist: {'Yes' if new_cfg.canSetTokenBlacklist else 'No'}")
                print(f"  - Initiated Block: {change['initiated_block']}")
                print(f"  - Confirm Block: {change['confirm_block']}")

    # Check for pending registry changes (AddressRegistry module)
    print("\n### Pending Registry Changes")
    fetch_registry_pending_changes(hq, "UndyHq")


def fetch_undy_token_state():
    """Fetch and print UNDY token state (totalSupply, isPaused)."""
    hq = protocol.hq

    print("\n" + "=" * 80)
    print("\n<a id=\"undy-token\"></a>")
    print("# UNDY Token State")

    try:
        undy_token_addr = str(hq.undyToken())
        print(f"Address: {undy_token_addr}")

        time.sleep(RPC_DELAY)
        undy_token = boa.from_etherscan(undy_token_addr, name="UndyToken")

        time.sleep(RPC_DELAY)
        total_supply = undy_token.totalSupply()
        time.sleep(RPC_DELAY)
        is_paused = undy_token.isPaused()

        rows = [
            ("totalSupply", format_token_amount(total_supply, 18, "UNDY")),
            ("isPaused", is_paused),
        ]

        # Try to get token metadata
        try:
            time.sleep(RPC_DELAY)
            name = undy_token.name()
            time.sleep(RPC_DELAY)
            symbol = undy_token.symbol()
            time.sleep(RPC_DELAY)
            decimals = undy_token.decimals()
            rows.insert(0, ("name", name))
            rows.insert(1, ("symbol", symbol))
            rows.insert(2, ("decimals", decimals))
        except Exception:
            pass

        print_table("Token State", ["Parameter", "Value"], rows)

    except Exception as e:
        print(f"\n*Could not fetch UNDY token state: {e}*")


def fetch_department_pause_states():
    """Fetch and print pause states for all departments."""
    print("\n" + "=" * 80)
    print("\n<a id=\"department-pause-states\"></a>")
    print("# Department Pause States")

    departments_to_check = [
        ("Appraiser", protocol.core_contracts.get("Appraiser")),
        ("Billing", protocol.core_contracts.get("Billing")),
        ("Hatchery", protocol.core_contracts.get("Hatchery")),
        ("LootDistributor", protocol.core_contracts.get("LootDistributor")),
    ]

    rows = []
    for dept_name, contract in departments_to_check:
        if contract:
            try:
                time.sleep(RPC_DELAY)
                is_paused = contract.isPaused()
                rows.append((dept_name, "Paused" if is_paused else "Active"))
            except Exception:
                rows.append((dept_name, "N/A (no isPaused)"))
        else:
            rows.append((dept_name, "Not loaded"))

    print_table("Department Status", ["Department", "Status"], rows)


def fetch_ripe_rewards_config(mc):
    """Fetch and print RIPE rewards config from MissionControl.

    This is a new feature - gracefully fails if not available in deployed contract.
    The RIPE rewards config was moved from LootDistributor to MissionControl.
    """
    try:
        print("\n<a id=\"ripe-rewards-config\"></a>")
        time.sleep(RPC_DELAY)
        ripe_config = mc.ripeRewardsConfig()

        ripe_rows = [
            ("stakeRatio", format_percent(ripe_config.stakeRatio)),
            ("lockDuration", format_blocks_to_time(ripe_config.lockDuration)),
        ]
        print_table("RIPE Rewards Config", ["Parameter", "Value"], ripe_rows)
    except Exception:
        print("\n*Could not fetch RIPE rewards config from MissionControl (not available in this contract version - check LootDistributor).*")


def fetch_security_signers(mc):
    """Fetch and print security signers from MissionControl (iterable).

    This is a new feature - gracefully fails if not available in deployed contract.
    """
    try:
        print("\n<a id=\"security-signers\"></a>")
        time.sleep(RPC_DELAY)
        num_signers = mc.numSecuritySigners()

        # Actual count is num_signers - 1 (index 0 is sentinel)
        actual_count = num_signers - 1 if num_signers > 0 else 0

        if actual_count > 0:
            print(f"\n**Security Signers ({actual_count}):**")
            print("| Index | Address |")
            print("| --- | --- |")
            for i in range(1, num_signers):
                time.sleep(RPC_DELAY)
                signer_addr = str(mc.securitySigners(i))
                if signer_addr != ZERO_ADDRESS:
                    print(f"| {i} | {format_address(signer_addr, _get_known_addresses)} |")
        else:
            print("\n*No security signers registered.*")
    except Exception:
        print("\n*Could not fetch security signers (not available in this contract version).*")


def fetch_whitelisted_creators(mc):
    """Fetch and print whitelisted creators from MissionControl (iterable).

    This is a new feature - gracefully fails if not available in deployed contract.
    """
    try:
        print("\n<a id=\"creator-whitelist\"></a>")
        time.sleep(RPC_DELAY)
        num_creators = mc.numWhitelistedCreators()

        # Actual count is num_creators - 1 (index 0 is sentinel)
        actual_count = num_creators - 1 if num_creators > 0 else 0

        if actual_count > 0:
            print(f"\n**Creator Whitelist ({actual_count}):**")
            print("| Index | Address |")
            print("| --- | --- |")
            for i in range(1, num_creators):
                time.sleep(RPC_DELAY)
                creator_addr = str(mc.whitelistedCreators(i))
                if creator_addr != ZERO_ADDRESS:
                    print(f"| {i} | {format_address(creator_addr, _get_known_addresses)} |")
        else:
            print("\n*No whitelisted creators registered.*")
    except Exception:
        print("\n*Could not fetch creator whitelist (not available in this contract version).*")


def discover_configured_assets():
    """Discover assets that may have MissionControl per-asset configs.

    Since assetConfig is a HashMap (not iterable), we discover assets from:
    1. Yield legos via getAssets()
    2. Known tokens from BluePrint

    Returns a set of asset addresses to check.
    """
    from params_utils import KNOWN_TOKENS

    candidate_assets = set()

    # Add known tokens from BluePrint
    for addr in KNOWN_TOKENS.keys():
        candidate_assets.add(addr)

    # Discover assets from yield legos
    lb = protocol.core_contracts.get("LegoBook")
    if lb:
        try:
            num_legos = lb.numAddrs()
            for lego_id in range(1, num_legos):
                time.sleep(RPC_DELAY)
                lego_addr = str(lb.getAddr(lego_id))
                if lego_addr == ZERO_ADDRESS:
                    continue

                try:
                    time.sleep(RPC_DELAY)
                    lego = boa.from_etherscan(lego_addr, name=f"Lego_{lego_id}")
                    # Try to get assets - only yield legos have this
                    time.sleep(RPC_DELAY)
                    assets = lego.getAssets()
                    for asset in assets:
                        candidate_assets.add(str(asset).lower())
                except Exception:
                    # DEX lego or no getAssets method
                    pass
        except Exception:
            pass

    return candidate_assets


def fetch_per_asset_configs(mc):
    """Fetch and print per-asset configs from MissionControl."""
    print("\n<a id=\"per-asset-configs\"></a>")
    print("\n### Per-Asset Configs")
    print("\n*Asset-specific fee, ambassador revenue share, and yield configurations.*")

    # Discover candidate assets
    candidate_assets = discover_configured_assets()

    if not candidate_assets:
        print("\n*No candidate assets discovered.*")
        return

    configured_assets = []

    for asset_addr in candidate_assets:
        try:
            time.sleep(RPC_DELAY)
            config = mc.assetConfig(asset_addr)

            # Check if config exists (hasConfig flag)
            if config.hasConfig:
                time.sleep(RPC_DELAY)
                is_stablecoin = mc.isStablecoin(asset_addr)

                configured_assets.append({
                    "address": asset_addr,
                    "config": config,
                    "isStablecoin": is_stablecoin,
                })
        except Exception:
            pass

    if not configured_assets:
        print("\n*No assets with custom configurations found.*")
        return

    # Print summary table
    print(f"\n**Found {len(configured_assets)} assets with custom configs:**\n")
    print("| Asset | Stablecoin | Swap Fee | Stable Fee | Rewards Fee |")
    print("| --- | --- | --- | --- | --- |")

    for asset_data in configured_assets:
        asset_addr = asset_data["address"]
        config = asset_data["config"]
        is_stable = asset_data["isStablecoin"]

        # Get asset name
        asset_name = get_token_name(asset_addr, _get_known_addresses, try_fetch=True)

        # TxFees
        tx_fees = config.txFees

        print(f"| {asset_name} | {'Yes' if is_stable else 'No'} | {format_percent(tx_fees.swapFee)} | {format_percent(tx_fees.stableSwapFee)} | {format_percent(tx_fees.rewardsFee)} |")

    # Print detailed per-asset configs
    for asset_data in configured_assets:
        asset_addr = asset_data["address"]
        config = asset_data["config"]
        asset_name = get_token_name(asset_addr, _get_known_addresses, try_fetch=True)

        print(f"\n#### {asset_name}")
        print(f"Address: `{asset_addr}`")

        # Ambassador Rev Share
        rev_share = config.ambassadorRevShare
        rev_rows = [
            ("swapRatio", format_percent(rev_share.swapRatio)),
            ("rewardsRatio", format_percent(rev_share.rewardsRatio)),
            ("yieldRatio", format_percent(rev_share.yieldRatio)),
        ]
        print_table("Ambassador Revenue Share", ["Parameter", "Value"], rev_rows)

        # Yield Config
        yield_config = config.yieldConfig
        yield_rows = [
            ("maxYieldIncrease", format_percent(yield_config.maxYieldIncrease)),
            ("performanceFee", format_percent(yield_config.performanceFee)),
            ("ambassadorBonusRatio", format_percent(yield_config.ambassadorBonusRatio)),
            ("bonusRatio", format_percent(yield_config.bonusRatio)),
            ("bonusAsset", format_address(str(yield_config.bonusAsset), _get_known_addresses)),
        ]
        print_table("Yield Config", ["Parameter", "Value"], yield_rows)


def fetch_mission_control_data():
    """Fetch and print MissionControl configuration data."""
    mc = protocol.core_contracts.get("MissionControl")
    if not mc:
        return

    mc_addr = protocol.core_addresses.get("MissionControl", "Unknown")

    print("\n" + "=" * 80)
    print("\n<a id=\"mission-control\"></a>")
    print("# MissionControl - Core Protocol Configuration")
    print(f"Address: {mc_addr}")

    # User Wallet Config
    print("\n<a id=\"user-wallet-config\"></a>")
    uwc = mc.userWalletConfig()
    rows = [
        ("walletTemplate", format_address(str(uwc.walletTemplate), _get_known_addresses)),
        ("configTemplate", format_address(str(uwc.configTemplate), _get_known_addresses)),
        ("numUserWalletsAllowed", uwc.numUserWalletsAllowed),
        ("enforceCreatorWhitelist", uwc.enforceCreatorWhitelist),
        ("minKeyActionTimeLock", format_blocks_to_time(uwc.minKeyActionTimeLock)),
        ("maxKeyActionTimeLock", format_blocks_to_time(uwc.maxKeyActionTimeLock)),
        ("depositRewardsAsset", format_address(str(uwc.depositRewardsAsset), _get_known_addresses)),
        ("lootClaimCoolOffPeriod", format_blocks_to_time(uwc.lootClaimCoolOffPeriod)),
    ]
    print_table("User Wallet Config", ["Parameter", "Value"], rows)

    # Tx Fees
    tx_fees = uwc.txFees
    fee_rows = [
        ("swapFee", format_percent(tx_fees.swapFee)),
        ("stableSwapFee", format_percent(tx_fees.stableSwapFee)),
        ("rewardsFee", format_percent(tx_fees.rewardsFee)),
    ]
    print_table("Default Transaction Fees", ["Parameter", "Value"], fee_rows)

    # Ambassador Rev Share
    rev_share = uwc.ambassadorRevShare
    rev_rows = [
        ("swapRatio", format_percent(rev_share.swapRatio)),
        ("rewardsRatio", format_percent(rev_share.rewardsRatio)),
        ("yieldRatio", format_percent(rev_share.yieldRatio)),
    ]
    print_table("Default Ambassador Revenue Share", ["Parameter", "Value"], rev_rows)

    # Yield Config
    yield_config = uwc.yieldConfig
    yield_rows = [
        ("maxYieldIncrease", format_percent(yield_config.maxYieldIncrease)),
        ("performanceFee", format_percent(yield_config.performanceFee)),
        ("ambassadorBonusRatio", format_percent(yield_config.ambassadorBonusRatio)),
        ("bonusRatio", format_percent(yield_config.bonusRatio)),
        ("bonusAsset", format_address(str(yield_config.bonusAsset), _get_known_addresses)),
    ]
    print_table("Default Yield Config", ["Parameter", "Value"], yield_rows)

    # Agent Config
    print("\n<a id=\"agent-config\"></a>")
    ac = mc.agentConfig()
    agent_rows = [
        ("startingAgent", format_address(str(ac.startingAgent), _get_known_addresses)),
        ("startingAgentActivationLength", format_blocks_to_time(ac.startingAgentActivationLength)),
    ]
    print_table("Agent Config", ["Parameter", "Value"], agent_rows)

    # Enumerate AgentWrapper senders
    fetch_agent_wrapper_senders(str(ac.startingAgent))

    # Manager Config
    print("\n<a id=\"manager-config\"></a>")
    mgr = mc.managerConfig()
    mgr_rows = [
        ("managerPeriod", format_blocks_to_time(mgr.managerPeriod)),
        ("managerActivationLength", format_blocks_to_time(mgr.managerActivationLength)),
        ("mustHaveUsdValueOnSwaps", mgr.mustHaveUsdValueOnSwaps),
        ("maxNumSwapsPerPeriod", mgr.maxNumSwapsPerPeriod),
        ("maxSlippageOnSwaps", format_percent(mgr.maxSlippageOnSwaps)),
        ("onlyApprovedYieldOpps", mgr.onlyApprovedYieldOpps),
    ]
    print_table("Manager Config", ["Parameter", "Value"], mgr_rows)

    # Payee Config
    print("\n<a id=\"payee-config\"></a>")
    payee = mc.payeeConfig()
    payee_rows = [
        ("payeePeriod", format_blocks_to_time(payee.payeePeriod)),
        ("payeeActivationLength", format_blocks_to_time(payee.payeeActivationLength)),
    ]
    print_table("Payee Config", ["Parameter", "Value"], payee_rows)

    # Cheque Config
    print("\n<a id=\"cheque-config\"></a>")
    cheque = mc.chequeConfig()
    cheque_rows = [
        ("maxNumActiveCheques", cheque.maxNumActiveCheques),
        ("instantUsdThreshold", format_token_amount(cheque.instantUsdThreshold, 6, "USD")),
        ("periodLength", format_blocks_to_time(cheque.periodLength)),
        ("expensiveDelayBlocks", format_blocks_to_time(cheque.expensiveDelayBlocks)),
        ("defaultExpiryBlocks", format_blocks_to_time(cheque.defaultExpiryBlocks)),
    ]
    print_table("Cheque Config", ["Parameter", "Value"], cheque_rows)

    # Per-Asset Configs - discover and print asset-specific configs
    fetch_per_asset_configs(mc)

    # RIPE Rewards Config - new feature, graceful fail if not deployed
    fetch_ripe_rewards_config(mc)

    # Security Signers (iterable) - new feature, graceful fail if not deployed
    fetch_security_signers(mc)

    # Whitelisted Creators (iterable) - new feature, graceful fail if not deployed
    fetch_whitelisted_creators(mc)


def fetch_wallet_backpack_data():
    """Fetch and print WalletBackpack components."""
    wb = protocol.core_contracts.get("WalletBackpack")
    if not wb:
        return

    wb_addr = protocol.core_addresses.get("WalletBackpack", "Unknown")

    print("\n" + "=" * 80)
    print("\n<a id=\"wallet-backpack\"></a>")
    print("# WalletBackpack - Wallet Components")
    print(f"Address: {wb_addr}")

    rows = [
        ("kernel", format_address(str(wb.kernel()), _get_known_addresses)),
        ("sentinel", format_address(str(wb.sentinel()), _get_known_addresses)),
        ("highCommand", format_address(str(wb.highCommand()), _get_known_addresses)),
        ("paymaster", format_address(str(wb.paymaster()), _get_known_addresses)),
        ("chequeBook", format_address(str(wb.chequeBook()), _get_known_addresses)),
        ("migrator", format_address(str(wb.migrator()), _get_known_addresses)),
    ]
    print_table("Wallet Components", ["Component", "Address"], rows)

    # LocalGov settings
    time.sleep(RPC_DELAY)
    governance = str(wb.governance())
    time.sleep(RPC_DELAY)
    gov_timelock = wb.govChangeTimeLock()
    time.sleep(RPC_DELAY)
    pending_gov = wb.pendingGov()

    gov_rows = [
        ("governance", format_address(governance, _get_known_addresses)),
        ("govChangeTimeLock", format_blocks_to_time(gov_timelock)),
    ]

    pending_new_gov = str(pending_gov[0]) if pending_gov else ZERO_ADDRESS
    if pending_new_gov != ZERO_ADDRESS:
        gov_rows.append(("pendingGov.newGov", format_address(pending_new_gov, _get_known_addresses)))
        gov_rows.append(("pendingGov.initiatedBlock", pending_gov[1]))
        gov_rows.append(("pendingGov.confirmBlock", pending_gov[2]))
    else:
        gov_rows.append(("pendingGov", "None"))

    print_table("Governance Settings (LocalGov Module)", ["Parameter", "Value"], gov_rows)

    # TimeLock settings
    time.sleep(RPC_DELAY)
    min_timelock = wb.minActionTimeLock()
    time.sleep(RPC_DELAY)
    max_timelock = wb.maxActionTimeLock()
    time.sleep(RPC_DELAY)
    action_timelock = wb.actionTimeLock()
    time.sleep(RPC_DELAY)
    expiration = wb.expiration()

    timelock_rows = [
        ("minActionTimeLock", format_blocks_to_time(min_timelock)),
        ("maxActionTimeLock", format_blocks_to_time(max_timelock)),
        ("actionTimeLock", format_blocks_to_time(action_timelock)),
        ("expiration", format_blocks_to_time(expiration)),
    ]
    print_table("Timelock Settings (TimeLock Module)", ["Parameter", "Value"], timelock_rows)


def fetch_switchboard_data():
    """Fetch and print Switchboard registry data."""
    sb = protocol.core_contracts.get("Switchboard")
    if not sb:
        return

    sb_addr = protocol.core_addresses.get("Switchboard", "Unknown")

    print("\n" + "=" * 80)
    print("\n<a id=\"switchboard-registry\"></a>")
    print("# Switchboard - Config Contracts Registry")
    print(f"Address: {sb_addr}")

    num_addrs = sb.numAddrs()
    rows = [
        ("numAddrs (config contracts)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(sb.registryChangeTimeLock())),
    ]
    print_table("Registry Config (AddressRegistry Module)", ["Parameter", "Value"], rows)

    # LocalGov settings for Switchboard registry
    time.sleep(RPC_DELAY)
    governance = str(sb.governance())
    time.sleep(RPC_DELAY)
    gov_timelock = sb.govChangeTimeLock()
    time.sleep(RPC_DELAY)
    pending_gov = sb.pendingGov()

    gov_rows = [
        ("governance", format_address(governance, _get_known_addresses)),
        ("govChangeTimeLock", format_blocks_to_time(gov_timelock)),
    ]

    pending_new_gov = str(pending_gov[0]) if pending_gov else ZERO_ADDRESS
    if pending_new_gov != ZERO_ADDRESS:
        gov_rows.append(("pendingGov.newGov", format_address(pending_new_gov, _get_known_addresses)))
        gov_rows.append(("pendingGov.initiatedBlock", pending_gov[1]))
        gov_rows.append(("pendingGov.confirmBlock", pending_gov[2]))
    else:
        gov_rows.append(("pendingGov", "None"))

    print_table("Governance Settings (LocalGov Module)", ["Parameter", "Value"], gov_rows)

    # Check for pending registry changes
    print("\n### Pending Registry Changes")
    fetch_registry_pending_changes(sb, "Switchboard")

    # List registered config contracts from dynamically loaded data
    if protocol.switchboard_configs:
        print("\n### Registered Config Contracts")
        headers = ["ID", "Description", "Address"]
        config_rows = []
        for config_id, config_info in sorted(protocol.switchboard_configs.items()):
            config_rows.append([
                config_id,
                config_info["description"],
                format_address(config_info["address"], _get_known_addresses),
            ])

        if config_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in config_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")

        # Fetch detailed settings for each config contract
        for config_id, config_info in sorted(protocol.switchboard_configs.items()):
            time.sleep(RPC_DELAY)
            fetch_switchboard_config_settings(config_id, config_info)


def fetch_switchboard_config_settings(config_id: int, config_info: dict):
    """Fetch and print settings for a Switchboard config contract (LocalGov + TimeLock)."""
    config_addr = config_info["address"]
    config_name = config_info.get("description", f"Config_{config_id}")

    print(f"\n### {config_name}")
    print(f"Address: `{config_addr}`")

    config_contract = boa.from_etherscan(config_addr, name=config_name)

    # LocalGov settings
    time.sleep(RPC_DELAY)
    governance = str(config_contract.governance())
    time.sleep(RPC_DELAY)
    gov_timelock = config_contract.govChangeTimeLock()
    time.sleep(RPC_DELAY)
    pending_gov = config_contract.pendingGov()

    gov_rows = [
        ("governance", format_address(governance, _get_known_addresses)),
        ("govChangeTimeLock", format_blocks_to_time(gov_timelock)),
    ]

    pending_new_gov = str(pending_gov[0]) if pending_gov else ZERO_ADDRESS
    if pending_new_gov != ZERO_ADDRESS:
        gov_rows.append(("pendingGov.newGov", format_address(pending_new_gov, _get_known_addresses)))
        gov_rows.append(("pendingGov.initiatedBlock", pending_gov[1]))
        gov_rows.append(("pendingGov.confirmBlock", pending_gov[2]))
    else:
        gov_rows.append(("pendingGov", "None"))

    print_table("Governance Settings (LocalGov Module)", ["Parameter", "Value"], gov_rows)

    # TimeLock settings
    time.sleep(RPC_DELAY)
    min_timelock = config_contract.minActionTimeLock()
    time.sleep(RPC_DELAY)
    max_timelock = config_contract.maxActionTimeLock()
    time.sleep(RPC_DELAY)
    action_timelock = config_contract.actionTimeLock()
    time.sleep(RPC_DELAY)
    expiration = config_contract.expiration()

    timelock_rows = [
        ("minActionTimeLock", format_blocks_to_time(min_timelock)),
        ("maxActionTimeLock", format_blocks_to_time(max_timelock)),
        ("actionTimeLock", format_blocks_to_time(action_timelock)),
        ("expiration", format_blocks_to_time(expiration)),
    ]
    print_table("Timelock Settings (TimeLock Module)", ["Parameter", "Value"], timelock_rows)

    # Fetch pending actions
    fetch_pending_actions(config_contract, config_name)


def fetch_pending_actions(config_contract, config_name: str):
    """Fetch and print pending actions from a contract with TimeLock module.

    Checks pendingActions(i).confirmBlock != 0 for each action from 1 to actionId.
    """
    try:
        time.sleep(RPC_DELAY)
        current_action_id = config_contract.actionId()

        if current_action_id <= 1:
            print("\n*No pending actions (action counter at 1)*")
            return

        pending_actions = []

        # Check all previous action IDs (1 to current_action_id - 1)
        for action_id in range(1, current_action_id):
            try:
                time.sleep(RPC_DELAY)
                pending_action = config_contract.pendingActions(action_id)

                # confirmBlock != 0 means pending action exists
                if pending_action.confirmBlock != 0:
                    # Check if confirmable and expired
                    try:
                        time.sleep(RPC_DELAY)
                        can_confirm = config_contract.canConfirmAction(action_id)
                    except Exception:
                        can_confirm = "N/A"

                    try:
                        time.sleep(RPC_DELAY)
                        is_expired = config_contract.isExpired(action_id)
                    except Exception:
                        is_expired = "N/A"

                    pending_actions.append({
                        "actionId": action_id,
                        "initiatedBlock": pending_action.initiatedBlock,
                        "confirmBlock": pending_action.confirmBlock,
                        "expiration": pending_action.expiration,
                        "canConfirm": can_confirm,
                        "isExpired": is_expired,
                    })
            except Exception:
                continue

        if pending_actions:
            print(f"\n**Pending Actions ({len(pending_actions)}):**\n")
            print("| Action ID | Initiated | Confirm After | Expires | Can Confirm | Expired |")
            print("| --- | --- | --- | --- | --- | --- |")

            for action in pending_actions:
                print(f"| {action['actionId']} | Block {action['initiatedBlock']} | Block {action['confirmBlock']} | Block {action['expiration']} | {action['canConfirm']} | {action['isExpired']} |")
        else:
            print(f"\n*No pending actions (checked {current_action_id - 1} action IDs)*")

    except Exception as e:
        print(f"\n*Could not fetch pending actions: {e}*")


def fetch_registry_pending_changes(registry, registry_name: str):
    """Fetch and print pending address registry changes.

    Checks pendingAddrUpdate and pendingAddrDisable for each registered ID.
    """
    try:
        num_addrs = registry.numAddrs()

        pending_updates = []
        pending_disables = []

        for reg_id in range(1, num_addrs):
            # Check pending update
            try:
                time.sleep(RPC_DELAY)
                pending_update = registry.pendingAddrUpdate(reg_id)
                if pending_update.confirmBlock != 0:
                    time.sleep(RPC_DELAY)
                    addr_info = registry.addrInfo(reg_id)
                    pending_updates.append({
                        "regId": reg_id,
                        "description": addr_info.description,
                        "currentAddr": str(addr_info.addr),
                        "newAddr": str(pending_update.newAddr),
                        "initiatedBlock": pending_update.initiatedBlock,
                        "confirmBlock": pending_update.confirmBlock,
                    })
            except Exception:
                pass

            # Check pending disable
            try:
                time.sleep(RPC_DELAY)
                pending_disable = registry.pendingAddrDisable(reg_id)
                if pending_disable.confirmBlock != 0:
                    time.sleep(RPC_DELAY)
                    addr_info = registry.addrInfo(reg_id)
                    pending_disables.append({
                        "regId": reg_id,
                        "description": addr_info.description,
                        "addr": str(addr_info.addr),
                        "initiatedBlock": pending_disable.initiatedBlock,
                        "confirmBlock": pending_disable.confirmBlock,
                    })
            except Exception:
                pass

        if pending_updates:
            print(f"\n**Pending Address Updates ({len(pending_updates)}):**\n")
            print("| ID | Description | Current | New | Confirm After |")
            print("| --- | --- | --- | --- | --- |")
            for update in pending_updates:
                print(f"| {update['regId']} | {update['description']} | `{update['currentAddr'][:10]}...` | `{update['newAddr'][:10]}...` | Block {update['confirmBlock']} |")

        if pending_disables:
            print(f"\n**Pending Address Disables ({len(pending_disables)}):**\n")
            print("| ID | Description | Address | Confirm After |")
            print("| --- | --- | --- | --- |")
            for disable in pending_disables:
                print(f"| {disable['regId']} | {disable['description']} | `{disable['addr'][:10]}...` | Block {disable['confirmBlock']} |")

        if not pending_updates and not pending_disables:
            print(f"\n*No pending registry changes in {registry_name}.*")

    except Exception as e:
        print(f"\n*Could not fetch registry pending changes for {registry_name}: {e}*")


def fetch_vault_token_registry(ledger):
    """Fetch and print registered vault tokens from Ledger.

    Vault tokens are discovered via yield legos, then checked against Ledger.vaultTokens().
    """
    print("\n<a id=\"vault-token-registry\"></a>")
    print("\n### Vault Token Registry")
    print("\n*Vault tokens registered in Ledger with their underlying assets and lego associations.*")

    # Discover vault tokens from yield legos
    lb = protocol.core_contracts.get("LegoBook")
    if not lb:
        print("\n*Could not load LegoBook to discover vault tokens.*")
        return

    vault_tokens = {}

    try:
        num_legos = lb.numAddrs()
        for lego_id in range(1, num_legos):
            time.sleep(RPC_DELAY)
            lego_addr = str(lb.getAddr(lego_id))
            if lego_addr == ZERO_ADDRESS:
                continue

            try:
                time.sleep(RPC_DELAY)
                lego = boa.from_etherscan(lego_addr, name=f"Lego_{lego_id}")
                # Try to get assets - only yield legos have this
                time.sleep(RPC_DELAY)
                assets = lego.getAssets()

                for asset in assets:
                    time.sleep(RPC_DELAY)
                    vaults = lego.getAssetOpportunities(asset)

                    for vault_addr in vaults:
                        if str(vault_addr) == ZERO_ADDRESS:
                            continue

                        # Query Ledger for this vault token
                        time.sleep(RPC_DELAY)
                        vault_info = ledger.vaultTokens(vault_addr)

                        # Only include if registered (underlyingAsset != empty)
                        if str(vault_info.underlyingAsset) != ZERO_ADDRESS:
                            vault_tokens[str(vault_addr)] = {
                                "legoId": vault_info.legoId,
                                "underlyingAsset": str(vault_info.underlyingAsset),
                                "decimals": vault_info.decimals,
                                "isRebasing": vault_info.isRebasing,
                                "discoveredFromLego": lego_id,
                            }
            except Exception:
                # DEX lego, skip
                pass
    except Exception as e:
        print(f"\n*Error discovering vault tokens: {e}*")
        return

    if not vault_tokens:
        print("\n*No vault tokens registered in Ledger.*")
        return

    print(f"\n**Found {len(vault_tokens)} registered vault tokens:**\n")
    print("| Vault Token | Underlying | Lego ID | Decimals | Rebasing |")
    print("| --- | --- | --- | --- | --- |")

    for vault_addr, info in vault_tokens.items():
        vault_name = get_token_name(vault_addr, _get_known_addresses, try_fetch=True)
        underlying_name = get_token_name(info["underlyingAsset"], _get_known_addresses, try_fetch=True)
        print(f"| {vault_name} | {underlying_name} | {info['legoId']} | {info['decimals']} | {'Yes' if info['isRebasing'] else 'No'} |")


def fetch_backpack_items(ledger):
    """Fetch and print registered backpack items from Ledger.

    Backpack items are discovered by checking known vaults and tokens.
    """
    print("\n<a id=\"backpack-items\"></a>")
    print("\n### Backpack Items")
    print("\n*Assets registered as backpack items (can be held in user wallet backpacks).*")

    from params_utils import KNOWN_TOKENS

    # Candidates: earn vaults + known tokens
    candidates = set()

    # Add earn vault addresses
    for vault_name, vault_info in protocol.vaults.items():
        candidates.add(vault_info["address"])

    # Add known tokens
    for addr in KNOWN_TOKENS.keys():
        candidates.add(addr)

    registered_items = []

    for addr in candidates:
        try:
            time.sleep(RPC_DELAY)
            is_registered = ledger.isRegisteredBackpackItem(addr)
            if is_registered:
                registered_items.append(addr)
        except Exception:
            pass

    if not registered_items:
        print("\n*No backpack items found among known assets.*")
        return

    print(f"\n**Found {len(registered_items)} registered backpack items:**\n")
    print("| Asset | Address |")
    print("| --- | --- |")

    for addr in registered_items:
        name = get_token_name(addr, _get_known_addresses, try_fetch=True)
        print(f"| {name} | `{addr}` |")


def fetch_ledger_data():
    """Fetch and print Ledger statistics."""
    ledger = protocol.core_contracts.get("Ledger")
    if not ledger:
        return

    ledger_addr = protocol.core_addresses.get("Ledger", "Unknown")

    print("\n" + "=" * 80)
    print("\n<a id=\"ledger\"></a>")
    print("# Ledger - Protocol Data")
    print(f"Address: {ledger_addr}")

    num_wallets = ledger.numUserWallets()
    rows = [
        ("numUserWallets", num_wallets - 1 if num_wallets > 0 else 0),
    ]
    print_table("Protocol Statistics", ["Parameter", "Value"], rows)

    # Global points
    points = ledger.globalPoints()
    points_rows = [
        ("usdValue", format_token_amount(points.usdValue, 18, "USD")),
        ("depositPoints", f"{points.depositPoints:,}"),
        ("lastUpdate (block)", f"{points.lastUpdate:,}"),
    ]
    print_table("Global Points", ["Parameter", "Value"], points_rows)

    # Vault Token Registry
    fetch_vault_token_registry(ledger)

    # Backpack Items
    fetch_backpack_items(ledger)


def fetch_loot_distributor_data():
    """Fetch and print LootDistributor configuration."""
    loot = protocol.core_contracts.get("LootDistributor")
    if not loot:
        return

    loot_addr = protocol.core_addresses.get("LootDistributor", "Unknown")

    print("\n" + "=" * 80)
    print("\n<a id=\"loot-distributor\"></a>")
    print("# LootDistributor - Rewards Configuration")
    print(f"Address: {loot_addr}")

    deposit_rewards = loot.depositRewards()

    rows = [
        ("depositRewards.asset", format_address(str(deposit_rewards.asset), _get_known_addresses)),
        ("depositRewards.amount", format_token_amount(deposit_rewards.amount, 18)),
    ]

    # Try to read RIPE config from LootDistributor (old contract version)
    # In new version, these have been moved to MissionControl.ripeRewardsConfig()
    try:
        time.sleep(RPC_DELAY)
        ripe_stake_ratio = loot.ripeStakeRatio()
        time.sleep(RPC_DELAY)
        ripe_lock_duration = loot.ripeLockDuration()
        rows.append(("ripeStakeRatio", format_percent(ripe_stake_ratio)))
        rows.append(("ripeLockDuration", format_blocks_to_time(ripe_lock_duration)))
    except Exception:
        rows.append(("ripeStakeRatio", "*Moved to MissionControl.ripeRewardsConfig()*"))
        rows.append(("ripeLockDuration", "*Moved to MissionControl.ripeRewardsConfig()*"))

    rows.append(("RIPE_TOKEN", format_address(str(loot.RIPE_TOKEN()), _get_known_addresses)))
    rows.append(("RIPE_REGISTRY", format_address(str(loot.RIPE_REGISTRY()), _get_known_addresses)))

    print_table("Loot Config", ["Parameter", "Value"], rows)

    # Fetch totalClaimableLoot per known token
    fetch_total_claimable_loot(loot)


def fetch_total_claimable_loot(loot):
    """Fetch and print totalClaimableLoot per known token.

    totalClaimableLoot is a HashMap[address, uint256] - not iterable.
    We check known tokens to see if any have accumulated loot.
    """
    from params_utils import KNOWN_TOKENS

    print("\n### Total Claimable Loot")
    print("\n*Accumulated loot per asset across all ambassadors (global pool).*")

    # Check known tokens for accumulated loot
    loot_by_asset = []

    for addr in KNOWN_TOKENS.keys():
        try:
            time.sleep(RPC_DELAY)
            amount = loot.totalClaimableLoot(addr)
            if amount > 0:
                # Try to get decimals
                try:
                    time.sleep(RPC_DELAY)
                    token = boa.from_etherscan(addr, name=f"Token_{addr[:8]}")
                    decimals = token.decimals()
                except Exception:
                    decimals = 18

                loot_by_asset.append({
                    "address": addr,
                    "symbol": KNOWN_TOKENS[addr],
                    "amount": amount,
                    "decimals": decimals,
                })
        except Exception:
            pass

    if not loot_by_asset:
        print("\n*No accumulated loot found for known tokens.*")
        return

    print(f"\n**Found loot in {len(loot_by_asset)} assets:**\n")
    print("| Asset | Amount |")
    print("| --- | --- |")

    for loot_data in loot_by_asset:
        formatted_amount = format_token_amount(loot_data["amount"], loot_data["decimals"], loot_data["symbol"])
        print(f"| {loot_data['symbol']} | {formatted_amount} |")


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point."""
    # Output file path (same directory as this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "production_params_output.md")

    # Progress messages go to stderr so user sees them
    print("Connecting to Base mainnet via Alchemy...", file=sys.stderr)

    # Set etherscan API for contract loading
    setup_boa_etherscan()

    # Fork at latest block
    with boa_fork_context() as block_number:
        print(f"Connected. Block: {block_number}\n", file=sys.stderr)

        # Initialize all protocol contracts from UNDY_HQ
        initialize_protocol()

        print(f"Writing output to {output_file}...", file=sys.stderr)

        # Write report to file
        with output_to_file(output_file):
            # Header
            print_report_header("Underscore Protocol Production Parameters", block_number)

            # Table of Contents
            print_table_of_contents()

            # Executive Summary
            print_executive_summary()

            # Fetch and display all data
            # Note: Vault data has been moved to vaults_params.py -> vaults_params_output.md
            # Note: Lego data has been moved to lego_params.py -> lego_params_output.md

            # Registries grouped together
            fetch_undy_hq_data()
            fetch_undy_token_state()
            fetch_switchboard_data()  # Includes all config contract details (LocalGov + TimeLock + Pending Actions)

            # Core Protocol
            fetch_department_pause_states()
            fetch_wallet_backpack_data()
            fetch_mission_control_data()
            fetch_loot_distributor_data()
            fetch_ledger_data()

            # Footer
            print_report_footer(block_number)

        print(f"Done! Output saved to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
