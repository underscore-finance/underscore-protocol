import requests
import json
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

api_url = "https://api.etherscan.io/v2/api"

REQUEST_TIMEOUT = 30

# Shared session with connection pooling (keep-alive) + automatic retries.
# Without connection reuse, the per-contract burst of getabi/verify/poll calls
# opens a fresh socket each time; across a manifest this exhausts the local
# ephemeral port range on macOS and surfaces as OSError [Errno 49]
# "Can't assign requested address". Reusing one connection avoids the churn,
# and the Retry rides out transient connection blips and rate limits (429/5xx).
_retry = Retry(
    total=5,
    connect=5,
    read=3,
    backoff_factor=1.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=frozenset(["GET", "POST"]),
    raise_on_status=False,
)
session = requests.Session()
_adapter = HTTPAdapter(max_retries=_retry)
session.mount("https://", _adapter)
session.mount("http://", _adapter)

chain_ids = {
    "eth-mainnet": 1,
    "eth-goerli": 5,
    "eth-sepolia": 11155111,
    "base-mainnet": 8453,
    "base-goerli": 84532,
    "base-sepolia": 84532,
}


contract_base_url = {
    "eth-mainnet": "https://etherscan.io/address/",
    "eth-goerli": "https://goerli.etherscan.io/address/",
    "eth-sepolia": "https://sepolia.etherscan.io/address/",
    "base-mainnet": "https://basescan.org/address/",
    "base-goerli": "https://goerli.basescan.org/address/",
    "base-sepolia": "https://sepolia.basescan.org/address/",
}


def is_contract_verified(api_key: str, contract_address: str, chain: str) -> bool:
    """Check if contract is already verified"""
    chain_id = chain_ids.get(chain, chain_ids["eth-mainnet"])

    params = {
        "chainid": chain_id,
        "apikey": api_key,
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
    }

    try:
        response = session.get(api_url, params=params, timeout=REQUEST_TIMEOUT)
        result = response.json()
    except requests.exceptions.RequestException as e:
        # Don't let a transient pre-check failure crash the whole run; treat it
        # as "not verified" so we fall through to an actual verification attempt.
        print(f"  Could not check existing verification status ({e}); attempting verification anyway")
        return False

    return result.get("status") == "1"


def verify_from_manifest(api_key: str, contract_name: str, manifest_data: dict, chain: str) -> bool:
    """Verify contract using manifest data"""

    print("Address: ", manifest_data["address"], 'url: ', contract_base_url[chain] + manifest_data["address"])

    # Check if already verified
    if is_contract_verified(api_key, manifest_data["address"], chain):
        return True

    # Prepare verification request
    # TODO: this path is unreliable for large, near-EIP-170 Vyper contracts
    # (e.g. HighCommand/ChequeBook/Migrator), which Basescan rejects with the
    # generic "Other Exception - Please contact us for more information". The
    # source/settings are correct (deployed bytecode matches a local recompile
    # modulo appended immutables) -- it's the submission shape. Workaround for
    # now: verify those manually by feeding solc_json as a vyper standard-JSON.
    # Proper fix: derive contractname from solc_json.settings.outputSelection
    # (the real target file) instead of next(iter(sources)), which currently
    # resolves to an interface .vyi file and only works by Basescan's tolerance.
    contract_file = next(iter(manifest_data["solc_json"]["sources"].keys()))
    
    chain_id = chain_ids.get(chain, chain_ids["eth-mainnet"])
    params = {
        "apikey": api_key,
        "module": "contract",
        "action": "verifysourcecode",
        "sourceCode": json.dumps(manifest_data["solc_json"]),
        "contractaddress": manifest_data["address"],
        "codeformat": "vyper-json",
        "contractname": f"{contract_file}:{contract_name}",  # Format: contractfile.vy:contractname
        "compilerversion": "vyper:0.4.3",
        "constructorArguements": manifest_data.get("args", ""),
        "optimizationUsed": "1",
        "runs": "200",
        "evmversion": ""
    }

    try:
        # Submit verification request
        response = session.post(api_url, params={"chainid": chain_id}, data=params, timeout=REQUEST_TIMEOUT)
        result = response.json()

        if result["status"] != "1":
            print(f"Verification submission failed: {result['result']}")
            return False

        guid = result["result"]
        print(f"Verification submitted. GUID: {guid}")

        # Check verification status
        check_params = {
            "chainid": chain_id,
            "apikey": api_key,
            "module": "contract",
            "action": "checkverifystatus",
            "guid": guid,
        }

        # Poll for verification result
        for _ in range(10):  # Try 10 times
            time.sleep(5)  # Wait 5 seconds between checks
            check_response = session.get(api_url, params=check_params, timeout=REQUEST_TIMEOUT)
            check_result = check_response.json()

            if check_result["result"] == "Pass - Verified":
                print(f"{contract_name} verified successfully!")
                return True
            elif check_result["result"] != "Pending in queue":
                print(f"Verification failed: {check_result['result']}")
                # Print more details if available
                if "message" in check_result:
                    print(f"Error message: {check_result['message']}")
                return False

        print("Verification timed out")
        return False

    except Exception as e:
        print(f"Error during verification: {str(e)}")
        return False
