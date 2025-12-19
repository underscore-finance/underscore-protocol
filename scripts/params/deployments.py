#!/usr/bin/env python3
"""
Output Deployments Script for Underscore Protocol

Fetches and displays all contract addresses from Underscore Protocol
on Base mainnet, formatted as markdown tables.

This is the canonical source for all live contract addresses.

Usage:
    python scripts/params/deployments.py
"""

import os
import sys
import time

import boa

# Import shared utilities
from params_utils import (
    UNDY_HQ,
    RPC_DELAY,
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
    HELPERS_ID,
    ZERO_ADDRESS,
    setup_boa_etherscan,
    boa_fork_context,
    print_report_header,
    print_report_footer,
    output_to_file,
)

# ============================================================================
# Global state
# ============================================================================


class DeploymentState:
    """Holds all contract addresses."""

    def __init__(self):
        self.hq = None
        self.core_addresses = {}
        self.wallet_backpack_components = {}
        self.templates = {}
        self.vaults = {}
        self.legos = {}
        self.switchboard_configs = {}


state = DeploymentState()


# ============================================================================
# Contract Loading
# ============================================================================


def load_core_addresses(hq):
    """Load all core contract addresses from UndyHq registry."""
    print("  Loading core addresses from UndyHq...", file=sys.stderr)
    return {
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
        "Helpers": str(hq.getAddr(HELPERS_ID)),
    }


def load_wallet_backpack_components(wb_addr):
    """Load wallet backpack component addresses."""
    print("  Loading WalletBackpack components...", file=sys.stderr)
    time.sleep(RPC_DELAY)
    wb = boa.from_etherscan(wb_addr, name="WalletBackpack")
    return {
        "Kernel": str(wb.kernel()),
        "Sentinel": str(wb.sentinel()),
        "HighCommand": str(wb.highCommand()),
        "Paymaster": str(wb.paymaster()),
        "ChequeBook": str(wb.chequeBook()),
        "Migrator": str(wb.migrator()),
    }


def load_templates_and_agent(mc_addr):
    """Load templates and agent wrapper from MissionControl."""
    print("  Loading templates and agent...", file=sys.stderr)
    time.sleep(RPC_DELAY)
    mc = boa.from_etherscan(mc_addr, name="MissionControl")
    user_wallet_config = mc.userWalletConfig()
    agent_config = mc.agentConfig()
    return {
        "UserWalletTemplate": str(user_wallet_config.walletTemplate),
        "UserWalletConfigTemplate": str(user_wallet_config.configTemplate),
        "AgentWrapper": str(agent_config.startingAgent),
    }


def load_vaults(vr_addr):
    """Load all vault addresses from VaultRegistry."""
    print("  Loading vaults...", file=sys.stderr)
    time.sleep(RPC_DELAY)
    vr = boa.from_etherscan(vr_addr, name="VaultRegistry")
    vaults = {}
    num_vaults = vr.numAddrs()

    for i in range(1, num_vaults):
        time.sleep(RPC_DELAY)
        addr = str(vr.getAddr(i))
        if addr != ZERO_ADDRESS:
            time.sleep(RPC_DELAY)
            vault = boa.from_etherscan(addr, name=f"Vault_{i}")
            name = vault.name()
            vaults[name] = {"address": addr, "reg_id": i}

    return vaults


def load_legos(lb_addr):
    """Load all lego addresses from LegoBook."""
    print("  Loading legos...", file=sys.stderr)
    time.sleep(RPC_DELAY)
    lb = boa.from_etherscan(lb_addr, name="LegoBook")
    legos = {}
    num_legos = lb.numAddrs()

    for i in range(1, num_legos):
        time.sleep(RPC_DELAY)
        addr = str(lb.getAddr(i))
        if addr != ZERO_ADDRESS:
            addr_info = lb.addrInfo(i)
            legos[i] = {"address": addr, "description": addr_info.description}

    return legos


def load_switchboard_configs(sb_addr):
    """Load all switchboard config contract addresses."""
    print("  Loading switchboard configs...", file=sys.stderr)
    time.sleep(RPC_DELAY)
    sb = boa.from_etherscan(sb_addr, name="Switchboard")
    configs = {}
    num_configs = sb.numAddrs()

    for i in range(1, num_configs):
        time.sleep(RPC_DELAY)
        addr = str(sb.getAddr(i))
        if addr != ZERO_ADDRESS:
            addr_info = sb.addrInfo(i)
            configs[i] = {"address": addr, "description": addr_info.description}

    return configs


def initialize_deployments():
    """Load all contract addresses from UNDY_HQ."""
    print("Loading contract addresses...", file=sys.stderr)

    # Load HQ first
    state.hq = boa.from_etherscan(UNDY_HQ, name="UndyHq")

    # Load core addresses
    state.core_addresses = load_core_addresses(state.hq)

    # Load wallet backpack components
    wb_addr = state.core_addresses.get("WalletBackpack")
    if wb_addr and wb_addr != ZERO_ADDRESS:
        state.wallet_backpack_components = load_wallet_backpack_components(wb_addr)

    # Load templates and agent
    mc_addr = state.core_addresses.get("MissionControl")
    if mc_addr and mc_addr != ZERO_ADDRESS:
        state.templates = load_templates_and_agent(mc_addr)

    # Load vaults
    vr_addr = state.core_addresses.get("VaultRegistry")
    if vr_addr and vr_addr != ZERO_ADDRESS:
        state.vaults = load_vaults(vr_addr)

    # Load legos
    lb_addr = state.core_addresses.get("LegoBook")
    if lb_addr and lb_addr != ZERO_ADDRESS:
        state.legos = load_legos(lb_addr)

    # Load switchboard configs
    sb_addr = state.core_addresses.get("Switchboard")
    if sb_addr and sb_addr != ZERO_ADDRESS:
        state.switchboard_configs = load_switchboard_configs(sb_addr)

    print("  All addresses loaded successfully.\n", file=sys.stderr)


# ============================================================================
# Output Functions
# ============================================================================


def print_table_of_contents():
    """Print a clickable table of contents."""
    print("""
## Table of Contents

1. [Core Registry (UndyHq)](#core-registry)
2. [Core Contracts](#core-contracts)
3. [Wallet Backpack Components](#wallet-backpack-components)
4. [Templates & Agent](#templates-agent)
5. [Vaults](#vaults)
6. [Legos](#legos)
7. [Switchboard Config Contracts](#switchboard-configs)
8. [Other Contracts](#other-contracts)
""")


def print_all_addresses():
    """Print all contract addresses."""

    # UndyHq
    print("\n<a id=\"core-registry\"></a>")
    print("## Core Registry")
    print("\n| Contract | Address |")
    print("| --- | --- |")
    print(f"| UndyHq | `{UNDY_HQ}` |")

    # Core Contracts
    print("\n<a id=\"core-contracts\"></a>")
    print("## Core Contracts (from UndyHq)")
    print("\n| ID | Contract | Address |")
    print("| --- | --- | --- |")
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
        addr = state.core_addresses.get(name, "")
        if addr and addr != ZERO_ADDRESS:
            print(f"| {reg_id} | {name} | `{addr}` |")

    # Wallet Backpack Components
    print("\n<a id=\"wallet-backpack-components\"></a>")
    print("## Wallet Backpack Components")
    print("\n| Component | Address |")
    print("| --- | --- |")
    for name, addr in state.wallet_backpack_components.items():
        if addr and addr != ZERO_ADDRESS:
            print(f"| {name} | `{addr}` |")

    # Templates & Agent
    print("\n<a id=\"templates-agent\"></a>")
    print("## Templates & Agent (from MissionControl)")
    print("\n| Contract | Address |")
    print("| --- | --- |")
    for name, addr in state.templates.items():
        if addr and addr != ZERO_ADDRESS:
            print(f"| {name} | `{addr}` |")

    # Vaults
    print("\n<a id=\"vaults\"></a>")
    print("## Vaults (from VaultRegistry)")
    print("\n| ID | Vault | Address |")
    print("| --- | --- | --- |")
    for vault_name, vault_info in state.vaults.items():
        print(f"| {vault_info['reg_id']} | {vault_name} | `{vault_info['address']}` |")

    # Legos
    print("\n<a id=\"legos\"></a>")
    print("## Legos (from LegoBook)")
    print("\n| ID | Lego | Address |")
    print("| --- | --- | --- |")
    for lego_id, lego_info in sorted(state.legos.items()):
        print(f"| {lego_id} | {lego_info['description']} | `{lego_info['address']}` |")

    # Switchboard Configs
    print("\n<a id=\"switchboard-configs\"></a>")
    print("## Switchboard Config Contracts")
    print("\n| ID | Config | Address |")
    print("| --- | --- | --- |")
    for config_id, config_info in sorted(state.switchboard_configs.items()):
        print(f"| {config_id} | {config_info['description']} | `{config_info['address']}` |")



# ============================================================================
# Main Entry Point
# ============================================================================


def main():
    """Main entry point."""
    # Output file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "deployments_output.md")

    print("Connecting to Base mainnet via Alchemy...", file=sys.stderr)

    # Set etherscan API
    setup_boa_etherscan()

    # Fork at latest block
    with boa_fork_context() as block_number:
        print(f"Connected. Block: {block_number}\n", file=sys.stderr)

        # Load all contract addresses
        initialize_deployments()

        print(f"Writing output to {output_file}...", file=sys.stderr)

        # Write report to file
        with output_to_file(output_file):
            # Header
            print_report_header("Underscore Protocol Deployments", block_number)

            print("\nComplete list of all live contract addresses in the Underscore Protocol.\n")

            # Table of Contents
            print_table_of_contents()

            # All addresses
            print_all_addresses()

            # Footer
            print_report_footer(block_number)

        print(f"Done! Output saved to {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
