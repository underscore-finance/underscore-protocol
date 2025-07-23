from web3 import Web3
import requests
import time
import hashlib
import webbrowser

CREATE_CALL_ABI = [{
    "type": "function",
    "name": "performCreate",
    "stateMutability": "payable",
    "inputs": [
        {"name": "value", "type": "uint256"},
        {"name": "initCode", "type": "bytes"}
    ],
    "outputs": [{"name": "newContract", "type": "address"}],
}]

CREATE_CALL_ADDR = Web3.to_checksum_address(
    "0x7cBB62EaA69F79e6873cD1ecB2392971036cFAa4"
)


class SafeAccount:
    def __init__(self, safe_address, rpc_url, safe_transaction_service_url=None, sender_address=None, sender_private_key=None):
        self.address = safe_address
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.sender_address = sender_address  # The Safe owner who will submit the transaction
        self.sender_private_key = sender_private_key  # Private key for signing authentication

        # Safe Transaction Service URL
        if safe_transaction_service_url:
            self.safe_service_url = safe_transaction_service_url
        else:
            # Auto-detect based on chain
            chain_id = self.w3.eth.chain_id
            if chain_id == 1:  # Mainnet
                self.safe_service_url = "https://safe-transaction-mainnet.safe.global"
            elif chain_id == 137:  # Polygon
                self.safe_service_url = "https://safe-transaction-polygon.safe.global"
            elif chain_id == 10:  # Optimism
                self.safe_service_url = "https://safe-transaction-optimism.safe.global"
            elif chain_id == 42161:  # Arbitrum
                self.safe_service_url = "https://safe-transaction-arbitrum.safe.global"
            elif chain_id == 8453:  # Base
                self.safe_service_url = "https://safe-transaction-base.safe.global"
            elif chain_id == 84532:  # Base Sepolia
                self.safe_service_url = "https://safe-transaction-base-sepolia.safe.global"
            else:
                raise ValueError(f"No Safe Transaction Service URL for chain {chain_id}")

        # Verify sender is a Safe owner
        if sender_address and not self._verify_safe_owner(sender_address):
            raise ValueError(f"Address {sender_address} is not a Safe owner")

        # Safe contract ABI (full version for getTransactionHash)
        self.safe_abi = [
            {
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "data", "type": "bytes"},
                    {"name": "operation", "type": "uint8"},
                    {"name": "safeTxGas", "type": "uint256"},
                    {"name": "baseGas", "type": "uint256"},
                    {"name": "gasPrice", "type": "uint256"},
                    {"name": "gasToken", "type": "address"},
                    {"name": "refundReceiver", "type": "address"},
                    {"name": "signatures", "type": "bytes"}
                ],
                "name": "execTransaction",
                "outputs": [{"name": "success", "type": "bool"}],
                "stateMutability": "nonpayable",
                "type": "function"
            },
            {
                "inputs": [
                    {"name": "to", "type": "address"},
                    {"name": "value", "type": "uint256"},
                    {"name": "data", "type": "bytes"},
                    {"name": "operation", "type": "uint8"},
                    {"name": "safeTxGas", "type": "uint256"},
                    {"name": "baseGas", "type": "uint256"},
                    {"name": "gasPrice", "type": "uint256"},
                    {"name": "gasToken", "type": "address"},
                    {"name": "refundReceiver", "type": "address"},
                    {"name": "nonce", "type": "uint256"}
                ],
                "name": "getTransactionHash",
                "outputs": [{"name": "", "type": "bytes32"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "nonce",
                "outputs": [{"name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function"
            },
            {
                "inputs": [],
                "name": "getOwners",
                "outputs": [{"name": "", "type": "address[]"}],
                "stateMutability": "view",
                "type": "function"
            }
        ]

        self.safe_contract = self.w3.eth.contract(
            address=safe_address,
            abi=self.safe_abi
        )

    def get_create_call_tx(self, init_code):
        # Convert init code to bytes
        init_code_bytes = bytes.fromhex(init_code[2:])

        create_call = self.w3.eth.contract(
            address=CREATE_CALL_ADDR, abi=CREATE_CALL_ABI
        )
        data = create_call.functions.performCreate(0, init_code_bytes).build_transaction({})["data"]

        return {
            "to": CREATE_CALL_ADDR,
            "value": 0,
            "data": data,
            "operation": 1,          # DELEGATECALL!
            "safeTxGas": 0           # let the service estimate
        }

    def _verify_safe_owner(self, address):
        """Verify that an address is a Safe owner"""
        try:
            # Try to get owners from contract first
            owners = self.safe_contract.functions.getOwners().call()
            return address.lower() in [owner.lower() for owner in owners]
        except Exception:
            # Fallback to API
            try:
                response = requests.get(f"{self.safe_service_url}/api/v1/safes/{self.address}")
                if response.status_code == 200:
                    safe_info = response.json()
                    owners = safe_info.get('owners', [])
                    return address.lower() in [owner.lower() for owner in owners]
            except Exception as e:
                print(f"Warning: Could not verify Safe owner: {e}")

        return False

    def send_transaction(self, tx_data):
        """
        Simulate signing a transaction by proposing it to the Safe and waiting for execution.
        Since Safe transactions are multi-sig, we propose the transaction and wait for it to be executed.
        """
        if tx_data.get('to') is None:
            tx_data = self.get_create_call_tx(tx_data.get('data'))

        # Propose the transaction to the Safe
        safe_tx = self._create_safe_tx(tx_data, 0)

        # Actually propose the transaction (POST)
        self._propose_transaction(safe_tx)

        # Wait for execution by polling by nonce
        nonce = safe_tx['nonce']
        tx = self._wait_for_execution(nonce)
        return {"hash": tx.get('transactionHash')}

    def _create_safe_tx(self, tx_data, gas_estimate):
        """Create a Safe transaction from raw transaction data"""
        # Get Safe owners if sender not provided
        if not self.sender_address:
            owners = self._get_safe_owners()
            if owners:
                self.sender_address = owners[0]  # Use first owner as sender
            else:
                raise ValueError("No Safe owners found and no sender address provided")

        # Verify sender is a Safe owner (but don't require private key)
        if self.sender_address and not self._verify_safe_owner(self.sender_address):
            print(f"⚠️  Warning: Sender {self.sender_address} may not be a Safe owner")

        # Get current nonce
        nonce = self._get_safe_nonce()

        # Handle contract creation (to is None)
        to_address = tx_data.get('to') if tx_data.get(
            'to') is not None else '0x0000000000000000000000000000000000000000'

        # Create Safe transaction
        safe_tx = {
            'to': to_address,
            'value': str(tx_data.get('value', 0)),
            'data': tx_data.get('data', '0x'),
            'operation': 0,  # 0 = call, 1 = delegate call
            'safeTxGas': int(gas_estimate * 1.5),
            'baseGas': '0',
            'gasPrice': '0',
            'gasToken': '0x0000000000000000000000000000000000000000',
            'refundReceiver': '0x0000000000000000000000000000000000000000',
            'nonce': str(nonce),
            'sender': self.sender_address,
            'signature': '0x',  # Will be filled by Safe Transaction Service
            'origin': 'Boa Safe Integration'
        }

        # Get the correct contract transaction hash from Safe contract
        contract_tx_hash = self._get_contract_tx_hash(safe_tx)
        safe_tx['contractTransactionHash'] = contract_tx_hash

        return safe_tx

    def _get_contract_tx_hash(self, safe_tx):
        """Get the correct contract transaction hash from Safe contract"""
        try:
            # Convert nonce to int for the contract call
            nonce = int(safe_tx['nonce'])

            # Call Safe's getTransactionHash function with correct types
            contract_tx_hash = self.safe_contract.functions.getTransactionHash(
                safe_tx['to'] if safe_tx['to'] is not None else '0x0000000000000000000000000000000000000000',
                int(safe_tx['value']),
                safe_tx['data'],
                int(safe_tx['operation']),
                int(safe_tx['safeTxGas']),
                int(safe_tx['baseGas']),
                int(safe_tx['gasPrice']),
                safe_tx['gasToken'],
                safe_tx['refundReceiver'],
                nonce
            ).call()

            return contract_tx_hash.hex()

        except Exception as e:
            print(f"❌ Error getting contract transaction hash: {e}")
            # Fallback to a simple hash calculation
            tx_data = f"{safe_tx['to']}{safe_tx['value']}{safe_tx['data']}{safe_tx['nonce']}"
            return hashlib.sha256(tx_data.encode()).hexdigest()

    def _get_safe_nonce(self):
        """Get the current nonce from the Safe contract"""
        try:
            nonce = self.safe_contract.functions.nonce().call()
            return nonce
        except Exception as e:
            print(f"❌ Error getting Safe nonce: {e}")
            # Fallback to 0
            return 0

    def _get_nonce(self):
        """Get the next nonce for the Safe"""
        try:
            # Get from Safe Transaction Service
            response = requests.get(f"{self.safe_service_url}/api/v1/safes/{self.address}")
            if response.status_code == 200:
                safe_info = response.json()
                return safe_info.get('nonce', 0)
        except Exception as e:
            print(f"Warning: Could not get nonce from Safe Transaction Service: {e}")

        return 0

    def _get_safe_owners(self):
        """Get Safe owners from the API"""
        try:
            response = requests.get(f"{self.safe_service_url}/api/v1/safes/{self.address}")
            if response.status_code == 200:
                safe_info = response.json()
                return safe_info.get('owners', [])
        except Exception as e:
            print(f"Warning: Could not get Safe owners: {e}")

        return []

    def _generate_safe_transaction_link(self, tx_hash):
        """Generate direct link to view transaction in Safe web interface"""
        # Extract chain name from Safe Transaction Service URL
        if "base-sepolia" in self.safe_service_url:
            chain_name = "base-sepolia"
        elif "base" in self.safe_service_url:
            chain_name = "base"
        elif "mainnet" in self.safe_service_url:
            chain_name = "eth"
        elif "polygon" in self.safe_service_url:
            chain_name = "matic"
        elif "optimism" in self.safe_service_url:
            chain_name = "oeth"
        elif "arbitrum" in self.safe_service_url:
            chain_name = "arb1"
        else:
            chain_name = "unknown"

        return f"https://app.safe.global/transactions/tx?safe={chain_name}:{self.address}&id={tx_hash}"

    def _propose_transaction(self, safe_tx):
        """Propose transaction to Safe Transaction Service (reverted to previous working version)"""
        to_address = safe_tx['to'] if safe_tx['to'] is not None else '0x0000000000000000000000000000000000000000'
        if not self.sender_address:
            owners = self._get_safe_owners()
            if owners:
                self.sender_address = owners[0]
            else:
                raise ValueError("No Safe owners found and no sender address provided")
        payload = {
            'to': to_address,
            'value': str(safe_tx['value']),
            'data': safe_tx['data'],
            'operation': safe_tx['operation'],
            'safeTxGas': str(safe_tx['safeTxGas']),
            'baseGas': str(safe_tx['baseGas']),
            'gasPrice': str(safe_tx['gasPrice']),
            'gasToken': safe_tx['gasToken'],
            'refundReceiver': safe_tx['refundReceiver'],
            'nonce': safe_tx['nonce'],
            'contractTransactionHash': safe_tx['contractTransactionHash'],
            'sender': self.sender_address
        }

        response = requests.post(
            f"{self.safe_service_url}/api/v1/safes/{self.address}/multisig-transactions/",
            json=payload,
            headers={'Content-Type': 'application/json'}
        )
        if response.status_code == 201:
            url = self._generate_safe_transaction_link(safe_tx['contractTransactionHash'])
            print(f"\n📱 Open this link to view and sign the transaction in Safe web interface:")
            print(url)
            webbrowser.open(url)
        else:
            print(f"❌ Failed to propose transaction: {response.status_code}")
            print(f"Response: {response.text}")
            raise Exception(f"Failed to propose Safe transaction: {response.status_code}")

    def _wait_for_execution(self, nonce=None):
        """Wait for the Safe transaction to be executed. If safeTxHash is not found, poll by nonce until it appears."""
        poll_interval = 5

        is_executed = False
        tx = None

        # If safe_tx_hash is None or empty, poll by nonce until we get the hash
        while (not is_executed):
            txs = requests.get(
                f"{self.safe_service_url}/api/v1/safes/{self.address}/multisig-transactions/?nonce={nonce}"
            )
            if txs.status_code == 200:
                results = txs.json().get('results', [])
                if results:
                    is_executed = results[0]['isExecuted']
                    tx = results[0]
                    break
            time.sleep(poll_interval)

        print(f"✅ Safe Transaction executed")
        return tx

    def _gas_estimation(self, tx_data):
        """Test gas estimation for the transaction"""
        # Try to estimate gas
        gas_estimate = self.w3.eth.estimate_gas({
            'from': self.address,
            'to': tx_data.get('to', None),
            'data': tx_data.get('data', '0x'),
            'value': tx_data.get('value', 0)
        })

        # Try to simulate the transaction
        self.w3.eth.call({
            'from': self.address,
            'to': tx_data.get('to', None),
            'data': tx_data.get('data', '0x'),
            'value': tx_data.get('value', 0)
        })
        return gas_estimate
