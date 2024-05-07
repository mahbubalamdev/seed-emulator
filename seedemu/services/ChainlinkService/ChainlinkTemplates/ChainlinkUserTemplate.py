from typing import Dict

ChainlinkUserTemplate: Dict[str, str] = {}

ChainlinkUserTemplate['get_contract_addresses']="""\
#!/bin/env python3

import requests
import re
import logging
import time
import json
import os

def check_oracle_contracts(init_server_url, number_of_normal_servers):
    oracle_contracts_found = 0
    link_token_contract_address = None

    while oracle_contracts_found != number_of_normal_servers:
        try:
            response = requests.get(init_server_url)
            if response and response.status_code == 200:
                html_content = response.text

                oracle_contracts = re.findall(r'<h1>Oracle Contract Address: (.+?)</h1>', html_content)
                oracle_contracts_found = len(oracle_contracts)
                logging.info(f"Checking for oracle contracts, found: {{oracle_contracts_found}}")

                match = re.search(r'<h1>Link Token Contract: (.+?)</h1>', html_content)
                if match and match.group(1):
                    link_token_contract_address = match.group(1)
                    logging.info(f"Found Link Token address: {{link_token_contract_address}}")

                if oracle_contracts_found == number_of_normal_servers:
                    logging.info("Found all required oracle contracts.")
                    break
                else:
                    logging.info(f"Number of oracle contracts found ({{oracle_contracts_found}}) does not match the target ({{number_of_normal_servers}}). Retrying...")
            else:
                logging.warning("Failed to fetch data from server. Retrying...")

        except Exception as e:
            logging.error(f"An error occurred: {{e}}")

        # Wait 30 seconds before retrying
        time.sleep(30)

    return oracle_contracts, link_token_contract_address

init_server_url = "http://{init_node_url}"
number_of_normal_servers = {number_of_normal_servers}
oracle_contracts, link_token_contract_address = check_oracle_contracts(init_server_url, number_of_normal_servers)
logging.info(f"Oracle Contracts: {{oracle_contracts}}")
logging.info(f"Link Token Contract Address: {{link_token_contract_address}}")
# Save this information to a file
data = {{
    'oracle_contracts': oracle_contracts,
    'link_token_contract_address': link_token_contract_address
}}
directory = './info'
if not os.path.exists(directory):
    os.makedirs(directory)
    
with open('./info/contract_addresses.json', 'w') as f:
    json.dump(data, f)
"""

ChainlinkUserTemplate['deploy_user_contract']='''\
#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
import requests
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

rpc_url = "http://{rpc_url}:{rpc_port}"
faucet_url = "http://{faucet_url}:{faucet_port}"

web3 = Web3(HTTPProvider(rpc_url))
while not web3.isConnected():
    logging.error("Failed to connect to Ethereum node. Retrying...")
    time.sleep(5)

web3.middleware_onion.inject(geth_poa_middleware, layer=0)
logging.info("Successfully connected to the Ethereum node.")

user_account = web3.eth.account.create()
account_address = user_account.address
private_key = user_account.privateKey.hex()

# Save user account information to a file
data = {{
    'account_address': account_address,
    'private_key': private_key
}}
with open('./info/user_account.json', 'w') as f:
    json.dump(data, f)
    
logging.info(f"User account address: {{account_address}}")

# Check if the faucet server is running for 600 seconds
timeout = 600
start_time = time.time()
while True:
    try:
        response = requests.get(faucet_url)
        if response.status_code == 200:
            logging.info("faucet server connection succeed.")
            break
        logging.info("faucet server connection failed: try again 10 seconds after.")
        
        time.sleep(10)
        if time.time() - start_time > timeout:
            logging.info("faucet server connection failed: 600 seconds exhausted.")
            exit()
    except Exception as e:
        pass

def send_fundme_request(account_address):
	data = {{'address': account_address, 'amount': 10}}
	logging.info(data)
	request_url = "http://{faucet_url}:{faucet_port}/fundme"
	try:
		response = requests.post(request_url, headers={{"Content-Type": "application/json"}}, data=json.dumps(data))
		logging.info(response)
		if response.status_code == 200:
			api_response = response.json()
			message = api_response['message']
			if message:
				print(f"Success: {{message}}")
			else:
				logging.error("Funds request was successful but the response format is unexpected.")
		else:
			api_response = response.json()
			message = api_response['message']
			logging.error(f"Failed to request funds from faucet server. Status code: {{response.status_code}} Message: {{message}}")
			# Send another request
			logging.info("Sending another request to faucet server.")
			send_fundme_request(account_address)
	except Exception as e:
		logging.error(f"An error occurred: {{str(e)}}")
		exit()

# Send /fundme request to faucet server
send_fundme_request(account_address)
timeout = 100
isAccountFunded = False
start = time.time()
while time.time() - start < timeout:
	balance = web3.eth.get_balance(account_address)
	if balance > 0:
		isAccountFunded = True
		break
	time.sleep(5)
 

if isAccountFunded:
	logging.info(f"Account funded: {{account_address}}")
else:
	logging.error(f"Failed to fund account: {{account_address}}")
	exit()

with open('./contracts/user_contract.abi', 'r') as abi_file:
	user_contract_abi = abi_file.read()
with open('./contracts/user_contract.bin', 'r') as bin_file:
	user_contract_bin = bin_file.read().strip()

user_contract = web3.eth.contract(abi=user_contract_abi, bytecode=user_contract_bin)

# Deploy the user contract
user_contract_data = user_contract.constructor().buildTransaction({{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
}})['data']

def sendTransaction(recipient, amount, sender_name='', 
            gas=30000, nonce:int=-1, data:str='', 
            maxFeePerGas:float=3.0, maxPriorityFeePerGas:float=2.0, 
            wait=True, verbose=True):
    if nonce == -1:
        nonce = web3.eth.getTransactionCount(account_address)
    
    maxFeePerGas = Web3.toWei(maxFeePerGas, 'gwei')
    maxPriorityFeePerGas = Web3.toWei(maxPriorityFeePerGas, 'gwei')
    transaction = {{
        'nonce':    nonce,
        'from':     account_address,
        'to':       recipient,
        'value':    0,
        'chainId':  {chain_id},
        'gas':      gas,
        'maxFeePerGas':         maxFeePerGas,
        'maxPriorityFeePerGas': maxPriorityFeePerGas,
        'data':     data
    }}

    tx_hash = sendRawTransaction(private_key, transaction, wait, verbose)
    return tx_hash

def sendRawTransaction(key, transaction:dict, wait=True, verbose=True):
    signed_tx = web3.eth.account.sign_transaction(transaction, key)
    tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
    if wait:
        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_hash

tx_hash = sendTransaction(None, 0, '', gas=3000000, data=user_contract_data, wait=True, verbose=True)
contract_address = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300).contractAddress
logging.info(f"User contract deployed at address: {{contract_address}}")

# Save the contract address to a file
data = {{'contract_address': contract_address}}
with open('./info/user_contract.json', 'w') as f:
    json.dump(data, f)
'''

ChainlinkUserTemplate['set_contract_addresses']='''\
#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
import requests
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

rpc_url = "http://{rpc_url}:{rpc_port}"
faucet_url = "http://{faucet_url}:{faucet_port}"

web3 = Web3(HTTPProvider(rpc_url))
while not web3.isConnected():
    logging.error("Failed to connect to Ethereum node. Retrying...")
    time.sleep(5)

web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Load the oracle contracts and link token contract address
with open('./info/contract_addresses.json', 'r') as f:
    contract_addresses = json.load(f)
    
oracle_contracts = contract_addresses.get('oracle_contracts', [])
link_token_contract_address = contract_addresses.get('link_token_contract_address', '')

# Load user account information
with open('./info/user_account.json', 'r') as f:
    user_account = json.load(f)
    
account_address = user_account.get('account_address', '')
private_key = user_account.get('private_key', '')

# Load the user contract address
with open('./info/user_contract.json', 'r') as f:
    user_contract = json.load(f)

user_contract_address = user_contract.get('contract_address', '')

# Load the user contract ABI
with open('./contracts/user_contract.abi', 'r') as f:
    user_contract_abi = f.read()

user_contract = web3.eth.contract(address=user_contract_address, abi=user_contract_abi)
set_link_token_function = user_contract.functions.setLinkToken(link_token_contract_address)
transaction_info = {{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'chainId': {chain_id}
}}
set_link_token_tx = set_link_token_function.buildTransaction(transaction_info)
signed_tx = web3.eth.account.sign_transaction(set_link_token_tx, private_key)
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
if tx_receipt['status'] == 0:
    logging.error("Failed to set Link Token contract address in user contract.")
    exit()
logging.info("Set Link Token contract address in user contract mined successfully.")

# Set the oracle contracts in the user contract
job_id = "7599d3c8f31e4ce78ad2b790cbcfc673"
add_oracle_function = user_contract.functions.addOracles(oracle_contracts, job_id)
transaction_info = {{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'chainId': {chain_id}
}}
add_oracle_tx = add_oracle_function.buildTransaction(transaction_info)
signed_tx = web3.eth.account.sign_transaction(add_oracle_tx, private_key)
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
# If the status is 0, the transaction failed
if tx_receipt['status'] == 0:
    logging.error("Failed to set oracle contracts in user contract.")
    exit()
logging.info("Add oracles function in user contract mined successfully.")
'''

ChainlinkUserTemplate['fund_user_contract']='''\
#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
import requests
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

rpc_url = "http://{rpc_url}:{rpc_port}"
faucet_url = "http://{faucet_url}:{faucet_port}"

web3 = Web3(HTTPProvider(rpc_url))
while not web3.isConnected():
    logging.error("Failed to connect to Ethereum node. Retrying...")
    time.sleep(5)

web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Load user account information
with open('./info/user_account.json', 'r') as f:
	user_account = json.load(f)

account_address = user_account.get('account_address', '')
private_key = user_account.get('private_key', '')

link_token_abi = None
with open('./contracts/link_token.abi', 'r') as f:
	link_token_abi = f.read()

# Load the link token contract address
with open('./info/contract_addresses.json', 'r') as f:
	contract_addresses = json.load(f)

link_token_contract_address = contract_addresses.get('link_token_contract_address', '')
link_token_contract_address = web3.toChecksumAddress(link_token_contract_address)

link_token_contract = web3.eth.contract(address=link_token_contract_address, abi=link_token_abi)

transaction_info = {{
    'from': account_address,
    'to': link_token_contract_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'gasPrice': web3.toWei(50, 'gwei'),
    'value': web3.toWei(1, 'ether'),
    'chainId': {chain_id}
}}
signed_tx = web3.eth.account.sign_transaction(transaction_info, private_key)
eth_to_link_tx = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
eth_to_link_tx_receipt = web3.eth.wait_for_transaction_receipt(eth_to_link_tx, timeout=300)
if eth_to_link_tx_receipt['status'] == 0:
	logging.error("Failed to send 1 ETH to LINK token contract.")
	exit()
logging.info("Sent 1 ETH to LINK token contract successfully.")

# Transfer 100 LINK tokens to the user contract
with open('./info/user_contract.json', 'r') as f:
	user_contract = json.load(f)

user_contract_address = user_contract.get('contract_address', '')
user_contract_address = web3.toChecksumAddress(user_contract_address)

link_amount_to_transfer = web3.toWei(100, 'ether')
transfer_function = link_token_contract.functions.transfer(user_contract_address, link_amount_to_transfer)
transaction_info = {{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'chainId': {chain_id}
}}
transfer_tx = transfer_function.buildTransaction(transaction_info)
signed_tx = web3.eth.account.sign_transaction(transfer_tx, private_key)
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
if tx_receipt['status'] == 0:
	logging.error("Failed to transfer LINK tokens to user contract.")
	exit()
logging.info("Transferred LINK tokens to user contract successfully.")

# Check the balance of user contract
balance = link_token_contract.functions.balanceOf(user_contract_address).call()
logging.info(f"User contract balance: {{balance}}")
'''

ChainlinkUserTemplate['request_eth_price']='''\
#!/bin/env python3

import time
from web3 import Web3, HTTPProvider
from web3.middleware import geth_poa_middleware
import requests
import logging
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

rpc_url = "http://{rpc_url}:{rpc_port}"
faucet_url = "http://{faucet_url}:{faucet_port}"

web3 = Web3(HTTPProvider(rpc_url))
while not web3.isConnected():
    logging.error("Failed to connect to Ethereum node. Retrying...")
    time.sleep(5)

web3.middleware_onion.inject(geth_poa_middleware, layer=0)

# Load user account information
with open('./info/user_account.json', 'r') as f:
	user_account = json.load(f)

account_address = user_account.get('account_address', '')
private_key = user_account.get('private_key', '')


# Load the user contract address
with open('./info/user_contract.json', 'r') as f:
    user_contract = json.load(f)

user_contract_address = user_contract.get('contract_address', '')

# Load the user contract ABI
with open('./contracts/user_contract.abi', 'r') as f:
    user_contract_abi = f.read()

user_contract = web3.eth.contract(address=user_contract_address, abi=user_contract_abi)
request_eth_price_data_function = user_contract.functions.requestETHPriceData("{url}", "{path}")
transaction_info = {{
    'from': account_address,
    'nonce': web3.eth.getTransactionCount(account_address),
    'gas': 3000000,
    'chainId': {chain_id}
}}
invoke_request_eth_price_data_tx = request_eth_price_data_function.buildTransaction(transaction_info)
signed_tx = web3.eth.account.sign_transaction(invoke_request_eth_price_data_tx, private_key)
tx_hash = web3.eth.sendRawTransaction(signed_tx.rawTransaction)
tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=300)
if tx_receipt['status'] == 0:
	logging.error("Failed to request ETH price data.")
	exit()
logging.info("Requested ETH price data successfully.")

# Wait for responses to be received
response_count = 0
while response_count < {number_of_normal_servers}:
	response_count = user_contract.functions.responsesCount().call()
	logging.info(f"Awaiting responses... Current responses count: {{response_count}}")
	time.sleep(10)

average_price = user_contract.functions.averagePrice().call()
logging.info(f"Response count: {{response_count}}")
logging.info(f"Average ETH price: {{average_price}}")
logging.info("Chainlink user example service completed.")
'''

ChainlinkUserTemplate['user_contract_abi']="""\
[
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "owner",
				"type": "address"
			}
		],
		"name": "OwnableInvalidOwner",
		"type": "error"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "account",
				"type": "address"
			}
		],
		"name": "OwnableUnauthorizedAccount",
		"type": "error"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "bytes32",
				"name": "id",
				"type": "bytes32"
			}
		],
		"name": "ChainlinkCancelled",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "bytes32",
				"name": "id",
				"type": "bytes32"
			}
		],
		"name": "ChainlinkFulfilled",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "bytes32",
				"name": "id",
				"type": "bytes32"
			}
		],
		"name": "ChainlinkRequested",
		"type": "event"
	},
	{
		"anonymous": false,
		"inputs": [
			{
				"indexed": true,
				"internalType": "address",
				"name": "previousOwner",
				"type": "address"
			},
			{
				"indexed": true,
				"internalType": "address",
				"name": "newOwner",
				"type": "address"
			}
		],
		"name": "OwnershipTransferred",
		"type": "event"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "_oracle",
				"type": "address"
			},
			{
				"internalType": "string",
				"name": "_jobId",
				"type": "string"
			}
		],
		"name": "addOracle",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address[]",
				"name": "_oracles",
				"type": "address[]"
			},
			{
				"internalType": "string",
				"name": "_jobId",
				"type": "string"
			}
		],
		"name": "addOracles",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "_index",
				"type": "uint256"
			}
		],
		"name": "deactivateOracle",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "bytes32",
				"name": "_requestId",
				"type": "bytes32"
			},
			{
				"internalType": "uint256",
				"name": "_price",
				"type": "uint256"
			}
		],
		"name": "fulfill",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "renounceOwnership",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "string",
				"name": "url",
				"type": "string"
			},
			{
				"internalType": "string",
				"name": "path",
				"type": "string"
			}
		],
		"name": "requestETHPriceData",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "_link_token",
				"type": "address"
			}
		],
		"name": "setLinkToken",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "address",
				"name": "newOwner",
				"type": "address"
			}
		],
		"name": "transferOwnership",
		"outputs": [],
		"stateMutability": "nonpayable",
		"type": "function"
	},
	{
		"stateMutability": "payable",
		"type": "receive"
	},
	{
		"inputs": [],
		"stateMutability": "nonpayable",
		"type": "constructor"
	},
	{
		"inputs": [],
		"name": "averagePrice",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "getResponsesCount",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "linkToken",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"name": "oracles",
		"outputs": [
			{
				"internalType": "address",
				"name": "oracle",
				"type": "address"
			},
			{
				"internalType": "bytes32",
				"name": "jobId",
				"type": "bytes32"
			},
			{
				"internalType": "bool",
				"name": "isActive",
				"type": "bool"
			},
			{
				"internalType": "uint256",
				"name": "price",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "owner",
		"outputs": [
			{
				"internalType": "address",
				"name": "",
				"type": "address"
			}
		],
		"stateMutability": "view",
		"type": "function"
	},
	{
		"inputs": [],
		"name": "responsesCount",
		"outputs": [
			{
				"internalType": "uint256",
				"name": "",
				"type": "uint256"
			}
		],
		"stateMutability": "view",
		"type": "function"
	}
]
"""

ChainlinkUserTemplate['user_contract_bin']="""\
6080604052600160045534801561001557600080fd5b5033600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff16036100895760006040517f1e4fbdf700000000000000000000000000000000000000000000000000000000815260040161008091906101a5565b60405180910390fd5b6100988161009e60201b60201c565b506101c0565b6000600660009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905081600660006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055508173ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff167f8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e060405160405180910390a35050565b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b600061018f82610164565b9050919050565b61019f81610184565b82525050565b60006020820190506101ba6000830184610196565b92915050565b612791806101cf6000396000f3fe6080604052600436106100e15760003560e01c80637ca9a7901161007f5780639c24ea40116100595780639c24ea4014610294578063a0352ea3146102bd578063e67f54f8146102e8578063f2fde38b14610311576100e8565b80637ca9a790146102155780637f525a8a146102405780638da5cb5b14610269576100e8565b806357970e93116100bb57806357970e931461016a5780635b69a7d8146101955780636af6e5ff146101d5578063715018a6146101fe576100e8565b8063071a56df146100ed57806322d277b2146101165780634357855e14610141576100e8565b366100e857005b600080fd5b3480156100f957600080fd5b50610114600480360381019061010f9190611b0a565b61033a565b005b34801561012257600080fd5b5061012b610437565b6040516101389190611b7f565b60405180910390f35b34801561014d57600080fd5b5061016860048036038101906101639190611bfc565b61043d565b005b34801561017657600080fd5b5061017f6107c5565b60405161018c9190611c4b565b60405180910390f35b3480156101a157600080fd5b506101bc60048036038101906101b79190611c66565b6107eb565b6040516101cc9493929190611cbd565b60405180910390f35b3480156101e157600080fd5b506101fc60048036038101906101f79190611dca565b610858565b005b34801561020a57600080fd5b50610213610989565b005b34801561022157600080fd5b5061022a61099d565b6040516102379190611b7f565b60405180910390f35b34801561024c57600080fd5b5061026760048036038101906102629190611e42565b6109a7565b005b34801561027557600080fd5b5061027e610ba6565b60405161028b9190611c4b565b60405180910390f35b3480156102a057600080fd5b506102bb60048036038101906102b69190611eba565b610bd0565b005b3480156102c957600080fd5b506102d2610c25565b6040516102df9190611b7f565b60405180910390f35b3480156102f457600080fd5b5061030f600480360381019061030a9190611c66565b610c2b565b005b34801561031d57600080fd5b5061033860048036038101906103339190611eba565b610cbb565b005b610342610d41565b600061034d82610dc8565b9050600a60405180608001604052808573ffffffffffffffffffffffffffffffffffffffff1681526020018381526020016001151581526020016000815250908060018154018082558091505060019003906000526020600020906004020160009091909190915060008201518160000160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055506020820151816001015560408201518160020160006101000a81548160ff021916908315150217905550606082015181600301555050505050565b60085481565b816005600082815260200190815260200160002060009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff163373ffffffffffffffffffffffffffffffffffffffff16146104df576040517f08c379a00000000000000000000000000000000000000000000000000000000081526004016104d690611f6a565b60405180910390fd5b6005600082815260200190815260200160002060006101000a81549073ffffffffffffffffffffffffffffffffffffffff0219169055807f7cc135e0cebb02c3480ae5d74d377283180a2601f8f644edf7987b009316c63a60405160405180910390a2600b600084815260200190815260200160002060009054906101000a900460ff166105a2576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161059990611fd6565b60405180910390fd5b6000600b600085815260200190815260200160002060006101000a81548160ff02191690831515021790555060008060005b600a805490508110156106d1573373ffffffffffffffffffffffffffffffffffffffff16600a828154811061060c5761060b611ff6565b5b906000526020600020906004020160000160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff161480156106905750600a81815481106106705761066f611ff6565b5b906000526020600020906004020160020160009054906101000a900460ff165b156106c45784600a82815481106106aa576106a9611ff6565b5b9060005260206000209060040201600301819055506106d1565b80806001019150506105d4565b5060005b600a8054905081101561079a57600a81815481106106f6576106f5611ff6565b5b906000526020600020906004020160020160009054906101000a900460ff16801561074657506000600a828154811061073257610731611ff6565b5b906000526020600020906004020160030154115b1561078d57600a818154811061075f5761075e611ff6565b5b9060005260206000209060040201600301548361077c9190612054565b9250818061078990612088565b9250505b80806001019150506106d5565b5060008111156107be5780826107b091906120ff565b600781905550806008819055505b5050505050565b600960009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1681565b600a81815481106107fb57600080fd5b90600052602060002090600402016000915090508060000160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16908060010154908060020160009054906101000a900460ff16908060030154905084565b610860610d41565b600061086b82610dc8565b905060005b835181101561098357600a604051806080016040528086848151811061089957610898611ff6565b5b602002602001015173ffffffffffffffffffffffffffffffffffffffff1681526020018481526020016001151581526020016000815250908060018154018082558091505060019003906000526020600020906004020160009091909190915060008201518160000160006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055506020820151816001015560408201518160020160006101000a81548160ff0219169083151502179055506060820151816003015550508080600101915050610870565b50505050565b610991610d41565b61099b6000610df1565b565b6000600854905090565b60005b600a80549050811015610ba157600a81815481106109cb576109ca611ff6565b5b906000526020600020906004020160020160009054906101000a900460ff1615610b94576000610a28600a8381548110610a0857610a07611ff6565b5b90600052602060002090600402016001015430634357855e60e01b610eb7565b9050610a746040518060400160405280600381526020017f67657400000000000000000000000000000000000000000000000000000000008152508583610ee89092919063ffffffff16565b610abe6040518060400160405280600481526020017f70617468000000000000000000000000000000000000000000000000000000008152508483610ee89092919063ffffffff16565b610b096040518060400160405280600881526020017f6d756c7469706c79000000000000000000000000000000000000000000000000815250606483610f1b9092919063ffffffff16565b6000610b63600a8481548110610b2257610b21611ff6565b5b906000526020600020906004020160000160009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16836712dfb0cb5e880000610f4e565b90506001600b600083815260200190815260200160002060006101000a81548160ff02191690831515021790555050505b80806001019150506109aa565b505050565b6000600660009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905090565b610bd8610d41565b610be18161101a565b80600960006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555050565b60075481565b610c33610d41565b600a805490508110610c7a576040517f08c379a0000000000000000000000000000000000000000000000000000000008152600401610c719061217c565b60405180910390fd5b6000600a8281548110610c9057610c8f611ff6565b5b906000526020600020906004020160020160006101000a81548160ff02191690831515021790555050565b610cc3610d41565b600073ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff1603610d355760006040517f1e4fbdf7000000000000000000000000000000000000000000000000000000008152600401610d2c9190611c4b565b60405180910390fd5b610d3e81610df1565b50565b610d4961105e565b73ffffffffffffffffffffffffffffffffffffffff16610d67610ba6565b73ffffffffffffffffffffffffffffffffffffffff1614610dc657610d8a61105e565b6040517f118cdaa7000000000000000000000000000000000000000000000000000000008152600401610dbd9190611c4b565b60405180910390fd5b565b6000808290506000815103610de3576000801b915050610dec565b60208301519150505b919050565b6000600660009054906101000a900473ffffffffffffffffffffffffffffffffffffffff16905081600660006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff1602179055508173ffffffffffffffffffffffffffffffffffffffff168173ffffffffffffffffffffffffffffffffffffffff167f8be0079c531659141344cd1fd0a4f28419497f9722a3daafe3b4186f6b6457e060405160405180910390a35050565b610ebf6118cb565b610ec76118cb565b610ede85858584611066909392919063ffffffff16565b9150509392505050565b610eff82846080015161111690919063ffffffff16565b610f1681846080015161111690919063ffffffff16565b505050565b610f3282846080015161111690919063ffffffff16565b610f4981846080015161113b90919063ffffffff16565b505050565b6000806004549050600181610f639190612054565b6004819055506000634042994660e01b60008087600001513089604001518760018c6080015160000151604051602401610fa4989796959493929190612256565b604051602081830303815290604052907bffffffffffffffffffffffffffffffffffffffffffffffffffffffff19166020820180517bffffffffffffffffffffffffffffffffffffffffffffffffffffffff8381831617835250505050905061100f868386846111e8565b925050509392505050565b80600260006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff16021790555050565b600033905090565b61106e6118cb565b61107e856080015161010061137d565b508385600001818152505082856020019073ffffffffffffffffffffffffffffffffffffffff16908173ffffffffffffffffffffffffffffffffffffffff16815250508185604001907bffffffffffffffffffffffffffffffffffffffffffffffffffffffff191690817bffffffffffffffffffffffffffffffffffffffffffffffffffffffff191681525050849050949350505050565b61112382600383516113e7565b611136818361156c90919063ffffffff16565b505050565b7fffffffffffffffffffffffffffffffffffffffffffffffff00000000000000008112156111725761116d828261158e565b6111e4565b67ffffffffffffffff8113156111915761118c8282611605565b6111e3565b600081126111aa576111a5826000836113e7565b6111e2565b6111e1826001837fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff6111dc91906122e5565b6113e7565b5b5b5b5050565b600030846040516020016111fd9291906123e1565b604051602081830303815290604052805190602001209050846005600083815260200190815260200160002060006101000a81548173ffffffffffffffffffffffffffffffffffffffff021916908373ffffffffffffffffffffffffffffffffffffffff160217905550807fb5e6e01e79f91267dc17b4e6314d5d4d03593d2ceee0fbb452b750bd70ea5af960405160405180910390a2600260009054906101000a900473ffffffffffffffffffffffffffffffffffffffff1673ffffffffffffffffffffffffffffffffffffffff16634000aea08685856040518463ffffffff1660e01b81526004016112f39392919061240d565b6020604051808303816000875af1158015611312573d6000803e3d6000fd5b505050506040513d601f19601f820116820180604052508101906113369190612477565b611375576040517f08c379a000000000000000000000000000000000000000000000000000000000815260040161136c90612516565b60405180910390fd5b949350505050565b611385611938565b60006020836113949190612536565b146113c0576020826113a69190612536565b60206113b29190612567565b826113bd9190612054565b91505b81836020018181525050604051808452600081528281016020016040525082905092915050565b60178167ffffffffffffffff161161141e576114188160058460ff16901b60ff16178461165190919063ffffffff16565b50611567565b60ff8167ffffffffffffffff16116114745761144d601860058460ff16901b178461165190919063ffffffff16565b5061146e8167ffffffffffffffff166001856116719092919063ffffffff16565b50611566565b61ffff8167ffffffffffffffff16116114cb576114a4601960058460ff16901b178461165190919063ffffffff16565b506114c58167ffffffffffffffff166002856116719092919063ffffffff16565b50611565565b63ffffffff8167ffffffffffffffff1611611524576114fd601a60058460ff16901b178461165190919063ffffffff16565b5061151e8167ffffffffffffffff166004856116719092919063ffffffff16565b50611564565b611541601b60058460ff16901b178461165190919063ffffffff16565b506115628167ffffffffffffffff166008856116719092919063ffffffff16565b505b5b5b5b505050565b611574611938565b61158683846000015151848551611693565b905092915050565b6115ac60036005600660ff16901b178361165190919063ffffffff16565b5061160182827fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff6115dd91906122e5565b6040516020016115ed9190611b7f565b604051602081830303815290604052611782565b5050565b61162360026005600660ff16901b178361165190919063ffffffff16565b5061164d82826040516020016116399190611b7f565b604051602081830303815290604052611782565b5050565b611659611938565b61166983846000015151846117a7565b905092915050565b611679611938565b61168a8485600001515185856117fd565b90509392505050565b61169b611938565b82518211156116a957600080fd5b846020015182856116ba9190612054565b11156116ef576116ee8560026116df886020015188876116da9190612054565b61188b565b6116e9919061259b565b6118a7565b5b60008086518051876020830101935080888701111561170e5787860182525b60208701925050505b6020841061175557805182526020826117309190612054565b915060208161173f9190612054565b905060208461174e9190612567565b9350611717565b60006001856020036101000a03905080198251168184511681811785525050508692505050949350505050565b61178f82600283516113e7565b6117a2818361156c90919063ffffffff16565b505050565b6117af611938565b836020015183106117d5576117d484600286602001516117cf919061259b565b6118a7565b5b835180516020858301018481538186036117f0576001820183525b5050508390509392505050565b611805611938565b846020015184836118169190612054565b111561183e5761183d856002868561182e9190612054565b611838919061259b565b6118a7565b5b60006001836101006118509190612710565b61185a9190612567565b9050855183868201018583198251161781528151858801111561187d5784870182525b505085915050949350505050565b60008183111561189d578290506118a1565b8190505b92915050565b6000826000015190506118ba838361137d565b506118c5838261156c565b50505050565b6040518060a0016040528060008019168152602001600073ffffffffffffffffffffffffffffffffffffffff16815260200160007bffffffffffffffffffffffffffffffffffffffffffffffffffffffff1916815260200160008152602001611932611938565b81525090565b604051806040016040528060608152602001600081525090565b6000604051905090565b600080fd5b600080fd5b600073ffffffffffffffffffffffffffffffffffffffff82169050919050565b600061199182611966565b9050919050565b6119a181611986565b81146119ac57600080fd5b50565b6000813590506119be81611998565b92915050565b600080fd5b600080fd5b6000601f19601f8301169050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052604160045260246000fd5b611a17826119ce565b810181811067ffffffffffffffff82111715611a3657611a356119df565b5b80604052505050565b6000611a49611952565b9050611a558282611a0e565b919050565b600067ffffffffffffffff821115611a7557611a746119df565b5b611a7e826119ce565b9050602081019050919050565b82818337600083830152505050565b6000611aad611aa884611a5a565b611a3f565b905082815260208101848484011115611ac957611ac86119c9565b5b611ad4848285611a8b565b509392505050565b600082601f830112611af157611af06119c4565b5b8135611b01848260208601611a9a565b91505092915050565b60008060408385031215611b2157611b2061195c565b5b6000611b2f858286016119af565b925050602083013567ffffffffffffffff811115611b5057611b4f611961565b5b611b5c85828601611adc565b9150509250929050565b6000819050919050565b611b7981611b66565b82525050565b6000602082019050611b946000830184611b70565b92915050565b6000819050919050565b611bad81611b9a565b8114611bb857600080fd5b50565b600081359050611bca81611ba4565b92915050565b611bd981611b66565b8114611be457600080fd5b50565b600081359050611bf681611bd0565b92915050565b60008060408385031215611c1357611c1261195c565b5b6000611c2185828601611bbb565b9250506020611c3285828601611be7565b9150509250929050565b611c4581611986565b82525050565b6000602082019050611c606000830184611c3c565b92915050565b600060208284031215611c7c57611c7b61195c565b5b6000611c8a84828501611be7565b91505092915050565b611c9c81611b9a565b82525050565b60008115159050919050565b611cb781611ca2565b82525050565b6000608082019050611cd26000830187611c3c565b611cdf6020830186611c93565b611cec6040830185611cae565b611cf96060830184611b70565b95945050505050565b600067ffffffffffffffff821115611d1d57611d1c6119df565b5b602082029050602081019050919050565b600080fd5b6000611d46611d4184611d02565b611a3f565b90508083825260208201905060208402830185811115611d6957611d68611d2e565b5b835b81811015611d925780611d7e88826119af565b845260208401935050602081019050611d6b565b5050509392505050565b600082601f830112611db157611db06119c4565b5b8135611dc1848260208601611d33565b91505092915050565b60008060408385031215611de157611de061195c565b5b600083013567ffffffffffffffff811115611dff57611dfe611961565b5b611e0b85828601611d9c565b925050602083013567ffffffffffffffff811115611e2c57611e2b611961565b5b611e3885828601611adc565b9150509250929050565b60008060408385031215611e5957611e5861195c565b5b600083013567ffffffffffffffff811115611e7757611e76611961565b5b611e8385828601611adc565b925050602083013567ffffffffffffffff811115611ea457611ea3611961565b5b611eb085828601611adc565b9150509250929050565b600060208284031215611ed057611ecf61195c565b5b6000611ede848285016119af565b91505092915050565b600082825260208201905092915050565b7f536f75726365206d75737420626520746865206f7261636c65206f662074686560008201527f2072657175657374000000000000000000000000000000000000000000000000602082015250565b6000611f54602883611ee7565b9150611f5f82611ef8565b604082019050919050565b60006020820190508181036000830152611f8381611f47565b9050919050565b7f52657175657374206973206e6f742076616c6964000000000000000000000000600082015250565b6000611fc0601483611ee7565b9150611fcb82611f8a565b602082019050919050565b60006020820190508181036000830152611fef81611fb3565b9050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052603260045260246000fd5b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601160045260246000fd5b600061205f82611b66565b915061206a83611b66565b925082820190508082111561208257612081612025565b5b92915050565b600061209382611b66565b91507fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff82036120c5576120c4612025565b5b600182019050919050565b7f4e487b7100000000000000000000000000000000000000000000000000000000600052601260045260246000fd5b600061210a82611b66565b915061211583611b66565b925082612125576121246120d0565b5b828204905092915050565b7f496e76616c6964206f7261636c6520696e646578000000000000000000000000600082015250565b6000612166601483611ee7565b915061217182612130565b602082019050919050565b6000602082019050818103600083015261219581612159565b9050919050565b60007fffffffff0000000000000000000000000000000000000000000000000000000082169050919050565b6121d18161219c565b82525050565b600081519050919050565b600082825260208201905092915050565b60005b838110156122115780820151818401526020810190506121f6565b60008484015250505050565b6000612228826121d7565b61223281856121e2565b93506122428185602086016121f3565b61224b816119ce565b840191505092915050565b60006101008201905061226c600083018b611c3c565b612279602083018a611b70565b6122866040830189611c93565b6122936060830188611c3c565b6122a060808301876121c8565b6122ad60a0830186611b70565b6122ba60c0830185611b70565b81810360e08301526122cc818461221d565b90509998505050505050505050565b6000819050919050565b60006122f0826122db565b91506122fb836122db565b925082820390508181126000841216828213600085121516171561232257612321612025565b5b92915050565b6000819050919050565b600061234d61234861234384611966565b612328565b611966565b9050919050565b600061235f82612332565b9050919050565b600061237182612354565b9050919050565b60008160601b9050919050565b600061239082612378565b9050919050565b60006123a282612385565b9050919050565b6123ba6123b582612366565b612397565b82525050565b6000819050919050565b6123db6123d682611b66565b6123c0565b82525050565b60006123ed82856123a9565b6014820191506123fd82846123ca565b6020820191508190509392505050565b60006060820190506124226000830186611c3c565b61242f6020830185611b70565b8181036040830152612441818461221d565b9050949350505050565b61245481611ca2565b811461245f57600080fd5b50565b6000815190506124718161244b565b92915050565b60006020828403121561248d5761248c61195c565b5b600061249b84828501612462565b91505092915050565b7f756e61626c6520746f207472616e73666572416e6443616c6c20746f206f726160008201527f636c650000000000000000000000000000000000000000000000000000000000602082015250565b6000612500602383611ee7565b915061250b826124a4565b604082019050919050565b6000602082019050818103600083015261252f816124f3565b9050919050565b600061254182611b66565b915061254c83611b66565b92508261255c5761255b6120d0565b5b828206905092915050565b600061257282611b66565b915061257d83611b66565b925082820390508181111561259557612594612025565b5b92915050565b60006125a682611b66565b91506125b183611b66565b92508282026125bf81611b66565b915082820484148315176125d6576125d5612025565b5b5092915050565b60008160011c9050919050565b6000808291508390505b6001851115612634578086048111156126105761260f612025565b5b600185161561261f5780820291505b808102905061262d856125dd565b94506125f4565b94509492505050565b60008261264d5760019050612709565b8161265b5760009050612709565b8160018114612671576002811461267b576126aa565b6001915050612709565b60ff84111561268d5761268c612025565b5b8360020a9150848211156126a4576126a3612025565b5b50612709565b5060208310610133831016604e8410600b84101617156126df5782820a9050838111156126da576126d9612025565b5b612709565b6126ec84848460016125ea565b9250905081840481111561270357612702612025565b5b81810290505b9392505050565b600061271b82611b66565b915061272683611b66565b92506127537fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff848461263d565b90509291505056fea2646970667358221220a39325a8492a574132127f74790dd5fb8c51e607ab27282d771efedd86c3611c64736f6c63430008190033
"""