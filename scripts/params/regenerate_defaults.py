#!/usr/bin/env python3
"""
Regenerate DefaultsBase.vy from Live MissionControl Parameters

This script reads current production parameters from MissionControl on Base mainnet
and generates a new DefaultsBase.vy file with hardcoded production values.

This is a safety measure to preserve all current params when redeploying MissionControl.

Usage:
    python scripts/params/regenerate_defaults.py
"""

import os
import sys
import time

import boa

# Import shared utilities
from params_utils import (
    UNDY_HQ,
    RPC_DELAY,
    MISSION_CONTROL_ID,
    setup_boa_etherscan,
    boa_fork_context,
)

# ============================================================================
# CONSTANTS FOR VYPER VALUE FORMATTING
# ============================================================================

EIGHTEEN_DECIMALS = 10**18
HUNDRED_PERCENT = 100_00
DAY_IN_BLOCKS = 43_200  # ~2 second blocks on Base
WEEK_IN_BLOCKS = 7 * DAY_IN_BLOCKS
MONTH_IN_BLOCKS = 30 * DAY_IN_BLOCKS
YEAR_IN_BLOCKS = 365 * DAY_IN_BLOCKS

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


# ============================================================================
# VALUE FORMATTING FUNCTIONS
# ============================================================================


def format_blocks(blocks: int) -> str:
    """Convert block counts to readable time constants."""
    if blocks == 0:
        return "0"

    # Check exact matches first
    if blocks == DAY_IN_BLOCKS // 2:
        return "DAY_IN_BLOCKS // 2"
    if blocks == DAY_IN_BLOCKS:
        return "DAY_IN_BLOCKS"
    if blocks == WEEK_IN_BLOCKS:
        return "WEEK_IN_BLOCKS"
    if blocks == MONTH_IN_BLOCKS:
        return "MONTH_IN_BLOCKS"
    if blocks == YEAR_IN_BLOCKS:
        return "YEAR_IN_BLOCKS"

    # Handle multiples (check largest units first)
    if blocks % YEAR_IN_BLOCKS == 0:
        mult = blocks // YEAR_IN_BLOCKS
        return f"{mult} * YEAR_IN_BLOCKS"
    if blocks % MONTH_IN_BLOCKS == 0:
        mult = blocks // MONTH_IN_BLOCKS
        return f"{mult} * MONTH_IN_BLOCKS"
    if blocks % WEEK_IN_BLOCKS == 0:
        mult = blocks // WEEK_IN_BLOCKS
        return f"{mult} * WEEK_IN_BLOCKS"
    if blocks % DAY_IN_BLOCKS == 0:
        mult = blocks // DAY_IN_BLOCKS
        return f"{mult} * DAY_IN_BLOCKS"

    # Fall back to raw number with underscores for readability
    return f"{blocks:_}"


def format_percent(value: int) -> str:
    """Format percentage values for readability (basis points).

    Examples:
        2000 -> "20_00"   (20.00%)
        500  -> "5_00"    (5.00%)
        25   -> "25"      (0.25%)
        0    -> "0"
    """
    if value == 0:
        return "0"
    if value == HUNDRED_PERCENT:
        return "100_00"
    if value >= 100:
        return f"{value // 100}_{value % 100:02d}"
    return str(value)


def format_uint(value: int) -> str:
    """Format uint256 values with underscores for readability."""
    if value == 0:
        return "0"
    if value >= 1_000:
        return f"{value:_}"
    return str(value)


def format_token_amount(value: int) -> str:
    """Format token amounts (18 decimals) for Vyper code.

    Examples:
        100 * 10**18 -> "100 * EIGHTEEN_DECIMALS"
        1000 * 10**18 -> "1_000 * EIGHTEEN_DECIMALS"
    """
    if value == 0:
        return "0"

    # Check if it's a clean multiple of 10**18
    if value % EIGHTEEN_DECIMALS == 0:
        whole = value // EIGHTEEN_DECIMALS
        return f"{format_uint(whole)} * EIGHTEEN_DECIMALS"

    # Otherwise return the raw value
    return f"{value:_}"


def format_address(addr: str) -> str:
    """Format address for Vyper code."""
    if addr == ZERO_ADDRESS:
        return "empty(address)"
    return addr


# ============================================================================
# CODE GENERATION
# ============================================================================


def generate_defaults_vy(
    user_wallet_config,
    agent_config,
    manager_config,
    payee_config,
    cheque_config,
    ripe_rewards_config,
    security_signers: list,
    whitelisted_creators: list,
) -> str:
    """Generate the DefaultsBase.vy file content."""

    # Extract addresses for constants
    wallet_template = str(user_wallet_config.walletTemplate)
    config_template = str(user_wallet_config.configTemplate)
    starting_agent = str(agent_config.startingAgent)
    rewards_asset = str(user_wallet_config.depositRewardsAsset)
    bonus_asset = str(user_wallet_config.yieldConfig.bonusAsset)

    code = f'''#     Underscore Protocol License: https://github.com/underscore-finance/underscore-protocol/blob/master/LICENSE.md

# @version 0.4.3

implements: Defaults
from interfaces import Defaults
import interfaces.ConfigStructs as cs

EIGHTEEN_DECIMALS: constant(uint256) = 10 ** 18

# blocks
DAY_IN_BLOCKS: constant(uint256) = 43_200
WEEK_IN_BLOCKS: constant(uint256) = 7 * DAY_IN_BLOCKS
MONTH_IN_BLOCKS: constant(uint256) = 30 * DAY_IN_BLOCKS
YEAR_IN_BLOCKS: constant(uint256) = 365 * DAY_IN_BLOCKS

# user wallet templates
USER_WALLET_TEMPLATE: constant(address) = {wallet_template}
USER_WALLET_CONFIG_TEMPLATE: constant(address) = {config_template}

# agent
STARTING_AGENT: constant(address) = {starting_agent}

# rewards
REWARDS_ASSET: constant(address) = {rewards_asset}
BONUS_ASSET: constant(address) = {bonus_asset}


# general configs


@view
@external
def userWalletConfig() -> cs.UserWalletConfig:
    return cs.UserWalletConfig(
        walletTemplate = USER_WALLET_TEMPLATE,
        configTemplate = USER_WALLET_CONFIG_TEMPLATE,
        numUserWalletsAllowed = {format_uint(user_wallet_config.numUserWalletsAllowed)},
        enforceCreatorWhitelist = {str(user_wallet_config.enforceCreatorWhitelist)},
        minKeyActionTimeLock = {format_blocks(user_wallet_config.minKeyActionTimeLock)},
        maxKeyActionTimeLock = {format_blocks(user_wallet_config.maxKeyActionTimeLock)},
        depositRewardsAsset = REWARDS_ASSET,
        lootClaimCoolOffPeriod = {format_blocks(user_wallet_config.lootClaimCoolOffPeriod)},
        txFees = cs.TxFees(
            swapFee = {format_percent(user_wallet_config.txFees.swapFee)},
            stableSwapFee = {format_percent(user_wallet_config.txFees.stableSwapFee)},
            rewardsFee = {format_percent(user_wallet_config.txFees.rewardsFee)},
        ),
        ambassadorRevShare = cs.AmbassadorRevShare(
            swapRatio = {format_percent(user_wallet_config.ambassadorRevShare.swapRatio)},
            rewardsRatio = {format_percent(user_wallet_config.ambassadorRevShare.rewardsRatio)},
            yieldRatio = {format_percent(user_wallet_config.ambassadorRevShare.yieldRatio)},
        ),
        yieldConfig = cs.YieldConfig(
            maxYieldIncrease = {format_percent(user_wallet_config.yieldConfig.maxYieldIncrease)},
            performanceFee = {format_percent(user_wallet_config.yieldConfig.performanceFee)},
            ambassadorBonusRatio = {format_percent(user_wallet_config.yieldConfig.ambassadorBonusRatio)},
            bonusRatio = {format_percent(user_wallet_config.yieldConfig.bonusRatio)},
            bonusAsset = BONUS_ASSET,
        ),
    )


@view
@external
def agentConfig() -> cs.AgentConfig:
    return cs.AgentConfig(
        startingAgent = STARTING_AGENT,
        startingAgentActivationLength = {format_blocks(agent_config.startingAgentActivationLength)},
    )


@view
@external
def managerConfig() -> cs.ManagerConfig:
    return cs.ManagerConfig(
        managerPeriod = {format_blocks(manager_config.managerPeriod)},
        managerActivationLength = {format_blocks(manager_config.managerActivationLength)},
        mustHaveUsdValueOnSwaps = {str(manager_config.mustHaveUsdValueOnSwaps)},
        maxNumSwapsPerPeriod = {format_uint(manager_config.maxNumSwapsPerPeriod)},
        maxSlippageOnSwaps = {format_percent(manager_config.maxSlippageOnSwaps)},
        onlyApprovedYieldOpps = {str(manager_config.onlyApprovedYieldOpps)},
    )


@view
@external
def payeeConfig() -> cs.PayeeConfig:
    return cs.PayeeConfig(
        payeePeriod = {format_blocks(payee_config.payeePeriod)},
        payeeActivationLength = {format_blocks(payee_config.payeeActivationLength)},
    )


@view
@external
def chequeConfig() -> cs.ChequeConfig:
    return cs.ChequeConfig(
        maxNumActiveCheques = {format_uint(cheque_config.maxNumActiveCheques)},
        instantUsdThreshold = {format_token_amount(cheque_config.instantUsdThreshold)},
        periodLength = {format_blocks(cheque_config.periodLength)},
        expensiveDelayBlocks = {format_blocks(cheque_config.expensiveDelayBlocks)},
        defaultExpiryBlocks = {format_blocks(cheque_config.defaultExpiryBlocks)},
    )


@view
@external
def ripeRewardsConfig() -> cs.RipeRewardsConfig:
    return cs.RipeRewardsConfig(
        stakeRatio = {format_percent(ripe_rewards_config.stakeRatio)},
        lockDuration = {format_blocks(ripe_rewards_config.lockDuration)},
    )


@view
@external
def securitySigners() -> DynArray[address, 10]:
    return [{generate_address_array(security_signers)}]


@view
@external
def whitelistedCreators() -> DynArray[address, 50]:
    return [{generate_address_array(whitelisted_creators)}]
'''

    return code


def generate_address_array(addresses: list) -> str:
    """Generate a comma-separated list of addresses for Vyper array literal."""
    if not addresses:
        return ""
    # Format each address on its own line for readability
    formatted = ",\n        ".join(addresses)
    return f"\n        {formatted},\n    "


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    # Output file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_file = os.path.join(project_root, "contracts", "config", "DefaultsBase.vy")

    print("Connecting to Base mainnet via Alchemy...", file=sys.stderr)

    # Set etherscan API for contract loading
    setup_boa_etherscan()

    # Fork at latest block
    with boa_fork_context() as block_number:
        print(f"Connected. Block: {block_number}", file=sys.stderr)

        # Load UndyHQ
        print("Loading UndyHQ...", file=sys.stderr)
        hq = boa.from_etherscan(UNDY_HQ, name="UndyHq")

        # Get MissionControl address
        time.sleep(RPC_DELAY)
        mc_addr = str(hq.getAddr(MISSION_CONTROL_ID))
        print(f"MissionControl: {mc_addr}", file=sys.stderr)

        # Load MissionControl
        time.sleep(RPC_DELAY)
        mc = boa.from_etherscan(mc_addr, name="MissionControl")

        # Read all configs
        print("Reading configs from MissionControl...", file=sys.stderr)

        time.sleep(RPC_DELAY)
        user_wallet_config = mc.userWalletConfig()
        print(f"  userWalletConfig: OK", file=sys.stderr)

        time.sleep(RPC_DELAY)
        agent_config = mc.agentConfig()
        print(f"  agentConfig: OK", file=sys.stderr)

        time.sleep(RPC_DELAY)
        manager_config = mc.managerConfig()
        print(f"  managerConfig: OK", file=sys.stderr)

        time.sleep(RPC_DELAY)
        payee_config = mc.payeeConfig()
        print(f"  payeeConfig: OK", file=sys.stderr)

        time.sleep(RPC_DELAY)
        cheque_config = mc.chequeConfig()
        print(f"  chequeConfig: OK", file=sys.stderr)

        time.sleep(RPC_DELAY)
        try:
            ripe_rewards_config = mc.ripeRewardsConfig()
            print(f"  ripeRewardsConfig: OK", file=sys.stderr)
        except AttributeError:
            # ripeRewardsConfig not available on this version of MissionControl
            # Use default values that match the current DefaultsBase.vy
            print(f"  ripeRewardsConfig: NOT AVAILABLE (using defaults)", file=sys.stderr)
            # Create a simple object with default values
            class DefaultRipeRewardsConfig:
                stakeRatio = 80_00  # 80%
                lockDuration = 6 * MONTH_IN_BLOCKS
            ripe_rewards_config = DefaultRipeRewardsConfig()

        # Fetch security signers (iterable)
        security_signers = []
        try:
            time.sleep(RPC_DELAY)
            num_signers = mc.numSecuritySigners()
            for i in range(1, num_signers):  # Start at 1, index 0 is sentinel
                time.sleep(RPC_DELAY)
                signer = str(mc.securitySigners(i))
                if signer != ZERO_ADDRESS:
                    security_signers.append(signer)
            print(f"  securitySigners: {len(security_signers)} found", file=sys.stderr)
        except AttributeError:
            print(f"  securitySigners: NOT AVAILABLE (iterable not supported)", file=sys.stderr)

        # Fetch whitelisted creators (iterable)
        whitelisted_creators = []
        try:
            time.sleep(RPC_DELAY)
            num_creators = mc.numWhitelistedCreators()
            for i in range(1, num_creators):  # Start at 1, index 0 is sentinel
                time.sleep(RPC_DELAY)
                creator = str(mc.whitelistedCreators(i))
                if creator != ZERO_ADDRESS:
                    whitelisted_creators.append(creator)
            print(f"  whitelistedCreators: {len(whitelisted_creators)} found", file=sys.stderr)
        except AttributeError:
            print(f"  whitelistedCreators: NOT AVAILABLE (iterable not supported)", file=sys.stderr)

        # Generate Vyper code
        print("\nGenerating DefaultsBase.vy...", file=sys.stderr)
        vyper_code = generate_defaults_vy(
            user_wallet_config,
            agent_config,
            manager_config,
            payee_config,
            cheque_config,
            ripe_rewards_config,
            security_signers,
            whitelisted_creators,
        )

        # Write to file
        with open(output_file, "w") as f:
            f.write(vyper_code)

        print(f"\nWritten to: {output_file}", file=sys.stderr)

        # Print summary
        print("\n" + "=" * 60, file=sys.stderr)
        print("Production Parameter Summary:", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"Block: {block_number}", file=sys.stderr)
        print(f"MissionControl: {mc_addr}", file=sys.stderr)
        print(f"\nAddresses:", file=sys.stderr)
        print(f"  USER_WALLET_TEMPLATE: {user_wallet_config.walletTemplate}", file=sys.stderr)
        print(f"  USER_WALLET_CONFIG_TEMPLATE: {user_wallet_config.configTemplate}", file=sys.stderr)
        print(f"  STARTING_AGENT: {agent_config.startingAgent}", file=sys.stderr)
        print(f"  REWARDS_ASSET: {user_wallet_config.depositRewardsAsset}", file=sys.stderr)
        print(f"  BONUS_ASSET: {user_wallet_config.yieldConfig.bonusAsset}", file=sys.stderr)
        print(f"\nKey Values:", file=sys.stderr)
        print(f"  numUserWalletsAllowed: {user_wallet_config.numUserWalletsAllowed}", file=sys.stderr)
        print(f"  enforceCreatorWhitelist: {user_wallet_config.enforceCreatorWhitelist}", file=sys.stderr)
        print(f"  swapFee: {user_wallet_config.txFees.swapFee / 100:.2f}%", file=sys.stderr)
        print(f"  stableSwapFee: {user_wallet_config.txFees.stableSwapFee / 100:.2f}%", file=sys.stderr)
        print(f"  rewardsFee: {user_wallet_config.txFees.rewardsFee / 100:.2f}%", file=sys.stderr)
        print(f"  performanceFee: {user_wallet_config.yieldConfig.performanceFee / 100:.2f}%", file=sys.stderr)
        print(f"  ripeStakeRatio: {ripe_rewards_config.stakeRatio / 100:.2f}%", file=sys.stderr)
        print(f"\nSecurity Signers ({len(security_signers)}):", file=sys.stderr)
        for signer in security_signers:
            print(f"  {signer}", file=sys.stderr)
        if not security_signers:
            print(f"  (none)", file=sys.stderr)
        print(f"\nWhitelisted Creators ({len(whitelisted_creators)}):", file=sys.stderr)
        for creator in whitelisted_creators:
            print(f"  {creator}", file=sys.stderr)
        if not whitelisted_creators:
            print(f"  (none)", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print("\nDone!", file=sys.stderr)


if __name__ == "__main__":
    main()
