# Shared

This folder contains **shared contracts and canonical demo data**.

## Purpose

This is the handshake between backend and frontend.

Keep here:
- `contracts/` — request/response shapes, JSON examples, schema notes
- `demo-data/` — sample cases, expected outputs, golden-path demo fixtures

## Rule

Backend and frontend should both depend on the shapes defined here.
This reduces drift while the disease and referral lane is still being narrowed.
