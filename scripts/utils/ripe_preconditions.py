import boa
from eth_utils import keccak


def _require_approved_code(address, expected_codehash, label: str):
    if not expected_codehash:
        raise RuntimeError(f"Robinhood {label} codehash is not configured")
    runtime = boa.env.get_code(address)
    if not runtime:
        raise RuntimeError(f"Robinhood {label} has no code")
    actual_codehash = "0x" + keccak(runtime).hex()
    if actual_codehash.lower() != str(expected_codehash).lower():
        raise RuntimeError(
            f"Robinhood {label} codehash is {actual_codehash}, "
            f"expected {expected_codehash}"
        )


def require_robinhood_ripe_dependencies(migration):
    """Authenticate immutable RIPE dependencies before core deployment."""
    ripe_hq = migration.blueprint.INTEGRATION_ADDYS.get("RIPE_HQ_V1")
    ripe_token = migration.blueprint.TOKENS.get("RIPE")
    price_desk = migration.blueprint.INTEGRATION_ADDYS.get("RIPE_PRICE_DESK")
    expected_teller = migration.blueprint.INTEGRATION_ADDYS.get("RIPE_TELLER")
    zero_address = migration.blueprint.CONSTANTS.ZERO_ADDRESS

    configured = (
        ("RipeHq", ripe_hq),
        ("RIPE", ripe_token),
        ("PriceDesk", price_desk),
        ("Teller", expected_teller),
    )
    for label, address in configured:
        if not address or str(address).lower() == zero_address.lower():
            raise RuntimeError(f"Robinhood {label} address is not configured")

    approved_code = (
        (
            ripe_hq,
            migration.blueprint.INTEGRATION_ADDYS.get("RIPE_HQ_V1_CODEHASH"),
            "RipeHq",
        ),
        (
            ripe_token,
            migration.blueprint.INTEGRATION_ADDYS.get("RIPE_TOKEN_CODEHASH"),
            "RIPE",
        ),
        (
            price_desk,
            migration.blueprint.INTEGRATION_ADDYS.get("RIPE_PRICE_DESK_CODEHASH"),
            "PriceDesk",
        ),
        (
            expected_teller,
            migration.blueprint.INTEGRATION_ADDYS.get("RIPE_TELLER_CODEHASH"),
            "Teller",
        ),
    )
    for address, expected_codehash, label in approved_code:
        _require_approved_code(address, expected_codehash, label)

    try:
        registry = boa.load_abi(
            "scripts/abis/UndyHq.json",
            name="RipeRegistryPreflight",
        ).at(ripe_hq)
        live_ripe = registry.getAddr(3)
        live_price_desk = registry.getAddr(7)
        teller = registry.getAddr(17)
    except Exception as exc:
        raise RuntimeError("Robinhood RipeHq registry reads failed") from exc

    if str(live_ripe).lower() != ripe_token.lower():
        raise RuntimeError(
            f"Robinhood RipeHq ID 3 is {live_ripe}, expected RIPE at {ripe_token}"
        )
    if str(live_price_desk).lower() != price_desk.lower():
        raise RuntimeError(
            "Robinhood RipeHq ID 7 is "
            f"{live_price_desk}, expected PriceDesk at {price_desk}"
        )
    if str(teller).lower() != expected_teller.lower():
        raise RuntimeError(
            f"Robinhood RipeHq ID 17 is {teller}, expected Teller at "
            f"{expected_teller}"
        )

    return ripe_hq, ripe_token, price_desk, str(teller)
