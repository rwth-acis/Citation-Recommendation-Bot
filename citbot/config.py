import configparser
import argparse


parser = argparse.ArgumentParser()
parser.add_argument("--k", type=int, help="number of recommended papers")
parser.add_argument("--server_address", help="MongoDB's server address")
args = parser.parse_args()

config = configparser.ConfigParser()
config["DEFAULT"] = {"k" :args.k, "server_address": args.server_address}

f = open("config.ini", mode="w", encoding="utf-8")
config.write(f)
f.flush()
f.close()