#!/usr/bin/env python3
"""
Output Production Parameters Script for Underscore Protocol

Fetches and displays all current production configuration from Underscore Protocol
smart contracts on Base mainnet, formatted as markdown tables.

This script only requires the UNDY_HQ address - all other contract addresses
are dynamically derived from the on-chain registries.

Usage:
    python scripts/output_production_params.py
"""

import os
import sys
import time
from datetime import datetime, timezone

import boa

# Rate limiting to avoid Alchemy 429 errors
RPC_DELAY = 0.25  # seconds between RPC batches

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.BluePrint import TOKENS
from tests.constants import ZERO_ADDRESS

# ============================================================================
# CONFIGURATION - Only UNDY_HQ needs to be hardcoded
# ============================================================================

UNDY_HQ = "0x44Cf3c4f000DFD76a35d03298049D37bE688D6F9"

# RPC URL
RPC_URL = f"https://base-mainnet.g.alchemy.com/v2/{os.environ.get('WEB3_ALCHEMY_API_KEY')}"

# ============================================================================
# Registry IDs (from contracts/modules/Addys.vy)
# ============================================================================

LEDGER_ID = 1
MISSION_CONTROL_ID = 2
LEGO_BOOK_ID = 3
SWITCHBOARD_ID = 4
HATCHERY_ID = 5
LOOT_DISTRIBUTOR_ID = 6
APPRAISER_ID = 7
WALLET_BACKPACK_ID = 8
BILLING_ID = 9
VAULT_REGISTRY_ID = 10

# ============================================================================
# Constants for formatting
# ============================================================================

HUNDRED_PERCENT = 100_00  # 100.00%
DECIMALS_18 = 10**18
DECIMALS_6 = 10**6

# Build KNOWN_TOKENS from BluePrint (invert address -> symbol mapping)
KNOWN_TOKENS = {addr.lower(): symbol for symbol, addr in TOKENS.get("base", {}).items()}

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

# Cache for resolved token symbols
_token_symbol_cache = {}


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
# Address Resolution Helpers
# ============================================================================


def get_token_name(address: str, try_fetch: bool = True) -> str:
    """Resolve address to token symbol or return truncated address."""
    if address == ZERO_ADDRESS:
        return "None"

    addr_lower = address.lower()

    # Check cache first
    if addr_lower in _token_symbol_cache:
        return _token_symbol_cache[addr_lower]

    # Check known external tokens
    if addr_lower in KNOWN_TOKENS:
        _token_symbol_cache[addr_lower] = KNOWN_TOKENS[addr_lower]
        return KNOWN_TOKENS[addr_lower]

    # Check dynamically loaded protocol addresses
    known_addresses = protocol.get_known_addresses()
    if addr_lower in known_addresses:
        _token_symbol_cache[addr_lower] = known_addresses[addr_lower]
        return known_addresses[addr_lower]

    # Try to fetch symbol from contract
    if try_fetch:
        try:
            token_contract = boa.from_etherscan(address, name=f"Token_{address[:8]}")
            symbol = token_contract.symbol()
            if symbol:
                _token_symbol_cache[addr_lower] = symbol
                return symbol
        except Exception:
            pass

    # Return full address if no name found
    _token_symbol_cache[addr_lower] = address
    return address


def format_address(address: str) -> str:
    """Format address with resolved name and full address."""
    if address == ZERO_ADDRESS:
        return "None"
    name = get_token_name(address, try_fetch=False)
    # Check if we got a real name (not just truncated address)
    if name and not name.startswith("0x"):
        return f"{name} ({address})"
    return f"`{address}`"


# ============================================================================
# Formatting Helpers
# ============================================================================


def format_percent(value: int, base: int = HUNDRED_PERCENT) -> str:
    """Format a percentage value."""
    return f"{value / base * 100:.2f}%"


def format_wei(value: int, decimals: int = 18) -> str:
    """Format a wei value with appropriate decimals."""
    return f"{value / 10**decimals:,.6f}"


def format_blocks_to_time(blocks: int, block_time: float = 2.0) -> str:
    """Convert blocks to approximate time (Base ~2s blocks)."""
    seconds = blocks * block_time
    if seconds < 60:
        return f"{blocks} blocks (~{seconds:.0f}s)"
    elif seconds < 3600:
        return f"{blocks} blocks (~{seconds/60:.1f}m)"
    elif seconds < 86400:
        return f"{blocks} blocks (~{seconds/3600:.1f}h)"
    else:
        return f"{blocks} blocks (~{seconds/86400:.1f}d)"


def format_token_amount(raw_value: int, decimals: int = 18, symbol: str = "") -> str:
    """Format token amount with human-readable units."""
    amount = raw_value / (10**decimals)
    if amount >= 1_000_000_000_000:
        return f"Very High ({amount:.2e} {symbol})"
    elif amount >= 1_000_000_000:
        return f"{amount / 1_000_000_000:,.2f}B {symbol}"
    elif amount >= 1_000_000:
        return f"{amount / 1_000_000:,.2f}M {symbol}"
    elif amount >= 1_000:
        return f"{amount / 1_000:,.2f}K {symbol}"
    else:
        return f"{amount:,.2f} {symbol}"


def get_vault_decimals(vault_name: str) -> int:
    """Get decimals for a vault from its contract."""
    vault_info = protocol.vaults.get(vault_name)
    if vault_info and vault_info.get("contract"):
        return vault_info["contract"].decimals()
    return 18  # Default fallback


# ============================================================================
# Table Printing Helpers
# ============================================================================


def print_table(title: str, headers: list, rows: list, anchor: str = None):
    """Print a markdown table with optional anchor."""
    if anchor:
        print(f"\n<a id=\"{anchor}\"></a>")
    print(f"\n## {title}")
    print(f"| {' | '.join(headers)} |")
    print(f"| {' | '.join(['---' for _ in headers])} |")
    for row in rows:
        print(f"| {' | '.join(str(cell) for cell in row)} |")


def print_table_of_contents():
    """Print a clickable table of contents."""
    print("""
## Table of Contents

1. [Executive Summary](#executive-summary)
2. [All Contract Addresses](#all-addresses)
3. [UndyHq Configuration](#undy-hq)
4. [MissionControl Configuration](#mission-control)
   - [User Wallet Config](#user-wallet-config)
   - [Agent Config](#agent-config)
   - [Manager Config](#manager-config)
   - [Payee Config](#payee-config)
   - [Cheque Config](#cheque-config)
5. [SwitchboardAlpha Timelock](#switchboard-alpha)
6. [VaultRegistry Configuration](#vault-registry)
7. [Earn Vaults](#earn-vaults)
8. [Earn Vault Details](#earn-vault-details)
9. [WalletBackpack Components](#wallet-backpack)
10. [LegoBook Registry](#lego-book)
11. [Switchboard Registry](#switchboard-registry)
12. [LootDistributor Config](#loot-distributor)
13. [Ledger Statistics](#ledger)
""")


# ============================================================================
# Data Fetching Functions
# ============================================================================


def print_all_addresses():
    """Print all contract addresses in the protocol."""
    print("\n" + "=" * 80)
    print("\n<a id=\"all-addresses\"></a>")
    print("# All Contract Addresses")
    print("\nComplete list of all live contract addresses in the Underscore Protocol.\n")

    # UndyHq
    print("## Core Registry")
    print(f"| Contract | Address |")
    print(f"| --- | --- |")
    print(f"| UndyHq | `{UNDY_HQ}` |")

    # Core Contracts
    print("\n## Core Contracts (from UndyHq)")
    print(f"| ID | Contract | Address |")
    print(f"| --- | --- | --- |")
    id_to_name = {
        LEDGER_ID: "Ledger",
        MISSION_CONTROL_ID: "MissionControl",
        LEGO_BOOK_ID: "LegoBook",
        SWITCHBOARD_ID: "Switchboard",
        HATCHERY_ID: "Hatchery",
        LOOT_DISTRIBUTOR_ID: "LootDistributor",
        APPRAISER_ID: "Appraiser",
        WALLET_BACKPACK_ID: "WalletBackpack",
        BILLING_ID: "Billing",
        VAULT_REGISTRY_ID: "VaultRegistry",
    }
    for reg_id, name in id_to_name.items():
        addr = protocol.core_addresses.get(name, "")
        if addr and addr != ZERO_ADDRESS:
            print(f"| {reg_id} | {name} | `{addr}` |")

    # Wallet Backpack Components
    print("\n## Wallet Backpack Components")
    print(f"| Component | Address |")
    print(f"| --- | --- |")
    for name, addr in protocol.wallet_backpack_components.items():
        if addr and addr != ZERO_ADDRESS:
            print(f"| {name} | `{addr}` |")

    # Templates & Agent
    print("\n## Templates & Agent (from MissionControl)")
    print(f"| Contract | Address |")
    print(f"| --- | --- |")
    for name, addr in protocol.templates.items():
        if addr and addr != ZERO_ADDRESS:
            print(f"| {name} | `{addr}` |")

    # Earn Vaults
    print("\n## Earn Vaults (from VaultRegistry)")
    print(f"| ID | Vault | Address |")
    print(f"| --- | --- | --- |")
    for vault_name, vault_info in protocol.vaults.items():
        print(f"| {vault_info['reg_id']} | {vault_name} | `{vault_info['address']}` |")

    # Legos
    print("\n## Legos (from LegoBook)")
    print(f"| ID | Lego | Address |")
    print(f"| --- | --- | --- |")
    for lego_id, lego_info in sorted(protocol.legos.items()):
        print(f"| {lego_id} | {lego_info['description']} | `{lego_info['address']}` |")

    # Switchboard Configs
    print("\n## Switchboard Config Contracts")
    print(f"| ID | Config | Address |")
    print(f"| --- | --- | --- |")
    for config_id, config_info in sorted(protocol.switchboard_configs.items()):
        print(f"| {config_id} | {config_info['description']} | `{config_info['address']}` |")

    # LegoTools (from LegoBook)
    lb = protocol.core_contracts.get("LegoBook")
    if lb:
        lego_tools = str(lb.legoTools())
        if lego_tools != ZERO_ADDRESS:
            print("\n## Other Contracts")
            print(f"| Contract | Address |")
            print(f"| --- | --- |")
            print(f"| LegoTools | `{lego_tools}` |")


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


def fetch_undy_hq_data():
    """Fetch and print UndyHq configuration data."""
    hq = protocol.hq

    print("\n" + "=" * 80)
    print("\n<a id=\"undy-hq\"></a>")
    print("# UndyHq - Main Registry & Governance")
    print(f"Address: {UNDY_HQ}")

    num_addrs = hq.numAddrs()
    rows = [
        ("undyToken", format_address(str(hq.undyToken()))),
        ("mintEnabled", hq.mintEnabled()),
        ("numAddrs (departments)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(hq.registryChangeTimeLock())),
    ]

    print_table("Registry Config", ["Parameter", "Value"], rows)

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
                format_address(contract_addr),
                "Yes" if hq_config.canMintUndy else "No",
                "Yes" if hq_config.canSetTokenBlacklist else "No",
            ])

        if dept_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in dept_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")


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
        ("walletTemplate", format_address(str(uwc.walletTemplate))),
        ("configTemplate", format_address(str(uwc.configTemplate))),
        ("numUserWalletsAllowed", uwc.numUserWalletsAllowed),
        ("enforceCreatorWhitelist", uwc.enforceCreatorWhitelist),
        ("minKeyActionTimeLock", format_blocks_to_time(uwc.minKeyActionTimeLock)),
        ("maxKeyActionTimeLock", format_blocks_to_time(uwc.maxKeyActionTimeLock)),
        ("depositRewardsAsset", format_address(str(uwc.depositRewardsAsset))),
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
        ("bonusAsset", format_address(str(yield_config.bonusAsset))),
    ]
    print_table("Default Yield Config", ["Parameter", "Value"], yield_rows)

    # Agent Config
    print("\n<a id=\"agent-config\"></a>")
    ac = mc.agentConfig()
    agent_rows = [
        ("startingAgent", format_address(str(ac.startingAgent))),
        ("startingAgentActivationLength", format_blocks_to_time(ac.startingAgentActivationLength)),
    ]
    print_table("Agent Config", ["Parameter", "Value"], agent_rows)

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


def fetch_vault_registry_data():
    """Fetch and print VaultRegistry configuration data."""
    vr = protocol.core_contracts.get("VaultRegistry")
    if not vr:
        return

    vr_addr = protocol.core_addresses.get("VaultRegistry", "Unknown")

    print("\n" + "=" * 80)
    print("\n<a id=\"vault-registry\"></a>")
    print("# VaultRegistry - Vault Configuration")
    print(f"Address: {vr_addr}")

    num_addrs = vr.numAddrs()
    rows = [
        ("numAddrs (vaults)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(vr.registryChangeTimeLock())),
    ]
    print_table("Registry Config", ["Parameter", "Value"], rows)


def fetch_earn_vault_data():
    """Fetch and print per-vault configuration data."""
    vr = protocol.core_contracts.get("VaultRegistry")
    if not vr:
        return

    print("\n" + "=" * 80)
    print("\n<a id=\"earn-vaults\"></a>")
    print("# Earn Vaults - Per-Vault Configuration")

    for vault_name, vault_info in protocol.vaults.items():
        time.sleep(RPC_DELAY * 2)  # Extra pause between vaults
        vault_addr = vault_info["address"]

        print(f"\n### {vault_name}")
        print(f"Address: {vault_addr}")

        decimals = get_vault_decimals(vault_name)
        time.sleep(RPC_DELAY)
        vault_config = vr.vaultConfigs(vault_addr)
        time.sleep(RPC_DELAY)
        num_tokens = vr.numApprovedVaultTokens(vault_addr)

        max_deposit = vault_config.maxDepositAmount
        rows = [
            ("canDeposit", vault_config.canDeposit),
            ("canWithdraw", vault_config.canWithdraw),
            ("maxDepositAmount", "Unlimited" if max_deposit == 0 else format_token_amount(max_deposit, decimals)),
            ("isVaultOpsFrozen", vault_config.isVaultOpsFrozen),
            ("redemptionBuffer", format_percent(vault_config.redemptionBuffer)),
            ("minYieldWithdrawAmount", format_token_amount(vault_config.minYieldWithdrawAmount, decimals)),
            ("performanceFee", format_percent(vault_config.performanceFee)),
            ("shouldAutoDeposit", vault_config.shouldAutoDeposit),
            ("defaultTargetVaultToken", format_address(str(vault_config.defaultTargetVaultToken))),
            ("isLeveragedVault", vault_config.isLeveragedVault),
            ("shouldEnforceAllowlist", vault_config.shouldEnforceAllowlist),
        ]
        print_table(f"{vault_name} Config", ["Parameter", "Value"], rows)

        # Approved vault tokens (num_tokens already fetched above)
        if num_tokens > 0:
            print(f"\n**Approved Vault Tokens ({num_tokens}):**")
            token_rows = []
            for i in range(1, num_tokens + 1):
                time.sleep(RPC_DELAY)
                token_addr = vr.approvedVaultTokens(vault_addr, i)
                if str(token_addr) != ZERO_ADDRESS:
                    token_rows.append([i, format_address(str(token_addr))])
            if token_rows:
                print("| Index | Token |")
                print("| --- | --- |")
                for row in token_rows:
                    print(f"| {row[0]} | {row[1]} |")


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
        ("kernel", format_address(str(wb.kernel()))),
        ("sentinel", format_address(str(wb.sentinel()))),
        ("highCommand", format_address(str(wb.highCommand()))),
        ("paymaster", format_address(str(wb.paymaster()))),
        ("chequeBook", format_address(str(wb.chequeBook()))),
        ("migrator", format_address(str(wb.migrator()))),
    ]
    print_table("Wallet Components", ["Component", "Address"], rows)


def fetch_lego_book_data():
    """Fetch and print LegoBook registry data."""
    lb = protocol.core_contracts.get("LegoBook")
    if not lb:
        return

    lb_addr = protocol.core_addresses.get("LegoBook", "Unknown")

    print("\n" + "=" * 80)
    print("\n<a id=\"lego-book\"></a>")
    print("# LegoBook - Lego Registry")
    print(f"Address: {lb_addr}")

    num_addrs = lb.numAddrs()
    rows = [
        ("legoTools", format_address(str(lb.legoTools()))),
        ("numAddrs (legos)", num_addrs - 1 if num_addrs > 0 else 0),
        ("registryChangeTimeLock", format_blocks_to_time(lb.registryChangeTimeLock())),
    ]
    print_table("Registry Config", ["Parameter", "Value"], rows)

    # List registered legos from dynamically loaded data
    if protocol.legos:
        print("\n### Registered Legos")
        headers = ["ID", "Description", "Address"]
        lego_rows = []
        for lego_id, lego_info in sorted(protocol.legos.items()):
            lego_rows.append([
                lego_id,
                lego_info["description"],
                format_address(lego_info["address"]),
            ])

        if lego_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in lego_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")


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
    print_table("Registry Config", ["Parameter", "Value"], rows)

    # List registered config contracts from dynamically loaded data
    if protocol.switchboard_configs:
        print("\n### Registered Config Contracts")
        headers = ["ID", "Description", "Address"]
        config_rows = []
        for config_id, config_info in sorted(protocol.switchboard_configs.items()):
            config_rows.append([
                config_id,
                config_info["description"],
                format_address(config_info["address"]),
            ])

        if config_rows:
            print(f"| {' | '.join(headers)} |")
            print(f"| {' | '.join(['---' for _ in headers])} |")
            for row in config_rows:
                print(f"| {' | '.join(str(cell) for cell in row)} |")


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
        ("depositRewards.asset", format_address(str(deposit_rewards.asset))),
        ("depositRewards.amount", format_token_amount(deposit_rewards.amount, 18)),
        ("ripeStakeRatio", format_percent(loot.ripeStakeRatio())),
        ("ripeLockDuration", format_blocks_to_time(loot.ripeLockDuration())),
        ("RIPE_TOKEN", format_address(str(loot.RIPE_TOKEN()))),
        ("RIPE_REGISTRY", format_address(str(loot.RIPE_REGISTRY()))),
    ]
    print_table("Loot Config", ["Parameter", "Value"], rows)


def fetch_switchboard_alpha_timelock():
    """Fetch SwitchboardAlpha timelock settings."""
    # Get first switchboard config (SwitchboardAlpha is typically ID 1)
    if not protocol.switchboard_configs:
        return

    # Find SwitchboardAlpha
    sba_addr = None
    for config_id, config_info in protocol.switchboard_configs.items():
        if "Alpha" in config_info.get("description", ""):
            sba_addr = config_info["address"]
            break

    if not sba_addr:
        # Fallback to first config
        first_config = next(iter(protocol.switchboard_configs.values()), None)
        if first_config:
            sba_addr = first_config["address"]

    if not sba_addr:
        return

    print("\n" + "=" * 80)
    print("\n<a id=\"switchboard-alpha\"></a>")
    print("# SwitchboardAlpha - Timelock Settings")
    print(f"Address: {sba_addr}")

    sba = boa.from_etherscan(sba_addr, name="SwitchboardAlpha")
    rows = [
        ("minActionTimeLock", format_blocks_to_time(sba.minActionTimeLock())),
        ("maxActionTimeLock", format_blocks_to_time(sba.maxActionTimeLock())),
        ("actionTimeLock", format_blocks_to_time(sba.actionTimeLock())),
    ]
    print_table("Timelock Config", ["Parameter", "Value"], rows)


def fetch_earn_vault_details():
    """Fetch per-vault detailed configuration including managers."""
    vr = protocol.core_contracts.get("VaultRegistry")

    print("\n" + "=" * 80)
    print("\n<a id=\"earn-vault-details\"></a>")
    print("# Earn Vault Details - Managers & Assets")

    for vault_name, vault_info in protocol.vaults.items():
        time.sleep(RPC_DELAY * 2)  # Extra pause between vaults
        vault_addr = vault_info["address"]
        vault = vault_info["contract"]

        print(f"\n### {vault_name} Details")
        print(f"Address: {vault_addr}")

        decimals = get_vault_decimals(vault_name)
        time.sleep(RPC_DELAY)
        is_leveraged = vr.isLeveragedVault(vault_addr) if vr else False

        time.sleep(RPC_DELAY)
        num_managers = vault.numManagers()

        # Fetch values with delays to avoid rate limiting
        time.sleep(RPC_DELAY)
        asset_addr = str(vault.asset())
        time.sleep(RPC_DELAY)
        total_assets = vault.totalAssets()
        time.sleep(RPC_DELAY)
        total_supply = vault.totalSupply()

        rows = [
            ("asset", format_address(asset_addr)),
            ("totalAssets", format_token_amount(total_assets, decimals)),
            ("totalSupply (shares)", format_token_amount(total_supply, 18)),
            ("numManagers", num_managers - 1 if num_managers > 0 else 0),
        ]

        # Basic vaults have additional fields that leveraged vaults don't have
        if not is_leveraged:
            time.sleep(RPC_DELAY)
            num_assets = vault.numAssets()
            time.sleep(RPC_DELAY)
            last_underlying = vault.lastUnderlyingBal()
            time.sleep(RPC_DELAY)
            pending_yield = vault.pendingYieldRealized()
            rows.append(("numAssets (yield positions)", num_assets - 1 if num_assets > 0 else 0))
            rows.append(("lastUnderlyingBal", format_token_amount(last_underlying, decimals)))
            rows.append(("pendingYieldRealized", format_token_amount(pending_yield, decimals)))

        print_table(f"{vault_name} Stats", ["Parameter", "Value"], rows)

        # List managers
        if num_managers > 1:
            print(f"\n**Managers ({num_managers - 1}):**")
            manager_rows = []
            for i in range(1, min(num_managers, 11)):  # Limit to 10 for output
                time.sleep(RPC_DELAY)
                mgr = vault.managers(i)
                if str(mgr) != ZERO_ADDRESS:
                    manager_rows.append([i, format_address(str(mgr))])
            if manager_rows:
                print("| Index | Manager |")
                print("| --- | --- |")
                for row in manager_rows:
                    print(f"| {row[0]} | {row[1]} |")


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
    boa.set_etherscan(
        api_key=os.environ["ETHERSCAN_API_KEY"],
        uri="https://api.etherscan.io/v2/api?chainid=8453"
    )

    # Fork at latest block
    with boa.fork(RPC_URL):
        block_number = boa.env.evm.patch.block_number
        print(f"Connected. Block: {block_number}\n", file=sys.stderr)

        # Initialize all protocol contracts from UNDY_HQ
        initialize_protocol()

        print(f"Writing output to {output_file}...", file=sys.stderr)

        # Write report to file
        with open(output_file, "w") as f:
            # Redirect stdout to file
            old_stdout = sys.stdout
            sys.stdout = f

            print("=" * 80)

            # Header
            print("# Underscore Protocol Production Parameters")
            print(f"\n**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")
            print(f"**Block:** {block_number}")
            print(f"**Network:** Base Mainnet")

            # Table of Contents
            print_table_of_contents()

            # Executive Summary
            print_executive_summary()

            # All Contract Addresses
            print_all_addresses()

            # Fetch and display all data
            fetch_undy_hq_data()
            fetch_mission_control_data()
            fetch_switchboard_alpha_timelock()
            fetch_vault_registry_data()
            fetch_earn_vault_data()
            fetch_earn_vault_details()
            fetch_wallet_backpack_data()
            fetch_lego_book_data()
            fetch_switchboard_data()
            fetch_loot_distributor_data()
            fetch_ledger_data()

            print("\n" + "=" * 80)
            print("\n---")
            print(f"*Report generated at block {block_number} on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC*")

            # Restore stdout
            sys.stdout = old_stdout

        print(f"Done! Output saved to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
