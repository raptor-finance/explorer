import requests, rlp, flask, json, time
from rlp.sedes import Binary, big_endian_int, binary
from flask_cors import CORS
from dataclasses import asdict, dataclass
from typing import Optional
from eth_utils import keccak
from web3 import Web3, HTTPProvider
from web3.auto import w3

ROUTERADDRESS = "0x397D194abF71094247057642003EaCd463b7931f" # address of RaptorSwap router
FACTORYADDRESS = "0xB8F7aAdaC20Cd74237dDAB7AC7ead317BF049Fa3" # address of RaptorSwap factory
WRPTRADDRESS = "0xeF7cADE66695f4cD8a535f7916fBF659936818C4" # address of WRPTR

# ABIs to interact with smart contracts
ERC20ABI = """[{"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_from","type":"address"},{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transferFrom","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"name":"_to","type":"address"},{"name":"_value","type":"uint256"}],"name":"transfer","outputs":[{"name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"payable":true,"stateMutability":"payable","type":"fallback"},{"anonymous":false,"inputs":[{"indexed":true,"name":"owner","type":"address"},{"indexed":true,"name":"spender","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"name":"from","type":"address"},{"indexed":true,"name":"to","type":"address"},{"indexed":false,"name":"value","type":"uint256"}],"name":"Transfer","type":"event"}]"""
ROUTERABI = """[{"inputs":[{"internalType":"address","name":"_factory","type":"address"},{"internalType":"address","name":"_WETH","type":"address"}],"stateMutability":"nonpayable","type":"constructor"},{"inputs":[],"name":"WETH","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"amountADesired","type":"uint256"},{"internalType":"uint256","name":"amountBDesired","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"amountTokenDesired","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"addLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"},{"internalType":"uint256","name":"liquidity","type":"uint256"}],"stateMutability":"payable","type":"function"},{"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"reserveIn","type":"uint256"},{"internalType":"uint256","name":"reserveOut","type":"uint256"}],"name":"getAmountIn","outputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"reserveIn","type":"uint256"},{"internalType":"uint256","name":"reserveOut","type":"uint256"}],"name":"getAmountOut","outputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsIn","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"}],"name":"getAmountsOut","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"view","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"reserveA","type":"uint256"},{"internalType":"uint256","name":"reserveB","type":"uint256"}],"name":"quote","outputs":[{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"pure","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidity","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidityETH","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"removeLiquidityETHSupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityETHWithPermit","outputs":[{"internalType":"uint256","name":"amountToken","type":"uint256"},{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"token","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountTokenMin","type":"uint256"},{"internalType":"uint256","name":"amountETHMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityETHWithPermitSupportingFeeOnTransferTokens","outputs":[{"internalType":"uint256","name":"amountETH","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"},{"internalType":"uint256","name":"liquidity","type":"uint256"},{"internalType":"uint256","name":"amountAMin","type":"uint256"},{"internalType":"uint256","name":"amountBMin","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"bool","name":"approveMax","type":"bool"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"removeLiquidityWithPermit","outputs":[{"internalType":"uint256","name":"amountA","type":"uint256"},{"internalType":"uint256","name":"amountB","type":"uint256"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapETHForExactTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactETHForTokensSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"payable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForETHSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountIn","type":"uint256"},{"internalType":"uint256","name":"amountOutMin","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapExactTokensForTokensSupportingFeeOnTransferTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactETH","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"inputs":[{"internalType":"uint256","name":"amountOut","type":"uint256"},{"internalType":"uint256","name":"amountInMax","type":"uint256"},{"internalType":"address[]","name":"path","type":"address[]"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"deadline","type":"uint256"}],"name":"swapTokensForExactTokens","outputs":[{"internalType":"uint256[]","name":"amounts","type":"uint256[]"}],"stateMutability":"nonpayable","type":"function"},{"stateMutability":"payable","type":"receive"}]"""
FACTORYABI = """[{"inputs":[{"internalType":"address","name":"_feeToSetter","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"token0","type":"address"},{"indexed":true,"internalType":"address","name":"token1","type":"address"},{"indexed":false,"internalType":"address","name":"pair","type":"address"},{"indexed":false,"internalType":"uint256","name":"","type":"uint256"}],"name":"PairCreated","type":"event"},{"constant":true,"inputs":[],"name":"INIT_CODE_PAIR_HASH","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"uint256","name":"","type":"uint256"}],"name":"allPairs","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"allPairsLength","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"tokenA","type":"address"},{"internalType":"address","name":"tokenB","type":"address"}],"name":"createPair","outputs":[{"internalType":"address","name":"pair","type":"address"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"feeTo","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"feeToSetter","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"getPair","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"_feeTo","type":"address"}],"name":"setFeeTo","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"_feeToSetter","type":"address"}],"name":"setFeeToSetter","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"}]"""
PAIRABI = """[{"inputs":[],"payable":false,"stateMutability":"nonpayable","type":"constructor"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":true,"internalType":"address","name":"spender","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Approval","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"},{"indexed":true,"internalType":"address","name":"to","type":"address"}],"name":"Burn","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1","type":"uint256"}],"name":"Mint","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"sender","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount0In","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1In","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount0Out","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"amount1Out","type":"uint256"},{"indexed":true,"internalType":"address","name":"to","type":"address"}],"name":"Swap","type":"event"},{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint112","name":"reserve0","type":"uint112"},{"indexed":false,"internalType":"uint112","name":"reserve1","type":"uint112"}],"name":"Sync","type":"event"},{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"from","type":"address"},{"indexed":true,"internalType":"address","name":"to","type":"address"},{"indexed":false,"internalType":"uint256","name":"value","type":"uint256"}],"name":"Transfer","type":"event"},{"constant":true,"inputs":[],"name":"DOMAIN_SEPARATOR","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"MINIMUM_LIQUIDITY","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"PERMIT_TYPEHASH","outputs":[{"internalType":"bytes32","name":"","type":"bytes32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"},{"internalType":"address","name":"","type":"address"}],"name":"allowance","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"approve","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"burn","outputs":[{"internalType":"uint256","name":"amount0","type":"uint256"},{"internalType":"uint256","name":"amount1","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"decimals","outputs":[{"internalType":"uint8","name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"factory","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"getReserves","outputs":[{"internalType":"uint112","name":"_reserve0","type":"uint112"},{"internalType":"uint112","name":"_reserve1","type":"uint112"},{"internalType":"uint32","name":"_blockTimestampLast","type":"uint32"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"_token0","type":"address"},{"internalType":"address","name":"_token1","type":"address"}],"name":"initialize","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"kLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"mint","outputs":[{"internalType":"uint256","name":"liquidity","type":"uint256"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"name","outputs":[{"internalType":"string","name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[{"internalType":"address","name":"","type":"address"}],"name":"nonces","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"owner","type":"address"},{"internalType":"address","name":"spender","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"},{"internalType":"uint256","name":"deadline","type":"uint256"},{"internalType":"uint8","name":"v","type":"uint8"},{"internalType":"bytes32","name":"r","type":"bytes32"},{"internalType":"bytes32","name":"s","type":"bytes32"}],"name":"permit","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"price0CumulativeLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"price1CumulativeLast","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"to","type":"address"}],"name":"skim","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"uint256","name":"amount0Out","type":"uint256"},{"internalType":"uint256","name":"amount1Out","type":"uint256"},{"internalType":"address","name":"to","type":"address"},{"internalType":"bytes","name":"data","type":"bytes"}],"name":"swap","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[],"name":"sync","outputs":[],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":true,"inputs":[],"name":"token0","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"token1","outputs":[{"internalType":"address","name":"","type":"address"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":true,"inputs":[],"name":"totalSupply","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transfer","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},{"constant":false,"inputs":[{"internalType":"address","name":"from","type":"address"},{"internalType":"address","name":"to","type":"address"},{"internalType":"uint256","name":"value","type":"uint256"}],"name":"transferFrom","outputs":[{"internalType":"bool","name":"","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"}]"""

# token icons
TOKENICONURLS = {
    WRPTRADDRESS: "https://raptorchain.io/images/logo.png",
    "0x9ffE5c6EB6A8BFFF1a9a9DC07406629616c19d32": "https://bsc.duinocoin.com/ducowhite.png"
    
}

class RaptorChainPuller(object):
    class Transaction(object):
        class ETHTransactionDecoder(object):
            class Transaction(rlp.Serializable):
                fields = [
                    ("nonce", big_endian_int),
                    ("gas_price", big_endian_int),
                    ("gas", big_endian_int),
                    ("to", Binary.fixed_length(20, allow_empty=True)),
                    ("value", big_endian_int),
                    ("data", binary),
                    ("v", big_endian_int),
                    ("r", big_endian_int),
                    ("s", big_endian_int),
                ]


            @dataclass
            class DecodedTx:
                hash_tx: str
                from_: str
                to: Optional[str]
                nonce: int
                gas: int
                gas_price: int
                value: int
                data: str
                chain_id: int
                r: str
                s: str
                v: int


            def decode_raw_tx(self, raw_tx: str):
                bytesTx = bytes.fromhex(raw_tx.replace("0x", ""))
                tx = rlp.decode(bytesTx, self.Transaction)
                hash_tx = w3.toHex(keccak(bytesTx))
                from_ = w3.eth.account.recover_transaction(raw_tx)
                to = w3.toChecksumAddress(tx.to) if tx.to else None
                data = w3.toHex(tx.data)
                r = hex(tx.r)
                s = hex(tx.s)
                chain_id = (tx.v - 35) // 2 if tx.v % 2 else (tx.v - 36) // 2
                return self.DecodedTx(hash_tx, from_, to, tx.nonce, tx.gas, tx.gas_price, tx.value, data, chain_id, r, s, tx.v)
            
    
    
    
        def __init__(self, tx):
            txData = json.loads(tx["data"])
            self.contractDeployment = False
            self.txtype = (txData.get("type") or 0)
            self.data = b""
            self.sender = "0x0000000000000000000000000000000000000000"
            self.recipient = "0x0000000000000000000000000000000000000000"
            self.messages = []
            self.affectedAccounts = []
            self.typeName = ""
            self.value = 0
            if (self.txtype == 0): # legacy transfer
                self.sender = w3.toChecksumAddress(txData.get("from"))
                self.recipient = w3.toChecksumAddress(txData.get("to"))
                self.value = max(int(txData.get("tokens")), 0)
                self.affectedAccounts = [self.sender, self.recipient]
                self.gasprice = 0
                self.gasLimit = 69000
                self.fee = self.gasprice*self.gasLimit
                try:
                    self.data = bytes.fromhex(txData.get("callData", "").replace("0x", ""))
                except:
                    self.data = b""
                self.typeName = "legacy"
            if (self.txtype == 1): # block mining/staking tx
                self.fee = 0
                self.sender = w3.toChecksumAddress(txData.get("from"))
                self.blockData = txData.get("blockData")
                self.recipient = "0x0000000000000000000000000000000000000000"
                self.value = 0
                self.affectedAccounts = [self.sender]
                self.gasprice = 0
                self.typeName = "block production"
            elif self.txtype == 2: # metamask transaction
                decoder = self.ETHTransactionDecoder()
                ethDecoded = decoder.decode_raw_tx(txData.get("rawTx"))
                self.gasprice = ethDecoded.gas_price
                self.gasLimit = ethDecoded.gas
                self.fee = ethDecoded.gas_price*21000
                self.sender = ethDecoded.from_
                self.recipient = ethDecoded.to
                self.value = int(ethDecoded.value)
                self.nonce = ethDecoded.nonce
                self.ethData = ethDecoded.data
                self.ethTxid = ethDecoded.hash_tx
                self.v = ethDecoded.v
                self.r = ethDecoded.r
                self.s = ethDecoded.s
                self.data = bytes.fromhex(ethDecoded.data.replace("0x", ""))
                if not self.recipient:
                    self.recipient = w3.toChecksumAddress(w3.keccak(rlp.encode([bytes.fromhex(self.sender.replace("0x", "")), int(self.nonce)]))[12:])
                    self.contractDeployment = True
                self.typeName = "web3/metamask transaction"
            elif self.txtype == 3: # deposits checking trigger
                self.fee = 0
                self.l2hash = txData["l2hash"]
                self.value = 0
                self.sender = w3.toChecksumAddress(txData.get("from"))
                self.recipient = "0x0000000000000000000000000000000000000000"
                self.affectedAccounts = [self.sender]
            elif self.txtype == 4: # MN create
                self.fee = 0
                self.value = 1000000000000000000000000
                self.sender = w3.toChecksumAddress(txData.get("from"))
                self.recipient = w3.toChecksumAddress(txData.get("to"))
                self.affectedAccounts = [self.sender, self.recipient]
                self.typeName = "masternode registration"
            elif self.txtype == 5: # MN destroy
                self.fee = 0
                self.value = 0
                self.sender = w3.toChecksumAddress(txData.get("from"))
                self.recipient = w3.toChecksumAddress(txData.get("to"))
                self.affectedAccounts = [self.sender, self.recipient]
                self.typeName = "masternode deletion"
            elif self.txtype == 6:
                self.fee = 0
                self.sender = "0x0000000000000000000000000000000000000000"
                self.recipient = "0x0000000000000000000000000000000000000000"
                self.value = 0
                self.typeName = "system transaction"
            
            self.epoch = txData.get("epoch")
            self.bio = txData.get("bio")
            self.parent = txData.get("parent")
            self.message = txData.get("message")
            self.txid = w3.soliditySha3(["string"], [tx["data"]]).hex()
            self.indexToCheck = txData.get("indexToCheck", 0)
            
            
            # self.PoW = ""
            # self.endTimeStamp = 0
            
        def formatAddress(self, _addr):
            if (type(_addr) == int):
                hexfmt = hex(_addr)[2:]
                return w3.toChecksumAddress("0x" + ("0" * (40-len(hexfmt))) + hexfmt)
            return w3.toChecksumAddress(_addr)
            
        def markAccountAffected(self, addr):
            _addr = self.formatAddress(addr)
            if not _addr in self.affectedAccounts:
                self.affectedAccounts.append(_addr)
                
    class Account(object):
        def __init__(self, infoDict):
            self.balance = infoDict.get("balance", 0)
            self.storage = infoDict.get("storage", {})
            self.transactions = infoDict.get("transactions", [])
            self.tempStorage = infoDict.get("storage", {})
            self.nonce = infoDict.get("nonce", 0)
            self.code = bytes.fromhex(infoDict.get("code", "").replace("0x", ""))
    
    class Stats(object):
        def __init__(self, infoDict):
            coinInfo = infoDict.get("coin", {})
            chainInfo = infoDict.get("chain", {})
            self.lastBlock = chainInfo.get("lastBlockHash", "0x0000000000000000000000000000000000000000000000000000000000000000")
            self.chainLength = chainInfo.get("length", 0)
            self.transactions = coinInfo.get("transactions", 0)
            self.holders = coinInfo.get("holders", 0)
            self.supply = coinInfo.get("supply", 0)
            self.blocks = list(filter(self.isPositive, list(range(self.chainLength-10, self.chainLength))))
            
        def isPositive(self, number):
            return number >= 0
    
    class Block(object):
        def __init__(self, infoDict):
            miningData = infoDict.get("miningData", {})
            self.miner = miningData.get("miner", "0x0000000000000000000000000000000000000000")
            self.proof = miningData.get("proof", "0x0000000000000000000000000000000000000000000000000000000000000000")
            self.parent = infoDict.get("parent", "0x0000000000000000000000000000000000000000000000000000000000000000")
            self.messages = infoDict.get("decodedMessages", [])
            self.height = infoDict.get("height", 0)
            self.timestamp = infoDict.get("timestamp", 0)
            self.txsRoot = infoDict.get("txsRoot", "0x0000000000000000000000000000000000000000000000000000000000000000")
            self.transactions = list(filter(bool, infoDict.get("transactions", {})))
    
    class Token(object):
        def __init__(self, contractInstance):
            self.contract = contractInstance
            self.name = contractInstance.functions.name().call()
            self.symbol = contractInstance.functions.symbol().call()
            self.symbol = contractInstance.functions.symbol().call()
            self.decimals = contractInstance.functions.decimals().call()
            self.rawSupply = contractInstance.functions.totalSupply().call()
            self.totalSupply = self.rawSupply / (10**self.decimals)
    
    class DefiStats(object):
        class RaptorSwap(object):
            class Pair(object):
                def __init__(self, _web3, _address):
                    self.web3 = _web3
                    self.contract = self.web3.eth.contract(address=w3.toChecksumAddress(_address), abi=PAIRABI)
                    
                    self.token0 = self.contract.functions.token0().call()
                    self.token1 = self.contract.functions.token1().call()
                    
                    self.token0contract = self.web3.eth.contract(address=w3.toChecksumAddress(self.token0), abi=ERC20ABI)
                    self.token1contract = self.web3.eth.contract(address=w3.toChecksumAddress(self.token1), abi=ERC20ABI)
                    
                    self.ticker0 = self.token0contract.functions.symbol().call()
                    self.ticker1 = self.token1contract.functions.symbol().call()
                    
                    self.decimals0 = self.token0contract.functions.decimals().call()
                    self.decimals1 = self.token1contract.functions.decimals().call()
                    
                    self.ticker0 = "RPTR" if (self.token0 == WRPTRADDRESS) else self.ticker0
                    self.ticker1 = "RPTR" if (self.token1 == WRPTRADDRESS) else self.ticker1
                    
                    
                    # filled by refresh
                    self.reserve0 = 0
                    self.reserve1 = 0
                    self.reserve0formatted = 0.0
                    self.reserve1formatted = 0.0
                    
                    # RPTR in pool
                    self.RPTRTVL = 0
                    
                    self.refresh()
                    
                def refresh(self):
                    (self.reserve0, self.reserve1, kLast) = self.contract.functions.getReserves().call()
                    (self.reserve0formatted, self.reserve1formatted) = ((self.reserve0 / (10**self.decimals0)), (self.reserve1 / (10**self.decimals1)))
                    self.RPTRTVL = ((self.reserve0formatted if (self.token0 == WRPTRADDRESS) else 0) + (self.reserve1formatted if (self.token1 == WRPTRADDRESS) else 0))
            
            def __init__(self, _web3):
                self.web3 = _web3
                self.router = self.web3.eth.contract(address=ROUTERADDRESS, abi=ROUTERABI)
                self.factory = self.web3.eth.contract(address=FACTORYADDRESS, abi=FACTORYABI)
                self.pairs = []
                self.pairsLenghtLast = 0
                self.fetchPairs()
                self.tvl = 0 # RPTR tvl
                
            def fetchPairs(self):
                _l = self.factory.functions.allPairsLength().call()
                self.pairs = [self.Pair(self.web3, self.factory.functions.allPairs(n).call()) for n in range(_l)] # fetches all pairs as objects
                self.pairsLenghtLast = _l
    
            def refresh(self):
                for _pair in self.pairs:
                    _pair.refresh()
                self.tvl = sum([p.RPTRTVL for p in self.pairs])
                
    
        def __init__(self, _web3):
            self.web3 = _web3
            self.raptorswap = self.RaptorSwap(_web3)
            self.price = 0
            self.tvl = 0
            self.refresh()
            
        def refresh(self):
            self.raptorswap.refresh()
            self.price = float(requests.get("https://bsc.api.0x.org/swap/v1/quote?buyToken=BUSD&sellToken=0x44c99ca267c2b2646ceec72e898273085ab87ca5&sellAmount=1000000000000000000").json().get("price"))
            self.tvl = self.raptorswap.tvl
            
    
    def __init__(self, node):
        self.node = node
        self.web3 = Web3(HTTPProvider(f"{node}/web3"))
        self.defi = self.DefiStats(self.web3)
        self.lastRefresh = time.time()
    
    def loadBlock(self, blockid):
        _url = f"{self.node}/chain/block/{blockid}" if ((type(blockid) == int) or (blockid.isnumeric())) else f"{self.node}/chain/blockByHash/{blockid}" # depends if we load it by height or hash
        print(_url)
        _raw = requests.get(_url).json().get("result", {})
        return self.Block(_raw)
        
    
    def loadTransaction(self, txid):
        _raw = requests.get(f"{self.node}/get/transactions/{txid}").json().get("result")
        return (self.Transaction(_raw[0]) if len(_raw) else None)
        
    def loadBatchOfTransactions(self, txids):
        formattedTxids = ",".join(txids)
        _raws = requests.get(f"{self.node}/get/transactions/{formattedTxids}").json().get("result") if len(txids) else []
        return [self.Transaction(_raw) for _raw in _raws]
    
    def loadAccount(self, address):
        _raw = requests.get(f"{self.node}/accounts/accountInfo/{address}").json().get("result")
        return self.Account(_raw)
        
    def loadToken(self, tokenAddr):
        return self.Token(self.web3.eth.contract(address=w3.toChecksumAddress(tokenAddr), abi=ERC20ABI))
        
    def getLastNTxs(self, n):
        _raw = requests.get(f"{self.node}/get/nLastTxs/{n}").json().get("result")
        return [self.Transaction(_rawtx) for _rawtx in _raw]
        
    def loadStats(self):
        _raw = requests.get(f"{self.node}/stats").json().get("result")
        return self.Stats(_raw)
        
    def refresh(self):
        if (time.time() > (self.lastRefresh - 300)): # if last refresh occured less than 5 minutes ago, keep cached value
            return
        self.lastRefresh = time.time()
        self.defi.refresh()
        
class RaptorChainExplorer(object):
    def __init__(self):
#        self.puller = RaptorChainPuller("http://localhost:4242/")
        self.puller = RaptorChainPuller("https://rpc.raptorchain.io")
        self.ticker = "RPTR"
        self.testnet = False
        self.decimals = 18
        self.port = 7000
        self.publicNode = "https://rpc.raptorchain.io/"
        self.burnAddress = "0x000000000000000000000000000000000000dead"

    def formatAmount(self, rawAmount):
        _withoutDecimals = rawAmount / (10**self.decimals)
        if _withoutDecimals >= 1000000:
            return f"{round(_withoutDecimals / 1000000, 3)}M"
        if _withoutDecimals >= 1000:
            return f"{round(_withoutDecimals / 1000, 3)}k"
        return f"{round(_withoutDecimals, 3)}"
    
    def formatTime(self, rawDelay):
        if rawDelay < 60:
            return f"{int(rawDelay)}s"
        elif rawDelay < 3600:
            return f"{int(rawDelay/60)}m"
        elif rawDelay < 86400:
            return f"{int(rawDelay/3600)}h"
        elif rawDelay < 604800:
            return f"{int(rawDelay/86400)}d {int((rawDelay%86400)/3600)}h"
        elif rawDelay < 604800:
            return f"{int(rawDelay/86400)}d {int((rawDelay%86400)/3600)}h"
        return f"{int(rawDelay/604800)} weeks {int((rawDelay%604800)/86400)} days"
    
    def styleSheets(self):
        return """
			body {
                background-color: #303030;
                background: url("https://raptorchain.io/images/bg-main.jpg");
                background-attachment: fixed;
				color: #ffffff;
			}
		
			.cardContainer {
				margin-left: 15px;
				padding-left: 15px;
				padding-right: 5%;
				padding-bottom: 1%;
				background-color: #21b451;
				color: #ffffff;
				padding-top: 20px;
				padding-bottom: 20px;
                border-radius: 50px;
			}
			
			.pageContainer {
				margin-left: auto;
				margin-right: auto;
			}
			
			.networkStats {
                border-radius: 25px;
				background-color: #21b451;
				padding-left: 10px;
				padding-top: 10px;
				padding-bottom: 10px;
				padding-right: 10%;
				float: right;
				
			}
			
			.defiStats {
                border-radius: 25px;
				background-color: #21b451;
				padding-left: 10px;
				padding-top: 10px;
				padding-bottom: 10px;
				float: right;
			}
			
			.cardTitle {
				color: #81C2BD;
			}
            
            .dexPair {
				padding-left: 15px;
				padding-top: 5%;
				padding-right: 5%;
				padding-bottom: 5%;
				background-color: #303030;
                border-radius: 50px;
            }
            
            .searchStuff {
                display: inline-block;
            }
            
            .rptrLogo {
				float: left;
				display: inline-flex;
            }
			
			
			a {
				color: #ffffff;
			}
			
            table {
                padding: 10px;
				background-color: #303030;
                border-radius: 25px;
            }
			
			input {
				background-color: #ffffff;
				color: #000000;
				border-radius: 10px;
			}
			
			button {
				background-color: #4CAF50;
				color: #ffffff;
				border-radius: 10px;
			}
            
            table,
            td {
                # border: 1px solid #333;
            }

            thead,
            tfoot {
                background-color: #333;
                color: #fff;
            }
			
			footer {
				color: #ffffff;
			}
        """


    
    def TransactionCard(self, txid):
        txObject = self.puller.loadTransaction(txid)
        return f"""
            <h3 class="cardTitle">Transaction {txid}</h3>
            <div class="cardContainer" id="transactionCard">
                <div>
                    <div>Sender : <a href="/address/{txObject.sender}">{txObject.sender}</a></div>
                    <div>Recipient : <a href="/address/{txObject.recipient}">{txObject.recipient}</a></div>
                    <div>Value : {txObject.value / (10**18)} {self.ticker}</div>
                    <div>Calldata : 0x{(txObject.data.hex()) if (len(txObject.data) < 64) else (txObject.data.hex()[:64] + "...")}</div>
                    <div>Epoch : <a href="/block/{txObject.epoch}">{txObject.epoch}</a></div>
                    <div>Type : {txObject.txtype} ({txObject.typeName})</div>
                </div>
            </div>
        """

    def BlockCard(self, bkid):
        block = self.puller.loadBlock(bkid)
        return f"""
            <h3 class="cardTitle">{f"Beacon block {block.height}" if block.height else "Genesis Block"}</h3>
            <div class="cardContainer" id="blockCard">
                <div>
                    <div>Miner/staker : <a href="/address/{block.miner}">{block.miner}</a></div>
					<div>Hash : {block.proof}</div>
                    <h4>Transactions</h4>
                        {self.txsMapped(list(reversed(block.transactions)))}
                </div>
            </div>
        """
    
    def refactortable(self, columns):
        lines = [l.copy() for l in ([[]] * len(columns[0]))]
        for columnid in range(len(columns)):
            for lineid in range(len(lines)):
                lines[lineid].append(columns[columnid][lineid])
        print(lines)
        return lines
    
    
    def renderTable(self, lines=[], columns=None, elementid=None):
        if columns:
            lines = self.refactortable(columns)
        fmtLines = []
        for line in lines:
            fmtLines.append("<tr>" + ("".join([f"<td>{v}</td>" for v in line])) + "</tr>")
            
        
            
    
        return f"""<table {f"id={elementid}" if elementid else ""}>
            <tbody>
                {"".join(fmtLines)}
            </tbody>
        </table>"""
        
        
    def txsMapped(self, txids):
        print(txids)
        txs = self.puller.loadBatchOfTransactions(txids)
        mappable = [["Hash", "Value", "Sender", "Recipient"]] + [[f'<a href="/tx/{tx.txid}">{tx.txid[:48]}...</a>', f"{self.formatAmount(tx.value)} {self.ticker}", f"<a href=/address/{tx.sender}>{tx.sender}</a>", f"<a href=/address/{tx.recipient}>{tx.recipient}</a>"] for tx in txs]
        return self.renderTable(lines=mappable)
        # return ("<ul>" + ("".join([f'<li><a href="/tx/{txid}">{txid}</a></li>' for txid in txids])) + "</ul>")
        
    def blocksTable(self, bkids):
        blocks = [["Height", "Hash", "Timestamp", "Miner"]] + [[f'<a href="/block/{bk.height}">{bk.height}</a>', f'<a href="/block/{bk.proof}">{bk.proof}</a>', f"{self.formatTime(time.time() - bk.timestamp)} ago", f'<a href="/address/{bk.miner}">{bk.miner}</a>'] for bk in [self.puller.loadBlock(bkid) for bkid in bkids]]
        return self.renderTable(lines=blocks)
        
        
    def blocksMapped(self, bkids):
        return ("<ul>" + ("".join([f'<li><a href="/block/{bkid}">{bkid}</a></li>' for bkid in bkids])) + "</ul>")

    def AccountCard(self, address):
        acctObject = self.puller.loadAccount(address)
        return f"""
            <h3 class="cardTitle">Account {address}</h3>
			<div class="cardContainer">
				<div>Balance : {acctObject.balance / (10**18)} {self.ticker}</div>
				<div>Nonce : {acctObject.nonce}</div>
				<h4>Transaction history</h4>
				{self.txsMapped(list(reversed(acctObject.transactions[1:])))}
			</div>
        """
        
    def TokenCard(self, address):
        tokenObject = self.puller.loadToken(address)
        return f"""
            <h3 class="cardTitle">{tokenObject.name} ({tokenObject.symbol})</h3>
			<div class="cardContainer">
				<div>Total supply : {tokenObject.totalSupply} {tokenObject.symbol}</div>
			</div>
        """
        
    def icon(self, imgurl, size):
        return f"""<img src="{imgurl}" height="{size}" width="{size}"></img>"""
        
    def SwapPairCard(self, _pair):
        icon0 = TOKENICONURLS.get(_pair.token0)
        icon1 = TOKENICONURLS.get(_pair.token1)
        return f"""
            <div class="dexPair">
                <font size="6">{_pair.ticker0}/{_pair.ticker1}</font>{self.icon(icon0, 25)}{self.icon(icon1, 25)}
                <div>{_pair.reserve0formatted} {self.icon(icon0, 18)}</div>
                <div>{_pair.reserve1formatted} {self.icon(icon1, 18)}</div>
            </div>
        """
        
    def RaptorSwapCard(self):
        _cards = "".join([self.SwapPairCard(p) for p in self.puller.defi.raptorswap.pairs])
        return f"""
			<div class="cardContainer">
                <h2>RaptorSwap</h2>
                {_cards}
            </div>
        """
        
    def DeFiCard(self):
        return f"""
            <h1 class="cardTitle">RaptorChain DeFi Dashboard</h1>
            {self.RaptorSwapCard()}
        """
        
        
    def getNavBar(self):
        return f"""
            <nav>
				<div>
					<a class="rptrLogo" href="/"><img src="https://raptorchain.io/images/logo.png" width=55 height=55></img></a>
					<input style="height: 59; width: 300" id="searchInput"></input><button style="height: 59; width: 100" onclick="handleSearch()">Search</button>
					<span style="width: 50%; float: right;">{self.networkStatsCard()}</span>
				</div>
            </nav>
        """

    def homepageCard(self):
        return f"""
			<font class="cardTitle" size=10>RaptorChain {'Testnet' if self.testnet else 'Mainnet'} Explorer</font>
            <div class="cardContainer">
                <font size=6>Last 10 transactions</font>
                <div id="txsContainerHomepage">
                    {self.txsMapped(list(reversed([_tx.txid for _tx in self.puller.getLastNTxs(10)])))}
                </div>
                <font size=6>Last 10 blocks</font>
                <div id="blocksContainerHomepage">
                    {self.blocksTable(list(reversed([height for height in self.puller.loadStats().blocks])))}
                </div>
				<script src="/homePageScripts.js"></script>
            </div>
        """


    def networkStatsCard(self):
        stats = self.puller.loadStats()
        burned = self.puller.loadAccount(self.burnAddress).balance
        return f"""
			<div class="networkStats">
				<div>

					<div>{self.ticker} on mainnet : {self.formatAmount(stats.supply)} {self.ticker}</div>
					<div>Total gas burned &#x1f525; : {self.formatAmount(burned)} {self.ticker}</div>
					<div>Holders : {stats.holders}</div>
					<div>Chain length : {stats.chainLength}</div>
				</div>
			</div>
			<div class="networkStats" style="margin-right: 3px">
				<div>
					<div><font size=6><a href="/defi">Raptor DeFi</a></font></div>
					<div>Raptor Price : <a href="https://www.dextools.io/app/bnb/pair-explorer/0x75d2d2abd51b725e3d80238276bd80c65d1674d7">{round(self.puller.defi.price, 7)}$</a></div>
					<div>TVL : {int(self.puller.defi.tvl)} RPTR</div>
				</div>
			</div>
        """

    def pageScripts(self):
        return """
            function getSearchUrl(_search) {
                if (_search.length == 42) {
                    return `/address/${_search}`;
                }
                return `/tx/${_search}`;
            }
			
			class RaptorChainInterface {
				// class Transaction {
					// constructor(txjson) {
						// this.txdata = JSON.parse(txjson);
						// this.type = this.txdata.type;
						// if (this.type == 0) {
							// this.sender = this.txdata.from;
							// this.recipient = this.txdata.to;
							// this.value = txdata.tokens;
						// }
						// else if this.type == 1 {
							// this.sender = this.txdata.from;
							// this.recipient = this.txdata.to;
							// this.value = txdata.tokens;
						// }
					// }
				// }
				
				constructor(nodeaddr) {
					this.node = nodeaddr;
				}
				
				async fetchJSON(url) {
					return (await (await fetch(url))).json();
				}
				
				async getBlock(bkid) {
					if (bkid.length == 66) {
						return (await this.fetchJSON(`${this.node}/chain/blockByHash/${bkid}`)).result;
					}
					if (bkid.length == 64) {
						return (await this.fetchJSON(`${this.node}/chain/blockByHash/0x${bkid}`)).result;
					}
					if (Number.isInteger(Number(bkid)) && Number(bkid) >= 0) {
						return (await this.fetchJSON(`${this.node}/chain/block/${bkid}`)).result;
					}
				}
				
				async getChainLength() {
					return (await this.fetchJSON(`${this.node}/chain/length`)).result;
				}
				
				async getRawTransaction(txid) {
					return (await this.fetchJSON(`${this.node}/get/transactions/${txid}`)).result[0];
				}
				
				async getAccount(address) {
					return (await this.fetchJSON(`${this.node}/accounts/accountInfo/${address}`));
				}
				
				async getNLastBlocks(N) {
					let _chainlength = (await this.getChainLength());
					let blocks = [];
					for (let n=_chainlength-1; n>=Math.max(_chainlength-N, 0); n--) {
						blocks.push(await this.getBlock(n));
					}
					return blocks;
				}
				
				async systemRoot() {
					return (await (await fetch(`https://${this.node}/chain/getlastblock`)).json()).result.txsRoot;
				}
			}
            
            function handleSearch() {
                _search = document.getElementById("searchInput").value;
                _url = getSearchUrl(_search);
				window.location.replace(_url);
//                open(_url);
            }
			
			class Rendering {
				constructor(puller) {
					this.puller = puller;
				}
				
				leftPadding(num, paddingValue) {
					let strnum = String(num);
					return (("0").repeat(paddingValue - strnum.length) + strnum)
				}
				
				formatTimestamp(inSeconds) {
					const dte = (new Date(inSeconds*1000));
					let time = `${dte.getHours()}:${this.leftPadding(dte.getMinutes(), 2)}:${this.leftPadding(dte.getSeconds(),2)}`;
					let date = `${this.leftPadding(dte.getDate())}/${this.leftPadding(dte.getMonth() + 1, 2)}/${dte.getFullYear()}`;
					return [time,date]
				}
				
				renderTable(lines) {
					let fmtLines = [];
					for (let n=0; n<lines.length; n++) {
						let fmtItems = [];
						for (let o=0; o<lines[n].length; o++) {
							fmtItems.push(`<td>${lines[n][o]}</td>`);
						}
						fmtLines.push("<tr>" + (fmtItems.join("")) + "</tr>")
					}
					return `<table><tbody>${fmtLines.join("")}</tbody></table>`
				}
			
				renderBlockList(blocks) {
					let _fmtList = [["Height", "Hash", "Time", "Date", "Miner"]];
					for (let n=0; n<blocks.length; n++) {
						let bk = blocks[n];
						let [_time, _date] = this.formatTimestamp(bk.timestamp);
						_fmtList.push([`<a href="/block/${bk.height}">${bk.height}</a>`, `<a href="/block/${bk.miningData.proof}">${bk.miningData.proof}</a>`, _time, _date, `<a href="/address/${bk.miningData.miner}">${bk.miningData.miner}</a>`]);
					}
					return this.renderTable(_fmtList);
				}
			}
        """
		
    def initScripts(self):
        return f"""
            // HAS TO BE LOADED AFTER PAGE SCRIPTS
			chain = new RaptorChainInterface("{self.publicNode}");
			rendering = new Rendering(chain);
			// BUT BEFORE PAGE-SPECIFIC SCRIPTS
        """

    def homePageScripts(self):
        return """
			async function refreshBlocks() {
				document.getElementById("blocksContainerHomepage").innerHTML = rendering.renderBlockList(await chain.getNLastBlocks(10));
			}
			refreshBlocks();
        """
		
		
    def pageTemplate(self, subtemplate, pageTitle="RaptorChain Explorer"):
        self.puller.refresh()
        return f"""
            <html>
				<head>
					<title>{pageTitle}</title>
                    <script src="/pageScripts.js"></script>
                    <script src="/initScripts.js"></script>
					<link rel="stylesheet" href="/style.css">
					<link rel="icon" href="https://raptorchain.io/images/logo32px.png"></link>
				</head>
                <body>
					<div style="float: none">
						{self.getNavBar()}
					</div>
                    <div style="height: 2%"></div>
					<!-- <div style="border: solid; width: 39%; display: inline-block; padding-left: 1%"> -->
						<!-- {self.networkStatsCard()} -->
					<!-- </div> -->
                    <div class="pageContainer">
                        <div style="width: 1%; height: 1;"></div>
                        <div style="width: 2%; height: 1;"></div>
                        <div style="display: inline-block;">
							<div>
								{subtemplate}
							</div>
                        </div>
                    </div>
                </body>
				<footer>
                    <div>
                        <i>Made with &#x2764;&#xFE0F; and &#9749; by <a href="https://github.com/ygboucherk">Yanis</a> from <a href="https://raptorchain.io">RaptorChain</a></i>
                    </div>
				</footer>
            </html>
        """
        
app = flask.Flask(__name__)
app.config["DEBUG"] = False
CORS(app)
explorer = RaptorChainExplorer()

@app.route("/pageScripts.js")
def getPageScripts():
    return explorer.pageScripts()

@app.route("/searchScripts.js")
def getSearchScripts():
    return explorer.pageScripts()

@app.route("/initScripts.js")
def getInitScripts():
    return explorer.initScripts()

@app.route("/homePageScripts.js")
def getHomePageScripts():
    return explorer.homePageScripts()


@app.route("/style.css")
def getStyleSheets():
    return explorer.styleSheets()

@app.route("/block/<bkid>")
def block(bkid):
    return explorer.pageTemplate(explorer.BlockCard(bkid), f"RaptorChain block {bkid}")

@app.route("/tx/<txid>")
def tx(txid):
    return explorer.pageTemplate(explorer.TransactionCard(txid), f"RaptorChain transaction {txid}")
    
@app.route("/address/<addr>")
def address(addr):
    return explorer.pageTemplate(explorer.AccountCard(addr), f"RaptorChain address {addr}")

@app.route("/token/<addr>")
def token(addr):
    return explorer.pageTemplate(explorer.TokenCard(addr), f"RaptorChain address {addr}")

@app.route("/defi")
def defi():
    return explorer.pageTemplate(explorer.DeFiCard())


@app.route("/")
def homepage():
    return explorer.pageTemplate(explorer.homepageCard())

def getApp():
    return app

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=explorer.port)