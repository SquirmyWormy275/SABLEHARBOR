"""Reuse accepted runtime, operating and industrial builders in a separate successor."""
import argparse
from enterprise.runtime.build_finance import build

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-working-tree', action='store_true')
    args = parser.parse_args()
    build(args.allow_working_tree, company_closeout=True)
