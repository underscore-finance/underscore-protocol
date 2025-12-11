"""
ExtraFi Supply APY Calculator

Calculates the supply/earn APY for ExtraFi Lend reserves on Base network,
including staking incentives (EXTRA and OP tokens).

Usage:
    python scripts/params/extrafi_apy.py

Formula:
    Base APY = Borrow Rate × Utilization Rate × (1 - 15% Fee)
    Total APY = Base APY + EXTRA Incentives APY + OP Incentives APY
"""

import boa
import os
import time

RPC_URL = "https://mainnet.base.org"
EXTRAFI_POOL = "0xBb505c54D71E9e599cB8435b4F0cEEc05fC71cbD"

# Reward token addresses
EXTRA_TOKEN = "0x2dAD3a13ef0C6366220f989157009e501e7938F8"
OP_TOKEN = "0x994ac01750047B9d35431a7Ae4Ed312ee955E030"  # axlOP (Axelar-bridged OP)

# Token prices (USD) - update these or fetch from oracle
EXTRA_PRICE_USD = 0.012  # ~$0.012 per EXTRA
OP_PRICE_USD = 0.31      # ~$0.31 per OP

SECONDS_PER_YEAR = 365 * 24 * 60 * 60
PROTOCOL_FEE_BPS = 1500  # 15%

# Known reserve IDs and their staking contracts
RESERVES = {
    "WETH": {
        "reserve_id": 1,
        "decimals": 18,
        "staking": "0x5F8d42635A2fa74D03b5F91c825dE6F44c443dA5",
    },
    "AERO": {
        "reserve_id": 3,
        "decimals": 18,
        "staking": "0x8f480b12B321dac9D5427aAD8F3e560fca2b3216",
    },
    "USDC": {
        "reserve_id": 25,
        "decimals": 6,
        "staking": "0xE61662C09c30E1F3f3CbAeb9BC1F13838Ed18957",
    },
}


def get_staking_rewards_apy(staking_contract, pool, reserve_id, decimals):
    """
    Calculate APY from staking rewards (EXTRA and OP tokens).

    Returns:
        dict: Contains extra_apy and op_apy as percentages
    """
    import time as time_module

    try:
        # Get total staked eTokens and convert to USD value
        total_staked = staking_contract.totalStaked()
        exchange_rate = pool.exchangeRateOfReserve(reserve_id)

        # Convert eTokens to underlying value
        total_underlying = total_staked * exchange_rate // 10**18
        total_usd_value = total_underlying / (10 ** decimals)

        if total_usd_value == 0:
            return {"extra_apy": 0.0, "op_apy": 0.0}

        extra_apy = 0.0
        op_apy = 0.0
        current_time = int(time_module.time())

        # Check number of reward tokens
        num_rewards = staking_contract.rewardsTokenListLength()

        for i in range(num_rewards):
            reward_token = str(staking_contract.rewardTokens(i))
            reward_data = staking_contract.rewardData(reward_token)

            # rewardData tuple: (startTime, endTime, rewardRate, lastUpdateTime, rewardPerTokenStored)
            end_time = reward_data[1]
            reward_rate = reward_data[2]

            # Only count rewards if the period is still active
            if current_time > end_time:
                continue  # Reward period has ended

            # Calculate annual rewards in USD
            rewards_per_year = reward_rate * SECONDS_PER_YEAR / 10**18

            if reward_token.lower() == EXTRA_TOKEN.lower():
                usd_per_year = rewards_per_year * EXTRA_PRICE_USD
                extra_apy = (usd_per_year / total_usd_value) * 100
            elif reward_token.lower() == OP_TOKEN.lower():
                usd_per_year = rewards_per_year * OP_PRICE_USD
                op_apy = (usd_per_year / total_usd_value) * 100

        return {"extra_apy": extra_apy, "op_apy": op_apy}

    except Exception as e:
        print(f"    Warning: Could not fetch staking rewards: {e}")
        return {"extra_apy": 0.0, "op_apy": 0.0}


def get_extrafi_supply_apy(pool, reserve_id):
    """
    Calculate ExtraFi base supply APY for a reserve.

    Returns:
        dict: Contains gross_apy, net_apy (after fees), and other metrics
    """
    borrow_rate = pool.borrowingRateOfReserve(reserve_id)  # 1e18 scaled
    utilization = pool.utilizationRateOfReserve(reserve_id)  # 1e18 scaled
    total_liquidity = pool.totalLiquidityOfReserve(reserve_id)
    total_borrows = pool.totalBorrowsOfReserve(reserve_id)

    # Gross APY = Borrow Rate × Utilization (before protocol fee)
    gross_rate_1e18 = borrow_rate * utilization // 10**18

    # Net APY = Gross APY × (1 - Fee Rate) (after protocol fee)
    supplier_share_bps = 10000 - PROTOCOL_FEE_BPS  # 8500 = 85%
    net_rate_1e18 = gross_rate_1e18 * supplier_share_bps // 10000

    return {
        "gross_apy": gross_rate_1e18 / 10**16,
        "net_apy": net_rate_1e18 / 10**16,
        "borrow_apy": borrow_rate / 10**16,
        "utilization": utilization / 10**16,
        "total_liquidity": total_liquidity,
        "total_borrows": total_borrows,
    }


def format_amount(amount, decimals=18):
    """Format a token amount for display."""
    return amount / (10 ** decimals)


def main():
    api_key = os.environ.get("ETHERSCAN_API_KEY", "")
    if api_key:
        boa.set_etherscan(
            api_key=api_key,
            uri="https://api.etherscan.io/v2/api?chainid=8453"
        )

    with boa.fork(RPC_URL):
        pool = boa.from_etherscan(EXTRAFI_POOL, name="ExtraFiPool")

        print("=" * 85)
        print("ExtraFi Supply APY Report (Base Network)")
        print("=" * 85)
        print(f"Pool Contract: {EXTRAFI_POOL}")
        print(f"Token Prices: EXTRA=${EXTRA_PRICE_USD}, OP=${OP_PRICE_USD}")
        print()

        # Table header
        print(f"{'Asset':<6} | {'Gross APY':>10} | {'Base APY':>10} | {'EXTRA':>8} | {'OP':>8} | {'Total APY':>10}")
        print("-" * 85)

        for name, config in RESERVES.items():
            reserve_id = config["reserve_id"]
            decimals = config["decimals"]
            staking_addr = config["staking"]

            time.sleep(0.25)  # Rate limit

            try:
                # Get base lending APY
                base_data = get_extrafi_supply_apy(pool, reserve_id)

                # Get staking rewards APY
                time.sleep(0.25)
                staking = boa.from_etherscan(staking_addr, name=f"Staking_{name}")
                rewards_data = get_staking_rewards_apy(staking, pool, reserve_id, decimals)

                gross_apy = base_data["gross_apy"]
                net_apy = base_data["net_apy"]
                extra_apy = rewards_data["extra_apy"]
                op_apy = rewards_data["op_apy"]
                total_apy = net_apy + extra_apy + op_apy

                # Print table row
                print(f"{name:<6} | {gross_apy:>9.2f}% | {net_apy:>9.2f}% | {extra_apy:>7.2f}% | {op_apy:>7.2f}% | {total_apy:>9.2f}%")

            except Exception as e:
                print(f"{name:<6} | Error: {e}")

        print("-" * 85)
        print()
        print("Legend:")
        print("  Gross APY  = Borrow Rate × Utilization (before 15% protocol fee)")
        print("  Base APY   = Gross APY × 85% (after protocol fee)")
        print("  EXTRA      = ExtraFi token staking incentives")
        print("  OP         = Optimism token staking incentives")
        print("  Total APY  = Base APY + EXTRA + OP")


if __name__ == "__main__":
    main()
