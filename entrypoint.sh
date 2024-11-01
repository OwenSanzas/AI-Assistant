#!/bin/bash

ollama serve &

sleep 5

python -m uvicorn main:app --host 0.0.0.0 --port $PORT

wait