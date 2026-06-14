#!/bin/bash
exec python -m uvicorn main:app --host 0.0.0.0 --port 8082 --loop uvloop --workers 1