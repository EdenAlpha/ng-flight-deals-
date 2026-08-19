#!/usr/bin/env python3
from __future__ import annotations
import argparse
import migrated_volume_full_replay_loso_v1 as fr
import migrated_volume_multisource15_replay_loso_v1 as base

fr.CHUNK = 1024

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',required=True)
    p.add_argument('--eps',required=True)
    p.add_argument('--out',required=True)
    base.main(p.parse_args())
