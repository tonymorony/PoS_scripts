from slickrpc import Proxy
import time
import sys
import datetime
import calendar
import time

def print_balance(rpc_connection_source, rpc_connection_destination):
    balance_source = rpc_connection_source.getbalance()
    balance_destination = rpc_connection_destination.getbalance()
    source_chain_name = rpc_connection_source.getinfo()["name"]
    destination_chain_name = rpc_connection_destination.getinfo()["name"]
    print("Source chain " + source_chain_name + " balance: " + str(balance_source))
    print("Destination chain " + destination_chain_name + " balance: " + str(balance_destination))


def create_import_transactions(rpc_connection, signed_hex, payouts, import_tx_list):
    while True:
        try:
            import_tx = rpc_connection.migrate_createimporttransaction(signed_hex["hex"], payouts)
        except Exception as e:
            print(e)
            print("Import transaction not created yet, waiting for 10 seconds more")
            time.sleep(10)
            pass
        else:
            print("Seems tx created")
            is_created = True
            import_tx_list.append(import_tx)
            break
    return is_created


def migrate_import_transactions(rpc_connection, import_tx, complete_tx_list):
    while True:
        try:
            complete_tx = rpc_connection.migrate_completeimporttransaction(import_tx)
        except Exception as e:
            print(e)
            print("Import transaction on KMD not created yet, waiting for 10 seconds more")
            time.sleep(10)
            pass
        else:
            print("Seems tx created")
            is_imported = True
            complete_tx_list.append(complete_tx)
            break
    return is_imported


def broadcast_on_destinationchain(rpc_connection, complete_tx, dest_tx_list):
    attempts = 0
    while True:
        if attempts < 60:
            try:
                sent_itx = rpc_connection.sendrawtransaction(complete_tx)
            except Exception:
                attempts = attempts + 1
                print("Tried to broadcast " + str(attempts) + " times")
                print("Will try to do it up to 60 times in total. Now rest for 15 seconds.")
                time.sleep(15)
            else:
                print("Transactinon broadcasted on destination chain")
                dest_tx_list.append(sent_itx)
                is_broadcasted = True
                break
        else:
            print("Too many attempts. Bye bye.")
            sys.exit()
    return is_broadcasted


# SET RPC CONNECTION DETAILS HERE
rpc_connection_sourcechain = Proxy("http://%s:%s@127.0.0.1:%d"%("user1531394351", "pass24e95276e008e3f6176b672631a89beef6959ce9dae44f8bdb7a92e5ca41e56c77", 30667))
rpc_connection_destinationchain = Proxy("http://%s:%s@127.0.0.1:%d"%("user2491106895", "pass253372aea1796039438e3e3c240a39cec6f9aa11cff7bc3d3c29ab93c0e985d73e", 50609))
rpc_connection_kmdblockchain = Proxy("http://%s:%s@127.0.0.1:%d"%("tony", "156ewr", 7771))
# SET ADDRESS AND MIGRATION AMOUNT HERE
address = "RSbcG63XbgfAwmFmPA362d4zqLb31hJiyt"
amount = 2
migrations_amount = 500

# preparing UTXOs if there is not enough
utxos_sourcechain = len(rpc_connection_sourcechain.listunspent())
utxos_destinationchain = len(rpc_connection_destinationchain.listunspent())

print(str(utxos_sourcechain) + " source chain UTXOs\n")
print(str(utxos_destinationchain) + " destination chain UTXOs\n")

while True:
    start_utxo_maker = input("Do you want to make more UTXOs? y/n: ")
    if start_utxo_maker == "y":
        utxos_amount = int(input("Input amount of UTXOs you want to make: "))
        amount_for_utxo = 0.1
        while utxos_amount > 0:
            source_utxo = rpc_connection_sourcechain.sendtoaddress(address, amount_for_utxo)
            destination_utxo = rpc_connection_destinationchain.sendtoaddress(address, amount_for_utxo)
            time.sleep(0.1)
            utxos_amount = utxos_amount - 1
            amount_for_utxo = amount_for_utxo + 0.11
        while True:
            confirmations_source = int(rpc_connection_sourcechain.gettransaction(source_utxo)["confirmations"])
            confirmations_destination = int(rpc_connection_destinationchain.gettransaction(destination_utxo)["confirmations"])
            if confirmations_source > 0 and confirmations_destination > 0:
                print("Seems more UTXOs created")
                utxos_sourcechain = len(rpc_connection_sourcechain.listunspent())
                utxos_destinationchain = len(rpc_connection_destinationchain.listunspent())
                print(str(utxos_sourcechain) + " source chain UTXOs\n")
                print(str(utxos_destinationchain) + " destination chain UTXOs\n")
                break
            else:
                print("Let's wait more...")
                time.sleep(15)
    elif start_utxo_maker == "n":
        break
    else:
        print("Input y or n\n")

t0 = time.time()

print_balance(rpc_connection_sourcechain, rpc_connection_destinationchain)

print("Sending " + str(amount) + " coins from " + rpc_connection_sourcechain.getinfo()["name"] + " chain " +\
      "to " + rpc_connection_destinationchain.getinfo()["name"] + " chain")

counter_raw = migrations_amount
sent_tx_list = []
payouts_list = []
signed_hex_list = []
while counter_raw > 0:
    raw_transaction = rpc_connection_sourcechain.createrawtransaction([], {address: amount})
    export_data = rpc_connection_sourcechain.migrate_converttoexport(raw_transaction, rpc_connection_destinationchain.getinfo()["name"])
    export_raw = export_data["exportTx"]
    export_funded_data = rpc_connection_sourcechain.fundrawtransaction(export_raw)
    export_funded_transaction = export_funded_data["hex"]
    payouts = export_data["payouts"]
    payouts_list.append(payouts)
    signed_hex = rpc_connection_sourcechain.signrawtransaction(export_funded_transaction)
    signed_hex_list.append(signed_hex)
    sent_tx = rpc_connection_sourcechain.sendrawtransaction(signed_hex["hex"])
    if len(sent_tx) != 64:
        print(signed_hex)
        print(sent_tx)
        print("Export TX not successfully created")
        sys.exit()
    sent_tx_list.append(sent_tx)
    counter_raw = counter_raw - 1

payouts_filename = "payouts_"+str(calendar.timegm(time.gmtime()))+".txt"
with open(payouts_filename, "a+") as payouts_file:
    payouts_file.writelines(payouts_list)

export_filename = "export_transactions_"+str(calendar.timegm(time.gmtime()))+".txt"
with open(export_filename, "a+") as export_transactions_file:
    export_transactions_file.writelines(sent_tx_list)

print("Payouts saved to: " + payouts_filename + "\n")
print("Export txids saved to: " + export_filename + "\n")

print(str(len(sent_tx_list)) + " export transactions sent:\n")
for sent_tx in sent_tx_list:
    print(sent_tx + "\n")


# Wait for a confirmation on source chain
while True:
    confirmed = all(int(rpc_connection_sourcechain.gettransaction(sent_tx)["confirmations"]) > 0 for sent_tx in sent_tx_list)
    if not confirmed:
        print("Waiting for all export transactions to be confirmed on source chain")
        time.sleep(5)
    else:
        print("All export transactions confirmed!")
        break

# Use migrate_createimporttransaction to create the import TX
import_list = []
while True:
    import_tx_created = all(create_import_transactions(rpc_connection_sourcechain, signed_hex, payouts, import_list) for signed_hex, payouts in zip(signed_hex_list, payouts_list))
    if not import_tx_created:
        print("Waiting for all import transactions to be created on source chain")
    else:
        print("All import transactions created!")
        break

# Use migrate_completeimporttransaction on KMD to complete the import tx
complete_list = []
while True:
    migration_complete = all(migrate_import_transactions(rpc_connection_kmdblockchain, import_tx, complete_list) for import_tx in import_list)
    if not migration_complete:
        print("Waiting for all migrations to be completed on Komodo blockchain")
    else:
        print("All migrations are completed on Komodo blockchain")
        break

# Broadcast tx to target chain
dest_txs = []
while True:
    broadcasted_on_target = all(broadcast_on_destinationchain(rpc_connection_destinationchain, complete_tx, dest_txs) for complete_tx in complete_list)
    if not broadcasted_on_target:
        print("Waiting for imports to be broadcasted on destination chain")
    else:
        print("All imports are broadcasted to destination chain")
        break

# Wait for a confirmation on destination chain
while True:
    try:
        confirmed = all(int(rpc_connection_destinationchain.getrawtransaction(dest_tx, 1)["confirmations"]) > 0 for dest_tx in dest_txs)
    except Exception as e:
        print(e)
        print("Transaction is not on blockchain yet. Let's wait a little.")
        time.sleep(10)
        pass
    else:
        if not confirmed:
            print("Waiting for all export transactions to be confirmed on source chain")
            time.sleep(5)
        else:
            print("All export transactions confirmed!")
            break

for sent_itx in dest_txs:
    print(rpc_connection_destinationchain.getinfo()["name"] + " : Confirmed import " + sent_itx + "  at: " + str(datetime.datetime.today().strftime('%Y-%m-%d-%M:%S')))

t1 = time.time()
print("Total migrations amount: " + str(migrations_amount))
print(str(t1-t0) + " migration time (sec)")