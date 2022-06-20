import requests, rlp, flask, json, time
from rlp.sedes import Binary, big_endian_int, binary
from flask_cors import CORS
from dataclasses import asdict, dataclass
from typing import Optional
from eth_utils import keccak
from web3.auto import w3

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
    
    def __init__(self, node):
        self.node = node
    
    def loadBlock(self, blockid):
        _url = f"{self.node}/chain/block/{blockid}" if ((type(blockid) == int) or (blockid.isnumeric())) else f"{self.node}/chain/blockByHash/{blockid}" # depends if we load it by height or hash
        print(_url)
        _raw = requests.get(_url).json().get("result", {})
        return self.Block(_raw)
        
    
    def loadTransaction(self, txid):
        _raw = requests.get(f"{self.node}/get/transactions/{txid}").json().get("result")[0]
        return self.Transaction(_raw)
        
    def loadBatchOfTransactions(self, txids):
        formattedTxids = ",".join(txids)
        _raws = requests.get(f"{self.node}/get/transactions/{formattedTxids}").json().get("result")
        return [self.Transaction(_raw) for _raw in _raws]
    
    def loadAccount(self, address):
        _raw = requests.get(f"{self.node}/accounts/accountInfo/{address}").json().get("result")
        return self.Account(_raw)
        
    def getLastNTxs(self, n):
        _raw = requests.get(f"{self.node}/get/nLastTxs/{n}").json().get("result")
        return [self.Transaction(_rawtx) for _rawtx in _raw]
        
        
    def loadStats(self):
        _raw = requests.get(f"{self.node}/stats").json().get("result")
        return self.Stats(_raw)
        
class RaptorChainExplorer(object):
    def __init__(self):
        self.puller = RaptorChainPuller("https://rpc-testnet.raptorchain.io/")
        self.ticker = "tRPTR"
        self.decimals = 18

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
            table {
                border: 1px solid #333;
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
        """


    
    def TransactionCard(self, txid):
        txObject = self.puller.loadTransaction(txid)
        return f"""
            <h3>Transaction {txid}</h3>
            <div style="border: solid; padding-left: 1%">
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
            <h3>{f"Beacon block {block.height}" if block.height else "Genesis Block"}</h3>
            <div style="border: solid; padding-left: 1%">
                <div>
                    <div>Miner/staker : <a href="/address/{block.miner}">{block.miner}</a></div>
					<div>Hash : {block.proof}</div>
                    <h4>Transactions</h4>
                        {self.txsMapped(list(reversed(block.transactions)))}
                </div>
            </div>
        """

    def showTransaction(self, tx):
        return f"""
            <div>
                
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
            <h3>Account {address}</h3>
			<div>
				Balance : {acctObject.balance / (10**18)} {self.ticker}
			</div>
			<div style="border: solid; padding-left: 1%">
				<h4>Transaction history</h4>
				{self.txsMapped(list(reversed(acctObject.transactions[1:])))}
			</div>
        """
        
    def getNavBar(self):
        return f"""
            <nav>
				<div>
					<a href="/"><img src="https://raptorchain.io/images/logo.png" width=40 height=40></img></a>
					<input style="height: 45" id="searchInput"></input><button style="height: 45" onclick="handleSearch()">Search</button>
					<span style="width: 30%; padding-right: 1%; float: right;"><div style="border: solid; padding-left: 1%">{self.networkStatsCard()}</div></span>
				</div>
            </nav>
        """

    def homepageCard(self):
        return f"""
			<font size=10>RaptorChain Explorer</font>
            <div style="border: solid; padding-left: 1%;">
                <font size=6>Last 10 transactions</font>
                <div>
                    {self.txsMapped(list(reversed([_tx.txid for _tx in self.puller.getLastNTxs(10)])))}
                </div>
                <font size=6>Last 10 blocks</font>
                <div>
                    {self.blocksTable(list(reversed([height for height in self.puller.loadStats().blocks])))}
                </div>
            </div>
        """

    def networkStatsCard(self):
        stats = self.puller.loadStats()
        return f"""
            <div>
                <div><font size=6>Stats</font></div>
                <div>Coin supply : {self.formatAmount(stats.supply)} {self.ticker}</div>
                <div>Holders : {stats.holders}</div>
                <div>Chain length : {stats.chainLength}</div>
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
            
            function handleSearch() {
                _search = document.getElementById("searchInput").value;
                _url = getSearchUrl(_search);
				window.location.replace(_url);
//                open(_url);
            }
            
            async function systemRoot() {
				return (await (await fetch("https://rpc-testnet.raptorchain.io/chain/getlastblock")).json()).result.txsRoot
			}
			
        """
		
    def pageTemplate(self, subtemplate, pageTitle="RaptorChain Explorer"):
        return f"""
            <html>
				<head>
					<title>{pageTitle}</title>
                    <script src="/searchScripts.js"></script>
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
                    <div>
                        <div style="width: 1%; height: 1;"></div>
                        <div style="width: 2%; height: 1;"></div>
                        <div style="width: 95%; display: inline-block;">
							<div>
								{subtemplate}
							</div>
                        </div>
                    </div>
                </body>
				<footer>
					<i>Made with &#x2764;&#xFE0F; and &#9749; by <a href="https://github.com/ygboucherk">Yanis</a> from <a href="https://raptorchain.io">RaptorChain</a></i>
				</footer>
            </html>
        """
        
app = flask.Flask(__name__)
app.config["DEBUG"] = False
CORS(app)
explorer = RaptorChainExplorer()

@app.route("/pageScripts.js")
def getSearchScripts():
    return explorer.pageScripts()

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

@app.route("/")
def homepage():
    return explorer.pageTemplate(explorer.homepageCard())

def getApp():
    return app

if __name__ == "__main__":
    app.run(host="0.0.0.0")